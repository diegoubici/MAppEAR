import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

# === GOOGLE DRIVE API ===
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive.file']
ROOT_FOLDER_ID = "1wP71l2KGx7IccvNex4HXUM0t2-NlneVn"  # Carpeta raíz en Drive


# === FUNCIONES DE GOOGLE DRIVE ===
def obtener_servicio_drive():
    """Crea o usa las credenciales almacenadas para acceder a Drive."""
    creds = None
    if os.path.exists('token.json'):
        with open('token.json', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)

            # 🔧 CAMBIO: se usa run_console() en lugar de run_local_server()
            # Esto evita el error "could not locate runnable browser" en Render
            creds = flow.run_console()

        with open('token.json', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)


def subir_a_drive(usuario, ruta_local):
    """Sube o reemplaza un archivo XLSX en una carpeta del usuario en Drive."""
    service = obtener_servicio_drive()
    carpeta_nombre = usuario

    # Buscar o crear carpeta del usuario
    q = f"name='{carpeta_nombre}' and mimeType='application/vnd.google-apps.folder' and '{ROOT_FOLDER_ID}' in parents"
    result = service.files().list(q=q, fields="files(id, name)").execute()
    items = result.get('files', [])
    if not items:
        folder_metadata = {
            'name': carpeta_nombre,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [ROOT_FOLDER_ID]
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder['id']
    else:
        folder_id = items[0]['id']

    # Subir o reemplazar el archivo
    nombre_archivo = os.path.basename(ruta_local)
    q = f"name='{nombre_archivo}' and '{folder_id}' in parents"
    result = service.files().list(q=q, fields="files(id, name)").execute()
    items = result.get('files', [])
    media = MediaFileUpload(
        ruta_local,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        resumable=True
    )
    if items:
        file_id = items[0]['id']
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {'name': nombre_archivo, 'parents': [folder_id]}
        service.files().create(body=metadata, media_body=media, fields='id').execute()

    print(f"✅ Archivo '{nombre_archivo}' subido a la carpeta '{carpeta_nombre}' en Drive.")


# === FLASK APP ===
app = Flask(__name__)
app.secret_key = "BanfiClaveSegura123"

# === CONFIGURACIÓN AUTOMÁTICA SEGÚN ENTORNO ===
def es_render():
    """Detecta si el sistema está corriendo en Render (entorno en la nube)."""
    return os.environ.get("RENDER", "") != "" or "render.com" in os.environ.get("HOSTNAME", "").lower()


if es_render():
    # ☁️ MODO RENDER (usa Google Drive)
    BASE_DIR = "/data"  # Carpeta temporal para manejo interno
    SUBIR_A_DRIVE = True
    USAR_DRIVE_COMO_FUENTE = True
else:
    # 🖥️ MODO LOCAL (usa carpetas del equipo)
    if os.path.exists(r"C:\MAPPEAR"):
        BASE_DIR = r"C:\MAPPEAR\data"
    elif os.path.exists(r"F:\MAPPEAR"):
        BASE_DIR = r"F:\MAPPEAR\data"
    else:
        BASE_DIR = os.path.join(os.getcwd(), "data")
    SUBIR_A_DRIVE = False
    USAR_DRIVE_COMO_FUENTE = False

os.makedirs(BASE_DIR, exist_ok=True)
print(f"📂 Carpeta de trabajo: {BASE_DIR}")
print(f"☁️ Subida a Drive habilitada: {SUBIR_A_DRIVE}")
print(f"📥 Lectura desde Drive habilitada: {USAR_DRIVE_COMO_FUENTE}")


# === FUNCIONES DE DESCARGA DESDE GOOGLE DRIVE (solo Render) ===
def descargar_de_drive(usuario, nombre_archivo):
    """Descarga un archivo XLSX del usuario desde Google Drive al directorio temporal."""
    try:
        service = obtener_servicio_drive()
        carpeta_nombre = usuario
        q = f"name='{carpeta_nombre}' and mimeType='application/vnd.google-apps.folder' and '{ROOT_FOLDER_ID}' in parents"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        items = result.get('files', [])
        if not items:
            print(f"⚠️ Carpeta del usuario '{usuario}' no encontrada en Drive.")
            return None
        folder_id = items[0]['id']

        # Buscar archivo dentro de la carpeta
        q = f"name='{nombre_archivo}' and '{folder_id}' in parents"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        archivos = result.get('files', [])
        if not archivos:
            print(f"⚠️ Archivo '{nombre_archivo}' no encontrado en la carpeta de {usuario}.")
            return None

        file_id = archivos[0]['id']
        ruta_local = os.path.join(BASE_DIR, nombre_archivo)
        request = service.files().get_media(fileId=file_id)
        with open(ruta_local, "wb") as f:
            response = service._http.request(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media")
            f.write(response[1])
        print(f"⬇️ Archivo '{nombre_archivo}' descargado de Drive.")
        return ruta_local
    except Exception as e:
        print(f"❌ Error al descargar de Drive: {e}")
        return None


# === USUARIOS Y ROLES ===
USERS = {
    "DSUBICI": {"password": "Banfi138", "rol": "admin"},
    "usuario1": {"password": "contraseña1", "rol": "user"},
    "usuario2": {"password": "contraseña2", "rol": "user"},
    "usuario3": {"password": "contraseña3", "rol": "user"},
    "usuario4": {"password": "contraseña4", "rol": "user"},
    "RIVADAVIA": {"password": "rivadavia5", "rol": "user"},
}


# === FUNCIONES AUXILIARES ===
def get_user_dir(username):
    if not username:
        return None
    user_dir = os.path.join(BASE_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def obtener_archivos(user_dir):
    if not user_dir or not os.path.exists(user_dir):
        return []
    return sorted([f for f in os.listdir(user_dir) if f.endswith(".xlsx")])


def cargar_poligonos(ruta_archivo):
    df = pd.read_excel(ruta_archivo)
    columnas = ["NOMBRE", "SUPERFICIE", "STATUS", "STATUS1", "STATUS2", "STATUS3", "PARTIDO", "COLOR HEX", "COORDENADAS"]
    for col in columnas:
        if col not in df.columns:
            df[col] = ""
    poligonos = []
    for _, fila in df.iterrows():
        coords = []
        if pd.notna(fila["COORDENADAS"]) and fila["COORDENADAS"]:
            try:
                puntos = str(fila["COORDENADAS"]).split(" ")
                for p in puntos:
                    lon, lat = map(float, p.split(","))
                    coords.append([lat, lon])
            except Exception:
                coords = []
        poligonos.append({
            "name": str(fila["NOMBRE"]),
            "superficie": str(fila["SUPERFICIE"]),
            "status": str(fila["STATUS"]),
            "status1": str(fila["STATUS1"]),
            "status2": str(fila["STATUS2"]),
            "status3": str(fila["STATUS3"]),
            "partido": str(fila["PARTIDO"]),
            "color": str(fila["COLOR HEX"]) if pd.notna(fila["COLOR HEX"]) else "#CCCCCC",
            "coords": coords,
            "COORDENADAS": str(fila["COORDENADAS"]) if pd.notna(fila["COORDENADAS"]) else ""
        })
    return poligonos


def guardar_poligonos(nuevos_datos, ruta_destino):
    columnas = ["NOMBRE", "SUPERFICIE", "STATUS", "STATUS1", "STATUS2", "STATUS3", "PARTIDO", "COLOR HEX", "COORDENADAS"]
    if not os.path.exists(ruta_destino):
        df = pd.DataFrame(columns=columnas)
    else:
        df = pd.read_excel(ruta_destino)
        for col in columnas:
            if col not in df.columns:
                df[col] = ""

    for i, dato in enumerate(nuevos_datos):
        if "COLOR HEX" not in dato and "color" in dato:
            dato["COLOR HEX"] = dato["color"]

        if i < len(df):
            for col in columnas:
                df.at[i, col] = dato.get(col, dato.get(col.lower(), ""))
        else:
            df.loc[i] = [dato.get(col, dato.get(col.lower(), "")) for col in columnas]

    df.to_excel(ruta_destino, index=False)


# === RUTAS FLASK ===
@app.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    user = USERS.get(username)
    if user and user["password"] == password:
        session["usuario"] = username
        session["rol"] = user["rol"]
        return redirect(url_for("seleccionar_archivo"))
    return render_template("login.html", error="Usuario o contraseña incorrectos.")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("https://www.google.com.ar")


@app.route("/inicio")
def seleccionar_archivo():
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    user_dir = get_user_dir(session["usuario"])
    archivos = obtener_archivos(user_dir)
    return render_template("seleccionar_archivo.html", archivos=archivos,
                           usuario=session["usuario"], rol=session["rol"])


@app.route("/abrir/<nombre>")
def abrir_archivo(nombre):
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    user_dir = get_user_dir(session["usuario"])
    archivos = obtener_archivos(user_dir)
    if nombre not in archivos:
        return "Archivo no encontrado", 404
    session['archivo_seleccionado'] = nombre
    ruta = os.path.join(user_dir, nombre)
    poligonos = cargar_poligonos(ruta)
    return render_template("mapa.html", usuario=session["usuario"],
                           rol=session["rol"], poligonos=poligonos)


@app.route("/nuevo_archivo", methods=["POST"])
def nuevo_archivo():
    nombre = request.form.get("nombre")
    if not nombre:
        return jsonify({"success": False, "mensaje": "Nombre inválido."})
    if not nombre.lower().endswith(".xlsx"):
        nombre += ".xlsx"
    user_dir = get_user_dir(session.get("usuario"))
    if not user_dir:
        return jsonify({"success": False, "mensaje": "Usuario no logueado."})
    ruta_nueva = os.path.join(user_dir, nombre)
    if os.path.exists(ruta_nueva):
        return jsonify({"success": False, "mensaje": "El archivo ya existe."})
    df = pd.DataFrame(columns=["NOMBRE", "SUPERFICIE", "STATUS", "STATUS1", "STATUS2", "STATUS3", "PARTIDO", "COLOR HEX", "COORDENADAS"])
    df.to_excel(ruta_nueva, index=False)
    return jsonify({"success": True, "archivo": nombre})


@app.route("/guardar", methods=["POST"])
def guardar():
    archivo_sel = session.get('archivo_seleccionado')
    if not archivo_sel:
        return jsonify({"success": False, "mensaje": "No hay archivo seleccionado."})
    try:
        data = request.get_json(force=True)
        if not data or "datos" not in data:
            return jsonify({"success": False, "mensaje": "Datos inválidos."})
        user_dir = get_user_dir(session.get("usuario"))
        ruta = os.path.join(user_dir, archivo_sel)
        guardar_poligonos(data["datos"], ruta)

        # 🔄 Subir a Drive solo si está habilitado
        if SUBIR_A_DRIVE:
            subir_a_drive(session.get("usuario"), ruta)

        return jsonify({"success": True, "mensaje": "✅ Cambios guardados correctamente."})
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"❌ Error: {e}"})


@app.route("/guardar_como", methods=["POST"])
def guardar_como():
    try:
        contenido = request.get_json(force=True)
        datos = contenido.get("datos", [])
        nuevo_nombre = contenido.get("nuevo_nombre", "").strip()
        if not nuevo_nombre:
            return jsonify({"success": False, "mensaje": "⚠️ No se indicó nombre para guardar."})
        if not nuevo_nombre.lower().endswith(".xlsx"):
            nuevo_nombre += ".xlsx"
        user_dir = get_user_dir(session.get("usuario"))
        ruta_nueva = os.path.join(user_dir, nuevo_nombre)
        guardar_poligonos(datos, ruta_nueva)

        # 🔄 Subir a Drive solo si está habilitado
        if SUBIR_A_DRIVE:
            subir_a_drive(session.get("usuario"), ruta_nueva)

        return jsonify({"success": True, "mensaje": f"✅ Archivo guardado como '{nuevo_nombre}' correctamente."})
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"❌ Error al guardar: {e}"})


# === EJECUCIÓN ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)

