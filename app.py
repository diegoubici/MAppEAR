import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

# === GOOGLE DRIVE API ===
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from google.oauth2 import service_account
import json

# === CONFIGURACIÓN DE SERVICE ACCOUNT ===
SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ['https://www.googleapis.com/auth/drive']
ROOT_FOLDER_ID = "1iVFEB2vhPyGucD5fSGdn1KpqXBs331yJ"  # Carpeta Drive correcta

# === DETECTAR MODO DE EJECUCIÓN ===
def es_render():
    return os.environ.get("RENDER", "") != "" or "render.com" in os.environ.get("HOSTNAME", "").lower()

MODO_RENDER = es_render()

if MODO_RENDER:
    print("🌐 MODO: RENDER (usando Google Drive)")
    BASE_DIR = "/tmp"
    # Si estamos en Render, se crea temporalmente el archivo de credenciales
    if os.environ.get("GOOGLE_SERVICE_ACCOUNT"):
        try:
            creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT"]
            with open(SERVICE_ACCOUNT_FILE, "w") as f:
                f.write(creds_json)
            print("✅ Archivo service_account.json creado temporalmente desde variable de entorno.")
        except Exception as e:
            print(f"❌ Error creando archivo de credenciales desde variable de entorno: {e}")
    else:
        print("⚠️ Variable de entorno GOOGLE_SERVICE_ACCOUNT no encontrada.")
else:
    print("🖥️  MODO: LOCAL (usando carpetas locales)")
    if os.path.exists(r"C:\MAPPEAR"):
        BASE_DIR = r"C:\MAPPEAR\data"
    elif os.path.exists(r"F:\MAPPEAR"):
        BASE_DIR = r"F:\MAPPEAR\data"
    else:
        BASE_DIR = os.path.join(os.getcwd(), "data")

os.makedirs(BASE_DIR, exist_ok=True)
print(f"📁 BASE_DIR: {BASE_DIR}")


# === FUNCIÓN DE AUTENTICACIÓN (solo para RENDER) ===
def obtener_servicio_drive():
    """Autentica con la API de Google Drive usando cuenta de servicio."""
    if not MODO_RENDER:
        return None
    
    try:
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        elif os.environ.get("GOOGLE_SERVICE_ACCOUNT"):
            creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            raise FileNotFoundError("No se encontró el archivo service_account.json ni la variable de entorno.")

        service = build('drive', 'v3', credentials=creds)
        print("✅ Autenticado con Google Drive correctamente.")
        return service
    except Exception as e:
        print(f"❌ Error al autenticar con la cuenta de servicio: {e}")
        return None


# === FUNCIONES DE GOOGLE DRIVE (solo para RENDER) ===
def buscar_carpeta_usuario(service, usuario):
    """Busca la carpeta del usuario dentro de MappearUploads."""
    try:
        q = f"mimeType='application/vnd.google-apps.folder' and '{ROOT_FOLDER_ID}' in parents and trashed=false"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        folders = result.get("files", [])
        user_normalizado = usuario.strip().lower().replace(" ", "")
        for folder in folders:
            nombre_carpeta = folder["name"].strip().lower().replace(" ", "")
            if nombre_carpeta == user_normalizado:
                print(f"✅ Encontrada carpeta del usuario '{usuario}': {folder['name']} (ID: {folder['id']})")
                return folder['id']
        print(f"⚠️ No se encontró carpeta para el usuario '{usuario}'.")
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
        print(f"✅ Carpeta creada para '{usuario}' (ID: {folder['id']})")
        return folder['id']
    except Exception as e:
        print(f"❌ Error creando carpeta del usuario: {e}")
        return None


# === FUNCIONES UNIFICADAS (LOCAL + RENDER) ===

def listar_archivos(usuario):
    """Lista los archivos XLSX del usuario (LOCAL o DRIVE según el modo)."""
    if MODO_RENDER:
        # MODO RENDER: usar Google Drive
        return listar_archivos_drive(usuario)
    else:
        # MODO LOCAL: usar carpetas locales
        return listar_archivos_local(usuario)


