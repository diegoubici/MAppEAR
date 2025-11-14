import os

print("🔍 Verificando variables de entorno:")
print(f"R2_ACCESS_KEY: {os.getenv('R2_ACCESS_KEY')}")
print(f"R2_SECRET_KEY: {os.getenv('R2_SECRET_KEY')}")
print(f"R2_BUCKET: {os.getenv('R2_BUCKET')}")
print(f"R2_ENDPOINT: {os.getenv('R2_ENDPOINT')}")