# app/services/hotel/review.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sqlalchemy_models import UserTable, Accommodation, Review as ReviewSQL  # Renombramos el modelo SQLAlchemy
from app.models.pydantic_models import Review as ReviewPydantic, ReviewCreate, ReviewUpdate  # Renombramos el modelo Pydantic
from typing import List

async def create_review(db: AsyncSession, review_data: ReviewCreate, username: str) -> ReviewPydantic:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Accommodation).where(Accommodation.id == review_data.accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    result = await db.execute(
        select(ReviewSQL)  # Usamos ReviewSQL aquí
        .where(ReviewSQL.accommodation_id == review_data.accommodation_id)
        .where(ReviewSQL.user_username == username)
    )
    existing_review = result.scalar_one_or_none()
    if existing_review:
        raise HTTPException(status_code=400, detail="User has already reviewed this accommodation")

    db_review = ReviewSQL(
        accommodation_id=review_data.accommodation_id,
        user_username=username,
        rating=review_data.rating,
        comment=review_data.comment
    )
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return ReviewPydantic.model_validate(db_review)

async def get_reviews_by_accommodation(db: AsyncSession, accommodation_id: int) -> List[ReviewPydantic]:
    result = await db.execute(
        select(Accommodation).where(Accommodation.id == accommodation_id)
    )
    accommodation = result.scalar_one_or_none()
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    result = await db.execute(
        select(ReviewSQL).where(ReviewSQL.accommodation_id == accommodation_id)  # Usamos ReviewSQL aquí
    )
    reviews = result.scalars().all()
    return [ReviewPydantic.model_validate(review) for review in reviews]

async def get_review(db: AsyncSession, review_id: int) -> ReviewPydantic:
    result = await db.execute(
        select(ReviewSQL).where(ReviewSQL.id == review_id)  # Usamos ReviewSQL aquí
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewPydantic.model_validate(review)

async def update_review(
        db: AsyncSession,
        review_id: int,
        review_data: ReviewUpdate,
        username: str
) -> ReviewPydantic:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(ReviewSQL).where(ReviewSQL.id == review_id)  # Usamos ReviewSQL aquí
    )
    db_review = result.scalar_one_or_none()
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")

    if user.role != "admin" and db_review.user_username != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the review owner can update this review"
        )

    update_data = review_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_review, key, value)

    await db.commit()
    await db.refresh(db_review)
    return ReviewPydantic.model_validate(db_review)

async def delete_review(db: AsyncSession, review_id: int, username: str) -> None:
    result = await db.execute(select(UserTable).where(UserTable.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(ReviewSQL).where(ReviewSQL.id == review_id)  # Usamos ReviewSQL aquí
    )
    db_review = result.scalar_one_or_none()
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")

    if user.role != "admin" and db_review.user_username != username:
        raise HTTPException(
            status_code=403,
            detail="Only admin or the review owner can delete this review"
        )

    await db.delete(db_review)
    await db.commit()