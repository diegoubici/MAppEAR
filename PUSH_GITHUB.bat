@echo off
color 0A
echo ======================================
echo 🚀 SUBIENDO PROYECTO MAppEAR A GITHUB
echo ======================================

cd /d C:\MAPPEAR

REM Excluir credentials.json
git rm --cached credentials.json >nul 2>&1
echo credentials.json> .gitignore
git add .gitignore

REM Commit automático
set fecha=%date%_%time%
git add .
git commit -m "Auto commit %fecha%"
git push origin main --force

echo ======================================
echo ✅ PROYECTO SUBIDO A GITHUB CORRECTAMENTE
echo ======================================
pause
