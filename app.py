import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

# === GOOGLE DRIVE API ===
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io

SCOPES = ['https://www.googleapis.com/auth/drive.file']
ROOT_FOLDER_ID = "1wP71l2KGx7IccvNex4HXUM0t2-NlneVn"  # Carpeta raíz MappearUploads en Drive


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


def buscar_carpeta_usuario(service, usuario):
    """Busca la carpeta del usuario dentro de MappearUploads."""
    try:
        # Buscar todas las carpetas dentro de MappearUploads
        q = f"mimeType='application/vnd.google-apps.folder' and '{ROOT_FOLDER_ID}' in parents and trashed=false"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        folders = result.get("files", [])
        
        # Normalizar nombre del usuario para comparación
        user_normalizado = usuario.strip().lower().replace(" ", "")
        
        for folder in folders:
            nombre_carpeta = folder["name"].strip().lower().replace(" ", "")
            if nombre_carpeta == user_normalizado:
                print(f"✅ Encontrada carpeta del usuario '{usuario}': {folder['name']} (ID: {folder['id']})")
                return folder['id']
        
        print(f"⚠️ No se encontró carpeta para el usuario '{usuario}' en MappearUploads")
        return None
    except Exception as e:
        print(f"❌ Error buscando carpeta del usuario: {e}")
        return None


