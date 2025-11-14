from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# -----------------------------------------------------------
# CONFIGURACIÓN
# -----------------------------------------------------------
SERVICE_ACCOUNT_FILE = "service_account.json"   # JSON de tu service account
ROOT_FOLDER_ID = "1owQU7ef5s5jzY3w9Nj-DScziZnohaOrd"  # ID de "MappearUploads_SA"
TU_EMAIL = "diegoubici@gmail.com"               # tu email personal

# -----------------------------------------------------------
# AUTENTICAR SERVICE ACCOUNT
# -----------------------------------------------------------
creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/drive"]
)
service = build("drive", "v3", credentials=creds)


def compartir_carpeta(folder_id, email):
    """Comparte una carpeta con un usuario."""
    permission = {
        "type": "user",
        "role": "writer",   # Editor
        "emailAddress": email
    }
    try:
        service.permissions().create(
            fileId=folder_id,
            body=permission,
            sendNotificationEmail=False
        ).execute()
        print(f"   ✔ Compartida: {folder_id}")
    except Exception as e:
        print(f"   ❌ Error compartiendo {folder_id}: {e}")


# -----------------------------------------------------------
# BUSCAR SUBCARPETAS
# -----------------------------------------------------------
def obtener_subcarpetas(parent_id):
    """Devuelve todas las subcarpetas inmediatas."""
    query = f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    
    results = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    return results.get("files", [])


# -----------------------------------------------------------
# PROCESO
# -----------------------------------------------------------
print("📁 Compartiendo carpeta raíz...")
compartir_carpeta(ROOT_FOLDER_ID, TU_EMAIL)

print("📂 Buscando subcarpetas...")
subcarpetas = obtener_subcarpetas(ROOT_FOLDER_ID)

print(f"   Encontradas {len(subcarpetas)} subcarpetas.")

print("🔗 Compartiendo subcarpetas...")
for carpeta in subcarpetas:
    print(f" → {carpeta['name']} ({carpeta['id']})")
    compartir_carpeta(carpeta["id"], TU_EMAIL)

print("\n✅ LISTO: YA TENÉS ACCESO A TODA LA ESTRUCTURA.")
