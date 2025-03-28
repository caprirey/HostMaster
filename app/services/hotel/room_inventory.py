# app/services/hotel/room_inventory.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sqlalchemy_models import UserTable, Room, Accommodation, RoomInventory as RoomInventorySQL
from app.models.pydantic_models import RoomInventory as RoomInventoryPydantic, RoomInventoryCreate, RoomInventoryUpdate
from sqlalchemy import and_
from typing import List

async def create_room_inventory(
        db: AsyncSession,
        inventory_data: RoomInventoryCreate,
        username: str
) -> RoomInventoryPydantic:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Room).where(Room.id == inventory_data.room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    result = await db.execute(
        select(Accommodation).where(Accommodation.id == room.accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if user.role != "admin" and accommodation.created_by != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the accommodation creator can manage room inventory"
        )

    result = await db.execute(
        select(RoomInventorySQL).where(
            and_(
                RoomInventorySQL.room_id == inventory_data.room_id,
                RoomInventorySQL.product_name == inventory_data.product_name
            )
        )
    )
    existing_item = result.scalar_one_or_none()
    if existing_item:
        raise HTTPException(status_code=400, detail="This product already exists in the room inventory")

    db_inventory = RoomInventorySQL(
        room_id=inventory_data.room_id,
        product_name=inventory_data.product_name,
        quantity=inventory_data.quantity,
        min_quantity=inventory_data.min_quantity,
        needs_restock=inventory_data.quantity < inventory_data.min_quantity
    )
    db.add(db_inventory)
    await db.commit()
    await db.refresh(db_inventory)
    return RoomInventoryPydantic.model_validate(db_inventory)

async def get_room_inventory_by_room(db: AsyncSession, room_id: int) -> List[RoomInventoryPydantic]:
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    result = await db.execute(
        select(RoomInventorySQL).where(RoomInventorySQL.room_id == room_id)
    )
    inventory_items = result.scalars().all()
    return [RoomInventoryPydantic.model_validate(item) for item in inventory_items]

async def get_room_inventory(db: AsyncSession, inventory_id: int) -> RoomInventoryPydantic:
    result = await db.execute(
        select(RoomInventorySQL).where(RoomInventorySQL.id == inventory_id)
    )
    inventory = result.scalar_one_or_none()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return RoomInventoryPydantic.model_validate(inventory)

async def update_room_inventory(
        db: AsyncSession,
        inventory_id: int,
        inventory_data: RoomInventoryUpdate,
        username: str
) -> RoomInventoryPydantic:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(RoomInventorySQL).where(RoomInventorySQL.id == inventory_id)
    )
    db_inventory = result.scalar_one_or_none()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    result = await db.execute(
        select(Room).where(Room.id == db_inventory.room_id)
    )
    room = result.scalar_one_or_none()
    result = await db.execute(
        select(Accommodation).where(Accommodation.id == room.accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if user.role != "admin" and accommodation.created_by != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the accommodation creator can manage room inventory"
        )

    update_data = inventory_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_inventory, key, value)

    if "quantity" in update_data or "min_quantity" in update_data:
        db_inventory.needs_restock = db_inventory.quantity < db_inventory.min_quantity

    await db.commit()
    await db.refresh(db_inventory)
    return RoomInventoryPydantic.model_validate(db_inventory)

async def delete_room_inventory(db: AsyncSession, inventory_id: int, username: str) -> None:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(RoomInventorySQL).where(RoomInventorySQL.id == inventory_id)
    )
    db_inventory = result.scalar_one_or_none()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    result = await db.execute(
        select(Room).where(Room.id == db_inventory.room_id)
    )
    room = result.scalar_one_or_none()
    result = await db.execute(
        select(Accommodation).where(Accommodation.id == room.accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if user.role != "admin" and accommodation.created_by != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the accommodation creator can manage room inventory"
        )

    await db.delete(db_inventory)
    await db.commit()