def crear_carpeta_usuario(service, usuario):
    """Crea una carpeta para el usuario dentro de MappearUploads."""
    try:
        folder_metadata = {
            'name': usuario,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [ROOT_FOLDER_ID]
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder['id']
        print(f"✅ Carpeta creada para el usuario '{usuario}' (ID: {folder_id})")
        return folder_id
    except Exception as e:
        print(f"❌ Error creando carpeta del usuario: {e}")
        return None


def subir_a_drive(usuario, ruta_local):
    """Sube o reemplaza un archivo XLSX en la carpeta del usuario en Drive."""
    try:
        service = obtener_servicio_drive()
        
        # Buscar carpeta del usuario
        folder_id = buscar_carpeta_usuario(service, usuario)
        if not folder_id:
            # Si no existe, crear la carpeta
            folder_id = crear_carpeta_usuario(service, usuario)
            if not folder_id:
                print(f"❌ No se pudo crear carpeta para {usuario}")
                return False

        # Subir o reemplazar el archivo
        nombre_archivo = os.path.basename(ruta_local)
        
        # Buscar si el archivo ya existe
        q = f"name='{nombre_archivo}' and '{folder_id}' in parents and trashed=false"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        archivos_existentes = result.get('files', [])
        
        media = MediaFileUpload(
            ruta_local,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            resumable=True
        )
        
        if archivos_existentes:
            # Actualizar archivo existente
            file_id = archivos_existentes[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"✅ Archivo '{nombre_archivo}' actualizado en la carpeta '{usuario}' en Drive.")
        else:
            # Crear nuevo archivo
            metadata = {'name': nombre_archivo, 'parents': [folder_id]}
            service.files().create(body=metadata, media_body=media, fields='id').execute()
            print(f"✅ Archivo '{nombre_archivo}' subido a la carpeta '{usuario}' en Drive.")
        
        return True
    except Exception as e:
        print(f"❌ Error subiendo archivo a Drive: {e}")
        return False


def descargar_de_drive(usuario, nombre_archivo):
    """Descarga un archivo XLSX del usuario desde Google Drive al directorio temporal."""
    try:
        service = obtener_servicio_drive()
        
        # Buscar carpeta del usuario
        folder_id = buscar_carpeta_usuario(service, usuario)
        if not folder_id:
            print(f"⚠️ Carpeta del usuario '{usuario}' no encontrada en Drive.")
            return None

        # Buscar archivo dentro de la carpeta
        q = f"name='{nombre_archivo}' and '{folder_id}' in parents and trashed=false"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        archivos = result.get('files', [])
        
        if not archivos:
            print(f"⚠️ Archivo '{nombre_archivo}' no encontrado en la carpeta de {usuario}.")
            return None

        file_id = archivos[0]['id']
        ruta_local = os.path.join(BASE_DIR, nombre_archivo)
        
        # Descargar archivo
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(ruta_local, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        print(f"⬇️ Archivo '{nombre_archivo}' descargado de Drive.")
        return ruta_local
    except Exception as e:
        print(f"❌ Error al descargar de Drive: {e}")
        return None


def listar_archivos_drive(usuario):
    """Lista todos los archivos XLSX del usuario en Drive."""
    try:
        service = obtener_servicio_drive()
        
        # Buscar carpeta del usuario
        folder_id = buscar_carpeta_usuario(service, usuario)
        if not folder_id:
            print(f"⚠️ Carpeta del usuario '{usuario}' no encontrada en Drive.")
            return []

        # Listar archivos XLSX en la carpeta
        q = f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        archivos = result.get("files", [])
        
        archivos_xlsx = [f["name"] for f in archivos if f["name"].lower().endswith(".xlsx")]
        print(f"📂 Encontrados {len(archivos_xlsx)} archivos XLSX para {usuario} en Drive")
        return sorted(archivos_xlsx)
    except Exception as e:
        print(f"❌ Error listando archivos de Drive: {e}")
        return []


# === FLASK APP ===
app = Flask(__name__)
app.secret_key = "BanfiClaveSegura123"

# === CONFIGURACIÓN AUTOMÁTICA SEGÚN ENTORNO ===
def es_render():
    """Detecta si el sistema está corriendo en Render (entorno en la nube)."""
    return os.environ.get("RENDER", "") != "" or "render.com" in os.environ.get("HOSTNAME", "").lower()


if es_render():
    # ☁️ MODO RENDER (usa Google Drive)
    BASE_DIR = "/tmp"  # ✅ /tmp es la única carpeta con permisos de escritura en Render
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
    """Obtiene archivos XLSX del directorio local del usuario."""
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

    user = session["usuario"]
    user_dir = get_user_dir(user)

    # Obtener lista de archivos según el modo
    if USAR_DRIVE_COMO_FUENTE:
        # 🔽 Si estamos en Render, obtener archivos desde Drive
        archivos = listar_archivos_drive(user)
        
        # También descargar todos los archivos para tenerlos localmente disponibles
        try:
            service = obtener_servicio_drive()
            folder_id = buscar_carpeta_usuario(service, user)
            
            if folder_id:
                # Descargar todos los .xlsx de esa carpeta
                q = f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false"
                files = service.files().list(q=q, fields="files(id, name)").execute().get("files", [])
                
                for f in files:
                    if f["name"].lower().endswith(".xlsx"):
                        file_id = f["id"]
                        ruta_local = os.path.join(user_dir, f["name"])
                        print(f"⬇️ Descargando {f['name']} desde Drive (carpeta {user})...")
                        
                        request = service.files().get_media(fileId=file_id)
                        fh = io.FileIO(ruta_local, "wb")
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                
                print(f"✅ Archivos XLSX del usuario {user} descargados en {user_dir}")
        except Exception as e:
            print(f"❌ Error descargando archivos desde Drive: {e}")
    else:
        # 🔽 Si estamos en modo local, usar archivos del directorio
        archivos = obtener_archivos(user_dir)

    return render_template("seleccionar_archivo.html",
                           archivos=archivos,
                           usuario=user,
                           rol=session["rol"])


@app.route("/abrir/<nombre>")
def abrir_archivo(nombre):
    if "usuario" not in session:
        return redirect(url_for("login_page"))

    user = session["usuario"]
    user_dir = get_user_dir(user)
    ruta_local = os.path.join(user_dir, nombre)

    # 🔽 Si estamos en Render, asegurar que el archivo esté descargado
    if USAR_DRIVE_COMO_FUENTE:
        if not os.path.exists(ruta_local):
            descargado = descargar_de_drive(user, nombre)
            if descargado:
                ruta_local = descargado
            else:
                return f"❌ No se pudo descargar '{nombre}' desde Google Drive.", 404

    # Verificar existencia final
    if not os.path.exists(ruta_local):
        return "Archivo no encontrado.", 404

    session["archivo_seleccionado"] = nombre
    poligonos = cargar_poligonos(ruta_local)
    return render_template("mapa.html", usuario=user, rol=session["rol"], poligonos=poligonos)


@app.route("/nuevo_archivo", methods=["POST"])
def nuevo_archivo():
    nombre = request.form.get("nombre")
    if not nombre:
        return jsonify({"success": False, "mensaje": "Nombre inválido."})
    if not nombre.lower().endswith(".xlsx"):
        nombre += ".xlsx"
    
    user = session.get("usuario")
    user_dir = get_user_dir(user)
    if not user_dir:
        return jsonify({"success": False, "mensaje": "Usuario no logueado."})
    
    ruta_nueva = os.path.join(user_dir, nombre)
    
    # Verificar si existe localmente
    if os.path.exists(ruta_nueva):
        return jsonify({"success": False, "mensaje": "El archivo ya existe."})
    
    # Si usamos Drive, verificar también en Drive
    if USAR_DRIVE_COMO_FUENTE:
        archivos_drive = listar_archivos_drive(user)
        if nombre in archivos_drive:
            return jsonify({"success": False, "mensaje": "El archivo ya existe en Drive."})
    
    # Crear archivo vacío
    df = pd.DataFrame(columns=["NOMBRE", "SUPERFICIE", "STATUS", "STATUS1", "STATUS2", "STATUS3", "PARTIDO", "COLOR HEX", "COORDENADAS"])
    df.to_excel(ruta_nueva, index=False)
    
    # Subir a Drive si está habilitado
    if SUBIR_A_DRIVE:
        subir_a_drive(user, ruta_nueva)
    
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
        
        user = session.get("usuario")
        user_dir = get_user_dir(user)
        ruta = os.path.join(user_dir, archivo_sel)
        
        # Guardar localmente
        guardar_poligonos(data["datos"], ruta)

        # 🔄 Subir a Drive solo si está habilitado
        if SUBIR_A_DRIVE:
            exito = subir_a_drive(user, ruta)
            if not exito:
                return jsonify({"success": False, "mensaje": "❌ Error subiendo a Drive."})

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
        
        user = session.get("usuario")
        user_dir = get_user_dir(user)
        ruta_nueva = os.path.join(user_dir, nuevo_nombre)
        
        # Guardar localmente
        guardar_poligonos(datos, ruta_nueva)

        # 🔄 Subir a Drive solo si está habilitado
        if SUBIR_A_DRIVE:
            exito = subir_a_drive(user, ruta_nueva)
            if not exito:
                return jsonify({"success": False, "mensaje": "❌ Error subiendo a Drive."})

        return jsonify({"success": True, "mensaje": f"✅ Archivo guardado como '{nuevo_nombre}' correctamente."})
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"❌ Error al guardar: {e}"})


# === EJECUCIÓN ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)