def listar_archivos_local(usuario):
    """Lista archivos XLSX en la carpeta local del usuario."""
    try:
        user_dir = os.path.join(BASE_DIR, usuario)
        os.makedirs(user_dir, exist_ok=True)
        
        archivos = [f for f in os.listdir(user_dir) if f.lower().endswith(".xlsx")]
        print(f"📄 Archivos locales encontrados para {usuario}: {archivos}")
        return sorted(archivos)
    except Exception as e:
        print(f"❌ Error listando archivos locales: {e}")
        return []


def listar_archivos_drive(usuario):
    """Lista los archivos XLSX del usuario en Drive."""
    try:
        service = obtener_servicio_drive()
        if not service:
            return []
        folder_id = buscar_carpeta_usuario(service, usuario)
        if not folder_id:
            return []
        q = f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        archivos = result.get("files", [])
        archivos_xlsx = [f["name"] for f in archivos if f["name"].lower().endswith(".xlsx")]
        print(f"📄 Archivos Drive encontrados para {usuario}: {archivos_xlsx}")
        return sorted(archivos_xlsx)
    except Exception as e:
        print(f"❌ Error listando archivos de Drive: {e}")
        return []


def obtener_archivo(usuario, nombre_archivo):
    """Obtiene la ruta del archivo (LOCAL o descarga de DRIVE según el modo)."""
    if MODO_RENDER:
        # MODO RENDER: descargar de Drive
        return descargar_de_drive(usuario, nombre_archivo)
    else:
        # MODO LOCAL: ruta directa
        return obtener_archivo_local(usuario, nombre_archivo)


def obtener_archivo_local(usuario, nombre_archivo):
    """Obtiene la ruta del archivo en el sistema local."""
    try:
        user_dir = os.path.join(BASE_DIR, usuario)
        ruta_archivo = os.path.join(user_dir, nombre_archivo)
        
        if os.path.exists(ruta_archivo):
            print(f"✅ Archivo local encontrado: {ruta_archivo}")
            return ruta_archivo
        else:
            print(f"❌ Archivo local no encontrado: {ruta_archivo}")
            return None
    except Exception as e:
        print(f"❌ Error obteniendo archivo local: {e}")
        return None


def descargar_de_drive(usuario, nombre_archivo):
    """Descarga un archivo XLSX del usuario desde Google Drive."""
    try:
        service = obtener_servicio_drive()
        if not service:
            return None
        folder_id = buscar_carpeta_usuario(service, usuario)
        if not folder_id:
            return None
        q = f"name='{nombre_archivo}' and '{folder_id}' in parents and trashed=false"
        result = service.files().list(q=q, fields="files(id, name)").execute()
        archivos = result.get('files', [])
        if not archivos:
            return None

        file_id = archivos[0]['id']
        ruta_local = os.path.join(BASE_DIR, nombre_archivo)
        request_obj = service.files().get_media(fileId=file_id)
        with io.FileIO(ruta_local, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request_obj)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        print(f"⬇️ Archivo '{nombre_archivo}' descargado correctamente de Drive.")
        return ruta_local
    except Exception as e:
        print(f"❌ Error al descargar de Drive: {e}")
        return None


def guardar_archivo(usuario, ruta_local):
    """Guarda el archivo (LOCAL o sube a DRIVE según el modo)."""
    if MODO_RENDER:
        # MODO RENDER: subir a Drive
        return subir_a_drive(usuario, ruta_local)
    else:
        # MODO LOCAL: ya está guardado en la carpeta correcta
        print(f"✅ Archivo guardado localmente: {ruta_local}")
        return True


