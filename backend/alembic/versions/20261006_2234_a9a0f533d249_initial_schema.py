"""initial schema

Revision ID: a9a0f533d249
Revises:
Create Date: 2026-10-06 22:34:43.647475

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9a0f533d249"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "drivers",
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("license_number", sa.String(length=32), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "AVAILABLE",
                "ON_DUTY",
                "OFF_DUTY",
                name="driver_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('AVAILABLE', 'ON_DUTY', 'OFF_DUTY')", name=op.f("ck_drivers_status_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_drivers")),
        sa.UniqueConstraint("license_number", name=op.f("uq_drivers_license_number")),
    )
    op.create_table(
        "orders",
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("origin", sa.String(length=80), nullable=False),
        sa.Column("destination", sa.String(length=80), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "CONFIRMED",
                "PROCESSING",
                "SHIPPED",
                "DELIVERED",
                "CANCELLED",
                name="order_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "LOW",
                "NORMAL",
                "HIGH",
                "URGENT",
                name="order_priority",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("promised_delivery_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')", name=op.f("ck_orders_priority_valid")
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED')",
            name=op.f("ck_orders_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("order_number", name=op.f("uq_orders_order_number")),
    )
    op.create_index("ix_orders_created_at", "orders", ["created_at"], unique=False)
    op.create_index("ix_orders_destination", "orders", ["destination"], unique=False)
    op.create_index(
        "ix_orders_promised_delivery_at", "orders", ["promised_delivery_at"], unique=False
    )
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)
    op.create_table(
        "routes",
        sa.Column("route_number", sa.String(length=16), nullable=False),
        sa.Column("origin", sa.String(length=80), nullable=False),
        sa.Column("destination", sa.String(length=80), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PLANNED",
                "ACTIVE",
                "DELAYED",
                "COMPLETED",
                "CANCELLED",
                name="route_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "risk_level",
            sa.Enum(
                "LOW", "MEDIUM", "HIGH", "CRITICAL", name="risk_level", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_routes_risk_level_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('PLANNED', 'ACTIVE', 'DELAYED', 'COMPLETED', 'CANCELLED')",
            name=op.f("ck_routes_status_valid"),
        ),
        sa.CheckConstraint("distance_km > 0", name=op.f("ck_routes_distance_positive")),
        sa.CheckConstraint(
            "estimated_duration_minutes > 0", name=op.f("ck_routes_duration_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routes")),
        sa.UniqueConstraint("route_number", name=op.f("uq_routes_route_number")),
    )
    op.create_index("ix_routes_risk_level", "routes", ["risk_level"], unique=False)
    op.create_index("ix_routes_status", "routes", ["status"], unique=False)
    op.create_table(
        "warehouses",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("location", sa.String(length=80), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("current_utilization", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "OPERATIONAL",
                "CONGESTED",
                "DISRUPTED",
                "OFFLINE",
                name="warehouse_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('OPERATIONAL', 'CONGESTED', 'DISRUPTED', 'OFFLINE')",
            name=op.f("ck_warehouses_status_valid"),
        ),
        sa.CheckConstraint("capacity > 0", name=op.f("ck_warehouses_capacity_positive")),
        sa.CheckConstraint(
            "current_utilization >= 0 AND current_utilization <= capacity",
            name=op.f("ck_warehouses_utilization_within_capacity"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_warehouses")),
        sa.UniqueConstraint("code", name=op.f("uq_warehouses_code")),
    )
    op.create_index("ix_warehouses_location", "warehouses", ["location"], unique=False)
    op.create_index("ix_warehouses_status", "warehouses", ["status"], unique=False)
    op.create_table(
        "inventory_items",
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=32), nullable=False),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reserved_quantity", sa.Integer(), nullable=False),
        sa.Column("reorder_threshold", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity >= 0", name=op.f("ck_inventory_items_quantity_non_negative")),
        sa.CheckConstraint(
            "reorder_threshold >= 0", name=op.f("ck_inventory_items_threshold_non_negative")
        ),
        sa.CheckConstraint(
            "reserved_quantity <= quantity",
            name=op.f("ck_inventory_items_reserved_within_quantity"),
        ),
        sa.CheckConstraint(
            "reserved_quantity >= 0", name=op.f("ck_inventory_items_reserved_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name=op.f("fk_inventory_items_warehouse_id_warehouses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_items")),
        sa.UniqueConstraint("warehouse_id", "sku", name="uq_inventory_items_warehouse_sku"),
    )
    op.create_index("ix_inventory_items_sku", "inventory_items", ["sku"], unique=False)
    op.create_table(
        "vehicles",
        sa.Column("registration", sa.String(length=24), nullable=False),
        sa.Column(
            "vehicle_type",
            sa.Enum(
                "VAN",
                "TRUCK",
                "REFRIGERATED_TRUCK",
                "SEMI_TRAILER",
                name="vehicle_type",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "AVAILABLE",
                "IN_TRANSIT",
                "MAINTENANCE",
                "OFFLINE",
                name="vehicle_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("current_latitude", sa.Float(), nullable=True),
        sa.Column("current_longitude", sa.Float(), nullable=True),
        sa.Column("fuel_level", sa.Float(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('AVAILABLE', 'IN_TRANSIT', 'MAINTENANCE', 'OFFLINE')",
            name=op.f("ck_vehicles_status_valid"),
        ),
        sa.CheckConstraint(
            "vehicle_type IN ('VAN', 'TRUCK', 'REFRIGERATED_TRUCK', 'SEMI_TRAILER')",
            name=op.f("ck_vehicles_vehicle_type_valid"),
        ),
        sa.CheckConstraint(
            "current_latitude IS NULL OR (current_latitude BETWEEN -90 AND 90)",
            name=op.f("ck_vehicles_latitude_range"),
        ),
        sa.CheckConstraint(
            "current_longitude IS NULL OR (current_longitude BETWEEN -180 AND 180)",
            name=op.f("ck_vehicles_longitude_range"),
        ),
        sa.CheckConstraint(
            "fuel_level >= 0 AND fuel_level <= 100", name=op.f("ck_vehicles_fuel_level_percent")
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["drivers.id"],
            name=op.f("fk_vehicles_driver_id_drivers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vehicles")),
        sa.UniqueConstraint("driver_id", name=op.f("uq_vehicles_driver_id")),
        sa.UniqueConstraint("registration", name=op.f("uq_vehicles_registration")),
    )
    op.create_index("ix_vehicles_status", "vehicles", ["status"], unique=False)
    op.create_table(
        "shipments",
        sa.Column("shipment_number", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("route_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "CREATED",
                "PICKED",
                "PACKED",
                "LOADED",
                "IN_TRANSIT",
                "OUT_FOR_DELIVERY",
                "DELIVERED",
                name="shipment_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("origin", sa.String(length=80), nullable=False),
        sa.Column("destination", sa.String(length=80), nullable=False),
        sa.Column("carrier", sa.String(length=80), nullable=False),
        sa.Column("estimated_delivery", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_delivery", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "temperature_status",
            sa.Enum(
                "NOT_APPLICABLE",
                "NORMAL",
                "DEVIATION",
                name="temperature_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actual_delivery IS NULL OR status = 'DELIVERED'",
            name=op.f("ck_shipments_actual_delivery_only_when_delivered"),
        ),
        sa.CheckConstraint(
            "status IN ('CREATED', 'PICKED', 'PACKED', 'LOADED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED')",
            name=op.f("ck_shipments_status_valid"),
        ),
        sa.CheckConstraint(
            "temperature_status IN ('NOT_APPLICABLE', 'NORMAL', 'DEVIATION')",
            name=op.f("ck_shipments_temperature_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_shipments_order_id_orders"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.id"],
            name=op.f("fk_shipments_route_id_routes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name=op.f("fk_shipments_vehicle_id_vehicles"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            name=op.f("fk_shipments_warehouse_id_warehouses"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shipments")),
        sa.UniqueConstraint("shipment_number", name=op.f("uq_shipments_shipment_number")),
    )
    op.create_index("ix_shipments_destination", "shipments", ["destination"], unique=False)
    op.create_index(
        "ix_shipments_estimated_delivery", "shipments", ["estimated_delivery"], unique=False
    )
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"], unique=False)
    op.create_index("ix_shipments_route_id", "shipments", ["route_id"], unique=False)
    op.create_index("ix_shipments_status", "shipments", ["status"], unique=False)
    op.create_index("ix_shipments_vehicle_id", "shipments", ["vehicle_id"], unique=False)
    op.create_index("ix_shipments_warehouse_id", "shipments", ["warehouse_id"], unique=False)
    op.create_table(
        "shipment_exceptions",
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "DELAYED",
                "TEMPERATURE_DEVIATION",
                "DAMAGED",
                "MISSING_DOCUMENT",
                "STOCK_SHORTAGE",
                name="exception_type",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="exception_severity",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "INVESTIGATING",
                "RESOLVED",
                name="exception_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "(status = 'RESOLVED') = (resolved_at IS NOT NULL)",
            name=op.f("ck_shipment_exceptions_resolved_at_matches_status"),
        ),
        sa.CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_shipment_exceptions_severity_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'INVESTIGATING', 'RESOLVED')",
            name=op.f("ck_shipment_exceptions_status_valid"),
        ),
        sa.CheckConstraint(
            "type IN ('DELAYED', 'TEMPERATURE_DEVIATION', 'DAMAGED', 'MISSING_DOCUMENT', 'STOCK_SHORTAGE')",
            name=op.f("ck_shipment_exceptions_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name=op.f("fk_shipment_exceptions_shipment_id_shipments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shipment_exceptions")),
    )
    op.create_index(
        "ix_shipment_exceptions_shipment_id", "shipment_exceptions", ["shipment_id"], unique=False
    )
    op.create_index(
        "ix_shipment_exceptions_status_severity",
        "shipment_exceptions",
        ["status", "severity"],
        unique=False,
    )
    op.create_table(
        "tracking_events",
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "CREATED",
                "PICKED",
                "PACKED",
                "LOADED",
                "DEPARTED",
                "CHECKPOINT",
                "ARRIVED_HUB",
                "OUT_FOR_DELIVERY",
                "DELIVERED",
                "DELAY_REPORTED",
                "TEMPERATURE_ALERT",
                name="tracking_event_type",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('CREATED', 'PICKED', 'PACKED', 'LOADED', 'DEPARTED', 'CHECKPOINT', 'ARRIVED_HUB', 'OUT_FOR_DELIVERY', 'DELIVERED', 'DELAY_REPORTED', 'TEMPERATURE_ALERT')",
            name=op.f("ck_tracking_events_event_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name=op.f("fk_tracking_events_shipment_id_shipments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracking_events")),
    )
    op.create_index(
        "ix_tracking_events_occurred_at", "tracking_events", ["occurred_at"], unique=False
    )
    op.create_index(
        "ix_tracking_events_shipment_id_occurred_at",
        "tracking_events",
        ["shipment_id", "occurred_at"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_tracking_events_shipment_id_occurred_at", table_name="tracking_events")
    op.drop_index("ix_tracking_events_occurred_at", table_name="tracking_events")
    op.drop_table("tracking_events")
    op.drop_index("ix_shipment_exceptions_status_severity", table_name="shipment_exceptions")
    op.drop_index("ix_shipment_exceptions_shipment_id", table_name="shipment_exceptions")
    op.drop_table("shipment_exceptions")
    op.drop_index("ix_shipments_warehouse_id", table_name="shipments")
    op.drop_index("ix_shipments_vehicle_id", table_name="shipments")
    op.drop_index("ix_shipments_status", table_name="shipments")
    op.drop_index("ix_shipments_route_id", table_name="shipments")
    op.drop_index("ix_shipments_order_id", table_name="shipments")
    op.drop_index("ix_shipments_estimated_delivery", table_name="shipments")
    op.drop_index("ix_shipments_destination", table_name="shipments")
    op.drop_table("shipments")
    op.drop_index("ix_vehicles_status", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_inventory_items_sku", table_name="inventory_items")
    op.drop_table("inventory_items")
    op.drop_index("ix_warehouses_status", table_name="warehouses")
    op.drop_index("ix_warehouses_location", table_name="warehouses")
    op.drop_table("warehouses")
    op.drop_index("ix_routes_status", table_name="routes")
    op.drop_index("ix_routes_risk_level", table_name="routes")
    op.drop_table("routes")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_promised_delivery_at", table_name="orders")
    op.drop_index("ix_orders_destination", table_name="orders")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_table("orders")
    op.drop_table("drivers")
    # ### end Alembic commands ###
