import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# === CONFIG ===
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRET = 'credentials.json'
TOKEN_FILE = 'token.json'
ROOT_FOLDER_ID = '1wP71l2KGx7IccvNex4HXUM0t2-NlneVn'  # tu carpeta raíz en Drive

# === FUNCIONES ===
def obtener_servicio_drive():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return build('drive', 'v3', credentials=creds)

def listar_contenido_carpeta(service, folder_id):
    print(f"\n📁 Contenido de la carpeta ID {folder_id}:")
    query = f"'{folder_id}' in parents"
    result = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    items = result.get('files', [])
    if not items:
        print("   (vacía)")
    for f in items:
        tipo = "Carpeta" if f['mimeType'] == 'application/vnd.google-apps.folder' else "Archivo"
        print(f" - {tipo}: {f['name']} (ID: {f['id']})")

# === EJECUCIÓN ===
if __name__ == "__main__":
    service = obtener_servicio_drive()
    try:
        carpeta = service.files().get(fileId=ROOT_FOLDER_ID, fields="id, name, mimeType").execute()
        print("✅ Carpeta raíz encontrada:")
        print(f"   Nombre: {carpeta['name']}")
        print(f"   ID: {carpeta['id']}")
        print(f"   Tipo: {carpeta['mimeType']}")
        
        # Listar contenido
        listar_contenido_carpeta(service, ROOT_FOLDER_ID)
    except Exception as e:
        print("❌ Error:", e)