def subir_a_drive(usuario, ruta_local):
    """Sube o reemplaza un archivo XLSX en la carpeta del usuario en Drive."""
    print(f"📤 [SUBIR_DRIVE] Usuario: {usuario}, Archivo: {ruta_local}")
    try:
        # Verificar que el archivo existe antes de subir
        if not os.path.exists(ruta_local):
            print(f"❌ [SUBIR_DRIVE] Archivo no existe: {ruta_local}")
            return False
        
        file_size = os.path.getsize(ruta_local)
        print(f"📤 [SUBIR_DRIVE] Tamaño del archivo: {file_size} bytes")
        
        service = obtener_servicio_drive()
        if not service:
            print(f"❌ [SUBIR_DRIVE] No se pudo obtener servicio")
            return False
        
        folder_id = buscar_carpeta_usuario(service, usuario)
        if not folder_id:
            print(f"📁 [SUBIR_DRIVE] Carpeta no existe, creando...")
            folder_id = crear_carpeta_usuario(service, usuario)
            if not folder_id:
                print(f"❌ [SUBIR_DRIVE] No se pudo crear carpeta")
                return False

        nombre_archivo = os.path.basename(ruta_local)
        print(f"📤 [SUBIR_DRIVE] Nombre del archivo: {nombre_archivo}")
        
        q = f"name='{nombre_archivo}' and '{folder_id}' in parents and trashed=false"
        result = service.files().list(q=q, fields="files(id)").execute()
        archivos_existentes = result.get("files", [])

        media = MediaFileUpload(
            ruta_local, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
            resumable=True
        )

        if archivos_existentes:
            file_id = archivos_existentes[0]['id']
            print(f"🔁 [SUBIR_DRIVE] Actualizando archivo existente (ID: {file_id})")
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"✅ [SUBIR_DRIVE] Archivo '{nombre_archivo}' actualizado en Drive")
        else:
            print(f"📤 [SUBIR_DRIVE] Creando nuevo archivo")
            metadata = {'name': nombre_archivo, 'parents': [folder_id]}
            service.files().create(body=metadata, media_body=media, fields='id').execute()
            print(f"✅ [SUBIR_DRIVE] Archivo '{nombre_archivo}' subido a Drive")
        
        return True
    except Exception as e:
        print(f"❌ [SUBIR_DRIVE] Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False


# === FLASK APP ===
app = Flask(__name__)
app.secret_key = "BanfiClaveSegura123"

USERS = {
    "DSUBICI": {"password": "Banfi138", "rol": "admin"},
    "usuario1": {"password": "contraseña1", "rol": "user"},
    "usuario2": {"password": "contraseña2", "rol": "user"},
    "usuario3": {"password": "contraseña3", "rol": "user"},
    "usuario4": {"password": "contraseña4", "rol": "user"},
    "RIVADAVIA": {"password": "rivadavia5", "rol": "user"},
}


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
    """
    Guarda los datos actualizados en el archivo Excel con nombres de columna fijos
    y en el orden correcto. Evita mezclas entre mayúsculas/minúsculas.
    """
    columnas = ["NOMBRE", "SUPERFICIE", "STATUS", "STATUS1", "STATUS2", "STATUS3", "PARTIDO", "COLOR HEX", "COORDENADAS"]

    # Crear DataFrame nuevo con los datos recibidos
    df = pd.DataFrame([
        {
            "NOMBRE": dato.get("name", ""),
            "SUPERFICIE": dato.get("superficie", ""),
            "STATUS": dato.get("status", ""),
            "STATUS1": dato.get("status1", ""),
            "STATUS2": dato.get("status2", ""),
            "STATUS3": dato.get("status3", ""),
            "PARTIDO": dato.get("partido", ""),
            "COLOR HEX": dato.get("color", "#CCCCCC"),
            "COORDENADAS": dato.get("COORDENADAS", "")
        }
        for dato in nuevos_datos
    ], columns=columnas)

    # Guardar Excel
    df.to_excel(ruta_destino, index=False)


# === RUTAS ===
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
    archivos = listar_archivos(user)  # ← Usa función unificada
    return render_template("seleccionar_archivo.html", archivos=archivos, usuario=user, rol=session["rol"])


@app.route("/abrir/<nombre>")
def abrir_archivo(nombre):
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    user = session["usuario"]
    ruta_local = obtener_archivo(user, nombre)  # ← Usa función unificada
    if not ruta_local:
        return f"No se pudo obtener '{nombre}'.", 404
    session["archivo_seleccionado"] = nombre
    poligonos = cargar_poligonos(ruta_local)
    return render_template("mapa.html", usuario=user, rol=session["rol"], poligonos=poligonos)


@app.route("/guardar", methods=["POST"])
def guardar():
    archivo_sel = session.get("archivo_seleccionado")
    if not archivo_sel:
        return jsonify({"success": False, "mensaje": "No hay archivo seleccionado."})
    try:
        data = request.get_json(force=True)
        user = session.get("usuario")
        
        # Determinar ruta según el modo
        if MODO_RENDER:
            ruta = os.path.join(BASE_DIR, archivo_sel)
        else:
            user_dir = os.path.join(BASE_DIR, user)
            os.makedirs(user_dir, exist_ok=True)
            ruta = os.path.join(user_dir, archivo_sel)
        
        guardar_poligonos(data["datos"], ruta)
        guardar_archivo(user, ruta)  # ← Usa función unificada
        return jsonify({"success": True, "mensaje": "✅ Cambios guardados correctamente."})
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"❌ Error: {e}"})


