from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_active_user, get_db
from app.models.pydantic_models import User, UserCreate, UserUpdate
from app.services.admin.admin import (
    create_user_service,
    get_users_service,
    get_user_service,
    delete_user_service,
    update_user_service,
    get_users_by_role_service
)
import json

router = APIRouter()

# Dependencia para verificar rol "admin"
async def get_admin_user(current_user: User = Depends(get_current_active_user)):
    print(f"Checking admin user: {current_user.username}, role: {current_user.role}")
    if current_user.role != "admin":
        print(f"Access denied for user {current_user.username}: role {current_user.role} not allowed")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    return current_user

# Dependencia para verificar rol "admin" o "employee"
async def get_admin_or_employee_user(current_user: User = Depends(get_current_active_user)):
    print(f"Checking admin/employee user: {current_user.username}, role: {current_user.role}")
    if current_user.role not in ["admin", "employee"]:
        print(f"Access denied for user {current_user.username}: role {current_user.role} not allowed")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or employees can access this endpoint"
        )
    return current_user

# Crear usuario
@router.post(
    "/users/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario",
    description="Crea un nuevo usuario como administrador. Solo accesible para usuarios con rol 'admin'. La imagen es opcional; no incluya el campo 'image' si no se sube un archivo.",
    responses={
        201: {"description": "Usuario creado exitosamente"},
        400: {"description": "Entrada inválida o datos duplicados"},
        403: {"description": "No autorizado (requiere rol admin)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def create_user_admin(
        username: Annotated[str, Form(description="Nombre de usuario único")],
        password: Annotated[str, Form(description="Contraseña del usuario")],
        firstname: Annotated[str, Form(description="Nombre del usuario")],
        lastname: Annotated[str, Form(description="Apellido del usuario")],
        document_number: Annotated[str, Form(description="Número de documento único")],
        phone_number: Annotated[str, Form(description="Número de teléfono (formato: +573001234567)")],
        db: Annotated[AsyncSession, Depends(get_db)],
        admin_user: Annotated[User, Depends(get_admin_user)],
        email: Annotated[str | None, Form(description="Correo electrónico (opcional)")] = None,
        full_name: Annotated[str | None, Form(description="Nombre completo (opcional)")] = None,
        role: Annotated[str | None, Form(description="Rol del usuario (opcional, por defecto 'user')")] = None,
        accommodation_ids: Annotated[str | None, Form(description="JSON con IDs de alojamientos (opcional)")] = None,
        image: Annotated[UploadFile | None, File(description="Imagen de perfil (opcional, JPG, JPEG, PNG). Omita este campo si no se sube un archivo.")] = None
):
    print(f"Creating user: {username}, role: {role} by admin: {admin_user.username}")
    accommodation_ids_list = None
    if accommodation_ids:
        try:
            accommodation_ids_list = json.loads(accommodation_ids)
            if not isinstance(accommodation_ids_list, list) or not all(isinstance(id, int) for id in accommodation_ids_list):
                raise ValueError("accommodation_ids debe ser una lista JSON de enteros")
        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de accommodation_ids inválido: {str(e)}"
            )

    user_data = UserCreate(
        username=username,
        email=email,
        full_name=full_name,
        password=password,
        accommodation_ids=accommodation_ids_list,
        role=role,
        firstname=firstname,
        lastname=lastname,
        document_number=document_number,
        image=None,
        phone_number=phone_number
    )

    return await create_user_service(db, user_data, image)

# Obtener todos los usuarios
@router.get(
    "/users/",
    response_model=List[User],
    summary="Obtener todos los usuarios",
    description="Devuelve una lista de todos los usuarios registrados. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Lista de usuarios obtenida exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_users_admin(
        db: Annotated[AsyncSession, Depends(get_db)],
        auth_user: Annotated[User, Depends(get_admin_or_employee_user)]
):
    print(f"Fetching all users by user: {auth_user.username}, role: {auth_user.role}")
    return await get_users_service(db)

# Obtener usuarios por rol
@router.get(
    "/users/by-role",
    response_model=List[User],
    summary="Obtener usuarios por rol",
    description="Devuelve una lista de usuarios con el rol especificado (por ejemplo, 'user', 'admin', 'employee'). Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Lista de usuarios obtenida exitosamente"},
        400: {"description": "Parámetro de rol inválido"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_users_by_role(
        role: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        auth_user: Annotated[User, Depends(get_admin_or_employee_user)]
):
    print(f"Fetching users with role {role} by user: {auth_user.username}, role: {auth_user.role}")
    return await get_users_by_role_service(db, role)

# Obtener un usuario por username
@router.get(
    "/users/{username}",
    response_model=User,
    summary="Obtener usuario por username",
    description="Devuelve los detalles de un usuario específico por su username. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Usuario obtenido exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        404: {"description": "Usuario no encontrado"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_user_admin(
        username: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        auth_user: Annotated[User, Depends(get_admin_or_employee_user)]
):
    print(f"Fetching user {username} by user: {auth_user.username}, role: {auth_user.role}")
    return await get_user_service(db, username)

# Actualizar usuario
@router.patch(
    "/users/{username}",
    response_model=User,
    summary="Actualizar usuario",
    description="Actualiza los detalles de un usuario específico por su username. Solo accesible para usuarios con rol 'admin' o 'employee'. La imagen es opcional; no incluya el campo 'image' si no se sube un archivo.",
    responses={
        200: {"description": "Usuario actualizado exitosamente"},
        400: {"description": "Entrada inválida o datos duplicados"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        404: {"description": "Usuario no encontrado"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def update_user_admin(
        username: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        auth_user: Annotated[User, Depends(get_admin_or_employee_user)],
        email: Annotated[str | None, Form(description="Correo electrónico (opcional)")] = None,
        full_name: Annotated[str | None, Form(description="Nombre completo (opcional)")] = None,
        firstname: Annotated[str | None, Form(description="Nombre (opcional)")] = None,
        lastname: Annotated[str | None, Form(description="Apellido (opcional)")] = None,
        document_number: Annotated[str | None, Form(description="Número de documento (opcional)")] = None,
        role: Annotated[str | None, Form(description="Rol del usuario (opcional)")] = None,
        password: Annotated[str | None, Form(description="Nueva contraseña (opcional)")] = None,
        accommodation_ids: Annotated[str | None, Form(description="JSON con IDs de alojamientos (opcional)")] = None,
        phone_number: Annotated[str | None, Form(description="Número de teléfono (opcional, formato: +573001234567)")] = None,  # Añadido
        image: Annotated[UploadFile | None, File(description="Imagen de perfil (opcional, JPG, JPEG, PNG). Omita este campo si no se sube un archivo.")] = None
):
    print(f"Updating user {username} by user: {auth_user.username}, role: {auth_user.role}")
    accommodation_ids_list = None
    if accommodation_ids:
        try:
            accommodation_ids_list = json.loads(accommodation_ids)
            if not isinstance(accommodation_ids_list, list) or not all(isinstance(id, int) for id in accommodation_ids_list):
                raise ValueError("accommodation_ids debe ser una lista JSON de enteros")
        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de accommodation_ids inválido: {str(e)}"
            )

    user_data = UserUpdate(
        email=email,
        full_name=full_name,
        firstname=firstname,
        lastname=lastname,
        document_number=document_number,
        role=role,
        password=password,
        accommodation_ids=accommodation_ids_list,
        phone_number=phone_number,  # Añadido
        image=None
    )

    return await update_user_service(db, username, user_data, image)

# Eliminar usuario
@router.delete(
    "/users/{username}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
    description="Elimina un usuario específico por su username. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        204: {"description": "Usuario eliminado exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        404: {"description": "Usuario no encontrado"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def delete_user_admin(
        username: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        auth_user: Annotated[User, Depends(get_admin_or_employee_user)]
):
    print(f"Deleting user {username} by user: {auth_user.username}, role: {auth_user.role}")
    await delete_user_service(db, username)
    return None