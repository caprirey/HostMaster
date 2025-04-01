from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.models.pydantic_models import User, UserCreate, UserUpdate
from app.models.sqlalchemy_models import UserTable, Accommodation
from app.utils.auth import get_password_hash

# Crear usuario (Create)
async def create_user_service(db: AsyncSession, user_data: UserCreate) -> User:
    # Validar si el username ya existe
    username_check = await db.execute(
        select(UserTable).where(UserTable.username == user_data.username)
    )
    if username_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    # Validar si el email ya existe (si se proporciona)
    if user_data.email:
        email_check = await db.execute(
            select(UserTable).where(UserTable.email == user_data.email)
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

    # Crear el nuevo usuario
    hashed_password = get_password_hash(user_data.password)
    new_user = UserTable(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        disabled=False,
        role=user_data.role  # Usar el role proporcionado, por defecto "user" desde UserCreate
    )

    # Asignar alojamientos si se proporcionan
    if user_data.accommodation_ids is not None:
        accommodations = await db.execute(
            select(Accommodation).where(Accommodation.id.in_(user_data.accommodation_ids))
        )
        accommodations_list = accommodations.scalars().all()
        if len(accommodations_list) != len(user_data.accommodation_ids):
            raise HTTPException(status_code=400, detail="One or more accommodation IDs do not exist")
        new_user.accommodations = accommodations_list

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Cargar relaciones
    result = await db.execute(
        select(UserTable)
        .where(UserTable.username == new_user.username)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    new_user = result.scalar_one()

    user_dict = {
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "disabled": new_user.disabled,
        "role": new_user.role,
        "reviews": new_user.reviews,
        "accommodation_ids": [a.id for a in new_user.accommodations] if new_user.accommodations else []
    }
    return User.model_validate(user_dict)

# Leer todos los usuarios (Read - List)
async def get_users_service(db: AsyncSession) -> List[User]:
    result = await db.execute(
        select(UserTable)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    users = result.scalars().all()
    return [
        User.model_validate({
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "disabled": user.disabled,
            "role": user.role,
            "reviews": user.reviews,
            "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
        }) for user in users
    ]

# Leer un usuario por username (Read - Detail)
async def get_user_service(db: AsyncSession, username: str) -> User:
    result = await db.execute(
        select(UserTable)
        .where(UserTable.username == username)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_dict = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "disabled": user.disabled,
        "role": user.role,
        "reviews": user.reviews,
        "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
    }
    return User.model_validate(user_dict)

# Actualizar usuario (Update)
async def update_user_service(db: AsyncSession, username: str, user_data: UserUpdate) -> User:
    result = await db.execute(
        select(UserTable)
        .where(UserTable.username == username)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Actualizar campos proporcionados
    if user_data.email is not None:
        email_check = await db.execute(
            select(UserTable).where(UserTable.email == user_data.email).where(UserTable.username != username)
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.accommodation_ids is not None:
        accommodations = await db.execute(
            select(Accommodation).where(Accommodation.id.in_(user_data.accommodation_ids))
        )
        accommodations_list = accommodations.scalars().all()
        if len(accommodations_list) != len(user_data.accommodation_ids):
            raise HTTPException(status_code=400, detail="One or more accommodation IDs do not exist")
        user.accommodations = accommodations_list
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.password is not None:
        user.hashed_password = get_password_hash(user_data.password)  # Hashear y actualizar la contraseña

    await db.commit()
    await db.refresh(user)

    user_dict = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "disabled": user.disabled,
        "role": user.role,
        "reviews": user.reviews,
        "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
    }
    return User.model_validate(user_dict)

# Eliminar usuario (Delete)
async def delete_user_service(db: AsyncSession, username: str) -> None:
    result = await db.execute(
        select(UserTable).where(UserTable.username == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()



async def get_users_by_role_service(db: AsyncSession, role: str) -> List[User]:
    result = await db.execute(
        select(UserTable)
        .where(UserTable.role == role)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    users = result.scalars().all()
    return [
        User.model_validate({
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "disabled": user.disabled,
            "role": user.role,
            "reviews": user.reviews,
            "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
        }) for user in users
    ]