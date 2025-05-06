from typing import Annotated
from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_active_user, get_db
from app.models.pydantic_models import Token, User, UserCreate, UserUpdate, ChangePasswordRequest
from app.services.auth.user import register_user_service, login_user_service, update_user_service, change_password_service
import json

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
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        firstname: Annotated[str, Form()],
        lastname: Annotated[str, Form()],
        document_number: Annotated[str, Form()],
        db: Annotated[AsyncSession, Depends(get_db)],
        email: Annotated[str | None, Form()] = None,
        full_name: Annotated[str | None, Form()] = None,
        # accommodation_ids: Annotated[str | None, Form()] = None,
        # role: Annotated[str | None, Form()] = "client",
        image: Annotated[UploadFile | None, File()] = None,
):
    """Register a new user with optional image and accommodation associations."""
    # Convert accommodation_ids from JSON string to list if provided
   # accommodation_ids_list = None
   # if accommodation_ids:
   #     try:
   #         accommodation_ids_list = json.loads(accommodation_ids)
   #         if not isinstance(accommodation_ids_list, list) or not all(isinstance(id, int) for id in accommodation_ids_list):
   #             raise ValueError("accommodation_ids must be a JSON list of integers")
   #     except (ValueError, json.JSONDecodeError) as e:
   #         raise HTTPException(
   #             status_code=status.HTTP_400_BAD_REQUEST,
   #             detail=f"Invalid accommodation_ids format: {str(e)}. Expected a JSON list of integers (e.g., '[1, 2, 3]')"
   #         )

    # Create UserCreate object
    user_data = UserCreate(
        username=username,
        email=email,
        full_name=full_name,
        password=password,
    #   accommodation_ids=accommodation_ids_list,
    #   role=role,
        firstname=firstname,
        lastname=lastname,
        document_number=document_number,
        image=None  # Image is processed in the service
    )

    return await register_user_service(db, user_data, image)

@router.put("/users/me/", response_model=User)
async def update_user(
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
        email: Annotated[str | None, Form()] = None,
        full_name: Annotated[str | None, Form()] = None,
        firstname: Annotated[str | None, Form()] = None,
        lastname: Annotated[str | None, Form()] = None,
        document_number: Annotated[str | None, Form()] = None,
        # role: Annotated[str | None, Form()] = None,
        # password: Annotated[str | None, Form()] = None,
        # accommodation_ids: Annotated[str | None, Form()] = None,
        image: Annotated[UploadFile | None, File()] = None,
):
    """Update the current authenticated user's details, including optional image."""
    # Convert accommodation_ids from JSON string to list if provided
    # accommodation_ids_list = None
    # if accommodation_ids:
    #    try:
    #        accommodation_ids_list = json.loads(accommodation_ids)
    #        if not isinstance(accommodation_ids_list, list) or not all(isinstance(id, int) for id in accommodation_ids_list):
    #            raise ValueError("accommodation_ids must be a JSON list of integers")
    #    except (ValueError, json.JSONDecodeError) as e:
    #        raise HTTPException(
    #            status_code=status.HTTP_400_BAD_REQUEST,
    #            detail=f"Invalid accommodation_ids format: {str(e)}. Expected a JSON list of integers (e.g., '[1, 2, 3]')"
    #        )

    # Create UserUpdate object
    user_data = UserUpdate(
        email=email,
        full_name=full_name,
        firstname=firstname,
        lastname=lastname,
        document_number=document_number,
    #    role=role,
    #     password=password,
    #    accommodation_ids=accommodation_ids_list,
        image=None  # Image is processed in the service
    )

    return await update_user_service(db, current_user.username, user_data, image)

@router.put("/users/me/password", response_model=User)
async def change_password(
        password_data: ChangePasswordRequest,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
):
    return await change_password_service(db, current_user.username, password_data)