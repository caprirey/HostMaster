from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import os
from app.database.db import engine, init_db, get_db
from app.routes.auth import router as auth_router
from app.routes.hotel import router as hotel_router
from app.routes.admin import router as admin_router
from app.seeds.seeder import seed_database
from app.config.settings import STATIC_DIR, IMAGES_DIR

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
    db_gen = get_db()
    db = await anext(db_gen)
    try:
        await seed_database(db)
        yield
    finally:
        await db_gen.aclose()
    await engine.dispose()

app = FastAPI(
    lifespan=lifespan,
    title="Hotel Management API",
    description="API for managing hotel accommodations and services",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar el directorio estático
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

# Incluir routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(hotel_router, prefix="/hotel")  # Sin tags=["hotel"]
app.include_router(admin_router, prefix="/admin", tags=["admin"])

# Personalizar el esquema OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Hotel Management API",
        version="1.0.0",
        description="API for managing hotel accommodations and services",
        routes=app.routes,
    )
    # Filtrar para mostrar solo rutas con tags definidos y ocultar "default"
    paths_to_keep = {}
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if "tags" in operation and operation["tags"] and "hotel" not in operation["tags"]:  # Excluir "hotel" como tag raíz
                if path not in paths_to_keep:
                    paths_to_keep[path] = {}
                paths_to_keep[path][method] = operation
    openapi_schema["paths"] = paths_to_keep
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)