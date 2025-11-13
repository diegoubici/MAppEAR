from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

print("="*70)
print("🚀 SETUP COMPLETO DE GOOGLE DRIVE PARA MAppEAR")
print("="*70)
print()

# Autenticar
print("🔐 Autenticando con Google Drive...")
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('drive', 'v3', credentials=creds)
print("✅ Autenticación exitosa")
print()

# Crear carpeta raíz NUEVA
print("📁 Creando carpeta raíz 'MappearUploads_SA'...")
folder_metadata = {
    'name': 'MappearUploads_SA',  # Nombre diferente para no confundir
    'mimeType': 'application/vnd.google-apps.folder'
}

try:
    folder = service.files().create(body=folder_metadata, fields='id, name, webViewLink').execute()
    ROOT_ID = folder['id']
    
    print(f"✅ Carpeta raíz creada: {folder['name']}")
    print(f"📁 ID: {ROOT_ID}")
    print(f"🔗 Link: {folder['webViewLink']}")
    print()
    
    # Crear subcarpetas para usuarios
    print("📂 Creando subcarpetas para usuarios...")
    usuarios = ["DSUBICI", "RIVADAVIA", "usuario1", "usuario2", "usuario3", "usuario4"]
    
    for usuario in usuarios:
        subfolder_metadata = {
            'name': usuario,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [ROOT_ID]
        }
        subfolder = service.files().create(body=subfolder_metadata, fields='id, name').execute()
        print(f"   ✅ {subfolder['name']} (ID: {subfolder['id']})")
    
    print()
    print("="*70)
    print("📋 COMPARTIR CARPETA CON TU EMAIL")
    print("="*70)
    print()
    
    # Pedir email del usuario
    tu_email = input("Ingresa tu email de Google para poder ver la carpeta: ").strip()
    
    if tu_email:
        print(f"\n📤 Compartiendo carpeta con {tu_email}...")
        permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': tu_email
        }
        
        try:
            service.permissions().create(
                fileId=ROOT_ID,
                body=permission,
                sendNotificationEmail=False
            ).execute()
            print(f"✅ Carpeta compartida con {tu_email}")
        except Exception as e:
            print(f"⚠️  No se pudo compartir: {e}")
            print("   Pero no te preocupes, la carpeta funciona igual.")
    
    print()
    print("="*70)
    print("⚠️  IMPORTANTE: COPIA ESTE ID PARA app.py")
    print("="*70)
    print()
    print(f"ROOT_FOLDER_ID = \"{ROOT_ID}\"")
    print()
    print("Abre app.py y reemplaza la línea 15 con el ID de arriba.")
    print()
    print("="*70)
    print("✅ SETUP COMPLETADO EXITOSAMENTE")
    print("="*70)
    print()
    print(f"🔗 Puedes ver la carpeta en: {folder['webViewLink']}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    print(traceback.format_exc())