from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
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
    rooms = relationship("Room", back_populates="type")

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True, index=True)
    accommodation_id = Column(Integer, ForeignKey('accommodations.id'))
    type_id = Column(Integer, ForeignKey('room_types.id'))
    number = Column(String, nullable=False)  # Nueva columna para el número de la habitación
    accommodation = relationship("Accommodation", back_populates="rooms")
    type = relationship("RoomType", back_populates="rooms")