@app.route("/guardar_como", methods=["POST"])
def guardar_como():
    try:
        contenido = request.get_json(force=True)
        datos = contenido.get("datos", [])
        nuevo_nombre = contenido.get("nuevo_nombre", "").strip()
        
        print(f"📝 [GUARDAR_COMO] Iniciando guardado como...")
        print(f"📝 [GUARDAR_COMO] Nuevo nombre solicitado: {nuevo_nombre}")
        print(f"📝 [GUARDAR_COMO] Cantidad de datos: {len(datos)}")
        
        if not nuevo_nombre:
            return jsonify({"success": False, "mensaje": "⚠️ No se indicó nombre."})
        
        # Forzar extensión .xlsx
        if not nuevo_nombre.lower().endswith(".xlsx"):
            nuevo_nombre += ".xlsx"
        
        print(f"📝 [GUARDAR_COMO] Nombre final: {nuevo_nombre}")
        
        user = session.get("usuario")
        print(f"📝 [GUARDAR_COMO] Usuario: {user}")
        print(f"📝 [GUARDAR_COMO] Modo: {'RENDER' if MODO_RENDER else 'LOCAL'}")
        
        # === DETERMINAR RUTA SEGÚN MODO ===
        if MODO_RENDER:
            # En Render, usar carpeta temporal /tmp (no BASE_DIR)
            ruta_nueva = os.path.join("/tmp", nuevo_nombre)
        else:
            # En modo local, guardar en carpeta del usuario
            user_dir = os.path.join(BASE_DIR, user)
            os.makedirs(user_dir, exist_ok=True)
            ruta_nueva = os.path.join(user_dir, nuevo_nombre)
        
        print(f"📝 [GUARDAR_COMO] Ruta temporal: {ruta_nueva}")
        
        # === GUARDAR LOCALMENTE ===
        guardar_poligonos(datos, ruta_nueva)
        
        # Verificar que se guardó
        if not os.path.exists(ruta_nueva):
            print(f"❌ [GUARDAR_COMO] Error: archivo no se creó en {ruta_nueva}")
            return jsonify({"success": False, "mensaje": "❌ Error: no se pudo crear el archivo local"})
        
        file_size = os.path.getsize(ruta_nueva)
        print(f"✅ [GUARDAR_COMO] Archivo creado localmente: {file_size} bytes")
        
        # === SUBIR A DRIVE EN RENDER ===
        if MODO_RENDER:
            print(f"📤 [GUARDAR_COMO] Subiendo a Google Drive...")
            exito = subir_a_drive(user, ruta_nueva)
            
            if exito:
                print(f"✅ [GUARDAR_COMO] Archivo subido a Drive exitosamente")
                
                # Eliminar archivo temporal
                try:
                    os.remove(ruta_nueva)
                    print(f"🗑️ [GUARDAR_COMO] Archivo temporal eliminado")
                except Exception as e:
                    print(f"⚠️ [GUARDAR_COMO] No se pudo eliminar temporal: {e}")
                
                return jsonify({
                    "success": True,
                    "mensaje": f"✅ Archivo '{nuevo_nombre}' guardado en Google Drive correctamente."
                })
            else:
                print(f"❌ [GUARDAR_COMO] Error al subir a Drive")
                return jsonify({
                    "success": False,
                    "mensaje": "❌ Error al subir el archivo a Google Drive. Revise los logs."
                })
        else:
            # Modo local
            print(f"✅ [GUARDAR_COMO] Archivo guardado localmente en: {ruta_nueva}")
            return jsonify({
                "success": True,
                "mensaje": f"✅ Archivo '{nuevo_nombre}' guardado localmente."
            })
    
    except Exception as e:
        print(f"❌ [GUARDAR_COMO] Excepción: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "mensaje": f"❌ Error al guardar: {str(e)}"
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)