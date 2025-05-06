from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.pydantic_models import (
    Accommodation,
    AccommodationBase,
    AccommodationUpdate
)
from app.models.sqlalchemy_models import (
    Accommodation as AccommodationTable,
    UserTable,
    City as CityTable,
)
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_accommodations(db: AsyncSession, username: str) -> List[Accommodation]:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin":
        result = await db.execute(
            select(AccommodationTable).options(
                selectinload(AccommodationTable.images),
                selectinload(AccommodationTable.reviews),
                selectinload(AccommodationTable.users)
            )
        )
        include_user_usernames = True
    elif user.role == "employee":
        result = await db.execute(
            select(AccommodationTable)
            .join(AccommodationTable.users)
            .where(UserTable.username == username)
            .options(
                selectinload(AccommodationTable.images),
                selectinload(AccommodationTable.reviews),
                selectinload(AccommodationTable.users)
            )
        )
        include_user_usernames = True
    elif user.role == "client":
        result = await db.execute(
            select(AccommodationTable).options(
                selectinload(AccommodationTable.images),
                selectinload(AccommodationTable.reviews)
            )
        )
        include_user_usernames = False
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    accommodations = result.scalars().all()
    return [
        Accommodation.model_validate({
            "id": acc.id,
            "name": acc.name,
            "city_id": acc.city_id,
            "address": acc.address,
            "information": acc.information,
            "user_usernames": [u.username for u in acc.users] if include_user_usernames else [],
            "images": acc.images,
            "reviews": acc.reviews
        }) for acc in accommodations
    ]

async def create_accommodation(
        db: AsyncSession,
        accommodation: AccommodationBase,
        username: str
) -> Accommodation:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    valid_roles = {"admin", "employee"}
    if user.role not in valid_roles:
        raise HTTPException(
            status_code=403,
            detail="Only users with 'admin' or 'employee' roles can create accommodations"
        )

    result = await db.execute(
        select(CityTable).where(CityTable.id == accommodation.city_id)
    )
    city = result.scalar_one_or_none()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    db_accommodation = AccommodationTable(
        name=accommodation.name,
        city_id=accommodation.city_id,
        address=accommodation.address,
        information=accommodation.information
    )
    db_accommodation.users = [user]

    db.add(db_accommodation)
    await db.commit()

    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == db_accommodation.id)
        .options(
            selectinload(AccommodationTable.images),
            selectinload(AccommodationTable.reviews),
            selectinload(AccommodationTable.users)
        )
    )
    db_accommodation = result.scalar_one()
    return Accommodation.model_validate({
        "id": db_accommodation.id,
        "name": db_accommodation.name,
        "city_id": db_accommodation.city_id,
        "address": db_accommodation.address,
        "information": db_accommodation.information,
        "user_usernames": [u.username for u in db_accommodation.users],
        "images": db_accommodation.images,
        "reviews": db_accommodation.reviews
    })

async def update_accommodation(
        db: AsyncSession,
        accommodation_id: int,
        accommodation_update: AccommodationUpdate,
        username: str
) -> Accommodation:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    valid_roles = {"admin", "employee"}
    if user.role not in valid_roles:
        raise HTTPException(
            status_code=403,
            detail="Only users with 'admin' or 'employee' roles can update accommodations"
        )

    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == accommodation_id)
        .options(
            selectinload(AccommodationTable.images),
            selectinload(AccommodationTable.reviews),
            selectinload(AccommodationTable.users)
        )
    )
    db_accommodation = result.scalar_one_or_none()
    if not db_accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    if accommodation_update.city_id is not None:
        result = await db.execute(
            select(CityTable).where(CityTable.id == accommodation_update.city_id)
        )
        city = result.scalar_one_or_none()
        if not city:
            raise HTTPException(status_code=404, detail="City not found")

    update_data = accommodation_update.model_dump(exclude_unset=True, exclude={"user_usernames"})
    for key, value in update_data.items():
        setattr(db_accommodation, key, value)

    if accommodation_update.user_usernames is not None:
        result = await db.execute(
            select(UserTable).where(UserTable.username.in_(accommodation_update.user_usernames))
        )
        users = result.scalars().all()
        if len(users) != len(accommodation_update.user_usernames):
            raise HTTPException(status_code=400, detail="One or more usernames do not exist")
        db_accommodation.users = users

    await db.commit()

    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == db_accommodation.id)
        .options(
            selectinload(AccommodationTable.images),
            selectinload(AccommodationTable.reviews),
            selectinload(AccommodationTable.users)
        )
    )
    db_accommodation = result.scalar_one()
    return Accommodation.model_validate({
        "id": db_accommodation.id,
        "name": db_accommodation.name,
        "city_id": db_accommodation.city_id,
        "address": db_accommodation.address,
        "information": db_accommodation.information,
        "user_usernames": [u.username for u in db_accommodation.users],
        "images": db_accommodation.images,
        "reviews": db_accommodation.reviews
    })

async def delete_accommodation(db: AsyncSession, accommodation_id: int, username: str) -> None:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(AccommodationTable)
        .where(AccommodationTable.id == accommodation_id)
        .options(
            selectinload(AccommodationTable.rooms),
            selectinload(AccommodationTable.images),
            selectinload(AccommodationTable.reviews),
            selectinload(AccommodationTable.users)
        )
    )
    db_accommodation = result.scalar_one_or_none()
    if not db_accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    if user.role != "admin" and username not in [u.username for u in db_accommodation.users]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this accommodation")

    if db_accommodation.rooms:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete accommodation with associated rooms"
        )

    if db_accommodation.reviews:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete accommodation with associated reviews"
        )

    for image in db_accommodation.images:
        await db.delete(image)

    await db.delete(db_accommodation)
    await db.commit()


async def get_accommodation_by_id(db: AsyncSession, accommodation_id: int, username: str) -> Accommodation:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = select(AccommodationTable).where(AccommodationTable.id == accommodation_id).options(
        selectinload(AccommodationTable.images),
        selectinload(AccommodationTable.reviews),
        selectinload(AccommodationTable.users)
    )

    if user.role == "employee":
        query = query.join(AccommodationTable.users).where(UserTable.username == username)
    elif user.role == "client":
        query = select(AccommodationTable).where(AccommodationTable.id == accommodation_id).options(
            selectinload(AccommodationTable.images),
            selectinload(AccommodationTable.reviews)
        )

    result = await db.execute(query)
    db_accommodation = result.scalar_one_or_none()
    if not db_accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    include_user_usernames = user.role in {"admin", "employee"}
    return Accommodation.model_validate({
        "id": db_accommodation.id,
        "name": db_accommodation.name,
        "city_id": db_accommodation.city_id,
        "address": db_accommodation.address,
        "information": db_accommodation.information,
        "user_usernames": [u.username for u in db_accommodation.users] if include_user_usernames else [],
        "images": db_accommodation.images,
        "reviews": db_accommodation.reviews
    })