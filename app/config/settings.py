from datetime import timedelta

# Configuración de JWT
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
ACCESS_TOKEN_EXPIRE_DELTA = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

# Configuración de la base de datos
DATABASE_URL = "sqlite+aiosqlite:///HostMasterV1.db"

# Configuración de archivos estáticos
STATIC_DIR = "static"
IMAGES_DIR = "images"  # Subdirectorio dentro de STATIC_DIR
USERS_DIR = "users"
BASE_URL = "http://0.0.0.0:8000"  # URL base para acceder a los archivos está

# Configuración de correo electrónico (Gmail)
MAIL_USERNAME = "ncprietoreyes@gmail.com"  # Tu dirección de Gmail
MAIL_PASSWORD = "iify rfja mhya axoy" # Contraseña de aplicación generada
MAIL_FROM = "HostMasterApp@gmail.com"
MAIL_PORT = 587
MAIL_SERVER = "smtp.gmail.com"
MAIL_FROM_NAME = "HostMaster API"
MAIL_STARTTLS = True
MAIL_SSL_TLS = False