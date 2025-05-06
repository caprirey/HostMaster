from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import update, delete
from app.models.sqlalchemy_models import Product as SQLAlchemyProduct
from app.models.sqlalchemy_models import Room, Accommodation as AccommodationTable, UserTable, room_product
from app.models.pydantic_models import Product as PydanticProduct, RoomProductDetails
from app.models.pydantic_models import RoomProduct, RoomProductCreate, RoomProductUpdate
from typing import List
import logging

logger = logging.getLogger(__name__)

async def create_room_product(db: AsyncSession, room_product_data: RoomProductCreate, username: str) -> RoomProduct:
    """Create a new room-product association. Restricted to admin, user, or authorized employee."""
    logger.info(f"User {username} attempting to create room-product association: room_id={room_product_data.room_id}, product_id={room_product_data.product_id}")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Verificar que la habitación exista
    result = await db.execute(
        select(Room)
        .where(Room.id == room_product_data.room_id)
        .options(selectinload(Room.accommodation).selectinload(AccommodationTable.users))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verificar que el producto exista
    result = await db.execute(select(SQLAlchemyProduct).where(SQLAlchemyProduct.id == room_product_data.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y User pueden crear asociaciones sin restricciones
    elif user.role == "employee":
        # Employee solo puede crear si está relacionado con el alojamiento
        if username not in [u.username for u in room.accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to create room-product association")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Verificar si la asociación ya existe
    result = await db.execute(
        select(room_product).where(
            (room_product.c.room_id == room_product_data.room_id) &
            (room_product.c.product_id == room_product_data.product_id)
        )
    )
    existing = result.first()
    if existing:
        raise HTTPException(status_code=400, detail="Room-product association already exists")

    # Insertar en la tabla intermedia
    stmt = room_product.insert().values(
        room_id=room_product_data.room_id,
        product_id=room_product_data.product_id,
        quantity=room_product_data.quantity,
        needs_restock=room_product_data.needs_restock
    )
    await db.execute(stmt)
    await db.commit()
    logger.info(f"Room-product association created: room_id={room_product_data.room_id}, product_id={room_product_data.product_id}")

    # Devolver el objeto creado
    return RoomProduct(
        room_id=room_product_data.room_id,
        product_id=room_product_data.product_id,
        quantity=room_product_data.quantity,
        needs_restock=room_product_data.needs_restock
    )

async def update_room_product(db: AsyncSession, room_id: int, product_id: int, room_product_update: RoomProductUpdate, username: str) -> RoomProduct:
    """Update an existing room-product association. Restricted to admin, user, or authorized employee."""
    logger.info(f"User {username} attempting to update room-product association: room_id={room_id}, product_id={product_id}")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Verificar que la habitación exista
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.accommodation).selectinload(AccommodationTable.users))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verificar que el producto exista
    result = await db.execute(select(SQLAlchemyProduct).where(SQLAlchemyProduct.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y User pueden actualizar asociaciones sin restricciones
    elif user.role == "employee":
        # Employee solo puede actualizar si está relacionado con el alojamiento
        if username not in [u.username for u in room.accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to update room-product association")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Verificar que la asociación exista
    result = await db.execute(
        select(room_product).where(
            (room_product.c.room_id == room_id) &
            (room_product.c.product_id == product_id)
        )
    )
    existing = result.first()
    if not existing:
        raise HTTPException(status_code=404, detail="Room-product association not found")

    # Actualizar los campos proporcionados
    update_data = room_product_update.model_dump(exclude_unset=True)
    if update_data:
        stmt = (
            update(room_product)
            .where(
                (room_product.c.room_id == room_id) &
                (room_product.c.product_id == product_id)
            )
            .values(**update_data)
        )
        await db.execute(stmt)
        await db.commit()
        logger.info(f"Room-product association updated: room_id={room_id}, product_id={product_id}")

    # Obtener los datos actualizados
    result = await db.execute(
        select(room_product).where(
            (room_product.c.room_id == room_id) &
            (room_product.c.product_id == product_id)
        )
    )
    updated = result.first()
    return RoomProduct(
        room_id=room_id,
        product_id=product_id,
        quantity=updated.quantity,
        needs_restock=updated.needs_restock
    )

async def get_room_products(db: AsyncSession, room_id: int, username: str) -> List[RoomProduct]:
    """Retrieve all room-product associations for a specific room. Restricted to admin, user, or authorized employee."""
    logger.info(f"User {username} attempting to get room-product associations for room {room_id}")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Verificar que la habitación exista
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.accommodation).selectinload(AccommodationTable.users))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y User pueden ver asociaciones sin restricciones
    elif user.role == "employee":
        # Employee solo puede ver si está relacionado con el alojamiento
        if username not in [u.username for u in room.accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to view room-product associations")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Obtener todas las asociaciones para la habitación
    result = await db.execute(
        select(room_product).where(room_product.c.room_id == room_id)
    )
    associations = result.fetchall()
    logger.info(f"Found {len(associations)} room-product associations for room {room_id}")

    return [
        RoomProduct(
            room_id=assoc.room_id,
            product_id=assoc.product_id,
            quantity=assoc.quantity,
            needs_restock=assoc.needs_restock
        )
        for assoc in associations
    ]

async def delete_room_product(db: AsyncSession, room_id: int, product_id: int, username: str) -> None:
    """Delete a room-product association. Restricted to admin, user, or authorized employee."""
    logger.info(f"User {username} attempting to delete room-product association: room_id={room_id}, product_id={product_id}")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Verificar que la habitación exista
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.accommodation).selectinload(AccommodationTable.users))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verificar que el producto exista
    result = await db.execute(select(SQLAlchemyProduct).where(SQLAlchemyProduct.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y User pueden eliminar asociaciones sin restricciones
    elif user.role == "employee":
        # Employee solo puede eliminar si está relacionado con el alojamiento
        if username not in [u.username for u in room.accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to delete room-product association")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Verificar que la asociación exista
    result = await db.execute(
        select(room_product).where(
            (room_product.c.room_id == room_id) &
            (room_product.c.product_id == product_id)
        )
    )
    existing = result.first()
    if not existing:
        raise HTTPException(status_code=404, detail="Room-product association not found")

    # Eliminar la asociación
    stmt = delete(room_product).where(
        (room_product.c.room_id == room_id) &
        (room_product.c.product_id == product_id)
    )
    await db.execute(stmt)
    await db.commit()
    logger.info(f"Room-product association deleted: room_id={room_id}, product_id={product_id}")



async def get_room_product_details(db: AsyncSession, room_id: int, username: str) -> List[RoomProductDetails]:
    """Retrieve all products associated with a room, including quantity and restock status. Restricted to admin, user, or authorized employee."""
    logger.info(f"User {username} attempting to get product details for room {room_id}")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Verificar que la habitación exista
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(
            selectinload(Room.accommodation).selectinload(AccommodationTable.users),
            selectinload(Room.products)
        )
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Aplicar permisos según el rol
    if user.role == "admin" or user.role == "client":
        pass  # Admin y User pueden ver productos sin restricciones
    elif user.role == "employee":
        # Employee solo puede ver si está relacionado con el alojamiento
        if username not in [u.username for u in room.accommodation.users]:
            raise HTTPException(status_code=403, detail="Not authorized to view product details for this room")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Obtener asociaciones de la tabla room_product con detalles del producto
    result = await db.execute(
        select(
            room_product.c.quantity,
            room_product.c.needs_restock,
            SQLAlchemyProduct
        )
        .join(SQLAlchemyProduct, room_product.c.product_id == SQLAlchemyProduct.id)
        .where(room_product.c.room_id == room_id)
    )
    associations = result.fetchall()

    product_details = []
    for row in associations:
        # Acceder a los campos usando índices o desempaquetado explícito
        quantity, needs_restock, product = row
        pydantic_product = PydanticProduct.model_validate(product)
        product_details.append(
            RoomProductDetails(
                product=pydantic_product,
                quantity=quantity,
                needs_restock=needs_restock
            )
        )

    logger.info(f"Found {len(product_details)} products with details for room {room_id}")
    return product_details