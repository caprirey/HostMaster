from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_active_user, get_db
from app.models.pydantic_models import (
    Accommodation, AccommodationBase, Room, RoomBase,
    City, CityBase, Country, CountryBase, State, StateBase, RoomType, RoomTypeBase, User
)
from app.services.hotel import (
    create_accommodation, create_room, get_accommodations, get_rooms,
    create_country, create_state, create_city, create_room_type,
    get_countries, get_country, get_states, get_state, get_cities, get_city
)

router = APIRouter()

@router.post("/countries/", response_model=Country)
async def create_country_route(
        country_data: CountryBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_country(db, country_data)

@router.get("/countries/", response_model=List[Country])
async def get_countries_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_countries(db)

@router.get("/countries/{country_id}", response_model=Country)
async def get_country_route(
        country_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_country(db, country_id)

@router.post("/states/", response_model=State)
async def create_state_route(
        state_data: StateBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_state(db, state_data)

@router.get("/states/", response_model=List[State])
async def get_states_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_states(db)

@router.get("/states/{state_id}", response_model=State)
async def get_state_route(
        state_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_state(db, state_id)

@router.post("/cities/", response_model=City)
async def create_city_route(
        city_data: CityBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_city(db, city_data)

@router.get("/cities/", response_model=List[City])
async def get_cities_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_cities(db)

@router.get("/cities/{city_id}", response_model=City)
async def get_city_route(
        city_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_city(db, city_id)

@router.post("/accommodations/", response_model=Accommodation)
async def create_accommodation_route(
        accommodation_data: AccommodationBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_accommodation(db, accommodation_data, current_user.username)

@router.get("/accommodations/", response_model=List[Accommodation])
async def get_accommodations_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_accommodations(db, current_user.username)

@router.post("/room_types/", response_model=RoomType)
async def create_room_type_route(
        room_type_data: RoomTypeBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_room_type(db, room_type_data)

@router.post("/rooms/", response_model=Room)
async def create_room_route(
        room_data: RoomBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_room(db, room_data)

@router.get("/rooms/", response_model=List[Room])
async def get_rooms_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        accommodation_id: Optional[int] = Query(None),  # Corregido: valor predeterminado con =
):
    return await get_rooms(db, current_user.username, accommodation_id)