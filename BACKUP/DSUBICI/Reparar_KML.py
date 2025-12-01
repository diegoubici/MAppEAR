import re

def reparar_kml(archivo_entrada):
    print(f"🔧 Reparando: {archivo_entrada}\n")
    
    archivo_salida = archivo_entrada.replace('.kml', '_REPARADO.kml')
    
    try:
        with open(archivo_entrada, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        print("📊 Estadísticas del archivo original:")
        print(f"   - Tamaño: {len(contenido):,} caracteres")
        print(f"   - Líneas: {contenido.count(chr(10)):,}")
        
        # Reparaciones
        print("\n🔧 Aplicando reparaciones...")
        
        # 1. Escapar ampersands
        print("   [1/5] Escapando caracteres especiales...")
        contenido = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', contenido)
        
        # 2. Cerrar etiquetas auto-cerrantes mal formadas
        print("   [2/5] Corrigiendo etiquetas auto-cerrantes...")
        contenido = re.sub(r'<(\w+)([^>]*[^/])>(\s*)<\1', r'<\1\2/>\3<\1', contenido)
        
        # 3. Remover caracteres de control inválidos
        print("   [3/5] Removiendo caracteres de control...")
        contenido = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', contenido)
        
        # 4. Balancear Placemark tags
        print("   [4/5] Balanceando etiquetas Placemark...")
        placemarks_apertura = contenido.count('<Placemark>')
        placemarks_cierre = contenido.count('</Placemark>')
        
        if placemarks_apertura > placemarks_cierre:
            faltantes = placemarks_apertura - placemarks_cierre
            print(f"      ⚠️ Faltan {faltantes} cierres de Placemark")
            # Agregar cierres antes del </Document>
            contenido = contenido.replace('</Document>', '</Placemark>' * faltantes + '\n</Document>')
        
        # 5. Verificar estructura básica
        print("   [5/5] Verificando estructura...")
        if '</kml>' not in contenido:
            contenido += '\n</kml>'
        
        # Guardar archivo reparado
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"\n✅ Archivo reparado guardado como: {archivo_salida}")
        print(f"📊 Tamaño del archivo reparado: {len(contenido):,} caracteres")
        
        # Verificar con parser XML
        print("\n🔍 Verificando validez del XML...")
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(contenido)
            print("✅ XML válido - El archivo debería abrirse correctamente")
        except ET.ParseError as e:
            print(f"⚠️ Aún hay errores de XML: {e}")
            print(f"   Pero el archivo podría ser parcialmente recuperable")
        
        return archivo_salida
        
    except Exception as e:
        print(f"❌ Error durante la reparación: {e}")
        import traceback
        traceback.print_exc()
        return None

# Ejecutar
archivo = "LA PAMPA BARON.kml"
archivo_reparado = reparar_kml(archivo)

if archivo_reparado:
    print(f"\n{'=' * 100}")
    print(f"✅ REPARACIÓN COMPLETADA")
    print(f"{'=' * 100}")
    print(f"\n📁 Archivo reparado: {archivo_reparado}")
    print(f"\n💡 Ahora intenta abrir el archivo: {archivo_reparado}")
else:
    print("\n❌ No se pudo reparar el archivo")