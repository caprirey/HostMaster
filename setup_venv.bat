@echo off
echo Creando el entorno virtual...
py -m venv venv

echo Activando el entorno virtual...
.\venv\Scripts\activate.bat

echo Instalando dependencias desde requirements.txt...
pip install -r requirements.txt

echo Instalación completada. El entorno virtual está activado.
cmd /k

# subir servidor
#  fastapi dev main.py