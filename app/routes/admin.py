from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_active_user, get_db
from app.models.pydantic_models import Token, User, UserCreate, UserUpdate, ChangePasswordRequest
from app.services.admin.admin import (
    create_user_service,
    get_users_service,
    get_user_service,
    delete_user_service,
    update_user_service,
    get_users_by_role_service
)

router = APIRouter()

# Dependencia para verificar rol "admin"
async def get_admin_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    return current_user


# Rutas CRUD para administradores bajo /auth/admin/users
@router.post("/users/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db),
        admin_user: User = Depends(get_admin_user)
):
    return await create_user_service(db, user_data)

@router.get("/users/", response_model=List[User])
async def get_users_admin(
        db: AsyncSession = Depends(get_db),
        admin_user: User = Depends(get_admin_user)
):
    return await get_users_service(db)

@router.get("/users/{username}", response_model=User)
async def get_user_admin(
        username: str,
        db: AsyncSession = Depends(get_db),
        admin_user: User = Depends(get_admin_user)
):
    return await get_user_service(db, username)

@router.patch("/users/{username}", response_model=User)  # Cambiado de PUT a PATCH
async def update_user_admin(
        username: str,
        user_data: UserUpdate,
        db: AsyncSession = Depends(get_db),
        admin_user: User = Depends(get_admin_user)
):
    return await update_user_service(db, username, user_data)

@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_admin(
        username: str,
        db: AsyncSession = Depends(get_db),
        admin_user: User = Depends(get_admin_user)
):
    await delete_user_service(db, username)
    return None

# Nueva ruta para obtener solo usuarios con role="user"
@router.get("/users/role/user", response_model=List[User])
async def get_users_role_user(
        db: AsyncSession = Depends(get_db),
        admin_user: User = Depends(get_admin_user)
):
    return await get_users_by_role_service(db, "user")