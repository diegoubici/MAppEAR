import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import boto3
from io import BytesIO

# ============================================
# CONFIGURACIÓN CLOUDFLARE R2
# ============================================

R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")

r2 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

# ============================================
# FLASK
# ============================================

app = Flask(__name__)
app.secret_key = "mi_clave_secreta"  # cámbiala por seguridad

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================
# LOGIN BÁSICO
# ============================================

USERS = {
    "admin": "admin123",
    "usuario1": "contraseña1",
    "usuario2": "contraseña2",
    "usuario3": "contraseña3",
    "usuario4": "contraseña4",
    "usuario5": "contraseña5",
}

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("lista_archivos"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
        if usuario in USERS and USERS[usuario] == contraseña:
            session["user"] = usuario
            return redirect(url_for("lista_archivos"))
        else:
            return render_template("login.html", error="Usuario o contraseña incorrectos")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ============================================
# LISTAR ARCHIVOS DESDE CLOUDFLARE R2
# ============================================

@app.route("/archivos")
def lista_archivos():
    if "user" not in session:
        return redirect(url_for("login"))

    objetos = r2.list_objects_v2(Bucket=R2_BUCKET)
    archivos = []

    if "Contents" in objetos:
        for obj in objetos["Contents"]:
            if obj["Key"].lower().endswith(".xlsx"):
                archivos.append(obj["Key"])

    return render_template("archivos.html", archivos=archivos)


# ============================================
# DESCARGAR .XLSX DESDE R2
# ============================================

def descargar_xlsx(nombre_archivo):
    try:
        archivo_r2 = r2.get_object(Bucket=R2_BUCKET, Key=nombre_archivo)
        data = archivo_r2["Body"].read()
        return pd.ExcelFile(BytesIO(data))
    except Exception as e:
        print("❌ Error al descargar desde R2:", e)
        return None


# ============================================
# EDITAR ARCHIVO
# ============================================

@app.route("/editar/<nombre>")
def editar_archivo(nombre):
    if "user" not in session:
        return redirect(url_for("login"))

    excel = descargar_xlsx(nombre)
    if excel is None:
        return "No se pudo abrir el archivo."

    hojas = excel.sheet_names
    return render_template("editar.html", archivo=nombre, hojas=hojas)


@app.route("/leer_hoja", methods=["POST"])
def leer_hoja():
    contenido = request.get_json(force=True)
    archivo = contenido["archivo"]
    hoja = contenido["hoja"]

    excel = descargar_xlsx(archivo)
    df = pd.read_excel(excel, sheet_name=hoja)

    return jsonify({
        "columnas": list(df.columns),
        "datos": df.fillna("").values.tolist()
    })


# ============================================
# GUARDAR CAMBIOS SOBRE EL MISMO ARCHIVO
# ============================================

@app.route("/guardar", methods=["POST"])
def guardar():
    contenido = request.get_json(force=True)
    archivo = contenido["archivo"]
    datos = contenido["datos"]
    columnas = contenido["columnas"]
    hoja = contenido["hoja"]

    df = pd.DataFrame(datos, columns=columnas)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=hoja)

    r2.put_object(
        Bucket=R2_BUCKET,
        Key=archivo,
        Body=buffer.getvalue(),
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    return jsonify({"ok": True})


# ============================================
# GUARDAR COMO (NUEVO ARCHIVO EN R2)
# ============================================

@app.route("/guardar_como", methods=["POST"])
def guardar_como():
    contenido = request.get_json(force=True)
    datos = contenido["datos"]
    columnas = contenido["columnas"]
    hoja = contenido["hoja"]
    nuevo_nombre = contenido["nuevo_nombre"].strip()

    if not nuevo_nombre.lower().endswith(".xlsx"):
        nuevo_nombre += ".xlsx"

    df = pd.DataFrame(datos, columns=columnas)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=hoja)

    r2.put_object(
        Bucket=R2_BUCKET,
        Key=nuevo_nombre,
        Body=buffer.getvalue(),
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    return jsonify({"ok": True})


# ============================================
# SUBIR ARCHIVO A R2
# ============================================

@app.route("/subir", methods=["POST"])
def subir():
    archivo = request.files["archivo"]
    nombre = secure_filename(archivo.filename)

    r2.put_object(
        Bucket=R2_BUCKET,
        Key=nombre,
        Body=archivo.read(),
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    return redirect(url_for("lista_archivos"))


# ============================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
