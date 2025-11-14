@echo off
cd /d C:\MAppEAR

echo ============================
echo   SUBIENDO CAMBIOS A GITHUB
echo ============================

git add app.py
git commit -m "Actualizacion automatica de app.py"
git push

echo.
echo ✔ LISTO: Cambios subidos a GitHub
echo ✔ Render deberia actualizar en unos segundos
echo.
pause
