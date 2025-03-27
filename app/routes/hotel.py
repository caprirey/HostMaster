from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_active_user, get_db
from app.models.pydantic_models import (
    Accommodation, AccommodationBase, Room, RoomBase, RoomUpdate,
    City, CityBase, Country, CountryBase, State, StateBase, RoomType, RoomTypeBase, User,
    Reservation, ReservationBase, ReservationUpdate, Image, ImageBase, AccommodationUpdate, ExtraService,
    ExtraServiceCreate, ExtraServiceUpdate, ReservationExtraService, ReservationExtraServiceCreate, ReservationExtraServiceUpdate
)
from app.services.hotel import (
    create_accommodation, get_accommodations, accommodation,
    create_country, create_state, create_city, create_room_type,
    get_countries, get_country, get_states, get_state, get_cities, get_city,
    create_reservation, get_reservations, create_image, get_images, reservation, extra_service, reservation_extra_service
)
from datetime import date
from app.models.sqlalchemy_models import UserTable


from app.services.hotel import image as images


router = APIRouter()

@router.post("/countries/", response_model=Country)
async def create_country_route(
        country_data: CountryBase,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_country(db, country_data)

@router.get("/countries/", response_model=List[Country])
async def get_countries_route(
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_countries(db)

@router.get("/countries/{country_id}", response_model=Country)
async def get_country_route(
        country_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_country(db, country_id)

@router.post("/states/", response_model=State)
async def create_state_route(
        state_data: StateBase,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_state(db, state_data)

@router.get("/states/", response_model=List[State])
async def get_states_route(
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_states(db)

@router.get("/states/{state_id}", response_model=State)
async def get_state_route(
        state_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_state(db, state_id)

@router.post("/cities/", response_model=City)
async def create_city_route(
        city_data: CityBase,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_city(db, city_data)

@router.get("/cities/", response_model=List[City])
async def get_cities_route(
        db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_cities(db)

@router.get("/cities/{city_id}", response_model=City)
async def get_city_route(
        city_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
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
        accommodation_id: int,
        accommodation_data: AccommodationUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await accommodation.update_accommodation(db, accommodation_id, accommodation_data, current_user.username)

@router.delete("/accommodations/{accommodation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_accommodation_route(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    await accommodation.delete_accommodation(db, accommodation_id, current_user.username)
    return None

@router.post("/room_types/", response_model=RoomType)
async def create_room_type_route(
        room_type_data: RoomTypeBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_room_type(db, room_type_data, current_user.username)


@router.get("/room_types/", response_model=List[RoomType])
async def get_room_types_route(
        db: AsyncSession = Depends(get_db),
        current_user: UserTable = Depends(get_current_active_user)
):
    return await accommodation.get_room_types(db, current_user.username)


@router.get("/room_types/{id}", response_model=RoomType)
async def get_room_type_route(
        room_type_id: int,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    return await accommodation.get_room_type(db, room_type_id)


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
        room_id: int,
        room_data: RoomUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await accommodation.update_room(db, room_id, room_data, current_user.username)

@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_route(
        room_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    await accommodation.delete_room(db, room_id, current_user.username)
    return None

@router.post("/reservations/", response_model=Reservation)
async def create_reservation_route(
        reservation_data: ReservationBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await create_reservation(db, reservation_data, current_user.username)


@router.patch("/reservations/{reservation_id}", response_model=Reservation)
async def update_reservation_route(
        reservation_id: int,
        reservation_data: ReservationUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await reservation.update_reservation(db, reservation_id, reservation_data, current_user.username)


@router.get("/reservations/", response_model=List[Reservation])
async def get_reservations_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await get_reservations(db, current_user.username)

@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation_route(
        reservation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    await reservation.delete_reservation(db, reservation_id, current_user.username)
    return None

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


@router.delete("/images", status_code=status.HTTP_204_NO_CONTENT)
async def delete_images_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
        accommodation_id: Optional[int] = None,
        room_id: Optional[int] = None,
):
    await images.delete_images(db, accommodation_id, room_id, current_user.username)
    return None


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


@router.post("/extra-services/", response_model=ExtraService, status_code=status.HTTP_201_CREATED)
async def create_extra_service_route(
        extra_service_data: ExtraServiceCreate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await extra_service.create_extra_service(db, extra_service_data, current_user.username)

@router.patch("/extra-services/{extra_service_id}", response_model=ExtraService)
async def update_extra_service_route(
        extra_service_id: int,
        extra_service_data: ExtraServiceUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await extra_service.update_extra_service(db, extra_service_id, extra_service_data, current_user.username)

@router.delete("/extra-services/{extra_service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_extra_service_route(
        extra_service_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    await extra_service.delete_extra_service(db, extra_service_id, current_user.username)
    return None



@router.get("/extra-services/{extra_service_id}", response_model=ExtraService)
async def get_extra_service_route(
        extra_service_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await extra_service.get_extra_service(db, extra_service_id, current_user.username)


@router.get("/extra-services/", response_model=List[ExtraService])
async def get_all_extra_services_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await extra_service.get_all_extra_services(db, current_user.username)


@router.post("/reservation-extra-services/", response_model=ReservationExtraService, status_code=status.HTTP_201_CREATED)
async def create_reservation_extra_service_route(
        reservation_extra_data: ReservationExtraServiceCreate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await reservation_extra_service.create_reservation_extra_service(db, reservation_extra_data, current_user.username)


@router.put("/reservation-extra-services/{reservation_id}", response_model=ReservationExtraService)
async def update_reservation_extra_service_route(
        reservation_id: int,
        reservation_extra_data: ReservationExtraServiceUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await reservation_extra_service.update_reservation_extra_service(db, reservation_id, reservation_extra_data, current_user.username)

@router.delete("/reservation-extra-services/{reservation_id}/{extra_service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation_extra_service_route(
        reservation_id: int,
        extra_service_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    await reservation_extra_service.delete_reservation_extra_service(db, reservation_id, extra_service_id, current_user.username)
    return None


@router.get("/reservation-extra-services/{reservation_id}", response_model=List[ReservationExtraService])
async def get_reservation_extra_services_route(
        reservation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    return await reservation_extra_service.get_reservation_extra_services(db, reservation_id, current_user.username)