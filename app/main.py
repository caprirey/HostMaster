from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # Agregamos esta importación
import os
from app.database.db import engine, init_db, get_db
from app.routes.auth import router as auth_router
from app.routes.hotel import router as hotel_router
from app.routes.admin import router as admin_router
from app.seeds.seeder import seed_database
from app.config.settings import STATIC_DIR, IMAGES_DIR  # Importamos las configuraciones

# Crear directorios estáticos si no existen
STATIC_PATH = STATIC_DIR
IMAGES_PATH = os.path.join(STATIC_DIR, IMAGES_DIR)

if not os.path.exists(STATIC_PATH):
    os.makedirs(STATIC_PATH)
if not os.path.exists(IMAGES_PATH):
    os.makedirs(IMAGES_PATH)

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

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

# Montar el directorio estático
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(hotel_router, prefix="/hotel", tags=["hotel"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)