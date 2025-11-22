@echo off
chcp 65001 >nul
color 0B
echo ======================================
echo 🚀 DEPLOY AUTOMÁTICO A RENDER
echo ======================================
echo.

REM Primero hacer push a GitHub
echo 📤 Paso 1: Subiendo cambios a GitHub...
call push_github.bat
echo.

REM Esperar un momento
echo ⏳ Esperando 5 segundos...
timeout /t 5 /nobreak >nul
echo.

echo 📡 Paso 2: Notificando a Render...
echo.
echo ℹ️  Render detectará automáticamente el push a GitHub
echo    y comenzará el deploy en unos segundos.
echo.
echo 🌐 Panel de Render: https://dashboard.render.com
echo.
echo ✅ Proceso completado. 
echo    Revisa el dashboard de Render para ver el progreso del deploy.
echo.

REM Opcional: Abrir dashboard de Render en el navegador
set /p abrir="¿Deseas abrir el dashboard de Render? (S/N): "
if /i "%abrir%"=="S" (
    start https://dashboard.render.com
)

echo.
pause