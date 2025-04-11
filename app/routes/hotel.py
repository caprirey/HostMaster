from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.utils.auth import get_current_active_user, get_db
from app.models.pydantic_models import (
    Accommodation, AccommodationBase, AccommodationUpdate,
    Room, RoomBase, RoomUpdate, RoomType, RoomTypeBase,
    City, CityBase, Country, CountryBase, State, StateBase,
    User, Reservation, ReservationBase, ReservationUpdate,
    Image, ImageBase, ExtraService, ExtraServiceCreate, ExtraServiceUpdate,
    ReservationExtraService, ReservationExtraServiceCreate, ReservationExtraServiceUpdate,
    Review as ReviewPydantic, ReviewCreate, ReviewUpdate,
    RoomInventory as RoomInventoryPydantic, RoomInventoryCreate, RoomInventoryUpdate
)
from app.models.sqlalchemy_models import UserTable
from app.services.hotel import (
    create_accommodation, get_accommodations, accommodation,
    create_country, create_state, create_city,
    get_countries, get_country, get_states, get_state, get_cities, get_city,
    create_reservation, get_reservations, create_image, get_images, reservation,
    extra_service, reservation_extra_service, review, room_inventory, room_type, room
)
from app.services.hotel import image as images
from app.services.hotel.room import get_rooms_by_accommodation

router = APIRouter()

