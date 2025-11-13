from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

# ID de la carpeta que creaste
FOLDER_ID = "1iVFEB2vhPyGucD5fSGdn1KpqXBs331yJ"

# TU EMAIL PERSONAL (el que usas en Google Drive)
TU_EMAIL = "diegoubici@gmail.com"  # ← CAMBIA ESTO por tu email

print("="*60)
print("🔓 COMPARTIENDO CARPETA CONTIGO")
print("="*60)
print()

# Autenticar
print("🔐 Autenticando...")
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('drive', 'v3', credentials=creds)
print("✅ Autenticación exitosa")
print()

# Compartir carpeta contigo
print(f"📤 Compartiendo carpeta con {TU_EMAIL}...")

permission = {
    'type': 'user',
    'role': 'writer',  # Permiso de escritura
    'emailAddress': TU_EMAIL
}

try:
    service.permissions().create(
        fileId=FOLDER_ID,
        body=permission,
        sendNotificationEmail=False  # No enviar email de notificación
    ).execute()
    
    print(f"✅ Carpeta compartida exitosamente con {TU_EMAIL}")
    print()
    print("🔗 Ahora puedes acceder desde:")
    print(f"   https://drive.google.com/drive/folders/{FOLDER_ID}")
    print()
    print("="*60)
    print("✅ PROCESO COMPLETADO")
    print("="*60)
    
except Exception as e:
    print(f"❌ Error al compartir: {e}")