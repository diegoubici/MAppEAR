import pandas as pd
import os

# Ruta del archivo Excel (puede ser relativo o absoluto)
file_path = 'LA PAMPA BARON.xlsx'

# Leer solo la primera hoja
data = pd.read_excel(file_path, sheet_name=0)

# Función para obtener el color de relleno desde la columna COLOR HEX
def get_fill_color(color_hex):
    if pd.isna(color_hex) or str(color_hex).strip() == "":
        return '00000000'  # Transparente
    return f'ff{str(color_hex).strip()[-6:]}'  # Color con opacidad FF

# Obtener la carpeta y el nombre base del Excel
carpeta_excel = os.path.dirname(os.path.abspath(file_path))
nombre_kml = os.path.splitext(os.path.basename(file_path))[0] + '.kml'
kml_path = os.path.join(carpeta_excel, nombre_kml)

# Crear el archivo KML
with open(kml_path, "w", encoding="utf-8") as file:
    file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    file.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
    file.write('  <Document>\n')
    file.write('    <name>Productores</name>\n')

    for index, row in data.iterrows():
        nombre = row.get('NOMBRE', 'Sin nombre')
        superficie = row.get('SUPERFICIE', '')
        color_hex = row.get('COLOR HEX', '')
        coordenadas = str(row.get('COORDENADAS', '')).strip()

        if not coordenadas:
            continue  # Saltar si no hay coordenadas

        poly_color = get_fill_color(color_hex)
        style_id = f"style{index}"
        highlight_style_id = f"highlightStyle{index}"

        # Estilo normal
        file.write(f'    <Style id="{style_id}">\n')
        file.write('      <LineStyle><color>FFFF0000</color><width>0.5</width></LineStyle>\n')
        file.write(f'      <PolyStyle><color>{poly_color}</color></PolyStyle>\n')
        file.write('    </Style>\n')

        # Estilo resaltado
        file.write(f'    <Style id="{highlight_style_id}">\n')
        file.write('      <LineStyle><color>FFFFFFFF</color><width>2.5</width></LineStyle>\n')
        file.write(f'      <PolyStyle><color>{poly_color}</color></PolyStyle>\n')
        file.write('      <BalloonStyle>\n')
        file.write(f'        <text><![CDATA[<b>Nombre:</b> {nombre}<br><b>Superficie:</b> {superficie}]]></text>\n')
        file.write('      </BalloonStyle>\n')
        file.write('    </Style>\n')

        # StyleMap
        file.write(f'    <StyleMap id="styleMap{index}">\n')
        file.write(f'      <Pair><key>normal</key><styleUrl>#{style_id}</styleUrl></Pair>\n')
        file.write(f'      <Pair><key>highlight</key><styleUrl>#{highlight_style_id}</styleUrl></Pair>\n')
        file.write('    </StyleMap>\n')

        # Placemark
        file.write('    <Placemark>\n')
        file.write(f'      <name>{nombre}</name>\n')
        file.write(f'      <styleUrl>#styleMap{index}</styleUrl>\n')
        file.write('      <Polygon>\n')
        file.write('        <outerBoundaryIs>\n')
        file.write('          <LinearRing>\n')
        file.write('            <coordinates>\n')
        file.write(f'              {coordenadas}\n')
        file.write('            </coordinates>\n')
        file.write('          </LinearRing>\n')
        file.write('        </outerBoundaryIs>\n')
        file.write('      </Polygon>\n')
        file.write('    </Placemark>\n')

    file.write('  </Document>\n')
    file.write('</kml>\n')

print(f"KML generado exitosamente en:\n{kml_path}")


 