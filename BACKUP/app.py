import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "BanfiClaveSegura123"

# === CONFIGURACIÓN ===
DATA_DIR = r"F:\MAPPEAR\data"
os.makedirs(DATA_DIR, exist_ok=True)

# Usuarios y roles
USERS = {
    "DSUBICI": {"password": "Banfi138", "rol": "admin"},
    "usuario1": {"password": "contraseña1", "rol": "user"},
    "usuario2": {"password": "contraseña2", "rol": "user"},
    "usuario3": {"password": "contraseña3", "rol": "user"},
    "usuario4": {"password": "contraseña4", "rol": "user"},
    "usuario5": {"password": "contraseña5", "rol": "user"},
}

archivo_seleccionado = None


# === FUNCIONES AUXILIARES ===
def obtener_archivos():
    return sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")])


def cargar_poligonos(ruta_archivo):
    df = pd.read_excel(ruta_archivo)
    columnas = ["NOMBRE", "SUPERFICIE", "STATUS", "PARTIDO", "COLOR HEX", "COORDENADAS"]
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
            "partido": str(fila["PARTIDO"]),
            "color": str(fila["COLOR HEX"]) if pd.notna(fila["COLOR HEX"]) else "#CCCCCC",
            "coords": coords,
            "COORDENADAS": str(fila["COORDENADAS"]) if pd.notna(fila["COORDENADAS"]) else ""
        })
    return poligonos


def guardar_poligonos(nuevos_datos, ruta_destino):
    columnas = ["NOMBRE", "SUPERFICIE", "STATUS", "PARTIDO", "COLOR HEX", "COORDENADAS"]
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
            df.at[i, "PARTIDO"] = dato.get("partido", "")
            df.at[i, "COLOR HEX"] = dato.get("color", "")
            df.at[i, "COORDENADAS"] = dato.get("COORDENADAS", "")
        else:
            df.loc[i] = [
                dato.get("name", ""),
                dato.get("superficie", ""),
                dato.get("status", ""),
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
        return redirect(url_for("index"))
    else:
        return render_template("login.html", error="Usuario o contraseña incorrectos.")


@app.route("/logout")
def logout():
    """Redirige a Google y limpia la sesión sin cerrar Flask."""
    session.clear()
    return redirect("https://www.google.com.ar")


# === INTERFAZ PRINCIPAL ===
@app.route("/inicio")
def index():
    if "usuario" not in session:
        return redirect(url_for("login_page"))

    global archivo_seleccionado
    archivos = obtener_archivos()
    if archivo_seleccionado is None:
        return render_template("seleccionar_archivo.html", archivos=archivos,
                               usuario=session["usuario"], rol=session["rol"])
    else:
        ruta = os.path.join(DATA_DIR, archivo_seleccionado)
        poligonos = cargar_poligonos(ruta)
        return render_template("mapa.html", usuario=session["usuario"],
                               rol=session["rol"], poligonos=poligonos)


@app.route("/abrir/<nombre>")
def abrir_archivo(nombre):
    global archivo_seleccionado
    if nombre not in obtener_archivos():
        return "Archivo no encontrado", 404
    archivo_seleccionado = nombre
    return redirect(url_for("index"))


@app.route("/nuevo_archivo", methods=["POST"])
def nuevo_archivo():
    global archivo_seleccionado
    nombre = request.form.get("nombre")
    if not nombre.endswith(".xlsx"):
        nombre += ".xlsx"
    ruta = os.path.join(DATA_DIR, nombre)
    if os.path.exists(ruta):
        return jsonify({"success": False, "mensaje": "El archivo ya existe."})
    df = pd.DataFrame(columns=["NOMBRE","SUPERFICIE","STATUS","PARTIDO","COLOR HEX","COORDENADAS"])
    df.to_excel(ruta, index=False)
    archivo_seleccionado = nombre
    return jsonify({"success": True, "archivo": nombre})


@app.route("/guardar", methods=["POST"])
def guardar():
    global archivo_seleccionado
    if archivo_seleccionado is None:
        return jsonify({"success": False, "mensaje": "No hay archivo seleccionado."})
    try:
        data = request.get_json(force=True)
        if not data or "datos" not in data:
            return jsonify({"success": False, "mensaje": "Datos inválidos."})
        ruta = os.path.join(DATA_DIR, archivo_seleccionado)
        guardar_poligonos(data["datos"], ruta)
        return jsonify({"success": True, "mensaje": "✅ Cambios guardados correctamente."})
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"❌ Error: {e}"})


# === EJECUCIÓN ===
if __name__ == "__main__":
    app.run(debug=True, port=5051)
