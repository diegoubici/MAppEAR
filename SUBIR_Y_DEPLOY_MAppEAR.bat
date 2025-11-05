@echo off
title 🚀 Subir MAppEAR a GitHub y Render
color 0A
echo =======================================
echo 🚀 INICIANDO SUBIDA DE PROYECTO MAPPEAR
echo =======================================
echo.

REM === 1. Mover a carpeta del proyecto ===
cd /d C:\MAPPEAR

REM === 2. Confirmar que credentials.json no se sube ===
if exist credentials.json (
    echo 🔒 Excluyendo credentials.json del push...
    git rm --cached credentials.json >nul 2>&1
)
echo credentials.json>> .gitignore

REM === 3. Commit automático con fecha ===
set fecha=%date:~6,4%-%date:~3,2%-%date:~0,2%
set hora=%time:~0,2%-%time:~3,2%
git add .
git commit -m "Auto commit %fecha%_%hora%" 
git push origin main

if %errorlevel% neq 0 (
    echo ❌ Error al subir a GitHub. Revisa la conexión o credenciales.
    pause
    exit /b
)

echo ✅ Subida a GitHub completada correctamente.
echo.

REM === 4. Desplegar en Render ===
echo 🌐 Iniciando Deploy en Render...
REM Verifica si está instalado Render CLI
where render-cli >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚙️ Instalando Render CLI...
    npm install -g render-cli
)

REM Ejecutar deploy automático (requiere render.yaml o configuración previa)
render deploy .

if %errorlevel% neq 0 (
    echo ❌ Error al hacer deploy en Render.
    echo 💡 Asegúrate de haber iniciado sesión en Render CLI con:
    echo     render login
    pause
    exit /b
)

echo =======================================
echo ✅ DEPLOY COMPLETADO EXITOSAMENTE
echo =======================================
pause
exit
