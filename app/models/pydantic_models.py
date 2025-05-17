from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from app.models.sqlalchemy_models import MaintenanceStatus, MaintenancePriority

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
    role: str = "client"
    firstname: str
    lastname: str
    document_number: str
    image: Optional[str] = None
    phone_number: str

class User(UserBase):
    reviews: List["Review"] = []
    accommodation_ids: List[int] = []
    model_config = {"from_attributes": True}

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    password: str
    accommodation_ids: Optional[List[int]] = None
    role: Optional[str] = "client"
    firstname: str
    lastname: str
    document_number: str
    image: Optional[str] = None
    phone_number: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    accommodation_ids: Optional[List[int]] = None
    role: Optional[str] = None
    password: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    document_number: Optional[str] = None
    image: Optional[str] = None
    phone_number: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

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

class Accommodation(AccommodationBase):
    id: int
    user_usernames: List[str] = []
    images: List["Image"] = []
    reviews: List["Review"] = []
    model_config = {"from_attributes": True}

class AccommodationUpdate(BaseModel):
    name: Optional[str] = None
    city_id: Optional[int] = None
    address: Optional[str] = None
    information: Optional[str] = None
    user_usernames: Optional[List[str]] = None

class RoomTypeBase(BaseModel):
    name: str
    max_guests: int
    description: Optional[str] = None

class RoomType(RoomTypeBase):
    id: int
    model_config = {"from_attributes": True}

class RoomTypeUpdate(BaseModel):
    name: Optional[str] = None
    max_guests: Optional[int] = None
    description: Optional[str] = None

class RoomBase(BaseModel):
    accommodation_id: int
    type_id: int
    number: str
    isAvailable: bool = True
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
    inventory_items: List["RoomInventory"] = []
    products: List["Product"] = []
    model_config = {"from_attributes": True}

class ReservationBase(BaseModel):
    room_id: int
    accommodation_id: int
    start_date: date
    end_date: date
    guest_count: int
    status: str = "pending"
    observations: Optional[str] = None
    user_username: Optional[str] = None

class ReservationUpdate(BaseModel):
    room_id: Optional[int] = None
    accommodation_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    guest_count: Optional[int] = None
    status: Optional[str] = None
    observations: Optional[str] = None
    user_username: Optional[str] = None

class Reservation(ReservationBase):
    id: int
    user_username: str
    extra_services: List["ExtraService"] = []
    model_config = {"from_attributes": True}

class ImageBase(BaseModel):
    accommodation_id: Optional[int] = None
    room_id: Optional[int] = None

class Image(ImageBase):
    id: int
    url: str
    model_config = {"from_attributes": True}

class ExtraServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

class ExtraServiceCreate(ExtraServiceBase):
    pass

class ExtraServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None

class ExtraService(ExtraServiceBase):
    id: int
    model_config = {"from_attributes": True}

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

class ReservationExtraServiceCreate(BaseModel):
    reservation_id: int
    extra_service_id: int

class ReservationExtraService(BaseModel):
    reservation_id: int
    extra_service_id: int
    model_config = {"from_attributes": True}

class ReservationExtraServiceUpdate(BaseModel):
    extra_service_id: int

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None

    @field_validator('price')
    @classmethod
    def price_must_be_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError('Price must be non-negative')
        return v

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None

    @field_validator('price')
    @classmethod
    def price_must_be_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError('Price must be non-negative')
        return v

class Product(ProductBase):
    id: int
    model_config = {"from_attributes": True}

class RoomProductBase(BaseModel):
    room_id: int
    product_id: int
    quantity: int
    needs_restock: bool

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class RoomProductCreate(RoomProductBase):
    pass

class RoomProductUpdate(BaseModel):
    quantity: Optional[int] = None
    needs_restock: Optional[bool] = None

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class RoomProduct(RoomProductBase):
    model_config = {"from_attributes": True}

class RoomProductDetails(BaseModel):
    product: Product
    quantity: int
    needs_restock: bool

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

    model_config = {"from_attributes": True}

# Maintenance Models
class MaintenanceBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    room_id: int = Field(..., gt=0)
    accommodation_id: int = Field(..., gt=0)
    assigned_to: Optional[str] = None

class MaintenanceCreate(MaintenanceBase):
    pass

class MaintenanceUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[MaintenanceStatus] = None
    priority: Optional[MaintenancePriority] = None
    assigned_to: Optional[str] = None

class Maintenance(MaintenanceBase):
    id: int
    status: MaintenanceStatus
    created_by: str
    created_at: date
    updated_at: date
    model_config = {"from_attributes": True}