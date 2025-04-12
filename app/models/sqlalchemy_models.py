from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, UniqueConstraint, Float, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

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
    reviews = relationship("Review", back_populates="user")
    accommodations = relationship(
        "Accommodation",
        secondary="user_accommodation",  # Usar la tabla intermedia
        back_populates="users"
    )

# Tabla intermedia UserAccommodation
user_accommodation = Table(
    'user_accommodation',
    Base.metadata,
    Column('user_username', String, ForeignKey('users.username'), primary_key=True),
    Column('accommodation_id', Integer, ForeignKey('accommodations.id'), primary_key=True)
)

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
    address = Column(String, nullable=False)
    information = Column(String, nullable=False)
    rooms = relationship("Room", back_populates="accommodation")
    city = relationship("City", back_populates="accommodations")
    images = relationship("Image", back_populates="accommodation")
    reviews = relationship("Review", back_populates="accommodation")
    users = relationship(
        "UserTable",
        secondary="user_accommodation",  # Usar la tabla intermedia
        back_populates="accommodations"
    )

class RoomType(Base):
    __tablename__ = 'room_types'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    max_guests = Column(Integer, nullable=False)
    description = Column(String, nullable=True)  # Nuevo campo description
    rooms = relationship("Room", back_populates="room_type")

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True, index=True)
    accommodation_id = Column(Integer, ForeignKey('accommodations.id'))
    type_id = Column(Integer, ForeignKey('room_types.id'))
    number = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    isAvailable = Column(Boolean, default=True, nullable=False)  # Nuevo campo
    accommodation = relationship("Accommodation", back_populates="rooms")
    room_type = relationship("RoomType", back_populates="rooms")
    reservations = relationship("Reservation", back_populates="room")
    images = relationship("Image", back_populates="room")  # Relación con imágenes
    inventory_items = relationship("RoomInventory", back_populates="room")  # Nueva relación
    products = relationship(  # Nueva relación muchos a muchos
        "Product",
        secondary="room_product",
        back_populates="rooms"
    )
    __table_args__ = (
        UniqueConstraint('accommodation_id', 'number', name='uix_accommodation_number'),
    )

class Reservation(Base):
    __tablename__ = 'reservations'
    id = Column(Integer, primary_key=True, index=True)
    user_username = Column(String, ForeignKey('users.username'), nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    accommodation_id = Column(Integer, ForeignKey('accommodations.id'), nullable=False)  # Nuevo campo
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    guest_count = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")  # Nuevo campo como String sin restricciones
    observations = Column(String, nullable=True)  # Nuevo campo opcional
    user = relationship("UserTable", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")
    accommodation = relationship("Accommodation")  # Nueva relación
    extra_services = relationship("ExtraService", secondary="reservation_extra_service", back_populates="reservations")


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

# Nuevo modelo Review
class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True, index=True)
    accommodation_id = Column(Integer, ForeignKey('accommodations.id'), nullable=False)
    user_username = Column(String, ForeignKey('users.username'), nullable=False)
    rating = Column(Integer, nullable=False)  # Calificación de 1 a 5
    comment = Column(String, nullable=True)  # Comentario opcional
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Fecha de creación

    accommodation = relationship("Accommodation", back_populates="reviews")
    user = relationship("UserTable", back_populates="reviews")

    __table_args__ = (
        UniqueConstraint('accommodation_id', 'user_username', name='uix_accommodation_user'),
    )

    # Nuevo modelo RoomInventory
class RoomInventory(Base):
    __tablename__ = 'room_inventory'
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    product_name = Column(String, nullable=False)  # Nombre del producto
    quantity = Column(Integer, nullable=False, default=0)  # Cantidad disponible
    min_quantity = Column(Integer, nullable=False, default=0)  # Cantidad mínima requerida
    needs_restock = Column(Boolean, nullable=False, default=False)  # ¿Necesita reposición?

    room = relationship("Room", back_populates="inventory_items")

    __table_args__ = (
        UniqueConstraint('room_id', 'product_name', name='uix_room_product'),
    )

    # Nueva tabla intermedia RoomProduct
room_product = Table(
    'room_product',
    Base.metadata,
    Column('room_id', Integer, ForeignKey('rooms.id'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('quantity', Integer, nullable=False, default=1),  # Cantidad asignada
    Column('needs_restock', Boolean, nullable=False, default=False)  # Necesita reposición
)

# Nueva tabla Products
class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Ejemplo: "Toallas", "Sábanas"
    description = Column(String, nullable=True)  # Descripción opcional
    price = Column(Float, nullable=True)  # Precio opcional del producto
    rooms = relationship(  # Relación muchos a muchos con Room
        "Room",
        secondary="room_product",
        back_populates="products"
    )