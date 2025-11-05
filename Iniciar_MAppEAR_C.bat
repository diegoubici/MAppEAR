@echo off
title 🚀 Iniciar MAppEAR C:
color 0A
echo =====================================
echo        INICIANDO MAPPEAR LOCAL
echo =====================================
echo.

REM Ir a la carpeta del proyecto
cd /d C:\MAppEAR

REM Activar entorno virtual si existe
if exist venv\Scripts\activate (
    echo 🔹 Activando entorno virtual...
    call venv\Scripts\activate
) else (
    echo ⚠️ No se encontró entorno virtual. Se usará Python global.
)

REM Verificar e instalar dependencias necesarias
echo.
echo 🔹 Verificando dependencias...
pip install --quiet --upgrade pip
pip install --quiet flask pandas openpyxl google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2

REM Mostrar confirmación
echo.
echo ✅ Dependencias listas.
echo -------------------------------------

REM Ejecutar la aplicación
echo 🚀 Ejecutando app.py ...
echo -------------------------------------
python app.py

REM Mantener la ventana abierta al salir
echo.
echo 💡 Si ves el mensaje "Running on http://127.0.0.1:10000", abrí esa dirección en tu navegador.
echo.
pause
