@echo off
chcp 65001 >nul
color 0E
echo ======================================
echo 🖥️  INICIANDO MAppEAR LOCAL
echo ======================================
echo.

REM Verificar que exista service_account.json
if not exist "service_account.json" (
    echo ❌ ERROR: No se encontró service_account.json
    echo.
    echo Este archivo es necesario para conectar con Google Drive.
    echo Asegúrate de tenerlo en la carpeta del proyecto.
    echo.
    pause
    exit /b
)

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    echo ✅ Activando entorno virtual...
    call venv\Scripts\activate.bat
)

REM Verificar dependencias
echo 📦 Verificando dependencias...
pip list | findstr Flask >nul
if errorlevel 1 (
    echo ⚠️  Faltan dependencias. Instalando...
    pip install -r requirements.txt
)

echo.
echo ✅ Iniciando aplicación...
echo.
echo 🌐 La aplicación estará disponible en:
echo    http://localhost:10000
echo.
echo ⚠️  Presiona Ctrl+C para detener el servidor
echo.
echo ======================================
echo.

python app.py