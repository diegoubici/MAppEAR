import os
import boto3

R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")

print("="*60)
print("🚀 SETUP DE CLOUDFLARE R2 PARA MAppEAR")
print("="*60)
print()

# Crear cliente
r2 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

# Usuarios a crear
usuarios = ["DSUBICI", "RIVADAVIA", "usuario1", "usuario2", "usuario3", "usuario4"]

print("📁 Creando estructura de carpetas...")
print()

for usuario in usuarios:
    try:
        # Crear "carpeta" (en S3/R2 las carpetas son objetos con / al final)
        key = f"{usuario}/.placeholder"
        r2.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=b"",  # Archivo vacío
            ContentType="text/plain"
        )
        print(f"   ✅ {usuario}/")
    except Exception as e:
        print(f"   ❌ Error en {usuario}: {e}")

print()
print("="*60)
print("✅ SETUP COMPLETADO")
print("="*60)
print()
print("Ahora puedes subir archivos .xlsx a cada carpeta de usuario.")