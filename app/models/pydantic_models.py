from pydantic import BaseModel
from typing import Optional, List
from datetime import date

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

class Accommodation(AccommodationBase):
    id: int
    created_by: str
    images: List["Image"] = []
    model_config = {"from_attributes": True}

class RoomTypeBase(BaseModel):
    name: str

class RoomType(RoomTypeBase):
    id: int
    model_config = {"from_attributes": True}

class RoomBase(BaseModel):
    accommodation_id: int
    type_id: int
    number: str

class Room(RoomBase):
    id: int
    images: List["Image"] = []
    model_config = {"from_attributes": True}

class ReservationBase(BaseModel):
    room_id: int
    start_date: date
    end_date: date

class Reservation(ReservationBase):
    id: int
    user_username: str
    model_config = {"from_attributes": True}

class ImageBase(BaseModel):
    accommodation_id: Optional[int] = None
    room_id: Optional[int] = None

class Image(ImageBase):
    id: int
    url: str
    model_config = {"from_attributes": True}