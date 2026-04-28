import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import os
import subprocess
import re
import mysql.connector

def generar_factura(row, output_dir):
    try:
        # Extraer datos (ajustado a tus columnas)
        factura_raw = str(row['FACTURA']).strip()

        # Extraer solo el número de la factura, ignorando cualquier carácter extraño
        num_match = re.search(r'\d+', factura_raw)

        if not num_match:
            raise ValueError(f"FACTURA inválida en fila: '{factura_raw}'")

        num_factura = re.sub(r'\D', '', factura_raw)[-9:].zfill(9)
        cliente = row.get('CLIENTE') or row.get('MARCACION')
        tallos = float(row['TALLOS'])
        precio_unitario = float(row['PU']) 
        fob = float(row['FOB']) 
        descuento = float(row['DESCUENTO'])
        # Manejo de fecha (clave para el error)
        if isinstance(row['FECHA FACTURA'], str):
            # Si es string, convertir a datetime
            fecha_emision = datetime.strptime(row['FECHA FACTURA'], "%d/%m/%Y")  # Ajusta el formato según tus datos
        else:
            # Si ya es datetime (pandas lo convierte automáticamente)
            fecha_emision = row['FECHA FACTURA']

        fecha_str = fecha_emision.strftime("%d%m%Y")  # Formato DDMMAAAA para clave
        fecha_emision_formatted = fecha_emision.strftime("%d/%m/%Y")  # Formato para XML
        
        info_texto = row["INFO ADICIONAL"]
        def format_price(number):
            s = f"{number:.6f}"
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return s
        formatted = format_price(precio_unitario)
        fecha_str = fecha_emision.strftime("%d%m%Y")
        clave_incompleta = (fecha_str 
        + "01" #Tipo de comprobante
        + "1716224967001" #RUC #Cambiar por finca
        + "2" #Ambiente
        + "001002" #Serie (Establecimiento y punto de emisión) #Cambiar por finca
        + num_factura #Secuencial
        + "43762667" #codigo aleatorio
        + "1") #Tipo de comprobante

        #Digito verificador

        def calcular_digito_verificador(clave_sin_digito):
        # Convertir la clave a reversa y eliminar no dígitos
            digits = clave_sin_digito[::-1]
    
            suma = 0
            factor = 2  # Inicia en 2
    
            for i in range(len(digits)):
                suma += int(digits[i]) * factor
                factor = 2 if factor == 7 else factor + 1  # Ciclo 2-7
    
            dv = 11 - (suma % 11)
            return 1 if dv == 10 else 0 if dv == 11 else dv
        digito_verificador = calcular_digito_verificador(clave_incompleta)
        clave_acceso = clave_incompleta + str(digito_verificador)

        # Guardar clave de acceso en un archivo de texto
