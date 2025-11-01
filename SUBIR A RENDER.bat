@echo off
echo ========================================
echo      SUBIENDO MAPPEAR A GITHUB / RENDER
echo ========================================

cd /d C:\MAPPEAR

REM === Verificar instalación de Git ===
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Git no está instalado o no se encuentra en el PATH.
    echo Instalalo desde https://git-scm.com/download/win
    pause
    exit /b
)

REM === Verificar repositorio ===
if not exist ".git" (
    echo ❌ ERROR: No existe repositorio Git en C:\MAPPEAR
    echo Ejecutá una sola vez estos comandos:
    echo git init
    echo git branch -M main
    echo git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
    pause
    exit /b
)

REM === Preguntar mensaje de commit ===
set /p msg=Escribí el mensaje del commit: 
if "%msg%"=="" set msg=Actualizacion automatica

echo.
echo === Subiendo cambios a GitHub ===
git add .
git commit -m "%msg%"
git push origin main

echo.
echo ========================================
echo ✅ Proyecto actualizado en GitHub
echo ✅ Render actualizará automáticamente la app
echo ========================================
pause
