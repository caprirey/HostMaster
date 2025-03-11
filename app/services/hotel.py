from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.pydantic_models import (
    Accommodation, AccommodationBase, Room, RoomBase,
    City, CityBase, Country, CountryBase, State, StateBase, RoomType, RoomTypeBase,
    Reservation, ReservationBase
)
from app.models.sqlalchemy_models import (
    Accommodation as AccommodationTable, Room as RoomTable,
    City as CityTable, Country as CountryTable, State as StateTable, RoomType as RoomTypeTable,
    UserTable, Reservation as ReservationTable
)

async def create_country(db: AsyncSession, country_data: CountryBase) -> Country:
    country = CountryTable(name=country_data.name)
    db.add(country)
    await db.commit()
    await db.refresh(country)
    return Country.model_validate(country)

async def create_state(db: AsyncSession, state_data: StateBase) -> State:
    state = StateTable(name=state_data.name, country_id=state_data.country_id)
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return State.model_validate(state)

async def create_city(db: AsyncSession, city_data: CityBase) -> City:
    city = CityTable(name=city_data.name, state_id=city_data.state_id)
    db.add(city)
    await db.commit()
    await db.refresh(city)
    return City.model_validate(city)

async def create_accommodation(db: AsyncSession, accommodation_data: AccommodationBase, username: str) -> Accommodation:
    accommodation = AccommodationTable(
        name=accommodation_data.name,
        city_id=accommodation_data.city_id,
        created_by=username
    )
    db.add(accommodation)
    await db.commit()
    await db.refresh(accommodation)
    return Accommodation.model_validate(accommodation)

async def create_room_type(db: AsyncSession, room_type_data: RoomTypeBase) -> RoomType:
    room_type = RoomTypeTable(name=room_type_data.name)
    db.add(room_type)
    await db.commit()
    await db.refresh(room_type)
    return RoomType.model_validate(room_type)

async def create_room(db: AsyncSession, room_data: RoomBase) -> Room:
    room = RoomTable(
        accommodation_id=room_data.accommodation_id,
        type_id=room_data.type_id,
        number=room_data.number  # Añadido
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return Room.model_validate(room)


async def create_reservation(db: AsyncSession, reservation_data: ReservationBase, username: str) -> Reservation:
    reservation = ReservationTable(
        user_username=username,
        room_id=reservation_data.room_id,
        start_date=reservation_data.start_date,
        end_date=reservation_data.end_date
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return Reservation.model_validate(reservation)



async def get_countries(db: AsyncSession) -> list[Country]:
    result = await db.execute(select(CountryTable))
    countries = result.scalars().all()
    return [Country.model_validate(country) for country in countries]

async def get_country(db: AsyncSession, country_id: int) -> Country:
    result = await db.execute(select(CountryTable).where(CountryTable.id == country_id))
    country = result.scalar_one_or_none()
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    return Country.model_validate(country)

async def get_states(db: AsyncSession) -> list[State]:
    result = await db.execute(select(StateTable))
    states = result.scalars().all()
    return [State.model_validate(state) for state in states]

async def get_state(db: AsyncSession, state_id: int) -> State:
    result = await db.execute(select(StateTable).where(StateTable.id == state_id))
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    return State.model_validate(state)

async def get_cities(db: AsyncSession) -> list[City]:
    result = await db.execute(select(CityTable))
    cities = result.scalars().all()
    return [City.model_validate(city) for city in cities]

async def get_city(db: AsyncSession, city_id: int) -> City:
    result = await db.execute(select(CityTable).where(CityTable.id == city_id))
    city = result.scalar_one_or_none()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    return City.model_validate(city)

async def get_accommodations(db: AsyncSession, username: str) -> list[Accommodation]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        result = await db.execute(select(AccommodationTable))
    elif user.role == "user":
        result = await db.execute(
            select(AccommodationTable).where(AccommodationTable.created_by == username)
        )
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    accommodations = result.scalars().all()
    return [Accommodation.model_validate(accommodation) for accommodation in accommodations]

async def get_rooms(db: AsyncSession, username: str, accommodation_id: int = None) -> list[Room]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = select(RoomTable)
    if accommodation_id is not None:
        query = query.where(RoomTable.accommodation_id == accommodation_id)
        if user.role == "user":
            result = await db.execute(
                select(AccommodationTable).where(
                    AccommodationTable.id == accommodation_id,
                    AccommodationTable.created_by == username
                )
            )
            accommodation = result.scalar_one_or_none()
            if not accommodation:
                return []
    elif user.role == "user":
        result = await db.execute(
            select(AccommodationTable).where(AccommodationTable.created_by == username)
        )
        user_accommodations = result.scalars().all()
        if not user_accommodations:
            return []
        query = query.where(RoomTable.accommodation_id.in_([a.id for a in user_accommodations]))

    result = await db.execute(query)
    rooms = result.scalars().all()
    return [Room.model_validate(room) for room in rooms]


async def get_reservations(db: AsyncSession, username: str) -> list[Reservation]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        result = await db.execute(select(ReservationTable))
    elif user.role == "user":
        result = await db.execute(
            select(ReservationTable).where(ReservationTable.user_username == username)
        )
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    reservations = result.scalars().all()
    return [Reservation.model_validate(reservation) for reservation in reservations]