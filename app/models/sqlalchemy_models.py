from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class UserTable(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)
    role = Column(String, default="user")
    reservations = relationship("Reservation", back_populates="user")

class Country(Base):
    __tablename__ = 'countries'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    states = relationship("State", back_populates="country")

class State(Base):
    __tablename__ = 'states'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    country_id = Column(Integer, ForeignKey('countries.id'))
    cities = relationship("City", back_populates="state")
    country = relationship("Country", back_populates="states")

class City(Base):
    __tablename__ = 'cities'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    state_id = Column(Integer, ForeignKey('states.id'))
    accommodations = relationship("Accommodation", back_populates="city")
    state = relationship("State", back_populates="cities")

class Accommodation(Base):
    __tablename__ = 'accommodations'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city_id = Column(Integer, ForeignKey('cities.id'))
    created_by = Column(String, ForeignKey('users.username'), nullable=False)
    rooms = relationship("Room", back_populates="accommodation")
    city = relationship("City", back_populates="accommodations")

class RoomType(Base):
    __tablename__ = 'room_types'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rooms = relationship("Room", back_populates="room_type")  # Cambiado de "type" a "room_type"

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True, index=True)
    accommodation_id = Column(Integer, ForeignKey('accommodations.id'))
    type_id = Column(Integer, ForeignKey('room_types.id'))
    number = Column(String, nullable=False)
    accommodation = relationship("Accommodation", back_populates="rooms")
    room_type = relationship("RoomType", back_populates="rooms")  # Cambiado de "type" a "room_type"
    reservations = relationship("Reservation", back_populates="room")

class Reservation(Base):
    __tablename__ = 'reservations'
    id = Column(Integer, primary_key=True, index=True)
    user_username = Column(String, ForeignKey('users.username'), nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    user = relationship("UserTable", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")