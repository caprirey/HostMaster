from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.pydantic_models import User, UserCreate, UserInDB, UserUpdate, ChangePasswordRequest
from app.models.sqlalchemy_models import UserTable, Accommodation
from app.utils.auth import get_password_hash, authenticate_user as auth_user, create_access_token
from app.config.settings import ACCESS_TOKEN_EXPIRE_DELTA
from sqlalchemy.orm import selectinload
from app.utils.auth import get_password_hash, verify_password

async def register_user_service(db: AsyncSession, user_data: UserCreate) -> User:
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

    # Crear el nuevo usuario
    hashed_password = get_password_hash(user_data.password)
    new_user = UserTable(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        disabled=False,
        role="user"
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
            selectinload(UserTable.accommodations),  # Cargar accommodations
            selectinload(UserTable.reviews)          # Cargar reviews
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
        "reviews": new_user.reviews,  # Lista vacía para nuevos usuarios
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

async def update_user_service(db: AsyncSession, username: str, user_data: UserUpdate) -> User:
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
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
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
        raise HTTPException(status_code=404, detail="User not found")

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
        "reviews": user.reviews,
        "accommodation_ids": [a.id for a in user.accommodations] if user.accommodations else []
    }
    return User.model_validate(user_dict)