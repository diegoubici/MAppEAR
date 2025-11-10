import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# === CONFIGURACIÓN ===
SERVICE_ACCOUNT_FILE = r"C:\MAppEAR\service_account.json"  # Ruta local al archivo JSON
SCOPES = ['https://www.googleapis.com/auth/drive']
ROOT_FOLDER_ID = "1wP71l2KGx7IccvNex4HXUM0t2-NlneVn"  # Carpeta raíz "MappearUploads" en tu Drive

print("🔍 Conectando a Google Drive...")

try:
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    print("✅ Conectado correctamente con la cuenta de servicio.")
except Exception as e:
    print(f"❌ Error autenticando con Google Drive: {e}")
    exit()

# === Verificar acceso a carpeta raíz ===
try:
    folder = service.files().get(fileId=ROOT_FOLDER_ID, fields="id, name").execute()
    print(f"📁 Carpeta raíz encontrada: {folder['name']} (ID: {folder['id']})")
except Exception as e:
    print(f"❌ No se pudo acceder a la carpeta raíz. Verificá permisos compartidos: {e}")
    exit()

# === Listar subcarpetas (usuarios) ===
print("\n📂 Listando subcarpetas dentro de MappearUploads...\n")

try:
    q = f"mimeType='application/vnd.google-apps.folder' and '{ROOT_FOLDER_ID}' in parents and trashed=false"
    result = service.files().list(q=q, fields="files(id, name)").execute()
    folders = result.get("files", [])

    if not folders:
        print("⚠️ No hay subcarpetas dentro de MappearUploads.")
    else:
        for f in folders:
            print(f"👤 Carpeta de usuario: {f['name']} (ID: {f['id']})")

            # Listar archivos XLSX dentro de cada carpeta
            q_archivos = f"'{f['id']}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'"
            res_archivos = service.files().list(q=q_archivos, fields="files(id, name)").execute()
            archivos = res_archivos.get("files", [])

            if archivos:
                for a in archivos:
                    if a["name"].lower().endswith(".xlsx"):
                        print(f"   📄 {a['name']}")
            else:
                print("   (sin archivos XLSX)")
except Exception as e:
    print(f"❌ Error listando carpetas o archivos: {e}")
