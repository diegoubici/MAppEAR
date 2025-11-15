
import os
import io
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import boto3
from botocore.exceptions import ClientError

# === CONFIG (lee todo desde variables de entorno) ===
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "BanfiClaveSegura123")

# Verificar configuración mínima
MODO_R2 = all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_ENDPOINT])

if MODO_R2:
    print("🌐 MODO: R2 (Cloudflare R2) - leyendo y guardando exclusivamente en R2")
    # crear cliente S3 compatible (Cloudflare R2)
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
            # ignorar "carpetas" (keys que terminan en '/')
            if key.lower().endswith(".xlsx"):
                # sacar prefijo usuario/
                nombre = key.split("/", 1)[1] if "/" in key else key
                if nombre:  # solo agregar si no está vacío
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

# === Funciones de polígonos - TODO en memoria, nunca en disco local ===

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
        
        poligonos.append({
            "name": str(fila["NOMBRE"]) if pd.notna(fila["NOMBRE"]) else "",
            "superficie": str(fila["SUPERFICIE"]) if pd.notna(fila["SUPERFICIE"]) else "",
            "status": str(fila["STATUS"]) if pd.notna(fila["STATUS"]) else "",
            "status1": str(fila["STATUS1"]) if pd.notna(fila["STATUS1"]) else "",
            "status2": str(fila["STATUS2"]) if pd.notna(fila["STATUS2"]) else "",
            "status3": str(fila["STATUS3"]) if pd.notna(fila["STATUS3"]) else "",
            "partido": str(fila["PARTIDO"]) if pd.notna(fila["PARTIDO"]) else "",
            "color": str(fila["COLOR HEX"]) if pd.notna(fila["COLOR HEX"]) else "#CCCCCC",
            "coords": coords,
            "COORDENADAS": str(fila["COORDENADAS"]) if pd.notna(fila["COORDENADAS"]) else ""
        })
    
    print(f"✅ Procesados {len(poligonos)} polígonos")
    return poligonos

def guardar_poligonos_en_r2(nuevos_datos, usuario, nombre_archivo):
    """Crea un Excel en memoria desde nuevos_datos y lo sube a R2 en usuario/nombre_archivo.
    TODO el proceso se hace en memoria, NUNCA se escribe en disco local."""
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
            "COLOR HEX": d.get("color", "#CCCCCC"),
            "COORDENADAS": d.get("COORDENADAS", "")
        } for d in nuevos_datos
    ], columns=columnas)
    
    # Crear Excel en memoria
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    bio.seek(0)
    
    # Subir directamente a R2
    return subir_bytes_a_r2(usuario, nombre_archivo, bio.read())

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
    
    if not MODO_R2:
        return "⚠️ R2 no está configurado. Configure las variables de entorno.", 500
    
    # Listar archivos del usuario en R2
    archivos = listar_archivos_r2(user)
    return render_template("seleccionar_archivo.html", 
                         archivos=archivos, 
                         usuario=user, 
                         rol=session.get("rol","user"))

@app.route("/abrir/<nombre>")
def abrir_archivo(nombre):
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    
    user = session["usuario"]
    
    if not MODO_R2:
        return "⚠️ R2 no está configurado.", 500
    
    # Descargar archivo de R2 a memoria
    bio = descargar_de_r2_a_bytesio(user, nombre)
    if not bio:
        return f"❌ No se pudo obtener '{nombre}' de R2.", 404
    
    # Procesar polígonos desde memoria
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
    
    if not MODO_R2:
        return jsonify({"success": False, "mensaje": "R2 no configurado."}), 500
    
    try:
        data = request.get_json(force=True)
        user = session.get("usuario")
        
        # Guardar directamente a R2, todo en memoria
        exito = guardar_poligonos_en_r2(data["datos"], user, archivo_sel)
        
        if exito:
            return jsonify({"success": True, "mensaje": "✅ Cambios guardados correctamente en R2."})
        else:
            return jsonify({"success": False, "mensaje": "❌ Error al guardar en R2."})
    except Exception as e:
        print(f"❌ Error en /guardar: {e}")
        return jsonify({"success": False, "mensaje": f"❌ Error: {e}"})

@app.route("/guardar_como", methods=["POST"])
def guardar_como():
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado."}), 401
    
    if not MODO_R2:
        return jsonify({"success": False, "mensaje": "R2 no configurado."}), 500
    
    try:
        contenido = request.get_json(force=True)
        datos = contenido.get("datos", [])
        nuevo_nombre = contenido.get("nuevo_nombre", "").strip()
        
        if not nuevo_nombre:
            return jsonify({"success": False, "mensaje": "⚠️ No se indicó nombre."})
        
        if not nuevo_nombre.lower().endswith(".xlsx"):
            nuevo_nombre += ".xlsx"
        
        user = session.get("usuario")
        
        # Guardar directamente a R2, todo en memoria
        exito = guardar_poligonos_en_r2(datos, user, nuevo_nombre)
        
        if exito:
            return jsonify({"success": True, "mensaje": f"✅ Archivo '{nuevo_nombre}' guardado en R2."})
        else:
            return jsonify({"success": False, "mensaje": "❌ Error al guardar archivo en R2."})
    except Exception as e:
        print(f"❌ Error en /guardar_como: {e}")
        return jsonify({"success": False, "mensaje": f"❌ Error: {str(e)}"})

if __name__ == "__main__":
    if not MODO_R2:
        print("=" * 60)
        print("⚠️  ADVERTENCIA: R2 NO ESTÁ CONFIGURADO")
        print("=" * 60)
        print("Configure las siguientes variables de entorno:")
        print("  - R2_ACCESS_KEY")
        print("  - R2_SECRET_KEY")
        print("  - R2_BUCKET")
        print("  - R2_ENDPOINT")
        print("=" * 60)
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