# --- Countries ---
@router.post("/countries/", response_model=Country, tags=["Countries"], summary="Create a new country")
async def create_country_route(
        country_data: CountryBase,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new country in the system."""
    return await create_country(db, country_data)

@router.get("/countries/", response_model=List[Country], tags=["Countries"], summary="Get all countries")
async def get_countries_route(
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve a list of all countries."""
    return await get_countries(db)

@router.get("/countries/{country_id}", response_model=Country, tags=["Countries"], summary="Get a country by ID")
async def get_country_route(
        country_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve details of a specific country by its ID."""
    return await get_country(db, country_id)

# --- States ---
@router.post("/states/", response_model=State, tags=["States"], summary="Create a new state")
async def create_state_route(
        state_data: StateBase,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new state in the system."""
    return await create_state(db, state_data)

@router.get("/states/", response_model=List[State], tags=["States"], summary="Get all states")
async def get_states_route(
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve a list of all states."""
    return await get_states(db)

@router.get("/states/{state_id}", response_model=State, tags=["States"], summary="Get a state by ID")
async def get_state_route(
        state_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve details of a specific state by its ID."""
    return await get_state(db, state_id)

# --- Cities ---
@router.post("/cities/", response_model=City, tags=["Cities"], summary="Create a new city")
async def create_city_route(
        city_data: CityBase,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new city in the system."""
    return await create_city(db, city_data)

@router.get("/cities/", response_model=List[City], tags=["Cities"], summary="Get all cities")
async def get_cities_route(
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve a list of all cities."""
    return await get_cities(db)

@router.get("/cities/{city_id}", response_model=City, tags=["Cities"], summary="Get a city by ID")
async def get_city_route(
        city_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve details of a specific city by its ID."""
    return await get_city(db, city_id)

# --- Accommodations ---
@router.post("/accommodations/", response_model=Accommodation, tags=["Accommodations"], summary="Create a new accommodation")
async def create_accommodation_route(
        accommodation_data: AccommodationBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Create a new accommodation. Restricted to admin and employee roles."""
    return await create_accommodation(db, accommodation_data, current_user.username)

@router.get("/accommodations/", response_model=List[Accommodation], tags=["Accommodations"], summary="Get accommodations")
async def get_accommodations_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Retrieve accommodations based on user role (admin: all, employee: related, user: all without usernames)."""
    return await get_accommodations(db, current_user.username)

@router.patch("/accommodations/{accommodation_id}", response_model=Accommodation, tags=["Accommodations"], summary="Update an accommodation")
async def update_accommodation_route(
        accommodation_id: int,
        accommodation_data: AccommodationUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Update an existing accommodation. Restricted to admin and employee roles."""
    return await accommodation.update_accommodation(db, accommodation_id, accommodation_data, current_user.username)

@router.delete("/accommodations/{accommodation_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Accommodations"], summary="Delete an accommodation")
async def delete_accommodation_route(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Delete an accommodation if it has no rooms or reviews. Restricted to admin and related users."""
    await accommodation.delete_accommodation(db, accommodation_id, current_user.username)
    return None

# --- Room Types ---
@router.post("/room-types/", response_model=RoomType, status_code=status.HTTP_201_CREATED, tags=["Room Types"], summary="Create a room type")
async def create_room_type_route(
        room_type_data: RoomTypeBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Create a new room type."""
    return await room_type.create_room_type(db, room_type_data, current_user)

@router.get("/room-types/", response_model=List[RoomType], tags=["Room Types"], summary="Get all room types")
async def get_room_types_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Retrieve a list of all room types."""
    return await room_type.get_room_types(db, current_user)

@router.get("/room-types/{room_type_id}", response_model=RoomType, tags=["Room Types"], summary="Get a room type by ID")
async def get_room_type_route(
        room_type_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Retrieve details of a specific room type by its ID."""
    return await room_type.get_room_type(db, room_type_id, current_user)

@router.put("/room-types/{room_type_id}", response_model=RoomType, tags=["Room Types"], summary="Update a room type")
async def update_room_type_route(
        room_type_id: int,
        room_type_update: RoomTypeBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Update an existing room type."""
    return await room_type.update_room_type(db, room_type_id, room_type_update, current_user)

@router.delete("/room-types/{room_type_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Room Types"], summary="Delete a room type")
async def delete_room_type_route(
        room_type_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Delete a room type."""
    await room_type.delete_room_type(db, room_type_id, current_user)
    return None

# --- Rooms ---
@router.post("/rooms/", response_model=Room, tags=["Rooms"], summary="Create a new room")
async def create_room_route(
        room_data: RoomBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Create a new room in an accommodation. Restricted to admin and related users."""
    return await room.create_room(db, room_data, current_user.username)

@router.get("/rooms/", response_model=List[Room], tags=["Rooms"], summary="Get all rooms")
async def get_all_rooms_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Retrieve all rooms (admin/user: all, employee: related accommodations)."""
    return await room.get_all_rooms(db, current_user.username)

@router.get("/accommodations/{accommodation_id}/rooms/", response_model=List[Room], tags=["Rooms"], summary="Get rooms by accommodation")
async def get_rooms_by_accommodation_route(
        accommodation_id: int,
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
        db: AsyncSession = Depends(get_db)
):
    """Retrieve all rooms for a specific accommodation (admin/user: all, employee: related)."""
    return await get_rooms_by_accommodation(db, accommodation_id, current_user.username)

@router.patch("/rooms/{room_id}", response_model=Room, tags=["Rooms"], summary="Update a room")
async def update_room_route(
        room_id: int,
        room_data: RoomUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Update an existing room. Restricted to admin and related users."""
    return await room.update_room(db, room_id, room_data, current_user.username)

@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Rooms"], summary="Delete a room")
async def delete_room_route(
        room_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Delete a room if it has no reservations. Restricted to admin and related users."""
    await room.delete_room(db, room_id, current_user.username)
    return None

@router.get("/available_rooms/", response_model=List[Room], tags=["Rooms"], summary="Get available rooms")
async def get_available_rooms_route(
        start_date: date = Query(..., description="Start date of the period"),
        end_date: date = Query(..., description="End date of the period"),
        accommodation_id: int | None = Query(None, description="Optional accommodation ID filter"),
        db: AsyncSession = Depends(get_db),
        current_user: UserTable = Depends(get_current_active_user)
):
    """Retrieve available rooms for a given date range."""
    return await room.get_available_rooms(db, start_date, end_date, current_user.username, accommodation_id)

@router.get("/booked_rooms/", response_model=List[Room], tags=["Rooms"], summary="Get booked rooms")
async def get_booked_rooms_route(
        start_date: date = Query(..., description="Start date of the period"),
        end_date: date = Query(..., description="End date of the period"),
        accommodation_id: int | None = Query(None, description="Optional accommodation ID filter"),
        db: AsyncSession = Depends(get_db),
        current_user: UserTable = Depends(get_current_active_user)
):
    """Retrieve booked rooms for a given date range."""
    return await room.get_booked_rooms(db, start_date, end_date, current_user.username, accommodation_id)

# --- Reservations ---
@router.post("/reservations/", response_model=Reservation, tags=["Reservations"], summary="Create a reservation")
async def create_reservation_route(
        reservation_data: ReservationBase,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Create a new reservation."""
    return await create_reservation(db, reservation_data, current_user.username)

@router.get("/reservations/", response_model=List[Reservation], tags=["Reservations"], summary="Get reservations")
async def get_reservations_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Retrieve reservations for the current user."""
    return await get_reservations(db, current_user.username)

@router.patch("/reservations/{reservation_id}", response_model=Reservation, tags=["Reservations"], summary="Update a reservation")
async def update_reservation_route(
        reservation_id: int,
        reservation_data: ReservationUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Update an existing reservation."""
    return await reservation.update_reservation(db, reservation_id, reservation_data, current_user.username)

@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Reservations"], summary="Delete a reservation")
async def delete_reservation_route(
        reservation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Delete a reservation."""
    await reservation.delete_reservation(db, reservation_id, current_user.username)
    return None

# --- Images ---
@router.post("/images/", response_model=Image, tags=["Images"], summary="Upload a single image")
async def create_image_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        image_data: ImageBase = Depends(),
        image: UploadFile = File(...),
):
    """Upload a single image for an accommodation or room."""
    return await create_image(db, image, image_data, current_user.username)

@router.get("/images/", response_model=List[Image], tags=["Images"], summary="Get images")
async def get_images_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        accommodation_id: Optional[int] = Query(None, description="Filter by accommodation ID"),
        room_id: Optional[int] = Query(None, description="Filter by room ID"),
):
    """Retrieve images, optionally filtered by accommodation or room."""
    return await get_images(db, current_user.username, accommodation_id, room_id)

@router.post("/upload_multiple_images/", response_model=List[Image], tags=["Images"], summary="Upload multiple images")
async def upload_multiple_images_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        request: ImageBase = Depends(),
        files: List[UploadFile] = File(...),
):
    """Upload multiple images for an accommodation or room."""
    return await room.upload_images(db, request, files, current_user.username)

@router.delete("/images", status_code=status.HTTP_204_NO_CONTENT, tags=["Images"], summary="Delete images")
async def delete_images_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
        accommodation_id: Optional[int] = Query(None, description="Delete images by accommodation ID"),
        room_id: Optional[int] = Query(None, description="Delete images by room ID"),
):
    """Delete images associated with an accommodation or room."""
    await images.delete_images(db, accommodation_id, room_id, current_user.username)
    return None

# --- Extra Services ---
@router.post("/extra-services/", response_model=ExtraService, status_code=status.HTTP_201_CREATED, tags=["Extra Services"], summary="Create an extra service")
async def create_extra_service_route(
        extra_service_data: ExtraServiceCreate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Create a new extra service."""
    return await extra_service.create_extra_service(db, extra_service_data, current_user.username)

@router.get("/extra-services/", response_model=List[ExtraService], tags=["Extra Services"], summary="Get all extra services")
async def get_all_extra_services_route(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Retrieve a list of all extra services."""
    return await extra_service.get_all_extra_services(db, current_user.username)

@router.get("/extra-services/{extra_service_id}", response_model=ExtraService, tags=["Extra Services"], summary="Get an extra service by ID")
async def get_extra_service_route(
        extra_service_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Retrieve details of a specific extra service by its ID."""
    return await extra_service.get_extra_service(db, extra_service_id, current_user.username)

@router.patch("/extra-services/{extra_service_id}", response_model=ExtraService, tags=["Extra Services"], summary="Update an extra service")
async def update_extra_service_route(
        extra_service_id: int,
        extra_service_data: ExtraServiceUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Update an existing extra service."""
    return await extra_service.update_extra_service(db, extra_service_id, extra_service_data, current_user.username)

@router.delete("/extra-services/{extra_service_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Extra Services"], summary="Delete an extra service")
async def delete_extra_service_route(
        extra_service_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Delete an extra service."""
    await extra_service.delete_extra_service(db, extra_service_id, current_user.username)
    return None

# --- Reservation Extra Services ---
@router.post("/reservation-extra-services/", response_model=ReservationExtraService, status_code=status.HTTP_201_CREATED, tags=["Reservation Extra Services"], summary="Link extra service to reservation")
async def create_reservation_extra_service_route(
        reservation_extra_data: ReservationExtraServiceCreate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Link an extra service to a reservation."""
    return await reservation_extra_service.create_reservation_extra_service(db, reservation_extra_data, current_user.username)

@router.get("/reservation-extra-services/{reservation_id}", response_model=List[ReservationExtraService], tags=["Reservation Extra Services"], summary="Get extra services for a reservation")
async def get_reservation_extra_services_route(
        reservation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Retrieve extra services linked to a specific reservation."""
    return await reservation_extra_service.get_reservation_extra_services(db, reservation_id, current_user.username)

@router.put("/reservation-extra-services/{reservation_id}", response_model=ReservationExtraService, tags=["Reservation Extra Services"], summary="Update reservation extra service")
async def update_reservation_extra_service_route(
        reservation_id: int,
        reservation_extra_data: ReservationExtraServiceUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Update an extra service linked to a reservation."""
    return await reservation_extra_service.update_reservation_extra_service(db, reservation_id, reservation_extra_data, current_user.username)

@router.delete("/reservation-extra-services/{reservation_id}/{extra_service_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Reservation Extra Services"], summary="Unlink extra service from reservation")
async def delete_reservation_extra_service_route(
        reservation_id: int,
        extra_service_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Remove an extra service from a reservation."""
    await reservation_extra_service.delete_reservation_extra_service(db, reservation_id, extra_service_id, current_user.username)
    return None

# --- Reviews ---
@router.post("/reviews/", response_model=ReviewPydantic, status_code=status.HTTP_201_CREATED, tags=["Reviews"], summary="Create a review")
async def create_review_route(
        review_data: ReviewCreate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Create a new review for an accommodation."""
    return await review.create_review(db, review_data, current_user.username)

@router.get("/reviews/accommodation/{accommodation_id}", response_model=List[ReviewPydantic], tags=["Reviews"], summary="Get reviews by accommodation")
async def get_reviews_by_accommodation_route(
        accommodation_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve all reviews for a specific accommodation."""
    return await review.get_reviews_by_accommodation(db, accommodation_id)

@router.get("/reviews/{review_id}", response_model=ReviewPydantic, tags=["Reviews"], summary="Get a review by ID")
async def get_review_route(
        review_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve details of a specific review by its ID."""
    return await review.get_review(db, review_id)

@router.put("/reviews/{review_id}", response_model=ReviewPydantic, tags=["Reviews"], summary="Update a review")
async def update_review_route(
        review_id: int,
        review_data: ReviewUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Update an existing review."""
    return await review.update_review(db, review_id, review_data, current_user.username)

@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Reviews"], summary="Delete a review")
async def delete_review_route(
        review_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Delete a review."""
    await review.delete_review(db, review_id, current_user.username)
    return None

# --- Room Inventory ---
@router.post("/room-inventory/", response_model=RoomInventoryPydantic, status_code=status.HTTP_201_CREATED, tags=["Room Inventory"], summary="Create room inventory")
async def create_room_inventory_route(
        inventory_data: RoomInventoryCreate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Create a new inventory item for a room."""
    return await room_inventory.create_room_inventory(db, inventory_data, current_user.username)

@router.get("/room-inventory/room/{room_id}", response_model=List[RoomInventoryPydantic], tags=["Room Inventory"], summary="Get inventory by room")
async def get_room_inventory_by_room_route(
        room_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve all inventory items for a specific room."""
    return await room_inventory.get_room_inventory_by_room(db, room_id)

@router.get("/room-inventory/{inventory_id}", response_model=RoomInventoryPydantic, tags=["Room Inventory"], summary="Get inventory by ID")
async def get_room_inventory_route(
        inventory_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve details of a specific inventory item by its ID."""
    return await room_inventory.get_room_inventory(db, inventory_id)

@router.put("/room-inventory/{inventory_id}", response_model=RoomInventoryPydantic, tags=["Room Inventory"], summary="Update room inventory")
async def update_room_inventory_route(
        inventory_id: int,
        inventory_data: RoomInventoryUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Update an existing room inventory item."""
    return await room_inventory.update_room_inventory(db, inventory_id, inventory_data, current_user.username)

@router.delete("/room-inventory/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Room Inventory"], summary="Delete room inventory")
async def delete_room_inventory_route(
        inventory_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[UserTable, Depends(get_current_active_user)],
):
    """Delete a room inventory item."""
    await room_inventory.delete_room_inventory(db, inventory_id, current_user.username)
    return None