@echo off
chcp 65001 >nul
color 0A
echo ======================================
echo 🚀 SUBIENDO PROYECTO MAppEAR A GITHUB
echo ======================================
echo.

REM Verificar que no se suba el JSON
if exist "service_account.json" (
    echo ⚠️  ADVERTENCIA: service_account.json existe localmente
    echo ✅ Verificando que esté en .gitignore...
    findstr /C:"service_account.json" .gitignore >nul
    if errorlevel 1 (
        echo ❌ ERROR: service_account.json NO está en .gitignore
        echo.
        echo Agregando a .gitignore...
        echo service_account.json >> .gitignore
        echo *.json >> .gitignore
    ) else (
        echo ✅ service_account.json está protegido en .gitignore
    )
)
echo.

REM Mostrar estado actual
echo 📋 Estado actual del repositorio:
echo ----------------------------------------
git status
echo ----------------------------------------
echo.

REM Preguntar si continuar
set /p continuar="¿Deseas continuar con el push? (S/N): "
if /i not "%continuar%"=="S" (
    echo ❌ Push cancelado por el usuario
    pause
    exit /b
)
echo.

REM Agregar archivos
echo 📦 Agregando archivos...
git add .
echo.

REM Crear commit con fecha y hora
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set fecha=%datetime:~6,2%/%datetime:~4,2%/%datetime:~0,4%
set hora=%datetime:~8,2%:%datetime:~10,2%:%datetime:~12,2%

echo 💬 Mensaje del commit: Auto commit %fecha%_%hora%
git commit -m "Auto commit %fecha%_%hora%"
echo.

REM Push a GitHub
echo 🌐 Enviando a GitHub...
git push origin main
echo.

if %errorlevel% equ 0 (
    echo ✅ PROYECTO SUBIDO A GITHUB CORRECTAMENTE
    echo.
    echo 🔗 Repositorio: https://github.com/diegoubici/MAppEAR
) else (
    echo ❌ ERROR AL SUBIR A GITHUB
    echo.
    echo 💡 Posibles soluciones:
    echo    1. Verifica tu conexión a internet
    echo    2. Verifica tus credenciales de GitHub
    echo    3. Si dice "secret detected", elimina service_account.json del historial
    echo.
)

echo.
pause