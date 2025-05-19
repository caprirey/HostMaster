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
from datetime import datetime
from app.services.hotel.stats import (
    calculate_occupancy,
    estimate_revenue,
    get_reviews_summary,
    calculate_performance,
    recent_activity,
    get_maintenance_summary,
    daily_metrics,
    top_revenue_days_by_weekday, accommodation_summary
)

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
        phone_number: Annotated[str | None, Form(description="Número de teléfono (opcional, formato: +573001234567)")] = None,
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
        phone_number=phone_number,
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

# Nuevas rutas del dashboard
@router.get(
    "/dashboard/occupancy",
    summary="Obtener tasa de ocupación",
    description="Devuelve el porcentaje de ocupación y datos de reservas activas para un alojamiento en un período. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Datos de ocupación obtenidos exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_occupancy(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    print(f"Fetching occupancy for accommodation {accommodation_id} by user: {current_user.username}")
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    return await calculate_occupancy(db, accommodation_id, start, end)

@router.get(
    "/dashboard/revenue",
    summary="Obtener ingresos estimados",
    description="Devuelve una estimación de ingresos basada en precios de habitaciones y servicios extra para un alojamiento en un período. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Ingresos estimados obtenidos exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_revenue(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    print(f"Fetching revenue for accommodation {accommodation_id} by user: {current_user.username}")
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    return await estimate_revenue(db, accommodation_id, start, end)

@router.get(
    "/dashboard/reviews",
    summary="Obtener resumen de reseñas",
    description="Devuelve el promedio de calificaciones y las reseñas recientes para un alojamiento. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Resumen de reseñas obtenido exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_reviews(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)],
        limit: int = 5
):
    print(f"Fetching reviews for accommodation {accommodation_id} by user: {current_user.username}")
    return await get_reviews_summary(db, accommodation_id, limit)

@router.get(
    "/dashboard/performance",
    summary="Obtener métricas de rendimiento",
    description="Devuelve métricas como reservas por habitación y tasa de cancelaciones para un alojamiento en un período. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Métricas de rendimiento obtenidas exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_performance(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    print(f"Fetching performance for accommodation {accommodation_id} by user: {current_user.username}")
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    return await calculate_performance(db, accommodation_id, start, end)

@router.get(
    "/dashboard/recent-activity",
    summary="Obtener actividad reciente",
    description="Devuelve las últimas reservas, check-ins y check-outs de hoy para un alojamiento. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Actividad reciente obtenida exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_recent_activity(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)]
):
    print(f"Fetching recent activity for accommodation {accommodation_id} by user: {current_user.username}")
    return await recent_activity(db, accommodation_id)

@router.get(
    "/dashboard/maintenance",
    summary="Obtener resumen de mantenimiento",
    description="Devuelve las tareas de mantenimiento pendientes o en progreso para un alojamiento. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Resumen de mantenimiento obtenido exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"}
    },
)
async def get_maintenance(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)]
):
    print(f"Fetching maintenance for accommodation {accommodation_id} by user: {current_user.username}")
    return await get_maintenance_summary(db, accommodation_id)

@router.get(
    "/dashboard/daily-metrics",
    summary="Obtener métricas diarias",
    description="Devuelve ingresos estimados, habitaciones ocupadas, tasa de ocupación, reservas y problemas de mantenimiento por día para un alojamiento en un período. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Métricas diarias obtenidas exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"},
        400: {"description": "Formato de fecha inválido"}
    },
)
async def get_daily_metrics(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    print(f"Fetching daily metrics for accommodation {accommodation_id} by user: {current_user.username}")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de fecha inválido, use YYYY-MM-DD"
        )
    return await daily_metrics(db, accommodation_id, start, end)



@router.get(
    "/dashboard/top-revenue-days-by-weekday",
    summary="Obtener días de la semana más rentables",
    description="Devuelve los días de la semana (lunes a domingo) con mayores ingresos promedio estimados para un alojamiento en un período, ordenados de mayor a menor. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Días de la semana más rentables obtenidos exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"},
        400: {"description": "Formato de fecha inválido o start_date mayor a end_date"}
    },
)
async def get_top_revenue_days_by_weekday(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    print(f"Fetching top revenue days by weekday for accommodation {accommodation_id} by user: {current_user.username}, period: {start_date} to {end_date}")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        if start and end and start > end:
            raise HTTPException(status_code=400, detail="start_date debe ser menor o igual a end_date")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de fecha inválido, use YYYY-MM-DD"
        )
    return await top_revenue_days_by_weekday(db, accommodation_id, start, end)

@router.get(
    "/dashboard/summary",
    summary="Obtener resumen de métricas del alojamiento",
    description="Devuelve un resumen de métricas como ocupación, ingresos por tipo de habitación, servicios adicionales, reservas y mantenimientos para un alojamiento en un período. Solo accesible para usuarios con rol 'admin' o 'employee'.",
    responses={
        200: {"description": "Resumen obtenido exitosamente"},
        403: {"description": "No autorizado (requiere rol admin o employee)"},
        401: {"description": "No autenticado o token inválido"},
        400: {"description": "Formato de fecha inválido o start_date mayor a end_date"}
    },
)
async def get_accommodation_summary(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_admin_or_employee_user)],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    print(f"Fetching summary for accommodation {accommodation_id} by user: {current_user.username}, period: {start_date} to {end_date}")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        if start and end and start > end:
            raise HTTPException(status_code=400, detail="start_date debe ser menor o igual a end_date")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de fecha inválido, use YYYY-MM-DD"
        )
    return await accommodation_summary(db, accommodation_id, start, end)