from pydantic import BaseModel
from typing import Optional, List

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
    accommodation_ids: List[int] = []
    model_config = {"from_attributes": True}

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    password: str
    accommodation_ids: List[int] = []

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    accommodation_ids: Optional[List[int]] = None

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
    model_config = {"from_attributes": True}

class RoomTypeBase(BaseModel):
    name: str

class RoomType(RoomTypeBase):
    id: int
    model_config = {"from_attributes": True}

class RoomBase(BaseModel):
    accommodation_id: int
    type_id: int
    number: str  # Añadido para creación

class Room(RoomBase):
    id: int
    model_config = {"from_attributes": True}