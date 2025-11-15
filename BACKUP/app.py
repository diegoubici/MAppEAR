import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import boto3
from io import BytesIO

# === CLOUDFLARE R2 CONFIGURATION ===
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")

# Detectar si estamos en modo Render (con R2) o Local
MODO_R2 = all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_ENDPOINT])

if MODO_R2:
    print("🌐 MODO: RENDER/R2 (usando Cloudflare R2)")
    r2_client = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )
    BASE_DIR = "/tmp"
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

# === FUNCIONES R2 ===
def listar_archivos_r2(usuario):
    """Lista archivos .xlsx del usuario en R2"""
    try:
        prefix = f"{usuario}/"
        response = r2_client.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        
        archivos = []
        if "Contents" in response:
            for obj in response["Contents"]:
                nombre = obj["Key"]
                if nombre.lower().endswith(".xlsx") and "/" in nombre:
                    archivos.append(nombre.split("/", 1)[1])  # Quitar prefijo usuario/
        
        print(f"📄 Archivos R2 encontrados para {usuario}: {archivos}")
        return sorted(archivos)
    except Exception as e:
        print(f"❌ Error listando archivos R2: {e}")
        return []


def descargar_de_r2(usuario, nombre_archivo):
    """Descarga archivo desde R2"""
    try:
        key = f"{usuario}/{nombre_archivo}"
        response = r2_client.get_object(Bucket=R2_BUCKET, Key=key)
        data = response["Body"].read()
        
        ruta_local = os.path.join(BASE_DIR, nombre_archivo)
        with open(ruta_local, "wb") as f:
            f.write(data)
        
        print(f"⬇️ Archivo '{nombre_archivo}' descargado de R2")
        return ruta_local
    except Exception as e:
        print(f"❌ Error descargando de R2: {e}")
        return None


def subir_a_r2(usuario, ruta_local):
    """Sube archivo a R2"""
    try:
        nombre_archivo = os.path.basename(ruta_local)
        key = f"{usuario}/{nombre_archivo}"
        
        with open(ruta_local, "rb") as f:
            r2_client.put_object(
                Bucket=R2_BUCKET,
                Key=key,
                Body=f.read(),
                ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        print(f"✅ Archivo '{nombre_archivo}' subido a R2")
        return True
    except Exception as e:
        print(f"❌ Error subiendo a R2: {e}")
        return False


# === FUNCIONES LOCALES ===
def listar_archivos_local(usuario):
    """Lista archivos en carpeta local"""
    try:
        user_dir = os.path.join(BASE_DIR, usuario)
        os.makedirs(user_dir, exist_ok=True)
        
        archivos = [f for f in os.listdir(user_dir) if f.lower().endswith(".xlsx")]
        print(f"📄 Archivos locales encontrados para {usuario}: {archivos}")
        return sorted(archivos)
    except Exception as e:
        print(f"❌ Error listando archivos locales: {e}")
        return []


def obtener_archivo_local(usuario, nombre_archivo):
    """Obtiene ruta de archivo local"""
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


# === FUNCIONES UNIFICADAS ===
def listar_archivos_r2(usuario):
    """Lista archivos .xlsx del usuario en R2"""
    try:
        if not all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_ENDPOINT]):
            print("⚠️ Configuración R2 incompleta, usando lista vacía")
            return []
        
        prefix = f"{usuario}/"
        print(f"🔍 Listando archivos R2 con prefix: {prefix}")
        
        response = r2_client.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        
        archivos = []
        if "Contents" in response:
            for obj in response["Contents"]:
                nombre = obj["Key"]
                # Solo archivos .xlsx, no carpetas vacías
                if nombre.lower().endswith(".xlsx") and "/" in nombre:
                    archivo_solo = nombre.split("/", 1)[1]  # Quitar prefijo usuario/
                    if archivo_solo:  # No agregar strings vacíos
                        archivos.append(archivo_solo)
        
        print(f"📄 Archivos R2 encontrados para {usuario}: {archivos}")
        return sorted(archivos)
    except Exception as e:
        print(f"❌ Error listando archivos R2: {e}")
        import traceback
        print(traceback.format_exc())
        return []  # Retornar lista vacía en caso de error


def obtener_archivo(usuario, nombre_archivo):
    """Obtiene archivo (R2 o local según modo)"""
    if MODO_R2:
        return descargar_de_r2(usuario, nombre_archivo)
    else:
        return obtener_archivo_local(usuario, nombre_archivo)


def guardar_archivo(usuario, ruta_local):
    """Guarda archivo (R2 o local según modo)"""
    if MODO_R2:
        return subir_a_r2(usuario, ruta_local)
    else:
        print(f"✅ Archivo guardado localmente: {ruta_local}")
        return True

def listar_archivos(usuario):
    """Lista archivos según el modo (R2 o local)"""
    if MODO_R2:
        return listar_archivos_r2(usuario)
    else:
        return listar_archivos_local(usuario)


# === FUNCIONES DE POLÍGONOS ===
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
    
    try:
        archivos = listar_archivos(user)
        print(f"✅ Listado exitoso para {user}: {len(archivos)} archivos")
    except Exception as e:
        print(f"❌ Error al listar archivos para {user}: {e}")
        import traceback
        print(traceback.format_exc())
        archivos = []
    
    return render_template(
        "seleccionar_archivo.html", 
        archivos=archivos, 
        usuario=user, 
        rol=session.get("rol", "user")
    )

@app.route("/abrir/<nombre>")
def abrir_archivo(nombre):
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    user = session["usuario"]
    ruta_local = obtener_archivo(user, nombre)
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
        
        if MODO_R2:
            ruta = os.path.join(BASE_DIR, archivo_sel)
        else:
            user_dir = os.path.join(BASE_DIR, user)
            os.makedirs(user_dir, exist_ok=True)
            ruta = os.path.join(user_dir, archivo_sel)
        
        guardar_poligonos(data["datos"], ruta)
        guardar_archivo(user, ruta)
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
            return jsonify({"success": False, "mensaje": "⚠️ No se indicó nombre."})
        
        if not nuevo_nombre.lower().endswith(".xlsx"):
            nuevo_nombre += ".xlsx"
        
        user = session.get("usuario")
        
        if MODO_R2:
            ruta_nueva = os.path.join(BASE_DIR, nuevo_nombre)
        else:
            user_dir = os.path.join(BASE_DIR, user)
            os.makedirs(user_dir, exist_ok=True)
            ruta_nueva = os.path.join(user_dir, nuevo_nombre)
        
        guardar_poligonos(datos, ruta_nueva)
        exito = guardar_archivo(user, ruta_nueva)
        
        if exito:
            if MODO_R2:
                try:
                    os.remove(ruta_nueva)
                except:
                    pass
            return jsonify({"success": True, "mensaje": f"✅ Archivo '{nuevo_nombre}' guardado correctamente."})
        else:
            return jsonify({"success": False, "mensaje": "❌ Error al guardar archivo."})
    
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"❌ Error: {str(e)}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)