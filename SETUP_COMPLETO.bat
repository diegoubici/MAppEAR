@echo off
chcp 65001 >nul
color 0D
echo ======================================
echo 🔧 SETUP COMPLETO DE MAppEAR
echo ======================================
echo.

echo 📋 Este script realizará:
echo    1. Verificación de archivos necesarios
echo    2. Configuración de .gitignore
echo    3. Instalación de dependencias
echo    4. Inicialización de Git (si es necesario)
echo.
pause
echo.

REM 1. Verificar archivos críticos
echo 1️⃣  Verificando archivos críticos...
if not exist "app.py" (
    echo ❌ ERROR: No se encontró app.py
    pause
    exit /b
)
if not exist "requirements.txt" (
    echo ❌ ERROR: No se encontró requirements.txt
    pause
    exit /b
)
echo ✅ Archivos principales encontrados
echo.

REM 2. Crear/Verificar .gitignore
echo 2️⃣  Configurando .gitignore...
if not exist ".gitignore" (
    echo Creando .gitignore...
    (
        echo # Credenciales sensibles
        echo service_account.json
        echo *.json
        echo.
        echo # Python
        echo __pycache__/
        echo *.pyc
        echo *.pyo
        echo *.pyd
        echo .Python
        echo env/
        echo venv/
        echo.
        echo # Datos
        echo data/
        echo *.xlsx
        echo *.xls
        echo.
        echo # Sistema
        echo .DS_Store
        echo Thumbs.db
        echo desktop.ini
        echo.
        echo # Backup
        echo BACKUP/
        echo *_BACKUP/
    ) > .gitignore
    echo ✅ .gitignore creado
) else (
    echo ✅ .gitignore ya existe
)
echo.

REM 3. Instalar dependencias
echo 3️⃣  Instalando dependencias de Python...
pip install -r requirements.txt
echo.

REM 4. Inicializar Git si es necesario
echo 4️⃣  Verificando Git...
if not exist ".git" (
    echo Inicializando repositorio Git...
    git init
    git branch -M main
    echo ✅ Git inicializado
) else (
    echo ✅ Git ya está inicializado
)
echo.

REM 5. Verificar conexión con GitHub
echo 5️⃣  Verificando conexión con GitHub...
git remote -v | findstr origin >nul
if errorlevel 1 (
    echo ⚠️  No hay remote configurado
    set /p config_remote="¿Deseas configurar GitHub ahora? (S/N): "
    if /i "!config_remote!"=="S" (
        set /p repo_url="Ingresa la URL del repositorio: "
        git remote add origin !repo_url!
        echo ✅ Remote configurado
    )
) else (
    echo ✅ Remote ya está configurado
    git remote -v
)
echo.

echo ======================================
echo ✅ SETUP COMPLETADO
echo ======================================
echo.
echo 📝 Próximos pasos:
echo    1. Asegúrate de tener service_account.json en la carpeta
echo    2. Usa 'iniciar_app_local.bat' para probar localmente
echo    3. Usa 'push_github.bat' para subir cambios
echo    4. Usa 'deploy_render.bat' para desplegar
echo.
pause
```

---

## 🎯 CÓMO USAR LOS SCRIPTS

### Primera vez (Setup inicial):
```
1. Ejecuta: setup_completo.bat
```

### Para trabajar día a día:
```
1. Haz cambios en tu código
2. Ejecuta: push_github.bat (sube a GitHub)
3. Render detectará automáticamente y desplegará
```

### Para probar localmente:
```
Ejecuta: iniciar_app_local.bat