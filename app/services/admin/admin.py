from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status, UploadFile
from app.models.pydantic_models import User, UserCreate, UserUpdate
from app.models.sqlalchemy_models import UserTable, Accommodation
from app.utils.auth import get_password_hash
import os
import uuid
from pathlib import Path
from sqlalchemy import func

# Crear usuario (Create)
async def create_user_service(db: AsyncSession, user_data: UserCreate, image_file: UploadFile | None = None) -> User:
    print(f"Creating user: {user_data.username}, role: {user_data.role}")
    username_check = await db.execute(
        select(UserTable).where(UserTable.username == user_data.username)
    )
    if username_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    if user_data.email:
        email_check = await db.execute(
            select(UserTable).where(UserTable.email == user_data.email)
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    document_check = await db.execute(
        select(UserTable).where(UserTable.document_number == user_data.document_number)
    )
    if document_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document number already registered")

    image_path = None
    if image_file:
        allowed_extensions = {".jpg", ".jpeg", ".png"}
        file_extension = os.path.splitext(image_file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format. Only JPG, JPEG, and PNG are allowed",
            )

        unique_filename = f"user_{user_data.document_number}_{uuid.uuid4().hex}{file_extension}"
        image_dir = Path("static/images")
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = f"static/images/{unique_filename}"

        with open(image_path, "wb") as f:
            content = await image_file.read()
            f.write(content)

    hashed_password = get_password_hash(user_data.password)
    new_user = UserTable(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        disabled=False,
        role=user_data.role or "client",
        firstname=user_data.firstname,
        lastname=user_data.lastname,
        document_number=user_data.document_number,
        image=image_path,
        phone_number=user_data.phone_number
    )

    if user_data.accommodation_ids is not None:
        accommodations = await db.execute(
            select(Accommodation).where(Accommodation.id.in_(user_data.accommodation_ids))
        )
        accommodations_list = accommodations.scalars().all()
        if len(accommodations_list) != len(user_data.accommodation_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more accommodation IDs do not exist")
        new_user.accommodations = accommodations_list

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

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
        "firstname": new_user.firstname,
        "lastname": new_user.lastname,
        "document_number": new_user.document_number,
        "image": new_user.image,
        "phone_number": new_user.phone_number,
        "reviews": new_user.reviews or [],
        "accommodation_ids": [a.id for a in new_user.accommodations] if new_user.accommodations else []
    }
    return User.model_validate(user_dict)

# Leer todos los usuarios (Read - List)
async def get_users_service(db: AsyncSession) -> List[User]:
    print("Fetching all users")
    result = await db.execute(
        select(UserTable)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    users = result.scalars().all()
    print(f"Found {len(users)} users")
    return [
        User.model_validate({
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "disabled": user.disabled,
            "role": user.role,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "document_number": user.document_number,
            "image": user.image,
            "phone_number": user.phone_number,
            "reviews": user.reviews or [],
            "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
        }) for user in users
    ]

# Leer un usuario por username (Read - Detail)
async def get_user_service(db: AsyncSession, username: str) -> User:
    print(f"Fetching user: {username}")
    result = await db.execute(
        select(UserTable)
        .where(UserTable.username == username)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_dict = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "disabled": user.disabled,
        "role": user.role,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "document_number": user.document_number,
        "image": user.image,
        "phone_number": user.phone_number,
        "reviews": user.reviews or [],
        "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
    }
    return User.model_validate(user_dict)

# Leer usuarios por rol
async def get_users_by_role_service(db: AsyncSession, role: str) -> List[User]:
    print(f"Fetching users with role: {role}")
    role = role.strip().lower()
    valid_roles = ["client", "admin", "employee"]
    if role not in valid_roles:
        print(f"Invalid role requested: {role}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of {valid_roles}"
        )

    result = await db.execute(
        select(UserTable)
        .where(UserTable.role == role)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    users = result.scalars().all()
    print(f"Found {len(users)} users with role {role}")
    return [
        User.model_validate({
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "disabled": user.disabled,
            "role": user.role,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "document_number": user.document_number,
            "image": user.image,
            "phone_number": user.phone_number,
            "reviews": user.reviews or [],
            "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
        }) for user in users
    ]

# Actualizar usuario (Update)
async def update_user_service(db: AsyncSession, username: str, user_data: UserUpdate, image_file: UploadFile | None = None) -> User:
    print(f"Updating user: {username}")
    result = await db.execute(
        select(UserTable)
        .where(UserTable.username == username)
        .options(selectinload(UserTable.accommodations), selectinload(UserTable.reviews))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    image_path = user.image
    if image_file:
        allowed_extensions = {".jpg", ".jpeg", ".png"}
        file_extension = os.path.splitext(image_file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format. Only JPG, JPEG, and PNG are allowed",
            )

        unique_filename = f"user_{user_data.document_number or user.document_number}_{uuid.uuid4().hex}{file_extension}"
        image_dir = Path("static/images")
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = f"static/images/{unique_filename}"

        with open(image_path, "wb") as f:
            content = await image_file.read()
            f.write(content)

    if user_data.email is not None:
        email_check = await db.execute(
            select(UserTable).where(UserTable.email == user_data.email).where(UserTable.username != username)
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.firstname is not None:
        user.firstname = user_data.firstname
    if user_data.lastname is not None:
        user.lastname = user_data.lastname
    if user_data.document_number is not None:
        document_check = await db.execute(
            select(UserTable)
            .where(UserTable.document_number == user_data.document_number)
            .where(UserTable.username != username)
        )
        if document_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document number already registered")
        user.document_number = user_data.document_number
    if image_path is not None:
        user.image = image_path
    if user_data.phone_number is not None:
        user.phone_number = user_data.phone_number
    if user_data.accommodation_ids is not None:
        accommodations = await db.execute(
            select(Accommodation).where(Accommodation.id.in_(user_data.accommodation_ids))
        )
        accommodations_list = accommodations.scalars().all()
        if len(accommodations_list) != len(user_data.accommodation_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more accommodation IDs do not exist")
        user.accommodations = accommodations_list
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.password is not None:
        user.hashed_password = get_password_hash(user_data.password)

    await db.commit()
    await db.refresh(user)

    user_dict = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "disabled": user.disabled,
        "role": user.role,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "document_number": user.document_number,
        "image": user.image,
        "phone_number": user.phone_number,
        "reviews": user.reviews or [],
        "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
    }
    return User.model_validate(user_dict)

# Eliminar usuario (Delete)
async def delete_user_service(db: AsyncSession, username: str) -> None:
    print(f"Deleting user: {username}")
    result = await db.execute(
        select(UserTable).where(UserTable.username == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()