import os
import io
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import boto3
from botocore.exceptions import ClientError
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

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
    "RIVADAVIA": {"password": "rivadavia", "rol": "admin"},
    "usuario1": {"password": "contraseña1", "rol": "user"},
    "usuario2": {"password": "contraseña2", "rol": "user"},
    "usuario3": {"password": "contraseña3", "rol": "user"},
    "FENOCCHIO": {"password": "fenocchio", "rol": "user"},
    "usuario5": {"password": "contraseña5", "rol": "user"},
    "usuario6": {"password": "contraseña6", "rol": "user"},
    "usuario7": {"password": "contraseña7", "rol": "user"},
    "PELAYO": {"password": "pelayo", "rol": "user"},
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
    
    # Manejar caso especial: "TRANSPARENT"
    if color_hex == "TRANSPARENT":
        return {"color": "transparent", "opacity": 0.0}
    
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
    columnas = ["NOMBRE", "SUPERFICIE", "STATUS", "STATUS1", "STATUS2", "STATUS3", "PARTIDO", "COLOR HEX", "OPACIDAD", "COORDENADAS"]
    
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
            "OPACIDAD": d.get("opacidad", 0.6),
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
        # IR DIRECTO AL MAPA (no a seleccionar archivo)
        return redirect(url_for("mapa_vacio"))
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

@app.route("/mapa", methods=["GET"])
def mapa_vacio():
    """Cargar mapa vacío, los archivos se cargan desde el panel"""
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    
    user = session["usuario"]
    rol = session.get("rol", "user")
    
    # Mapa sin polígonos iniciales (lista vacía)
    poligonos_vacios = []
    
    print(f"🗺️ Cargando mapa vacío para: {user}")
    
    return render_template("mapa.html",
                         poligonos=poligonos_vacios,
                         usuario=user,
                         rol=rol,
                         nombre_archivo="")

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
    
    # Extraer nombre sin extensión para mostrar en el header
    nombre_sin_extension = os.path.splitext(nombre)[0]
    
    return render_template("mapa.html", 
                         usuario=user, 
                         rol=session.get("rol","user"), 
                         poligonos=poligonos,
                         archivo_nombre=nombre_sin_extension)

@app.route("/descargar/<nombre>")
def descargar_archivo(nombre):
    """Descarga un archivo Excel desde R2 o local"""
    if "usuario" not in session:
        return redirect(url_for("login_page"))
    
    user = session["usuario"]
    
    try:
        print(f"📥 Descargando archivo: {nombre} para usuario: {user}")
        
        # Leer el archivo
        bio = leer_archivo(user, nombre)
        
        if not bio:
            print(f"❌ Archivo no encontrado: {nombre}")
            return f"❌ No se pudo obtener '{nombre}'.", 404
        
        # Preparar para descarga
        from flask import send_file
        bio.seek(0)  # Volver al inicio del archivo
        
        print(f"✅ Enviando archivo para descarga: {nombre}")
        
        return send_file(
            bio,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nombre
        )
        
    except Exception as e:
        print(f"❌ Error descargando archivo: {e}")
        import traceback
        traceback.print_exc()
        return f"Error al descargar: {str(e)}", 500

@app.route("/guardar", methods=["POST"])
def guardar():
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado.", "tipo": "error"}), 401
    
    archivo_sel = session.get("archivo_seleccionado")
    if not archivo_sel:
        return jsonify({"success": False, "mensaje": "No hay archivo seleccionado.", "tipo": "error"})
    
    try:
        data = request.get_json(force=True)
        user = session.get("usuario")
        
        exito = guardar_poligonos(data["datos"], user, archivo_sel)
        
        if exito:
            if ES_LOCAL:
                return jsonify({
                    "success": True, 
                    "mensaje": "GRABACIÓN EXITOSA LOCALMENTE",
                    "detalle": "Archivo guardado en su computadora",
                    "tipo": "success"
                })
            else:
                return jsonify({
                    "success": True, 
                    "mensaje": "GRABACIÓN EXITOSA EN R2",
                    "detalle": "Archivo sincronizado en la nube",
                    "tipo": "success"
                })
        else:
            return jsonify({
                "success": False, 
                "mensaje": "Error al guardar",
                "detalle": "No se pudo completar la operación",
                "tipo": "error"
            })
    except Exception as e:
        print(f"❌ Error en /guardar: {e}")
        return jsonify({
            "success": False, 
            "mensaje": "Error al guardar",
            "detalle": str(e),
            "tipo": "error"
        })

