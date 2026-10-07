from fastapi import APIRouter

from app.api.v1 import health
from app.modules.dashboard.router import router as dashboard_router
from app.modules.drivers.router import router as drivers_router
from app.modules.exceptions.router import router as exceptions_router
from app.modules.inventory.router import router as inventory_router
from app.modules.orders.router import router as orders_router
from app.modules.routes.router import router as routes_router
from app.modules.shipments.router import router as shipments_router
from app.modules.tracking.router import feed_router as events_router
from app.modules.tracking.router import router as tracking_router
from app.modules.vehicles.router import router as vehicles_router
from app.modules.warehouses.router import router as warehouses_router
from app.modules.yard.router import router as yard_router

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(warehouses_router)
api_v1_router.include_router(yard_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(shipments_router)
api_v1_router.include_router(tracking_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(exceptions_router)
api_v1_router.include_router(routes_router)
api_v1_router.include_router(vehicles_router)
api_v1_router.include_router(drivers_router)
api_v1_router.include_router(dashboard_router)
# Each domain module exposes its own router; they are registered here as they are built.
