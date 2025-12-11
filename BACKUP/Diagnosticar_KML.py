def diagnosticar_kml(archivo):
    print(f"🔍 Diagnosticando: {archivo}\n")
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
        
        linea_error = 368809 - 1  # Python usa índice 0
        
        print(f"📍 LÍNEA PROBLEMÁTICA {linea_error + 1}:")
        print("=" * 100)
        
        # Mostrar contexto alrededor del error
        inicio = max(0, linea_error - 10)
        fin = min(len(lineas), linea_error + 10)
        
        for i in range(inicio, fin):
            if i == linea_error:
                print(f">>> {i+1:7d}: {lineas[i].rstrip()}")
                print(" " * 12 + "^" * 50 + " ERROR AQUÍ")
            else:
                print(f"    {i+1:7d}: {lineas[i].rstrip()}")
        
        print("=" * 100)
        
        # Extraer la línea exacta
        linea_problema = lineas[linea_error].strip()
        print(f"\n📝 Contenido exacto de la línea {linea_error + 1}:")
        print(f"   '{linea_problema}'")
        print(f"\n📏 Columna 51 (carácter problemático): '{linea_problema[50] if len(linea_problema) > 50 else 'N/A'}'")
        
        # Buscar etiquetas en la línea
        import re
        tags_apertura = re.findall(r'<(\w+)[^/>]*>', linea_problema)
        tags_cierre = re.findall(r'</(\w+)>', linea_problema)
        
        print(f"\n🏷️  Etiquetas en esta línea:")
        print(f"   Apertura: {tags_apertura}")
        print(f"   Cierre: {tags_cierre}")
        
        # Verificar balance de etiquetas hasta este punto
        print(f"\n🔍 Verificando balance de etiquetas hasta la línea {linea_error + 1}...")
        
        pila = []
        ultima_apertura = None
        
        for i in range(linea_error + 1):
            for tag in re.findall(r'<(\w+)[^/>]*(?<!/)>', lineas[i]):
                pila.append((tag, i + 1))
                ultima_apertura = (tag, i + 1)
            
            for tag in re.findall(r'</(\w+)>', lineas[i]):
                if pila and pila[-1][0] == tag:
                    pila.pop()
                else:
                    print(f"⚠️  Línea {i + 1}: Cierre de </{tag}> sin apertura correspondiente")
        
        if pila:
            print(f"\n⚠️  Etiquetas sin cerrar hasta la línea {linea_error + 1}:")
            for tag, linea_num in pila[-20:]:
                print(f"   - <{tag}> abierta en línea {linea_num}")
        
        print(f"\n💡 Última etiqueta abierta antes del error:")
        if ultima_apertura:
            print(f"   <{ultima_apertura[0]}> en línea {ultima_apertura[1]}")
        
    except Exception as e:
        print(f"❌ Error al analizar: {e}")
        import traceback
        traceback.print_exc()

# Ejecutar
archivo = "LA PAMPA BARON.kml"
diagnosticar_kml(archivo)

print("\n" + "=" * 100)
print("✅ Diagnóstico completado")
print("=" * 100)