@app.route("/guardar_como", methods=["POST"])
def guardar_como():
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado.", "tipo": "error"}), 401
    
    try:
        contenido = request.get_json(force=True)
        datos = contenido.get("datos", [])
        nuevo_nombre = contenido.get("nuevo_nombre", "").strip()
        
        if not nuevo_nombre:
            return jsonify({
                "success": False, 
                "mensaje": "Nombre de archivo requerido",
                "tipo": "warning"
            })
        
        if not nuevo_nombre.lower().endswith(".xlsx"):
            nuevo_nombre += ".xlsx"
        
        user = session.get("usuario")
        exito = guardar_poligonos(datos, user, nuevo_nombre)
        
        if exito:
            if ES_LOCAL:
                return jsonify({
                    "success": True, 
                    "mensaje": "GRABACIÓN EXITOSA LOCALMENTE",
                    "detalle": f"Archivo '{nuevo_nombre}' guardado",
                    "tipo": "success"
                })
            else:
                return jsonify({
                    "success": True, 
                    "mensaje": "GRABACIÓN EXITOSA EN R2",
                    "detalle": f"Archivo '{nuevo_nombre}' sincronizado",
                    "tipo": "success"
                })
        else:
            return jsonify({
                "success": False, 
                "mensaje": "Error al guardar archivo",
                "tipo": "error"
            })
    except Exception as e:
        print(f"❌ Error en /guardar_como: {e}")
        return jsonify({
            "success": False, 
            "mensaje": "Error al guardar",
            "detalle": str(e),
            "tipo": "error"
        })

# === NUEVAS RUTAS PARA MÚLTIPLES ARCHIVOS ===

@app.route("/cargar_archivo_adicional", methods=["POST"])
def cargar_archivo_adicional():
    """
    Carga un archivo adicional sin reemplazar los que ya están cargados.
    Retorna los polígonos del nuevo archivo con identificador único.
    """
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado"}), 401
    
    usuario = session["usuario"]
    
    if "archivo" not in request.files:
        return jsonify({"success": False, "mensaje": "No se envió archivo"}), 400
    
    file = request.files["archivo"]
    
    if file.filename == "":
        return jsonify({"success": False, "mensaje": "Archivo vacío"}), 400
    
    if not file.filename.lower().endswith('.xlsx'):
        return jsonify({"success": False, "mensaje": "Solo archivos .xlsx permitidos"}), 400
    
    try:
        # Leer Excel
        df = pd.read_excel(file)
        
        # Procesar polígonos
        poligonos = []
        
        for idx, row in df.iterrows():
            # Convertir row a dict
            data_dict = row.to_dict()
            
            # Crear estructura de polígono
            poligono = {
                "STATUS": [],
                "geometry": None,
                "color": data_dict.get("color", "#CCCCCC"),
                "opacity": float(data_dict.get("opacity", 0.3)) if pd.notna(data_dict.get("opacity")) else 0.3,
                "archivo_origen": file.filename,
                "indice_original": idx
            }
            
            # Convertir todas las columnas a STATUS
            for col, val in data_dict.items():
                if col.upper() == "COORDENADAS":
                    # Coordenadas van en geometry
                    if pd.notna(val) and str(val).strip():
                        poligono["geometry"] = str(val).strip()
                elif col.lower() not in ["color", "opacity"]:
                    # Resto va en STATUS
                    if pd.notna(val):
                        poligono["STATUS"].append([col, str(val)])
                    else:
                        poligono["STATUS"].append([col, ""])
            
            poligonos.append(poligono)
        
        return jsonify({
            "success": True,
            "archivo": file.filename,
            "poligonos": poligonos,
            "total": len(poligonos)
        })
        
    except Exception as e:
        print(f"❌ Error cargando archivo adicional: {e}")
        return jsonify({
            "success": False,
            "mensaje": f"Error al procesar archivo: {str(e)}"
        }), 500


