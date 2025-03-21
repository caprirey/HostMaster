from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_active_user, get_db
from app.models.pydantic_models import (
    Accommodation, AccommodationBase, Room, RoomBase, RoomUpdate,
    City, CityBase, Country, CountryBase, State, StateBase, RoomType, RoomTypeBase, User,
    Reservation, ReservationBase, Image, ImageBase, AccommodationUpdate
)
from app.services.hotel import (
    create_accommodation, create_room, get_accommodations, accommodation, get_rooms,
    create_country, create_state, create_city, create_room_type,
    get_countries, get_country, get_states, get_state, get_cities, get_city,
    create_reservation, get_reservations, create_image, get_images
)
from datetime import date
from app.models.sqlalchemy_models import UserTable

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


@router.patch("/accommodations/{id}", response_model=Accommodation)
async def update_accommodation_route(
        id: int,
        accommodation_data: AccommodationUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await accommodation.update_accommodation(db, id, accommodation_data, current_user.username)

@router.post("/room_types/", response_model=RoomType)
async def create_room_type_route(
        room_type_data: RoomTypeBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_room_type(db, room_type_data)


@router.get("/room_types/", response_model=List[RoomType])
async def get_room_types_route(
        accommodation_id: int | None = Query(None),
        db: AsyncSession = Depends(get_db),
        current_user: UserTable = Depends(get_current_active_user)
):
    return await accommodation.get_room_types(db, current_user.username, accommodation_id)


@router.get("/room_types/{id}", response_model=RoomType)
async def get_room_type_route(
        id: int,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    return await accommodation.get_room_type(db, id)


@router.post("/rooms/", response_model=Room)
async def create_room_route(
        room_data: RoomBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await accommodation.create_room(db, room_data, current_user.username)

@router.post("/rooms/", response_model=Room)
async def create_room_route(
        room_data: RoomBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await accommodation.create_room(db, room_data, current_user.username)

@router.patch("/rooms/{id}", response_model=Room)
async def update_room_route(
        id: int,
        room_data: RoomUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await accommodation.update_room(db, id, room_data, current_user.username)

@router.post("/reservations/", response_model=Reservation)
async def create_reservation_route(
        reservation_data: ReservationBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_reservation(db, reservation_data, current_user.username)

@router.get("/reservations/", response_model=List[Reservation])
async def get_reservations_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_reservations(db, current_user.username)

@router.post("/images/", response_model=Image)
async def create_image_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        image_data: ImageBase = Depends(),
        image: UploadFile = File(...),
):
    return await create_image(db, image, image_data, current_user.username)

@router.get("/images/", response_model=List[Image])
async def get_images_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        accommodation_id: Optional[int] = Query(None),
        room_id: Optional[int] = Query(None),
):
    return await get_images(db, current_user.username, accommodation_id, room_id)


@router.post("/upload_multiple_images/", response_model=List[Image])
async def upload_multiple_images_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        request: ImageBase = Depends(),
        files: List[UploadFile] = File(...),
):
    return await accommodation.upload_images(db, request, files, current_user.username)


@router.get("/available_rooms/", response_model=List[Room])
async def get_available_rooms_route(
        start_date: date = Query(...),
        end_date: date = Query(...),
        accommodation_id: int | None = Query(None),
        db: AsyncSession = Depends(get_db),
        current_user: UserTable = Depends(get_current_active_user)
):
    return await accommodation.get_available_rooms(db, start_date, end_date, current_user.username, accommodation_id)


@router.get("/booked_rooms/", response_model=List[Room])
async def get_booked_rooms_route(
        start_date: date = Query(...),
        end_date: date = Query(...),
        accommodation_id: int | None = Query(None),
        db: AsyncSession = Depends(get_db),
        current_user: UserTable = Depends(get_current_active_user)
):
    return await accommodation.get_booked_rooms(db, start_date, end_date, current_user.username, accommodation_id)


@router.get("/rooms/", response_model=List[Room])
async def get_all_rooms_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await accommodation.get_all_rooms(db, current_user.username)