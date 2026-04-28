import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import os
import re
import subprocess

def safe_str(value, default=""):
    if pd.isna(value):
        return default
    return str(value)

def calcular_digito_verificador(clave_sin_digito):
    # Mismo algoritmo que usas para la factura
    digits = clave_sin_digito[::-1]
    suma = 0
    factor = 2  # Inicia en 2

    for i in range(len(digits)):
        suma += int(digits[i]) * factor
        factor = 2 if factor == 7 else factor + 1  # Ciclo 2-7

    dv = 11 - (suma % 11)
    return 1 if dv == 10 else 0 if dv == 11 else dv

def format_price(number):
    s = f"{number:.6f}"
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s

def generar_nota_credito(row, output_dir):
    try:
        # ==========================
        # 1) DATOS BÁSICOS DESDE EXCEL
        # ==========================

        # Secuencial de la NOTA DE CRÉDITO (usa la columna que tengas para NC)
        nc_raw = str(row['NOTAS DE CREDITO']).strip()          # <-- CAMBIA 'NC' por la columna correcta
        num_match = re.search(r'\d+', nc_raw)
        if not num_match:
            raise ValueError(f"NC inválida en fila: '{nc_raw}'")

        num_nc = re.sub(r'\D', '', nc_raw)[-9:].zfill(9)

        # Factura que se modifica (doc sustento)
        doc_sustento_raw = str(row['FACTURA MODIFICADA']).strip()   # <-- CAMBIA nombre de columna
        num_doc_modificado = doc_sustento_raw

        cliente = safe_str(row.get("CLIENTE", row.get("MARCACION", "")))
        identificacion_comprador = str(int(row['IDENTIFICACION DEL COMPRADOR']))
        tallos = float(row['TALLOS'])
        precio_unitario = float(row['PU'])
        valor_modificacion = float(row['FOB'])   # total de la NC (puedes usar otra columna si manejas parciales)
        total_sin_impuestos = valor_modificacion

        # FECHA NOTA DE CRÉDITO
        if isinstance(row['FECHA NC'], str):     # <-- CAMBIA 'FECHA NC' por tu columna real
            fecha_emision = datetime.strptime(row['FECHA NC'], "%d/%m/%Y")
        else:
            fecha_emision = row['FECHA NC']

        fecha_str = fecha_emision.strftime("%d%m%Y")           # para clave
        fecha_emision_formatted = fecha_emision.strftime("%d/%m/%Y")  # para XML

        # FECHA DE LA FACTURA SUSTENTO (doc modificado)
        if isinstance(row['FECHA FACTURA'], str):
            fecha_sustento = datetime.strptime(row['FECHA FACTURA'], "%d/%m/%Y")
        else:
            fecha_sustento = row['FECHA FACTURA']
        fecha_sustento_str = fecha_sustento.strftime("%d/%m/%Y")

        #info_texto = safe_str(row.get("INFO ADICIONAL", ""))
        formatted_pu = format_price(precio_unitario)

        # ==========================
        # 2) CLAVE DE ACCESO (codDoc = 04)
        # ==========================
        clave_incompleta = (
            fecha_str +            # fecha emisión DDMMYYYY
            "04" +                 # Tipo de comprobante: 04 = Nota de crédito
            "1714208806001" +      # RUC  <-- CAMBIAR POR FINCA
            "2" +                  # Ambiente (1 = pruebas, 2 = producción)
            "002002" +             # Serie (estab + ptoEmi)  <-- CAMBIAR POR FINCA
            num_nc +               # Secuencial de la NC
            "43762667" +           # Código numérico (puede ser aleatorio)
            "1"                    # Tipo de emisión (normalmente 1)
        )

        digito_verificador = calcular_digito_verificador(clave_incompleta)
        clave_acceso = clave_incompleta + str(digito_verificador)

        # Opcional: guardar las claves
        with open("claves_acceso_nc.txt", "a", encoding="utf-8") as archivo:
            archivo.write(clave_acceso + "\n")

        # ==========================
        # 3) CONSTRUCCIÓN DEL XML NOTA DE CRÉDITO
        # ==========================

        nota = ET.Element("notaCredito", id="comprobante", version="1.0.0")

        # --- infoTributaria (igual que factura salvo codDoc y secuencial) ---
        info_trib = ET.SubElement(nota, "infoTributaria")
        ET.SubElement(info_trib, "ambiente").text = "2"
        ET.SubElement(info_trib, "tipoEmision").text = "1"
        ET.SubElement(info_trib, "razonSocial").text = "SAENZ SAENZ LUIS RAMIRO"  # CAMBIAR
        ET.SubElement(info_trib, "nombreComercial").text = "MARLYNSFLOR"          # CAMBIAR
        ET.SubElement(info_trib, "ruc").text = "1714208806001"                    # CAMBIAR
        ET.SubElement(info_trib, "claveAcceso").text = clave_acceso
        ET.SubElement(info_trib, "codDoc").text = "04"
        ET.SubElement(info_trib, "estab").text = "002"  # CAMBIAR
        ET.SubElement(info_trib, "ptoEmi").text = "002" # CAMBIAR
        ET.SubElement(info_trib, "secuencial").text = num_nc
        ET.SubElement(info_trib, "dirMatriz").text = "PICHINCHA / PEDRO MONCAYO / TOCACHI / PRINCIPAL SN Y PANAMERICANA"  # CAMBIAR

        # --- infoNotaCredito (estructura distinta a infoFactura) ---
        info_nc = ET.SubElement(nota, "infoNotaCredito")
        ET.SubElement(info_nc, "fechaEmision").text = fecha_emision_formatted
        ET.SubElement(info_nc, "dirEstablecimiento").text = (
            "PICHINCHA / PEDRO MONCAYO / TOCACHI / PRINCIPAL SN Y PANAMERICANA\t                                                             EXPORTADOR HABITUAL DE BIENES"
        )
        ET.SubElement(info_nc, "tipoIdentificacionComprador").text = "08"
        ET.SubElement(info_nc, "razonSocialComprador").text = cliente
        ET.SubElement(info_nc, "identificacionComprador").text = identificacion_comprador
        ET.SubElement(info_nc, "obligadoContabilidad").text = "NO"

        # Documento que se modifica (factura)
        ET.SubElement(info_nc, "codDocModificado").text = "01"
        ET.SubElement(info_nc, "numDocModificado").text = num_doc_modificado
        ET.SubElement(info_nc, "fechaEmisionDocSustento").text = fecha_sustento_str

        # Totales
        ET.SubElement(info_nc, "totalSinImpuestos").text = f"{total_sin_impuestos:.2f}"
        ET.SubElement(info_nc, "valorModificacion").text = f"{valor_modificacion:.2f}"
        ET.SubElement(info_nc, "moneda").text = "DOLAR"

        total_con_impuestos = ET.SubElement(info_nc, "totalConImpuestos")
        total_impuesto = ET.SubElement(total_con_impuestos, "totalImpuesto")
        ET.SubElement(total_impuesto, "codigo").text = "2"
        ET.SubElement(total_impuesto, "codigoPorcentaje").text = "0"
        ET.SubElement(total_impuesto, "baseImponible").text = f"{total_sin_impuestos:.2f}"
        # En tu XML de ejemplo de notaCredito, NO había <tarifa> en totalImpuesto:
        ET.SubElement(total_impuesto, "valor").text = "0.00"

        # Motivo de la NC
        motivo = row.get("MOTIVO", "ANULACION")
        ET.SubElement(info_nc, "motivo").text = str(motivo)

        # --- Detalles (estructura casi igual, pero con codigoInterno/codigoAdicional) ---
        detalles = ET.SubElement(nota, "detalles")
        detalle = ET.SubElement(detalles, "detalle")
        ET.SubElement(detalle, "codigoInterno").text = "0001"
        ET.SubElement(detalle, "codigoAdicional").text = "0001"
        ET.SubElement(detalle, "descripcion").text = "ROSAS"
        ET.SubElement(detalle, "cantidad").text = f"{tallos:.2f}"
        ET.SubElement(detalle, "precioUnitario").text = formatted_pu
        ET.SubElement(detalle, "descuento").text = "0"
        ET.SubElement(detalle, "precioTotalSinImpuesto").text = f"{valor_modificacion:.2f}"

        detalles_adicionales = ET.SubElement(detalle, "detallesAdicionales")
        ET.SubElement(detalles_adicionales, "detAdicional", nombre="USHTS 06031100000", valor="USHTS 06031100000")
        ET.SubElement(detalles_adicionales, "detAdicional", nombre="TALLOS", valor="TALLOS")

        impuestos = ET.SubElement(detalle, "impuestos")
        impuesto = ET.SubElement(impuestos, "impuesto")
        ET.SubElement(impuesto, "codigo").text = "2"
        ET.SubElement(impuesto, "codigoPorcentaje").text = "0"
        ET.SubElement(impuesto, "tarifa").text = "0.00"
        ET.SubElement(impuesto, "baseImponible").text = f"{valor_modificacion:.2f}"
        ET.SubElement(impuesto, "valor").text = "0.00"

        # --- infoAdicional ---
        #info_adicional = ET.SubElement(nota, "infoAdicional")
        #ET.SubElement(info_adicional, "campoAdicional", nombre="  ").text = info_texto

        # ==========================
        # 4) GUARDAR XML
        # ==========================
        tree = ET.ElementTree(nota)
        ET.indent(tree, space="\t", level=0)

        xml_str = ET.tostring(nota, encoding="unicode")
        xml_str = xml_str.replace(' />', '/>')

        archivo_salida = os.path.join(output_dir, f"{clave_acceso}.xml")
        with open(archivo_salida, 'w', encoding='UTF-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            f.write(xml_str)

        return archivo_salida

    except Exception as e:
        print(f"Error en NC fila {row.get('NOTAS DE CREDITO', 'SIN_NC')}: {str(e)}")
        return None

def firmar_xml(xml_path, tipo='factura'):
    """
    Firma un XML usando firmar_sri.mjs y guarda el archivo firmado
    en FIRMADOS (facturas) o FIRMADOS_NC (notas de crédito).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if tipo == 'nc':
        firmados_dir = os.path.join(script_dir, "FIRMADOS_NC")
    else:
        firmados_dir = os.path.join(script_dir, "FIRMADOS")

    os.makedirs(firmados_dir, exist_ok=True)

    # nombre_archivo.xml → nombre_archivo_firmado.xml
    nombre = os.path.basename(xml_path).replace(".xml", "_firmado.xml")
    firmado_path = os.path.join(firmados_dir, nombre)

    cmd = ['node', 'firmar_sri.mjs', tipo, xml_path, firmado_path]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("ERROR al firmar:", result.stderr)
        return None

    print("Firmado correctamente:", firmado_path)
    return firmado_path

def main_nc():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generados_dir = os.path.join(script_dir, "GENERADOS_NC")
    os.makedirs(generados_dir, exist_ok=True)

    archivo_nombre = input("Ingrese el nombre del archivo Excel de NOTAS DE CREDITO: ").strip()
    if not archivo_nombre.lower().endswith(".xlsx"):
        archivo_nombre += ".xlsx"

    excel_path = os.path.join(script_dir, archivo_nombre)

    if os.path.exists(excel_path):
        hoja = "REPORTE NC"  # <-- cambia al nombre real de tu hoja
        df = pd.read_excel(excel_path, sheet_name=hoja)

        for _, row in df.iterrows():
            if pd.notna(row.get('NOTAS DE CREDITO')):   # columna que uses para el número de nota de crédito
                xml_file = generar_nota_credito(row, generados_dir)
                if xml_file:
                    print(f"Nota de crédito generada: {xml_file}")

                    firmado = firmar_xml(xml_file, tipo='nc')
                    if firmado:
                        print(f"Nota de crédito firmada: {firmado}")
    else:
        print("ERROR: Archivo no encontrado:", excel_path)

if __name__ == "__main__":
    main_nc()