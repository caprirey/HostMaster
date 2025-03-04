from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.pydantic_models import User, UserCreate, UserInDB, UserUpdate
from app.models.sqlalchemy_models import UserTable, Accommodation
from app.utils.auth import get_password_hash, authenticate_user as auth_user, create_access_token
from app.config.settings import ACCESS_TOKEN_EXPIRE_DELTA

async def register_user_service(db: AsyncSession, user_data: UserCreate) -> User:
    if await auth_user(db, user_data.username, user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_password = get_password_hash(user_data.password)
    new_user = UserTable(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        disabled=False,
        role="user"
    )

    if user_data.accommodation_ids:
        accommodations = await db.execute(
            select(Accommodation).where(Accommodation.id.in_(user_data.accommodation_ids))
        )
        new_user.accommodations = accommodations.scalars().all()

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return User.model_validate(new_user, update={"accommodation_ids": [a.id for a in new_user.accommodations]})

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
    result = await db.execute(select(UserTable).where(UserTable.username == username))
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
        user.accommodations = accommodations.scalars().all()

    await db.commit()
    await db.refresh(user)
    return User.model_validate(user, update={"accommodation_ids": [a.id for a in user.accommodations]})