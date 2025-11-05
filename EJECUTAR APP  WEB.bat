@echo off
REM ===============================
REM Ejecutar la app Flask MAPPEAR
REM ===============================

REM Ruta donde está la app (cambiar si es necesario)
SET APP_DIR=C:\Users\Diego\MAPPEAR

REM Entrar a la carpeta de la app
cd /d "%APP_DIR%"

REM ===== OPCIONAL: activar entorno virtual =====
REM Si usás un virtualenv, descomentá la línea de abajo y ajustá la ruta
REM call .\venv\Scripts\activate

REM Ejecutar la app Flask
python app.py

REM Mantener la ventana abierta para ver mensajes
pause