@app.route("/guardar_archivo_especifico", methods=["POST"])
def guardar_archivo_especifico():
    """
    Guarda cambios en un archivo específico usando formato original.
    """
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado"}), 401
    
    usuario = session["usuario"]
    data = request.get_json()
    
    nombre_archivo = data.get("nombre_archivo")
    datos = data.get("datos", [])
    
    if not nombre_archivo:
        return jsonify({"success": False, "mensaje": "Nombre de archivo requerido"}), 400
    
    if not datos:
        return jsonify({"success": False, "mensaje": "Sin datos para guardar"}), 400
    
    try:
        # Usar función guardar_poligonos original
        exito = guardar_poligonos(datos, usuario, nombre_archivo)
        
        if exito:
            return jsonify({
                "success": True,
                "mensaje": f"✅ Archivo {nombre_archivo} guardado correctamente",
                "archivo": nombre_archivo
            })
        else:
            return jsonify({
                "success": False,
                "mensaje": "Error al guardar archivo"
            }), 500
            
    except Exception as e:
        print(f"❌ Error en guardar_archivo_especifico: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "mensaje": f"Error: {str(e)}"
        }), 500


@app.route("/listar_archivos_disponibles", methods=["GET"])
def listar_archivos_disponibles():
    """
    Lista todos los archivos .xlsx disponibles en la carpeta del usuario
    """
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado"}), 401
    
    usuario = session["usuario"]
    
    try:
        if ES_LOCAL:
            archivos = listar_archivos_local(usuario)
        else:
            archivos = listar_archivos_r2(usuario)
        
        return jsonify({
            "success": True,
            "archivos": archivos,
            "total": len(archivos)
        })
        
    except Exception as e:
        print(f"❌ Error listando archivos: {e}")
        return jsonify({
            "success": False,
            "mensaje": f"Error: {str(e)}"
        }), 500


@app.route("/cargar_archivo_desde_carpeta", methods=["POST"])
def cargar_archivo_desde_carpeta():
    """
    Carga un archivo específico de la carpeta del usuario
    """
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado"}), 401
    
    usuario = session["usuario"]
    nombre_archivo = request.form.get('nombre_archivo')
    
    if not nombre_archivo:
        return jsonify({"success": False, "mensaje": "Nombre de archivo requerido"}), 400
    
    try:
        # Leer archivo
        if ES_LOCAL:
            bio = leer_archivo_local(usuario, nombre_archivo)
        else:
            bio = descargar_de_r2_a_bytesio(usuario, nombre_archivo)
        
        if not bio:
            return jsonify({"success": False, "mensaje": "Archivo no encontrado"}), 404
        
        # Procesar Excel
        df = pd.read_excel(bio)
        poligonos = []
        
        print(f"📊 Columnas del archivo: {df.columns.tolist()}")
        
        for idx, row in df.iterrows():
            data_dict = row.to_dict()
            
            # Buscar color en múltiples columnas posibles
            color_hex = "#CCCCCC"  # Default
            for col_name in ["COLOR HEX", "color", "Color", "COLOR"]:
                if col_name in data_dict and pd.notna(data_dict[col_name]):
                    color_hex = str(data_dict[col_name]).strip()
                    # NO agregar # si es "transparent"
                    if color_hex.lower() != 'transparent' and not color_hex.startswith('#'):
                        color_hex = '#' + color_hex
                    break
            
            # Procesar color con transparencia
            color_info = procesar_color_con_transparencia(color_hex)
            
            poligono = {
                "STATUS": [],
                "geometry": None,
                "color": color_info["color"],
                "opacity": color_info["opacity"],
                "archivo_origen": nombre_archivo,
                "indice_original": idx
            }
            
            # Procesar todas las columnas
            for col, val in data_dict.items():
                if col.upper() == "COORDENADAS":
                    if pd.notna(val) and str(val).strip():
                        poligono["geometry"] = str(val).strip()
                else:
                    # IMPORTANTE: Incluir TODOS los campos en STATUS (incluyendo color y opacity)
                    if pd.notna(val):
                        poligono["STATUS"].append([col, str(val)])
                    else:
                        poligono["STATUS"].append([col, ""])
            
            poligonos.append(poligono)
        
        print(f"✅ Procesados {len(poligonos)} polígonos")
        if len(poligonos) > 0:
            print(f"📊 Primer polígono - Color: {poligonos[0]['color']}, STATUS: {poligonos[0]['STATUS'][:3]}")
        
        return jsonify({
            "success": True,
            "archivo": nombre_archivo,
            "poligonos": poligonos,
            "total": len(poligonos)
        })
        
    except Exception as e:
        print(f"❌ Error cargando archivo desde carpeta: {e}")
        return jsonify({
            "success": False,
            "mensaje": f"Error al cargar archivo: {str(e)}"
        }), 500


