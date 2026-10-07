"""Order use cases. Owns business rules and transaction boundaries (commit/rollback)."""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.pagination import Page
from app.modules.orders import rules
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreate, OrderListParams, OrderRead, OrderUpdate
from app.modules.shipments.models import ShipmentStatus

logger = logging.getLogger(__name__)


class OrderHasShipmentsError(ConflictError):
    code = "order_has_shipments"


# What a shipment's progress implies for its order.
_ORDER_STATUS_FOR_SHIPMENT = {
    ShipmentStatus.PICKED: OrderStatus.PROCESSING,
    ShipmentStatus.PACKED: OrderStatus.PROCESSING,
    ShipmentStatus.LOADED: OrderStatus.SHIPPED,
    ShipmentStatus.IN_TRANSIT: OrderStatus.SHIPPED,
    ShipmentStatus.OUT_FOR_DELIVERY: OrderStatus.SHIPPED,
    ShipmentStatus.DELIVERED: OrderStatus.DELIVERED,
}


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.orders = OrderRepository(session)

    async def create(self, data: OrderCreate) -> Order:
        order = Order(
            order_number=await self.orders.next_order_number(),
            status=OrderStatus.PENDING,
            **data.model_dump(),
        )
        self.orders.add(order)
        await self.session.commit()
        await self.session.refresh(order)  # load server-generated timestamps
        logger.info("Order %s created for %s", order.order_number, order.customer_name)
        return order

    async def list(self, params: OrderListParams) -> Page[OrderRead]:
        orders, total = await self.orders.list(params)
        return Page[OrderRead](
            items=[OrderRead.model_validate(order) for order in orders],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    async def get(self, order_id: uuid.UUID) -> Order:
        order = await self.orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found", details={"id": str(order_id)})
        return order

    async def get_by_number(self, order_number: str) -> Order:
        order = await self.orders.get_by_number(order_number)
        if order is None:
            raise NotFoundError(
                f"Order {order_number} not found", details={"order_number": order_number}
            )
        return order

    async def update(self, order_id: uuid.UUID, data: OrderUpdate) -> Order:
        order = await self.get(order_id)
        changes = data.changes()

        rules.ensure_editable(order.status, set(changes) - {"status"})
        if data.status is not None:
            rules.ensure_transition_allowed(order.status, data.status)
        # Validate the *resulting* order: changing only one side could still make them equal.
        origin = changes.get("origin", order.origin)
        destination = changes.get("destination", order.destination)
        if str(origin).casefold() == str(destination).casefold():
            raise rules.OrderNotEditableError("origin and destination must differ")

        for field, value in changes.items():
            setattr(order, field, value)
        await self.session.commit()
        await self.session.refresh(order)  # updated_at is set by the database
        logger.info("Order %s updated: %s", order.order_number, sorted(changes))
        return order

    async def delete(self, order_id: uuid.UUID) -> None:
        order = await self.get(order_id)
        # Read it now: a rollback (below) expires every loaded object, and touching an expired
        # attribute in async code raises MissingGreenlet.
        order_number = order.order_number
        if await self.orders.has_shipments(order.id):
            raise OrderHasShipmentsError(
                f"Order {order_number} has shipments and cannot be deleted; cancel it instead"
            )
        await self.orders.delete(order)
        try:
            await self.session.commit()
        except IntegrityError as error:
            # A shipment was created between the check and the delete (race condition);
            # the FK constraint caught it.
            await self.session.rollback()
            raise OrderHasShipmentsError(
                f"Order {order_number} has shipments and cannot be deleted"
            ) from error
        logger.info("Order %s deleted", order_number)

    async def ensure_can_follow_shipment(self, order_id: uuid.UUID) -> None:
        """Raise before any change is made if the order cannot follow its shipment."""
        order = await self.get(order_id)
        rules.advance_to(order.status, order.status)  # raises for cancelled orders

    async def follow_shipment(self, order_id: uuid.UUID, shipment_status: ShipmentStatus) -> None:
        """Move the order forward to match shipment progress. Does not commit (caller's
        transaction). DELIVERED only once every shipment of the order is delivered."""
        target = _ORDER_STATUS_FOR_SHIPMENT.get(shipment_status)
        if target is None:
            return
        order = await self.get(order_id)
        if target == OrderStatus.DELIVERED and await self.orders.has_undelivered_shipments(
            order_id
        ):
            target = OrderStatus.SHIPPED
        new_status = rules.advance_to(order.status, target)
        if new_status != order.status:
            logger.info("Order %s: %s -> %s", order.order_number, order.status, new_status)
            order.status = new_status
