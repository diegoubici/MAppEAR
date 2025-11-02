import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "BanfiClaveSegura123"

# === CONFIGURACIÓN: base de datos / carpetas ===
# Si existe la ruta local F:\MAPPEAR\data se usa (desarrollo local).
# Si no existe, se usa una carpeta "data" dentro del proyecto (entorno remoto, p.e. Render).
if os.path.exists(r"F:\MAPPEAR\data"):
    BASE_DIR = r"F:\MAPPEAR\data"
else:
    BASE_DIR = os.path.join(os.getcwd(), "data")

os.makedirs(BASE_DIR, exist_ok=True)


def get_user_dir(username):
    """Devuelve la carpeta específica del usuario dentro de BASE_DIR (la crea si no existe)."""
    if not username:
        return None
    user_dir = os.path.join(BASE_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


# Usuarios y roles
USERS = {
    "DSUBICI": {"password": "Banfi138", "rol": "admin"},
    "usuario1": {"password": "contraseña1", "rol": "user"},
    "usuario2": {"password": "contraseña2", "rol": "user"},
    "usuario3": {"password": "contraseña3", "rol": "user"},
    "usuario4": {"password": "contraseña4", "rol": "user"},
    "RIVADAVIA": {"password": "rivadavia5", "rol": "user"},
}


# === FUNCIONES AUXILIARES ===
def obtener_archivos(user_dir):
    """Lista archivos .xlsx en la carpeta del usuario (user_dir)."""
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
        if i < len(df):
            df.at[i, "NOMBRE"] = dato.get("name", "")
            df.at[i, "SUPERFICIE"] = dato.get("superficie", "")
            df.at[i, "STATUS"] = dato.get("status", "")
            df.at[i, "STATUS1"] = dato.get("status1", "")
            df.at[i, "STATUS2"] = dato.get("status2", "")
            df.at[i, "STATUS3"] = dato.get("status3", "")
            df.at[i, "PARTIDO"] = dato.get("partido", "")
            df.at[i, "COLOR HEX"] = dato.get("color", "")
            df.at[i, "COORDENADAS"] = dato.get("COORDENADAS", "")
        else:
            df.loc[i] = [
                dato.get("name", ""),
                dato.get("superficie", ""),
                dato.get("status", ""),
                dato.get("status1", ""),
                dato.get("status2", ""),
                dato.get("status3", ""),
                dato.get("partido", ""),
                dato.get("color", ""),
                dato.get("COORDENADAS", "")
            ]

    df.to_excel(ruta_destino, index=False)


# === LOGIN ===
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
        # Al loguearse vamos directamente a la pantalla de selección de archivos
        return redirect(url_for("seleccionar_archivo"))
    else:
        return render_template("login.html", error="Usuario o contraseña incorrectos.")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("https://www.google.com.ar")


# === SELECCIONAR ARCHIVO ===
@app.route("/inicio")
def seleccionar_archivo():
    if "usuario" not in session:
        return redirect(url_for("login_page"))

    user_dir = get_user_dir(session["usuario"])
    archivos = obtener_archivos(user_dir)
    return render_template("seleccionar_archivo.html", archivos=archivos,
                           usuario=session["usuario"], rol=session["rol"])


# === ABRIR ARCHIVO ===
@app.route("/abrir/<nombre>")
def abrir_archivo(nombre):
    if "usuario" not in session:
        return redirect(url_for("login_page"))

    user_dir = get_user_dir(session["usuario"])
    archivos = obtener_archivos(user_dir)
    if nombre not in archivos:
        return "Archivo no encontrado", 404

    # Guardar la selección en la sesión (por usuario)
    session['archivo_seleccionado'] = nombre

    ruta = os.path.join(user_dir, nombre)
    poligonos = cargar_poligonos(ruta)
    return render_template("mapa.html", usuario=session["usuario"],
                           rol=session["rol"], poligonos=poligonos)


# === NUEVO ARCHIVO ===
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

    # No seleccionamos automáticamente el archivo nuevo para forzar que el usuario lo abra desde /inicio
    return jsonify({"success": True, "archivo": nombre})


# === GUARDAR ===
@app.route("/guardar", methods=["POST"])
def guardar():
    archivo_sel = session.get('archivo_seleccionado')
    if not archivo_sel:
        return jsonify({"success": False, "mensaje": "No hay archivo seleccionado. Elegí uno en la pantalla de inicio."})
    try:
        data = request.get_json(force=True)
        if not data or "datos" not in data:
            return jsonify({"success": False, "mensaje": "Datos inválidos."})

        user_dir = get_user_dir(session.get("usuario"))
        ruta = os.path.join(user_dir, archivo_sel)
        guardar_poligonos(data["datos"], ruta)
        return jsonify({"success": True, "mensaje": "✅ Cambios guardados correctamente."})
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"❌ Error: {e}"})


# === GUARDAR COMO ===
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

        # No seleccionamos automáticamente; el usuario podrá abrirlo desde /inicio
        return jsonify({"success": True, "mensaje": f"✅ Archivo guardado como '{nuevo_nombre}' correctamente."})
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"❌ Error al guardar: {e}"})


# === EJECUCIÓN ===
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