# === FIN NUEVAS RUTAS ===

@app.route("/combinar_poligonos", methods=["POST"])
def combinar_poligonos():
    """Combina polígonos seleccionados en uno solo (solo para DSUBICI)"""
    if "usuario" not in session:
        return jsonify({"success": False, "mensaje": "No autenticado.", "tipo": "error"}), 401
    
    if session["usuario"] != "DSUBICI":
        return jsonify({"success": False, "mensaje": "Permiso denegado.", "tipo": "error"}), 403
    
    archivo_sel = session.get("archivo_seleccionado")
    if not archivo_sel:
        return jsonify({"success": False, "mensaje": "No hay archivo seleccionado.", "tipo": "error"})
    
    try:
        data = request.get_json(force=True)
        indices = data.get("indices", [])
        nombre_nuevo = data.get("nombre", "").strip()
        color_nuevo = data.get("color", "#CCCCCC").strip()
        todos_datos = data.get("datos", [])
        
        print(f"📥 Recibidos {len(indices)} índices para combinar: {indices}")
        print(f"📊 Total de datos: {len(todos_datos)}")
        
        if len(indices) < 2:
            return jsonify({
                "success": False,
                "mensaje": "Debe seleccionar al menos 2 polígonos",
                "tipo": "warning"
            })
        
        if not nombre_nuevo:
            return jsonify({
                "success": False,
                "mensaje": "Debe ingresar un nombre para el polígono combinado",
                "tipo": "warning"
            })
        
        # Extraer los polígonos seleccionados
        poligonos_a_combinar = []
        indices_con_coordenadas = []  # NUEVO: Guardar qué índices tienen coordenadas válidas
        superficie_total = 0.0
        
        for idx in indices:
            if idx < len(todos_datos):
                pol_data = todos_datos[idx]
                coords_str = pol_data.get("COORDENADAS", "")
                
                print(f"  Polígono {idx}: {pol_data.get('name', 'Sin nombre')}, coords: {len(coords_str)} chars")
                
                if coords_str and coords_str.strip():
                    # Parsear coordenadas
                    coords = []
                    puntos = coords_str.strip().split()
                    for p in puntos:
                        if "," in p:
                            try:
                                lon, lat = map(float, p.split(","))
                                coords.append((lon, lat))
                            except Exception as e:
                                print(f"    ⚠️ Error parseando punto {p}: {e}")
                    
                    if len(coords) >= 3:
                        poligonos_a_combinar.append(Polygon(coords))
                        indices_con_coordenadas.append(idx)  # NUEVO: Marcar este índice como válido
                        print(f"    ✅ Polígono válido con {len(coords)} puntos")
                        
                        # Sumar superficie
                        try:
                            sup_str = pol_data.get("superficie", "0")
                            sup = float(sup_str) if sup_str else 0.0
                            superficie_total += sup
                            print(f"    📐 Superficie: {sup} has")
                        except Exception as e:
                            print(f"    ⚠️ Error parseando superficie: {e}")
                else:
                    print(f"    ⚠️ Sin coordenadas válidas - será preservado sin combinar")
        
        print(f"📊 Resumen: {len(indices)} seleccionados, {len(indices_con_coordenadas)} con coordenadas válidas")
        
        if len(poligonos_a_combinar) < 2:
            return jsonify({
                "success": False,
                "mensaje": "Los polígonos seleccionados no tienen coordenadas válidas",
                "tipo": "error"
            })
        
        # Unir polígonos usando shapely
        print(f"🔄 Combinando {len(poligonos_a_combinar)} polígonos...")
        merged = unary_union(poligonos_a_combinar)
        
        # Convertir el resultado a coordenadas
        nuevos_poligonos = []  # Lista para almacenar TODOS los polígonos resultantes
        
        if isinstance(merged, Polygon):
            # Es un polígono simple - todos se tocan
            print(f"✅ Resultado: Polígono simple (todos los polígonos se tocan)")
            coords_combinadas = []
            for lon, lat in merged.exterior.coords:
                coords_combinadas.append(f"{lon},{lat}")
            
            coords_str = " ".join(coords_combinadas)
            
            nuevo_poligono = {
                "name": nombre_nuevo,
                "superficie": str(round(superficie_total, 2)),
                "status": "",
                "status1": "",
                "status2": "",
                "status3": "",
                "partido": "",
                "color": color_nuevo,
                "colorOriginal": color_nuevo,
                "COORDENADAS": coords_str
            }
            nuevos_poligonos.append(nuevo_poligono)
            print(f"✅ Creado 1 polígono combinado con {len(coords_combinadas)} puntos")
                
        elif isinstance(merged, MultiPolygon):
            # Son múltiples polígonos - NO todos se tocan
            print(f"⚠️ ATENCIÓN: Los polígonos seleccionados NO se tocan todos entre sí")
            print(f"   Se detectaron {len(merged.geoms)} grupos separados")
            
            # CREAR UN POLÍGONO POR CADA GRUPO QUE SE TOCA
            for i, geom in enumerate(merged.geoms):
                coords_combinadas = []
                for lon, lat in geom.exterior.coords:
                    coords_combinadas.append(f"{lon},{lat}")
                
                coords_str = " ".join(coords_combinadas)
                
                # Nombre diferente para cada grupo
                if len(merged.geoms) > 1:
                    nombre_parte = f"{nombre_nuevo} - PARTE {i+1}"
                else:
                    nombre_parte = nombre_nuevo
                
                # Calcular superficie proporcional (aproximada)
                area_relativa = geom.area / merged.area
                superficie_parte = superficie_total * area_relativa
                
                nuevo_pol = {
                    "name": nombre_parte,
                    "superficie": str(round(superficie_parte, 2)),
                    "status": "",
                    "status1": "",
                    "status2": "",
                    "status3": "",
                    "partido": "",
                    "color": color_nuevo,
                    "colorOriginal": color_nuevo,
                    "COORDENADAS": coords_str
                }
                nuevos_poligonos.append(nuevo_pol)
                print(f"   ✅ Creado: {nombre_parte} ({len(coords_combinadas)} puntos, {superficie_parte:.2f} has)")
            
            print(f"⚠️ Se crearon {len(merged.geoms)} polígonos separados en lugar de 1")
        
        print(f"✅ Total de polígonos resultantes: {len(nuevos_poligonos)}")
        
        # CAMBIO CRÍTICO: Crear nueva lista eliminando SOLO los que se combinaron
        indices_a_eliminar = set(indices_con_coordenadas)  # Solo eliminar los que tienen coordenadas válidas
        nuevos_datos = []
        
        # Preservar todos los polígonos que NO fueron procesados
        for i, pol in enumerate(todos_datos):
            if i not in indices_a_eliminar:
                nuevos_datos.append(pol)
                if i in indices:
                    print(f"   ⚠️ Preservando polígono {i} (sin coordenadas válidas): {pol.get('name', 'Sin nombre')}")
        
        # Agregar TODOS los nuevos polígonos al final
        nuevos_datos.extend(nuevos_poligonos)
        
        print(f"✅ Polígonos procesados y eliminados: {len(indices_con_coordenadas)}")
        print(f"✅ Polígonos preservados (sin procesar): {len(indices) - len(indices_con_coordenadas)}")
        print(f"✅ Polígonos nuevos creados: {len(nuevos_poligonos)}")
        print(f"📊 Superficie total combinada: {superficie_total} has")
        print(f"📄 Total final de polígonos: {len(nuevos_datos)}")
        
        # VERIFICACIÓN: Mostrar nombres de los primeros 5 polígonos
        print(f"\n📋 Verificación de datos finales (primeros 5):")
        for i, pol in enumerate(nuevos_datos[:5]):
            print(f"  [{i}] {pol.get('name', 'Sin nombre')} - {pol.get('superficie', '0')} has - Color: {pol.get('color', 'N/A')}")
        if len(nuevos_datos) > 5:
            print(f"  ... y {len(nuevos_datos) - 5} más")
        
        # NO GUARDAR AUTOMÁTICAMENTE - Solo devolver los datos actualizados
        print(f"\n⚠️ IMPORTANTE: Los cambios NO se guardan automáticamente")
        print(f"   El usuario debe hacer clic en GUARDAR para persistir los cambios")
        
        # Mensaje personalizado según el resultado
        if len(nuevos_poligonos) == 1:
            detalle_msg = f"{len(indices)} polígonos combinados en '{nombre_nuevo}'. ¡Recuerda GUARDAR los cambios!"
        else:
            detalle_msg = f"Se crearon {len(nuevos_poligonos)} polígonos separados. ¡Recuerda GUARDAR los cambios!"
        
        return jsonify({
            "success": True,
            "mensaje": "Polígonos combinados exitosamente",
            "detalle": detalle_msg,
            "tipo": "success" if len(nuevos_poligonos) == 1 else "warning",
            "nuevos_datos": nuevos_datos,  # TODOS los polígonos actualizados
            "indices_eliminados": list(indices_con_coordenadas),
            "nuevos_poligonos": nuevos_poligonos,
            "estadisticas": {
                "total_antes": len(todos_datos),
                "total_despues": len(nuevos_datos),
                "eliminados": len(indices_con_coordenadas),
                "creados": len(nuevos_poligonos)
            }
        })
        
    except Exception as e:
        print(f"❌ Error combinando polígonos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "mensaje": "Error al combinar polígonos",
            "detalle": str(e),
            "tipo": "error"
        })
    
