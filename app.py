import os
import io
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import boto3
from botocore.exceptions import ClientError

# Cargar variables de entorno desde archivo .env (solo en local)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Archivo .env cargado (desarrollo local)")
except ImportError:
    print("ℹ️ python-dotenv no instalado (modo producción)")

# === CONFIG (lee todo desde variables de entorno) ===
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "BanfiClaveSegura123")

# Detectar si estamos en LOCAL o PRODUCCIÓN
ES_LOCAL = os.path.exists('.env')  # Si existe .env, estamos en local
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')  # C:\MAppEAR\data

# Verificar configuración
MODO_R2 = all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_ENDPOINT]) and not ES_LOCAL

if ES_LOCAL:
    print("🖥️ MODO: LOCAL - usando carpeta C:\\MAppEAR\\data")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"📁 Carpeta creada: {DATA_DIR}")
    r2_client = None
elif MODO_R2:
    print("🌐 MODO: R2 (Cloudflare R2) - leyendo y guardando exclusivamente en R2")
    r2_client = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )
else:
    print("⚠️ R2 no está configurado completamente. El programa no funcionará sin R2.")
    r2_client = None

# === FLASK APP ===
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Usuarios
USERS = {
    "DSUBICI": {"password": "Banfi138", "rol": "admin"},
    "usuario1": {"password": "contraseña1", "rol": "user"},
    "usuario2": {"password": "contraseña2", "rol": "user"},
    "usuario3": {"password": "contraseña3", "rol": "user"},
    "usuario4": {"password": "contraseña4", "rol": "user"},
    "RIVADAVIA": {"password": "rivadavia5", "rol": "user"},
}

# === UTILIDADES LOCALES ===

def listar_archivos_local(usuario):
    """Lista archivos .xlsx en la carpeta data/usuario/"""
    usuario_dir = os.path.join(DATA_DIR, usuario)
    if not os.path.exists(usuario_dir):
        os.makedirs(usuario_dir)
        print(f"📁 Carpeta creada: {usuario_dir}")
        return []
    
    archivos = [f for f in os.listdir(usuario_dir) if f.lower().endswith('.xlsx')]
    archivos = sorted(archivos)
    print(f"📄 Archivos encontrados en {usuario_dir}: {archivos}")
    return archivos

def leer_archivo_local(usuario, nombre_archivo):
    """Lee un archivo local y devuelve un BytesIO"""
    ruta = os.path.join(DATA_DIR, usuario, nombre_archivo)
    if not os.path.exists(ruta):
        print(f"❌ Archivo no encontrado: {ruta}")
        return None
    
    try:
        with open(ruta, 'rb') as f:
            data = f.read()
        bio = io.BytesIO(data)
        print(f"✅ Leído {len(data)} bytes de {ruta}")
        return bio
    except Exception as e:
        print(f"❌ Error leyendo archivo local: {e}")
        return None

def guardar_archivo_local(usuario, nombre_archivo, bytes_data):
    """Guarda bytes en archivo local"""
    usuario_dir = os.path.join(DATA_DIR, usuario)
    if not os.path.exists(usuario_dir):
        os.makedirs(usuario_dir)
    
    ruta = os.path.join(usuario_dir, nombre_archivo)
    try:
        with open(ruta, 'wb') as f:
            f.write(bytes_data)
        print(f"✅ Guardado {len(bytes_data)} bytes en {ruta}")
        return True
    except Exception as e:
        print(f"❌ Error guardando archivo local: {e}")
        return False

# === UTILIDADES R2 ===

def listar_archivos_r2(usuario):
    """Lista archivos .xlsx dentro del prefijo usuario/ en R2."""
    if not MODO_R2:
        print("❌ R2 no configurado, no se pueden listar archivos")
        return []
    prefix = f"{usuario}/"
    try:
        resp = r2_client.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        archivos = []
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.lower().endswith(".xlsx"):
                nombre = key.split("/", 1)[1] if "/" in key else key
                if nombre:
                    archivos.append(nombre)
        archivos = sorted(archivos)
        print(f"📄 Archivos encontrados en R2/{usuario}: {archivos}")
        return archivos
    except ClientError as e:
        print(f"❌ Error listando en R2: {e}")
        return []
    except Exception as e:
        print(f"❌ Excepción listar_archivos_r2: {e}")
        return []

def descargar_de_r2_a_bytesio(usuario, nombre_archivo):
    """Descarga el archivo desde R2 y devuelve un BytesIO con el contenido."""
    if not MODO_R2:
        print("❌ R2 no configurado, no se puede descargar")
        return None
    key = f"{usuario}/{nombre_archivo}"
    try:
        print(f"📥 Descargando de R2: {key}")
        resp = r2_client.get_object(Bucket=R2_BUCKET, Key=key)
        data = resp["Body"].read()
        bio = io.BytesIO(data)
        print(f"✅ Descargado {len(data)} bytes de {key}")
        return bio
    except ClientError as e:
        print(f"❌ Error al descargar {key} de R2: {e}")
        return None
    except Exception as e:
        print(f"❌ Excepción descargar_de_r2_a_bytesio: {e}")
        return None

