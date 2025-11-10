from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ['https://www.googleapis.com/auth/drive.file']
ROOT_FOLDER_ID = "1wP71l2KGx7IccvNex4HXUM0t2-NlneVn"

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('drive', 'v3', credentials=creds)

# Listar todas las carpetas dentro de MappearUploads
q = f"mimeType='application/vnd.google-apps.folder' and '{ROOT_FOLDER_ID}' in parents and trashed=false"
result = service.files().list(q=q, fields="files(id, name)").execute()
folders = result.get("files", [])

print(f"📁 Carpetas encontradas en MappearUploads: {len(folders)}")
print("-" * 50)

for folder in folders:
    nombre_original = folder['name']
    nombre_normalizado = nombre_original.strip().lower().replace(" ", "")
    print(f"Original: '{nombre_original}'")
    print(f"Normalizado: '{nombre_normalizado}'")
    print(f"ID: {folder['id']}")
    print("-" * 50)

# Buscar específicamente RIVADAVIA
usuario = "RIVADAVIA"
user_normalizado = usuario.strip().lower().replace(" ", "")
print(f"\n🔍 Buscando usuario: '{usuario}'")
print(f"   Normalizado a: '{user_normalizado}'")

encontrado = False
for folder in folders:
    nombre_carpeta = folder["name"].strip().lower().replace(" ", "")
    if nombre_carpeta == user_normalizado:
        print(f"✅ ¡ENCONTRADA! Carpeta: '{folder['name']}' (ID: {folder['id']})")
        encontrado = True
        break

if not encontrado:
    print("❌ No se encontró la carpeta")
    print("\n💡 Verifica:")
    print("   1. Que exista una carpeta llamada 'RIVADAVIA' dentro de MappearUploads")
    print("   2. Que la carpeta NO esté en la papelera")
    print("   3. Que MappearUploads esté compartida con la cuenta de servicio")