from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.pydantic_models import Country, CountryBase, State, StateBase, City, CityBase
from app.models.sqlalchemy_models import Country as CountryTable, State as StateTable, City as CityTable

async def create_country(db: AsyncSession, country_data: CountryBase) -> Country:
    country = CountryTable(name=country_data.name)
    db.add(country)
    await db.commit()
    await db.refresh(country)
    return Country.model_validate(country)

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

async def create_state(db: AsyncSession, state_data: StateBase) -> State:
    state = StateTable(name=state_data.name, country_id=state_data.country_id)
    db.add(state)
    await db.commit()
    await db.refresh(state)
    return State.model_validate(state)

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

async def create_city(db: AsyncSession, city_data: CityBase) -> City:
    city = CityTable(name=city_data.name, state_id=city_data.state_id)
    db.add(city)
    await db.commit()
    await db.refresh(city)
    return City.model_validate(city)

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