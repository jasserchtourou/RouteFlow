"""CLI: `uv run python -m app.seed [--reset] [--seed N]`."""

import argparse
import asyncio

from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.seed.runner import DatabaseNotEmptyError, seed_database


async def main(reset: bool, seed: int) -> int:
    engine = create_engine(get_settings())
    try:
        async with create_session_factory(engine)() as session:
            data = await seed_database(session, reset=reset, seed=seed)
    except DatabaseNotEmptyError as error:
        print(error)
        return 1
    finally:
        await engine.dispose()

    print(
        f"Seeded {len(data.warehouses)} warehouses, {len(data.inventory)} inventory items, "
        f"{len(data.docks)} docks, {len(data.equipment)} equipment, "
        f"{len(data.orders)} orders, {len(data.shipments)} shipments, {len(data.events)} tracking "
        f"events, {len(data.exceptions)} exceptions, {len(data.routes)} routes, "
        f"{len(data.vehicles)} vehicles, {len(data.drivers)} drivers."
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the RouteFlow database.")
    parser.add_argument("--reset", action="store_true", help="delete existing data first")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.reset, args.seed)))
