from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status, UploadFile
from app.models.pydantic_models import User, UserCreate, UserInDB, UserUpdate, ChangePasswordRequest
from app.models.sqlalchemy_models import UserTable, Accommodation
from app.utils.auth import get_password_hash, authenticate_user as auth_user, create_access_token
from app.config.settings import ACCESS_TOKEN_EXPIRE_DELTA
from sqlalchemy.orm import selectinload
from app.utils.auth import get_password_hash, verify_password
import os
import uuid
from pathlib import Path

async def register_user_service(db: AsyncSession, user_data: UserCreate, image_file: UploadFile | None = None) -> User:
    # Validar si el username ya existe
    username_check = await db.execute(
        select(UserTable).where(UserTable.username == user_data.username)
    )
    if username_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Validar si el email ya existe (si se proporciona)
    if user_data.email:
        email_check = await db.execute(
            select(UserTable).where(UserTable.email == user_data.email)
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Validar si el document_number ya existe
    document_check = await db.execute(
        select(UserTable).where(UserTable.document_number == user_data.document_number)
    )
    if document_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document number already registered",
        )

    # Procesar la imagen si se proporciona
    image_path = None
    if image_file:
        # Validar tipo de archivo
        allowed_extensions = {".jpg", ".jpeg", ".png"}
        file_extension = os.path.splitext(image_file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format. Only JPG, JPEG, and PNG are allowed",
            )

        # Generar un nombre único para la imagen
        unique_filename = f"user_{user_data.document_number}_{uuid.uuid4().hex}{file_extension}"
        image_dir = Path("static/images")
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = f"static/images/{unique_filename}"

        # Guardar la imagen
        with open(image_path, "wb") as f:
            content = await image_file.read()
            f.write(content)

    # Crear el nuevo usuario
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

    # Asignar alojamientos solo si se proporcionan explícitamente
    if user_data.accommodation_ids is not None:
        accommodations = await db.execute(
            select(Accommodation).where(Accommodation.id.in_(user_data.accommodation_ids))
        )
        accommodations_list = accommodations.scalars().all()
        if len(accommodations_list) != len(user_data.accommodation_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more accommodation IDs do not exist",
            )
        new_user.accommodations = accommodations_list

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Recargar el usuario con las relaciones accommodations y reviews
    result = await db.execute(
        select(UserTable)
        .where(UserTable.username == new_user.username)
        .options(
            selectinload(UserTable.accommodations),
            selectinload(UserTable.reviews)
        )
    )
    new_user = result.scalar_one()

    # Construir el diccionario para el modelo Pydantic
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
        "reviews": new_user.reviews,
        "accommodation_ids": [a.id for a in new_user.accommodations] if new_user.accommodations else []
    }
    return User.model_validate(user_dict)

async def login_user_service(db: AsyncSession, username: str, password: str) -> dict:
    user = await auth_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=ACCESS_TOKEN_EXPIRE_DELTA
    )
    return {"access_token": access_token, "token_type": "bearer"}

async def update_user_service(db: AsyncSession, username: str, user_data: UserUpdate, image_file: UploadFile | None = None) -> User:
    result = await db.execute(
        select(UserTable)
        .where(UserTable.username == username)
        .options(
            selectinload(UserTable.accommodations),
            selectinload(UserTable.reviews)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Procesar la imagen si se proporciona
    image_path = user.image  # Mantener la imagen existente si no se proporciona una nueva
    if image_file:
        # Validar tipo de archivo
        allowed_extensions = {".jpg", ".jpeg", ".png"}
        file_extension = os.path.splitext(image_file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format. Only JPG, JPEG, and PNG are allowed",
            )

        # Generar un nombre único para la imagen
        unique_filename = f"user_{user_data.document_number or user.document_number}_{uuid.uuid4().hex}{file_extension}"
        image_dir = Path("static/images")
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = f"static/images/{unique_filename}"

        # Guardar la imagen
        with open(image_path, "wb") as f:
            content = await image_file.read()
            f.write(content)

    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.firstname is not None:
        user.firstname = user_data.firstname
    if user_data.lastname is not None:
        user.lastname = user_data.lastname
    if user_data.document_number is not None:
        # Validar si el nuevo document_number ya existe
        document_check = await db.execute(
            select(UserTable)
            .where(UserTable.document_number == user_data.document_number)
            .where(UserTable.username != username)
        )
        if document_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document number already registered",
            )
        user.document_number = user_data.document_number
    if image_path is not None:
        user.image = image_path
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.accommodation_ids is not None:
        accommodations = await db.execute(
            select(Accommodation).where(Accommodation.id.in_(user_data.accommodation_ids))
        )
        accommodations_list = accommodations.scalars().all()
        if len(accommodations_list) != len(user_data.accommodation_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more accommodation IDs do not exist",
            )
        user.accommodations = accommodations_list
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
        "reviews": user.reviews,
        "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
    }
    return User.model_validate(user_dict)

async def change_password_service(db: AsyncSession, username: str, password_data: ChangePasswordRequest) -> User:
    # Buscar el usuario con sus relaciones cargadas
    result = await db.execute(
        select(UserTable)
        .where(UserTable.username == username)
        .options(
            selectinload(UserTable.accommodations),
            selectinload(UserTable.reviews)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verificar la contraseña actual
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password",
        )

    # Actualizar la contraseña con el nuevo hash
    user.hashed_password = get_password_hash(password_data.new_password)

    await db.commit()
    await db.refresh(user)

    # Construir el diccionario para el modelo Pydantic
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
        "reviews": user.reviews,
        "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
    }
    return User.model_validate(user_dict)