def subir_bytes_a_r2(usuario, nombre_archivo, bytes_data):
    """Sube el contenido (bytes) a R2 en la key usuario/nombre_archivo"""
    if not MODO_R2:
        print("❌ R2 no configurado, no se puede subir")
        return False
    key = f"{usuario}/{nombre_archivo}"
    try:
        print(f"📤 Subiendo a R2: {key} ({len(bytes_data)} bytes)")
        r2_client.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=bytes_data,
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        print(f"✅ Subido exitosamente a R2: {key}")
        return True
    except ClientError as e:
        print(f"❌ Error subiendo a R2 {key}: {e}")
        return False
    except Exception as e:
        print(f"❌ Excepción subir_bytes_a_r2: {e}")
        return False

# === FUNCIONES UNIFICADAS (detectan automáticamente LOCAL o R2) ===

def listar_archivos(usuario):
    """Lista archivos según el modo (LOCAL o R2)"""
    if ES_LOCAL:
        return listar_archivos_local(usuario)
    else:
        return listar_archivos_r2(usuario)

def leer_archivo(usuario, nombre_archivo):
    """Lee archivo según el modo (LOCAL o R2)"""
    if ES_LOCAL:
        return leer_archivo_local(usuario, nombre_archivo)
    else:
        return descargar_de_r2_a_bytesio(usuario, nombre_archivo)

def guardar_archivo(usuario, nombre_archivo, bytes_data):
    """Guarda archivo según el modo (LOCAL o R2)"""
    if ES_LOCAL:
        return guardar_archivo_local(usuario, nombre_archivo, bytes_data)
    else:
        return subir_bytes_a_r2(usuario, nombre_archivo, bytes_data)

# === Funciones de utilidad para colores ===

def procesar_color_con_transparencia(color_hex):
    """Procesa un color HEX y extrae el color base y la opacidad."""
    if not color_hex or not isinstance(color_hex, str):
        return {"color": "#CCCCCC", "opacity": 1.0}
    
    color_hex = str(color_hex).strip().upper()
    
    if not color_hex.startswith("#"):
        color_hex = "#" + color_hex
    
    hex_sin_hash = color_hex[1:]
    
    if len(hex_sin_hash) == 8:
        color_base = "#" + hex_sin_hash[:6]
        alpha_hex = hex_sin_hash[6:8]
        try:
            alpha_decimal = int(alpha_hex, 16) / 255.0
            opacity = round(alpha_decimal, 2)
        except ValueError:
            opacity = 1.0
        return {"color": color_base, "opacity": opacity}
    
    elif len(hex_sin_hash) == 6:
        return {"color": color_hex, "opacity": 1.0}
    
    elif len(hex_sin_hash) == 3:
        r, g, b = hex_sin_hash
        color_expandido = f"#{r}{r}{g}{g}{b}{b}"
        return {"color": color_expandido, "opacity": 1.0}
    
    else:
        print(f"⚠️ Formato de color inválido: {color_hex}, usando color por defecto")
        return {"color": "#CCCCCC", "opacity": 1.0}

# === Funciones de polígonos ===

def cargar_poligonos_desde_bytesio(bio):
    """Lee un pandas DataFrame desde un BytesIO y devuelve la estructura de polígonos."""
    try:
        df = pd.read_excel(bio, engine='openpyxl')
        print(f"📊 Excel leído: {len(df)} filas")
    except Exception as e:
        print(f"❌ Error leyendo Excel desde bytes: {e}")
        return []
    
    columnas = ["NOMBRE", "SUPERFICIE", "STATUS", "STATUS1", "STATUS2", "STATUS3", "PARTIDO", "COLOR HEX", "COORDENADAS"]
    for col in columnas:
        if col not in df.columns:
            df[col] = ""
    
    poligonos = []
    for idx, fila in df.iterrows():
        coords = []
        if pd.notna(fila["COORDENADAS"]) and fila["COORDENADAS"]:
            try:
                puntos = str(fila["COORDENADAS"]).split(" ")
                for p in puntos:
                    if "," in p:
                        lon, lat = map(float, p.split(","))
                        coords.append([lat, lon])
            except Exception as e:
                print(f"⚠️ Error parseando coordenadas en fila {idx}: {e}")
                coords = []
        
        color_original = str(fila["COLOR HEX"]) if pd.notna(fila["COLOR HEX"]) else "#CCCCCC"
        color_info = procesar_color_con_transparencia(color_original)
        
        poligonos.append({
            "name": str(fila["NOMBRE"]) if pd.notna(fila["NOMBRE"]) else "",
            "superficie": str(fila["SUPERFICIE"]) if pd.notna(fila["SUPERFICIE"]) else "",
            "status": str(fila["STATUS"]) if pd.notna(fila["STATUS"]) else "",
            "status1": str(fila["STATUS1"]) if pd.notna(fila["STATUS1"]) else "",
            "status2": str(fila["STATUS2"]) if pd.notna(fila["STATUS2"]) else "",
            "status3": str(fila["STATUS3"]) if pd.notna(fila["STATUS3"]) else "",
            "partido": str(fila["PARTIDO"]) if pd.notna(fila["PARTIDO"]) else "",
            "color": color_info["color"],
            "opacity": color_info["opacity"],
            "colorOriginal": color_original,
            "coords": coords,
            "COORDENADAS": str(fila["COORDENADAS"]) if pd.notna(fila["COORDENADAS"]) else ""
        })
    
    print(f"✅ Procesados {len(poligonos)} polígonos")
    return poligonos

