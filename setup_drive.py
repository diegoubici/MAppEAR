from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

print("="*60)
print("🚀 CONFIGURACIÓN INICIAL DE GOOGLE DRIVE")
print("="*60)
print()

# Autenticar
print("🔐 Autenticando con Google Drive...")
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('drive', 'v3', credentials=creds)
print("✅ Autenticación exitosa")
print()

# Crear carpeta raíz
print("📁 Creando carpeta raíz 'MappearUploads'...")
folder_metadata = {
    'name': 'MappearUploads',
    'mimeType': 'application/vnd.google-apps.folder'
}

folder = service.files().create(body=folder_metadata, fields='id, name, webViewLink').execute()

print(f"✅ Carpeta creada: {folder['name']}")
print(f"📁 ID: {folder['id']}")
print(f"🔗 Link: {folder['webViewLink']}")
print()

# Crear subcarpetas para cada usuario
print("📂 Creando subcarpetas para usuarios...")
usuarios = ["DSUBICI", "RIVADAVIA", "usuario1", "usuario2", "usuario3", "usuario4"]

for usuario in usuarios:
    subfolder_metadata = {
        'name': usuario,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [folder['id']]
    }
    subfolder = service.files().create(body=subfolder_metadata, fields='id, name').execute()
    print(f"   ✅ {subfolder['name']} (ID: {subfolder['id']})")

print()
print("="*60)
print("⚠️  IMPORTANTE: COPIA ESTE ID")
print("="*60)
print()
print(f"ROOT_FOLDER_ID = \"{folder['id']}\"")
print()
print("Abre app.py y reemplaza la línea 15 con el ID de arriba.")
print()
print("="*60)
print("✅ CONFIGURACIÓN COMPLETADA")
print("="*60)