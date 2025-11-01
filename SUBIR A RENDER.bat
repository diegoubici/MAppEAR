@echo off
echo =========================================================
echo   🚀 SUBIENDO PROYECTO MAPPEAR A RENDER
echo =========================================================

REM Ir al directorio del proyecto
cd /d F:\MAPPEAR

REM Inicializar Git si no existe
if not exist ".git" (
    echo Inicializando repositorio Git...
    git init
    git branch -M main
)

REM Agregar todos los archivos
echo Agregando archivos al repositorio...
git add .

REM Confirmar cambios
git commit -m "Actualizacion automatica desde script"

REM Si no existe el remoto, pedirlo y guardarlo
git remote get-url render >nul 2>nul
if errorlevel 1 (
    echo.
    echo ⚠️  No se detecta remoto "render".
    echo Ingresa la URL del repositorio de Render (Git URL):
    set /p RENDER_URL="URL: "
    git remote add render %RENDER_URL%
)

REM Subir al remoto
echo.
echo Subiendo cambios a Render...
git push render main -f

echo.
echo =========================================================
echo ✅ Proyecto subido correctamente a Render
echo =========================================================
pause
