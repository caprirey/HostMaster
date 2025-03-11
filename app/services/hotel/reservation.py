from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.pydantic_models import Reservation, ReservationBase
from app.models.sqlalchemy_models import Reservation as ReservationTable, UserTable

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