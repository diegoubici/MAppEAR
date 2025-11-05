from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

# Ruta a tu archivo de credenciales
CLIENT_SECRET_FILE = "credentials.json"

# Permisos necesarios: lectura y escritura en Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

creds = None
TOKEN_FILE = 'token_drive.json'

# Si ya te autenticás una vez, se guarda token_drive.json y no pedirá login de nuevo
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
else:
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

# Conectarse a Drive
service = build('drive', 'v3', credentials=creds)

# Listar los 5 primeros archivos en tu Drive
results = service.files().list(pageSize=5, fields="files(id, name)").execute()
items = results.get('files', [])

if not items:
    print("No hay archivos en tu Drive.")
else:
    print("Archivos en tu Google Drive:")
    for item in items:
        print(f"{item['name']} ({item['id']})")
