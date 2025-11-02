@echo off
REM =========================================
REM Script automático para subir MAppEAR a GitHub/Render
REM =========================================

REM Cambiar al directorio del proyecto
cd /d C:\MAppEAR

REM Mostrar mensaje
echo =======================================
echo 🔹 Subiendo proyecto MAppEAR a GitHub...
echo =======================================

REM Agregar todos los cambios
git add .

REM Commit automático con fecha y hora
for /f "tokens=1-5 delims=/:. " %%d in ("%date% %time%") do (
    set fecha=%%d-%%e-%%f_%%g-%%h
)
git commit -m "Auto commit %fecha%"

REM Push automático a main
git push origin main

REM Mensaje final
echo.
echo =======================================
echo ✅ Proyecto subido correctamente a GitHub/Render
echo =======================================
pause
