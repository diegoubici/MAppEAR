from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# ============================
# CONFIGURACIÓN
# ============================

SERVICE_ACCOUNT_FILE = "service_account.json"   # tu JSON de Google
FOLDER_ID = "1owQU7ef5s5jzY3w9Nj-DScziZnohaOrd" # ID de la carpeta raíz
TU_EMAIL = "diegoubici@gmail.com"               # tu email personal

# ============================
# AUTENTICAR
# ============================

creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/drive"]
)

service = build("drive", "v3", credentials=creds)

# ============================
# COMPARTIR
# ============================

permission = {
    "type": "user",
    "role": "writer",
    "emailAddress": TU_EMAIL
}

try:
    service.permissions().create(
        fileId=FOLDER_ID,
        body=permission,
        sendNotificationEmail=False
    ).execute()

    print("✅ Carpeta compartida con tu email:", TU_EMAIL)

except Exception as e:
    print("❌ Error compartiendo la carpeta:", e)
