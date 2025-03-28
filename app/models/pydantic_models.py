from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime


# Auth Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class UserBase(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None
    role: str = "user"

class User(UserBase):
    reviews: List["Review"] = []  # Nueva relación
    model_config = {"from_attributes": True}

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None

# Hotel Models
class CountryBase(BaseModel):
    name: str

class Country(CountryBase):
    id: int
    model_config = {"from_attributes": True}

class StateBase(BaseModel):
    name: str
    country_id: int

class State(StateBase):
    id: int
    model_config = {"from_attributes": True}

class CityBase(BaseModel):
    name: str
    state_id: int

class City(CityBase):
    id: int
    model_config = {"from_attributes": True}

class AccommodationBase(BaseModel):
    name: str
    city_id: int
    address: str
    information: str

class AccommodationUpdate(BaseModel):
    name: Optional[str] = None
    city_id: Optional[int] = None
    address: Optional[str] = None
    information: Optional[str] = None

class Accommodation(AccommodationBase):
    id: int
    created_by: str
    images: List["Image"] = []
    reviews: List["Review"] = []  # Nueva relación
    model_config = {"from_attributes": True}

class RoomTypeBase(BaseModel):
    name: str
    max_guests: int

class RoomType(RoomTypeBase):
    id: int
    model_config = {"from_attributes": True}

class RoomBase(BaseModel):
    accommodation_id: int
    type_id: int
    number: str
    isAvailable: bool = True  # Nuevo campo, opcional con default True
    price: float

class RoomUpdate(BaseModel):
    accommodation_id: Optional[int] = None
    type_id: Optional[int] = None
    number: Optional[str] = None
    isAvailable: Optional[bool] = None
    price: Optional[float] = None

class Room(RoomBase):
    id: int
    images: List["Image"] = []
    inventory_items: List["RoomInventory"] = []  # Nueva relación
    model_config = {"from_attributes": True}

class ReservationBase(BaseModel):
    room_id: int
    start_date: date
    end_date: date
    guest_count: int  # Nuevo campo para el número de huéspedes

class ReservationUpdate(BaseModel):
    room_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    guest_count: Optional[int] = None  # Opcional para actualizaciones


class Reservation(ReservationBase):
    id: int
    user_username: str
    extra_services: List["ExtraService"] = []  # Nueva relación
    model_config = {"from_attributes": True}

class ImageBase(BaseModel):
    accommodation_id: Optional[int] = None
    room_id: Optional[int] = None

class Image(ImageBase):
    id: int
    url: str
    model_config = {"from_attributes": True}

# Nuevos modelos para ExtraService
class ExtraServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

class ExtraServiceCreate(ExtraServiceBase):
    pass  # Hereda todo de ExtraServiceBase

class ExtraServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None

class ExtraService(ExtraServiceBase):
    id: int
    model_config = {"from_attributes": True}


# Nuevos modelos para Review
class ReviewBase(BaseModel):
    accommodation_id: int
    rating: int
    comment: Optional[str] = None

    @field_validator('rating')
    @classmethod
    def rating_must_be_valid(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None

    @field_validator('rating')
    @classmethod
    def rating_must_be_valid_if_provided(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Rating must be between 1 and 5')
        return v

class Review(ReviewBase):
    id: int
    user_username: str
    created_at: datetime
    model_config = {"from_attributes": True}


# Nuevos modelos para RoomInventory
class RoomInventoryBase(BaseModel):
    room_id: int
    product_name: str
    quantity: int
    min_quantity: int

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Quantity must be non-negative')
        return v

    @field_validator('min_quantity')
    @classmethod
    def min_quantity_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Min quantity must be non-negative')
        return v

class RoomInventoryCreate(RoomInventoryBase):
    pass

class RoomInventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    min_quantity: Optional[int] = None
    needs_restock: Optional[bool] = None

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_non_negative_if_provided(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError('Quantity must be non-negative')
        return v

    @field_validator('min_quantity')
    @classmethod
    def min_quantity_must_be_non_negative_if_provided(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError('Min quantity must be non-negative')
        return v

class RoomInventory(RoomInventoryBase):
    id: int
    needs_restock: bool
    model_config = {"from_attributes": True}


# Nuevo modelo para ReservationExtraService
class ReservationExtraServiceCreate(BaseModel):
    reservation_id: int
    extra_service_id: int

class ReservationExtraService(BaseModel):
    reservation_id: int
    extra_service_id: int
    model_config = {"from_attributes": True}

# Nuevo modelo para actualización
class ReservationExtraServiceUpdate(BaseModel):
    extra_service_id: int  # Solo permitimos actualizar el servicio extra


class ReviewBase(BaseModel):
    accommodation_id: int
    rating: int
    comment: Optional[str] = None

    @field_validator('rating')
    @classmethod
    def rating_must_be_valid(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None

    @field_validator('rating')
    @classmethod
    def rating_must_be_valid_if_provided(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Rating must be between 1 and 5')
        return v

class Review(ReviewBase):
    id: int
    user_username: str
    created_at: datetime
    model_config = {"from_attributes": True}


class RoomInventoryBase(BaseModel):
    room_id: int
    product_name: str
    quantity: int
    min_quantity: int

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Quantity must be non-negative')
        return v

    @field_validator('min_quantity')
    @classmethod
    def min_quantity_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Min quantity must be non-negative')
        return v

class RoomInventoryCreate(RoomInventoryBase):
    pass

class RoomInventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    min_quantity: Optional[int] = None
    needs_restock: Optional[bool] = None

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_non_negative_if_provided(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError('Quantity must be non-negative')
        return v

    @field_validator('min_quantity')
    @classmethod
    def min_quantity_must_be_non_negative_if_provided(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError('Min quantity must be non-negative')
        return v

class RoomInventory(RoomInventoryBase):
    id: int
    needs_restock: bool
    model_config = {"from_attributes": True}