@app.route("/test_r2")
def test_r2():
    resultado = []
    resultado.append(f"ES_LOCAL: {ES_LOCAL}")
    resultado.append(f"MODO_R2: {MODO_R2}")
    resultado.append(f"R2_BUCKET: {R2_BUCKET}")
    resultado.append(f"R2_ENDPOINT: {R2_ENDPOINT[:50]}..." if R2_ENDPOINT else "None")
    resultado.append(f"R2_ACCESS_KEY existe: {bool(R2_ACCESS_KEY)}")
    resultado.append(f"R2_SECRET_KEY existe: {bool(R2_SECRET_KEY)}")
    
    if not MODO_R2:
        resultado.append("<br><strong>❌ No está en modo R2</strong>")
        return "<br>".join(resultado)
    
    try:
        resultado.append("<br><strong>Intentando conectar a R2...</strong>")
        resp = r2_client.list_objects_v2(Bucket=R2_BUCKET, MaxKeys=50)
        archivos = [obj["Key"] for obj in resp.get("Contents", [])]
        resultado.append(f"<br>✅ Conexión exitosa - Archivos encontrados: {len(archivos)}")
        
        if archivos:
            resultado.append("<br><strong>Archivos en R2:</strong>")
            for arch in archivos[:20]:
                resultado.append(f"  • {arch}")
            if len(archivos) > 20:
                resultado.append(f"  ... y {len(archivos) - 20} más")
        else:
            resultado.append("<br>⚠️ No hay archivos en el bucket")
            
    except Exception as e:
        resultado.append(f"<br><strong>❌ Error conectando a R2:</strong><br>{str(e)}")
    
    return "<br>".join(resultado)

if __name__ == "__main__":
    if not ES_LOCAL and not MODO_R2:
        print("=" * 60)
        print("⚠️  ADVERTENCIA: Configuración incompleta")
        print("=" * 60)
    
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