# Conectar a la Base de Datos Distribuida (MySQL en Docker)
        try:
            conexion = mysql.connector.connect(
                host="127.0.0.1",
                port=3307,
                user="root",
                password="1234",
                database="endless_floricola"
            )
            cursor = conexion.cursor()
            
            # 1. Insertar en la tabla conciliacion_dae
            sql_dae = """INSERT INTO conciliacion_dae 
                         (num_factura, cliente, tallos, precio_unitario, fecha_emision) 
                         VALUES (%s, %s, %s, %s, %s)"""
            val_dae = (num_factura, cliente, tallos, float(precio_unitario), fecha_emision.strftime('%Y-%m-%d'))
            cursor.execute(sql_dae, val_dae)
            
            # Obtener el ID de la factura que acabamos de insertar
            factura_id = cursor.lastrowid
            
            # 2. Insertar en la tabla bitacora_sri la clave de acceso
            sql_bitacora = """INSERT INTO bitacora_sri 
                              (factura_id, clave_acceso, mensaje_error) 
                              VALUES (%s, %s, %s)"""
            val_bitacora = (factura_id, clave_acceso, "Generado XML")
            cursor.execute(sql_bitacora, val_bitacora)
            
            conexion.commit() # Confirmar los cambios
            cursor.close()
            conexion.close()
            print(f"✅ Factura {num_factura} y Clave guardadas en MySQL.")
            
        except Exception as err:
            print(f"⚠️ Error conectando a BD: {err}")

        # Crear XML
        factura = ET.Element("factura", id="comprobante", version="1.1.0")
        
        # Info Tributaria (datos fijos)
        info_trib = ET.SubElement(factura, "infoTributaria")
        ET.SubElement(info_trib, "ambiente").text = "2"
        ET.SubElement(info_trib, "tipoEmision").text = "1"
        ET.SubElement(info_trib, "razonSocial").text = "LATORRE LATORRE JEAN PAUL SEBASTIAN" #Cambiar por finca
        ET.SubElement(info_trib, "nombreComercial").text = "LATORRE LATORRE JEAN PAUL SEBASTIAN" #Cambiar por finca
        ET.SubElement(info_trib, "ruc").text = "1716224967001" #Cambiar por finca
        ET.SubElement(info_trib, "claveAcceso").text = clave_acceso       
        ET.SubElement(info_trib, "codDoc").text = "01"
        ET.SubElement(info_trib, "estab").text = "001" #Cambiar por finca
        ET.SubElement(info_trib, "ptoEmi").text = "002" #Cambiar por finca
        ET.SubElement(info_trib, "secuencial").text = num_factura
        ET.SubElement(info_trib, "dirMatriz").text = "PICHINCHA / CAYAMBE / CAYAMBE / ASCAZUBI N2-06 Y VIVAR" #Cambiar por finca
        ET.SubElement(info_trib, "contribuyenteRimpe").text = "CONTRIBUYENTE RÉGIMEN RIMPE" # Solo si es contribuyente RIMPE, de lo contrario, eliminar esta línea #Cambiar por finca

        # Info Factura
        info_fact = ET.SubElement(factura, "infoFactura")
        ET.SubElement(info_fact, "fechaEmision").text = fecha_emision_formatted
        ET.SubElement(info_fact, "dirEstablecimiento").text = "PICHINCHA / CAYAMBE / CAYAMBE / ASCAZUBI N2-06 Y VIVAR                                                 EXPORTADOR HABITUAL DE BIENES" #Cambiar por finca
        ET.SubElement(info_fact, "obligadoContabilidad").text = "NO"
        ET.SubElement(info_fact, "comercioExterior").text = "EXPORTADOR"
        ET.SubElement(info_fact, "incoTermFactura").text = "FOB"
        ET.SubElement(info_fact, "lugarIncoTerm").text = "QUITO"  ##str(row['LUGARINCOTERM'])## se cambia si es diferente embarque
        ET.SubElement(info_fact, "paisOrigen").text = "593"
        ET.SubElement(info_fact, "puertoEmbarque").text = "QUITO" ##str(row['PUERTOEMBARQUE'])## se cambia si es diferente embarque
        ET.SubElement(info_fact, "puertoDestino").text = str(row['DESTINO'])
        ET.SubElement(info_fact, "tipoIdentificacionComprador").text = "08"
        ET.SubElement(info_fact, "razonSocialComprador").text = cliente
        ET.SubElement(info_fact, "identificacionComprador").text = str(int(row['IDENTIFICACION DEL COMPRADOR']))
        # ET.SubElement(info_fact, "direccionComprador").text = str(row['DIRECCION DEL COMPRADOR']) # Colocar si tiene dirección del comprador
        ET.SubElement(info_fact, "totalSinImpuestos").text = f"{fob:.2f}"
        ET.SubElement(info_fact, "incoTermTotalSinImpuestos").text = "FOB"
        ET.SubElement(info_fact, "totalDescuento").text = f"{descuento:.2f}"
        # TotalConImpuestos
        total_con_impuestos = ET.SubElement(info_fact, "totalConImpuestos")
        total_impuesto = ET.SubElement(total_con_impuestos, "totalImpuesto")
        ET.SubElement(total_impuesto, "codigo").text = "2"
        ET.SubElement(total_impuesto, "codigoPorcentaje").text = "0"
        ET.SubElement(total_impuesto, "baseImponible").text = f"{fob:.2f}"
        ET.SubElement(total_impuesto, "tarifa").text = "0.00"
        ET.SubElement(total_impuesto, "valor").text = "0.00"
        ET.SubElement(info_fact, "propina").text = "0.00"
        ET.SubElement(info_fact, "importeTotal").text = f"{fob:.2f}"
        ET.SubElement(info_fact, "moneda").text = "DOLAR"
        pagos = ET.SubElement(info_fact, "pagos")
        pago = ET.SubElement(pagos, "pago")
        ET.SubElement(pago, "formaPago").text = "20"
        ET.SubElement(pago, "total").text = f"{fob:.2f}"

        
        # Detalles
        detalles = ET.SubElement(factura, "detalles")
        detalle = ET.SubElement(detalles, "detalle")
        ET.SubElement(detalle, "codigoPrincipal").text = "0001"
        ET.SubElement(detalle, "codigoAuxiliar").text = "0001"
        ET.SubElement(detalle, "descripcion").text = "ROSAS"
        ET.SubElement(detalle, "cantidad").text = f"{tallos:.2f}"
        ET.SubElement(detalle, "precioUnitario").text = formatted
        ET.SubElement(detalle, "descuento").text = f"{descuento:.2f}"
        ET.SubElement(detalle, "precioTotalSinImpuesto").text = f"{fob:.2f}"
        detalles_adicionales = ET.SubElement(detalle, "detallesAdicionales")
        ET.SubElement(detalles_adicionales, "detAdicional", nombre="TALLOS", valor="TALLOS")
        ET.SubElement(detalles_adicionales, "detAdicional", nombre="USHTS 06031100000", valor="USHTS")
        impuestos = ET.SubElement(detalle, "impuestos")
        impuesto = ET.SubElement(impuestos, "impuesto")
        ET.SubElement(impuesto, "codigo").text = "2"
        ET.SubElement(impuesto, "codigoPorcentaje").text = "0"
        ET.SubElement(impuesto, "tarifa").text = "0.00"
        ET.SubElement(impuesto, "baseImponible").text = f"{fob:.2f}"
        ET.SubElement(impuesto, "valor").text = "0.00"
        info_adicional = ET.SubElement(factura, "infoAdicional")
        # ET.SubElement(info_adicional, "campoAdicional", nombre = "Dirección").text = str(row['DIRECCION DEL COMPRADOR']) # Se coloca Direccion del comprador si existe
        ET.SubElement(info_adicional, "campoAdicional", nombre="  ").text = info_texto
        
        
        
        
        # Guardar XML - Versión modificada con post-procesamiento
        tree = ET.ElementTree(factura)
        ET.indent(tree, space="\t", level=0)
        
        # 1. Primero guardamos en un string
        xml_str = ET.tostring(factura, encoding="unicode")
        
        # 2. Aplicamos las tabulaciones específicas
        xml_str = xml_str.replace('<puertoEmbarque>', '\t<puertoEmbarque>') \
                        .replace('<puertoDestino>', '\t<puertoDestino>')
        xml_str = xml_str.replace(' />', '/>')
        
        # 3. Aseguramos que paisOrigen esté en la misma línea
        xml_str = xml_str.replace('<paisOrigen>\n\t', '<paisOrigen>')
        
        # 4. Guardamos el archivo en la carpeta GENERADOS
        archivo_salida = os.path.join(output_dir, f"{clave_acceso}.xml")
        with open(archivo_salida, 'w', encoding='UTF-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            f.write(xml_str)
        
        return archivo_salida
        
    except Exception as e:
        print(f"Error en fila {row['FACTURA']}: {str(e)}")
        return None

def firmar_xml(xml_path, p12_path, p12_password, tipo='factura'):
    """
    Firma un XML enviando la ruta de la firma y la contraseña al script de Node.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    firmados_dir = os.path.join(script_dir, "FIRMADOS")
    os.makedirs(firmados_dir, exist_ok=True)

    nombre = os.path.basename(xml_path).replace(".xml", "_firmado.xml")
    firmado_path = os.path.join(firmados_dir, nombre)

    # Añadimos los nuevos parámetros al comando
    cmd = ['node', 'firmar_sri.mjs', tipo, xml_path, firmado_path, p12_path, p12_password]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("ERROR al firmar:", result.stderr)
        return None

    print("Firmado correctamente:", firmado_path)
    return firmado_path

def procesar_excel_automatico(ruta_excel, p12_path, p12_password):
    """
    Función adaptada que ahora recibe la ruta de la firma y la contraseña desde la API.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generados_dir = os.path.join(script_dir, "GENERADOS")
    os.makedirs(generados_dir, exist_ok=True)

    if os.path.exists(ruta_excel):
        hoja = "REPORTE FACTURACION"
        print(f"Iniciando procesamiento distribuido del archivo '{ruta_excel}'...")
        df = pd.read_excel(ruta_excel, sheet_name=hoja)
        
        for _, row in df.iterrows():
            if pd.notna(row.get('FACTURA')):
                xml_file = generar_factura(row, generados_dir)
                if xml_file:
                    # Le pasamos la firma y contraseña a la función de firmar
                    firmado = firmar_xml(xml_file, p12_path, p12_password, tipo='factura')
    else:
        print("ERROR: Archivo no encontrado.")

def main():
    try:
        # Configuración automática
        script_dir = os.path.dirname(os.path.abspath(__file__))
        generados_dir = os.path.join(script_dir, "GENERADOS")
        firmados_dir = os.path.join(script_dir, "FIRMADOS")
        os.makedirs(firmados_dir, exist_ok=True)
        # Crear carpeta GENERADOS si no existe
        os.makedirs(generados_dir, exist_ok=True)

        # Pedir al usuario el nombre del archivo Excel (solo nombre o con .xlsx)
        archivo_nombre = input("Ingrese el nombre del archivo Excel (ej: archivo.xlsx): ").strip()

        # Añadir la extensión si no está
        if not archivo_nombre.lower().endswith(".xlsx"):
            archivo_nombre += ".xlsx"

        excel_path = os.path.join(script_dir, archivo_nombre)

        if os.path.exists(excel_path):
            hoja = "REPORTE FACTURACION"
            print(f"Leyendo hoja '{hoja}' del archivo '{archivo_nombre}'...")
            df = pd.read_excel(excel_path, sheet_name=hoja)

            print(f"Columnas detectadas: {df.columns.tolist()}")
            
            for _, row in df.iterrows():
                if pd.notna(row.get('FACTURA')):
                    xml_file = generar_factura(row, generados_dir)
                    if xml_file:
                        print(f"Generado: {xml_file}")
                        firmado = firmar_xml(xml_file, tipo='factura')
                        if firmado:
                            print(f"XML firmado: {firmado}")
        else:
            print("ERROR: Archivo no encontrado en la ruta:", excel_path)

    except ValueError as ve:
        print(f"Error: No se pudo leer la hoja '{hoja}'. Detalles: {str(ve)}")
    except Exception as e:
        print(f"Error general: {str(e)}")


if __name__ == "__main__":
    main()

