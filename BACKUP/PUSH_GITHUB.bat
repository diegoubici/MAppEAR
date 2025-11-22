@echo off
echo ========================================
echo    GIT PUSH AUTOMATICO
echo ========================================
echo.

REM Agregar todos los cambios
echo [1/4] Agregando archivos...
git add .

REM Verificar si hay cambios
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo.
    echo No hay cambios para subir.
    echo.
    pause
    exit /b 0
)

REM Hacer commit con timestamp
echo.
echo [2/4] Haciendo commit...
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a:%%b)
git commit -m "Actualizacion automatica %mydate% %mytime%"

REM Hacer push
echo.
echo [3/4] Subiendo cambios a GitHub...
git push origin main

REM Verificar resultado
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo    PUSH EXITOSO!
    echo ========================================
    echo.
    echo Los cambios se subieron correctamente.
    echo Render comenzara a desplegar automaticamente.
    echo.
) else (
    echo.
    echo ========================================
    echo    ERROR EN EL PUSH
    echo ========================================
    echo.
    echo Revisa el error arriba.
    echo.
)

echo [4/4] Proceso completado.
echo.
pause