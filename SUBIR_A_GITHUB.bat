@echo off
REM -----------------------------
REM Configura estos valores:
SET REPO_URL=https://github.com/diegoubici/MAppEAR.git
SET RUTA_PROYECTO=C:\MAppEAR
REM -----------------------------

cd /d "%RUTA_PROYECTO%"

REM Inicializar git si no existe
git rev-parse --is-inside-work-tree >nul 2>&1
IF ERRORLEVEL 1 (
    echo Inicializando repositorio git...
    git init
)

REM Eliminar remoto origin si existe
git remote remove origin >nul 2>&1

REM Agregar remoto
git remote add origin %REPO_URL%

REM Asegurar que la rama principal se llame main
git branch -M main

REM Agregar todos los archivos
git add .

REM Hacer commit
git commit -m "Primer commit del proyecto MAPPEAR"

REM Subir al repositorio remoto
git push -u origin main

pause
