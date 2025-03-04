from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.db import engine, init_db, get_db
from app.routes.auth import router as auth_router
from app.routes.hotel import router as hotel_router
from app.seeds.seeder import seed_database

@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    # Manejar el generador asíncrono manualmente
    db_gen = get_db()
    db = await anext(db_gen)  # Obtener la sesión del generador
    try:
        await seed_database(db)
        yield
    finally:
        await db_gen.aclose()  # Cerrar el generador
    await engine.dispose()

app = FastAPI(lifespan=lifespan, title="Hotel Management API")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(hotel_router, prefix="/hotel", tags=["hotel"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)