from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_active_user, get_db
from app.models.pydantic_models import Token, User, UserCreate, UserUpdate, ChangePasswordRequest
from app.services.auth.user import register_user_service, login_user_service, update_user_service, change_password_service


router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await login_user_service(db, form_data.username, form_data.password)

@router.get("/users/me/", response_model=User)
async def read_users_me(
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user

@router.post("/register", response_model=User)
async def register_user(
        user_data: UserCreate,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await register_user_service(db, user_data)

@router.put("/users/me/", response_model=User)
async def update_user(
        user_data: UserUpdate,
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await update_user_service(db, current_user.username, user_data)

@router.put("/users/me/password", response_model=User)
async def change_password(
        password_data: ChangePasswordRequest,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
):
    return await change_password_service(db, current_user.username, password_data)