def guardar_poligonos(nuevos_datos, usuario, nombre_archivo):
    """Crea un Excel en memoria desde nuevos_datos y lo guarda."""
    columnas = ["NOMBRE", "SUPERFICIE", "STATUS", "STATUS1", "STATUS2", "STATUS3", "PARTIDO", "COLOR HEX", "COORDENADAS"]
    
    df = pd.DataFrame([
        {
            "NOMBRE": d.get("name", ""),
            "SUPERFICIE": d.get("superficie", ""),
            "STATUS": d.get("status", ""),
            "STATUS1": d.get("status1", ""),
            "STATUS2": d.get("status2", ""),
            "STATUS3": d.get("status3", ""),
            "PARTIDO": d.get("partido", ""),
            "COLOR HEX": d.get("colorOriginal", d.get("color", "#CCCCCC")),
            "COORDENADAS": d.get("COORDENADAS", "")
        } for d in nuevos_datos
    ], columns=columnas)
    
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    bio.seek(0)
    
    return guardar_archivo(usuario, nombre_archivo, bio.read())

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
        print(f"✅ Login exitoso: {username}")
        return redirect(url_for("seleccionar_archivo"))
    print(f"❌ Login fallido: {username}")
    return render_template("login.html", error="Usuario o contraseña incorrectos.")

@app.route("/logout")
def logout():
    usuario = session.get("usuario", "Desconocido")
    session.clear()
    print(f"👋 Logout: {usuario}")
    return redirect("/")

@app.route("/inicio", methods=["GET"])
def seleccionar_archivo():
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    
    user = session["usuario"]
    archivos = listar_archivos(user)
    
    return render_template("seleccionar_archivo.html", 
                         archivos=archivos, 
                         usuario=user, 
                         rol=session.get("rol","user"))

@app.route("/abrir/<nombre>")
def abrir_archivo(nombre):
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    
    user = session["usuario"]
    bio = leer_archivo(user, nombre)
    
    if not bio:
        return f"❌ No se pudo obtener '{nombre}'.", 404
    
    poligonos = cargar_poligonos_desde_bytesio(bio)
    session["archivo_seleccionado"] = nombre
    
    return render_template("mapa.html", 
                         usuario=user, 
                         rol=session.get("rol","user"), 
                         poligonos=poligonos)

@app.route("/guardar", methods=["POST"])
def guardar():
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado."}), 401
    
    archivo_sel = session.get("archivo_seleccionado")
    if not archivo_sel:
        return jsonify({"success": False, "mensaje": "No hay archivo seleccionado."})
    
    try:
        data = request.get_json(force=True)
        user = session.get("usuario")
        
        exito = guardar_poligonos(data["datos"], user, archivo_sel)
        
        if exito:
            modo = "LOCAL" if ES_LOCAL else "R2"
            return jsonify({"success": True, "mensaje": f"✅ Cambios guardados correctamente en {modo}."})
        else:
            return jsonify({"success": False, "mensaje": "❌ Error al guardar."})
    except Exception as e:
        print(f"❌ Error en /guardar: {e}")
        return jsonify({"success": False, "mensaje": f"❌ Error: {e}"})

@app.route("/guardar_como", methods=["POST"])
def guardar_como():
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado."}), 401
    
    try:
        contenido = request.get_json(force=True)
        datos = contenido.get("datos", [])
        nuevo_nombre = contenido.get("nuevo_nombre", "").strip()
        
        if not nuevo_nombre:
            return jsonify({"success": False, "mensaje": "⚠️ No se indicó nombre."})
        
        if not nuevo_nombre.lower().endswith(".xlsx"):
            nuevo_nombre += ".xlsx"
        
        user = session.get("usuario")
        exito = guardar_poligonos(datos, user, nuevo_nombre)
        
        if exito:
            modo = "LOCAL" if ES_LOCAL else "R2"
            return jsonify({"success": True, "mensaje": f"✅ Archivo '{nuevo_nombre}' guardado en {modo}."})
        else:
            return jsonify({"success": False, "mensaje": "❌ Error al guardar archivo."})
    except Exception as e:
        print(f"❌ Error en /guardar_como: {e}")
        return jsonify({"success": False, "mensaje": f"❌ Error: {str(e)}"})

if __name__ == "__main__":
    if not ES_LOCAL and not MODO_R2:
        print("=" * 60)
        print("⚠️  ADVERTENCIA: Configuración incompleta")
        print("=" * 60)
    
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)