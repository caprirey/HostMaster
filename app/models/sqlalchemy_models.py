from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, UniqueConstraint, Float, Table
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
    address = Column(String, nullable=False)  # Nuevo campo
    information = Column(String, nullable=False)  # Nuevo campo
    rooms = relationship("Room", back_populates="accommodation")
    city = relationship("City", back_populates="accommodations")
    images = relationship("Image", back_populates="accommodation")  # Relación con imágenes

class RoomType(Base):
    __tablename__ = 'room_types'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    max_guests = Column(Integer, nullable=False)
    rooms = relationship("Room", back_populates="room_type")

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True, index=True)
    accommodation_id = Column(Integer, ForeignKey('accommodations.id'))
    type_id = Column(Integer, ForeignKey('room_types.id'))
    number = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)  # Nuevo campo
    accommodation = relationship("Accommodation", back_populates="rooms")
    room_type = relationship("RoomType", back_populates="rooms")
    reservations = relationship("Reservation", back_populates="room")
    images = relationship("Image", back_populates="room")  # Relación con imágenes

    __table_args__ = (
        UniqueConstraint('accommodation_id', 'number', name='uix_accommodation_number'),
    )

class Reservation(Base):
    __tablename__ = 'reservations'
    id = Column(Integer, primary_key=True, index=True)
    user_username = Column(String, ForeignKey('users.username'), nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    guest_count = Column(Integer, nullable=False) # Nuevo campo
    user = relationship("UserTable", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")
    extra_services = relationship("ExtraService", secondary="reservation_extra_service", back_populates="reservations")  # Nueva relación

class Image(Base):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)  # URL o ruta de la imagen
    accommodation_id = Column(Integer, ForeignKey('accommodations.id'), nullable=True)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=True)
    accommodation = relationship("Accommodation", back_populates="images")
    room = relationship("Room", back_populates="images")


# Nueva tabla ExtraService
class ExtraService(Base):
    __tablename__ = 'extra_services'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Nombre del servicio (e.g., "Desayuno")
    description = Column(String, nullable=True)  # Descripción opcional
    price = Column(Float, nullable=False)  # Precio del servicio
    reservations = relationship("Reservation", secondary="reservation_extra_service", back_populates="extra_services")  # Relación inversa

# Tabla intermedia ReservationExtraService
reservation_extra_service = Table(
    'reservation_extra_service',
    Base.metadata,
    Column('reservation_id', Integer, ForeignKey('reservations.id'), primary_key=True),
    Column('extra_service_id', Integer, ForeignKey('extra_services.id'), primary_key=True)
)