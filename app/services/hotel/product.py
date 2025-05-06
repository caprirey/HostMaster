from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.sqlalchemy_models import Product as SQLAlchemyProduct
from app.models.sqlalchemy_models import Room, Accommodation as AccommodationTable, UserTable, room_product
from app.models.pydantic_models import Product as PydanticProduct
from app.models.pydantic_models import ProductCreate, ProductUpdate, RoomProductCreate
from typing import List
import logging

logger = logging.getLogger(__name__)

async def create_product(db: AsyncSession, product: ProductCreate, username: str) -> PydanticProduct:
    """Create a new product. Restricted to admin and user roles."""
    logger.info(f"User {username} attempting to create product: {product.name}")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Aplicar permisos según el rol
    if user.role not in ["admin", "client"]:
        raise HTTPException(status_code=403, detail="Not authorized to create products")

    # Crear el producto con el modelo SQLAlchemy
    db_product = SQLAlchemyProduct(name=product.name, description=product.description, price=product.price)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    logger.info(f"Product {db_product.name} created successfully with ID {db_product.id}")

    # Devolver el modelo Pydantic
    return PydanticProduct.model_validate(db_product)

async def get_products(db: AsyncSession, username: str) -> List[PydanticProduct]:
    """Retrieve all products. Restricted to admin and user roles."""
    logger.info(f"User {username} attempting to get all products")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Aplicar permisos según el rol
    if user.role not in ["admin", "client"]:
        raise HTTPException(status_code=403, detail="Not authorized to view products")

    # Obtener todos los productos
    result = await db.execute(select(SQLAlchemyProduct))
    products = result.scalars().all()
    logger.info(f"Found {len(products)} products")

    return [PydanticProduct.model_validate(product) for product in products]

async def update_product(db: AsyncSession, product_id: int, product_update: ProductUpdate, username: str) -> PydanticProduct:
    """Update an existing product. Restricted to admin and user roles."""
    logger.info(f"User {username} attempting to update product ID {product_id}")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Aplicar permisos según el rol
    if user.role not in ["admin", "client"]:
        raise HTTPException(status_code=403, detail="Not authorized to update products")

    # Verificar que el producto exista
    result = await db.execute(select(SQLAlchemyProduct).where(SQLAlchemyProduct.id == product_id))
    db_product = result.scalar_one_or_none()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Actualizar los campos proporcionados
    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)
    logger.info(f"Product ID {db_product.id} updated successfully")

    return PydanticProduct.model_validate(db_product)

async def delete_product(db: AsyncSession, product_id: int, username: str) -> None:
    """Delete a product. Restricted to admin and user roles."""
    logger.info(f"User {username} attempting to delete product ID {product_id}")

    # Verificar que el usuario exista
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User role: {user.role}")

    # Aplicar permisos según el rol
    if user.role not in ["admin", "client"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete products")

    # Verificar que el producto exista
    result = await db.execute(select(SQLAlchemyProduct).where(SQLAlchemyProduct.id == product_id))
    db_product = result.scalar_one_or_none()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Eliminar el producto
    await db.delete(db_product)
    await db.commit()
    logger.info(f"Product ID {product_id} deleted successfully")
