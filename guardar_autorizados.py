from enviar_al_sri import enviar_al_sri
import os 
from lxml import etree
from datetime import datetime


# ================================
# FUNCION BASE PARA PROCESAR CUALQUIER CARPETA
# ================================
def procesar_carpeta_firmados(carpeta_firmados, carpeta_autorizados):
    print(f"\n📁 Revisando: {carpeta_firmados}")

    if not os.path.isdir(carpeta_firmados):
        print(f"No existe la carpeta: {carpeta_firmados}")
        return

    archivos_xml = [
        f for f in os.listdir(carpeta_firmados)
        if f.lower().endswith(".xml")
    ]

    if not archivos_xml:
        print("No hay archivos XML en la carpeta.")
        return

    # Crear carpeta de autorizados
    os.makedirs(carpeta_autorizados, exist_ok=True)

    for archivo in archivos_xml:
        ruta = os.path.join(carpeta_firmados, archivo)
        print(f"\n🔄 Procesando: {archivo}")

        estado, mensaje, clave_registrada = enviar_al_sri(ruta, ambiente="2")

        print(f"📤 Estado recepción: {estado}")
        print(f"📄 Mensaje: {mensaje}")

        # Condiciones para guardar como autorizado
        if estado in ("RECIBIDA", "DEVUELTA") or clave_registrada:
            try:
                # Extraer clave de acceso
                root = etree.parse(ruta).getroot()
                clave_acceso = root.findtext(".//claveAcceso")

                if not clave_acceso:
                    raise ValueError("No se encontró claveAcceso en el XML firmado.")

                nombre_autorizado = f"AUT_{clave_acceso}.xml"
                path_autorizado = os.path.join(carpeta_autorizados, nombre_autorizado)

                # Leer contenido original
                with open(ruta, "r", encoding="utf-8") as f_xml:
                    contenido_xml = f_xml.read()

                # Fecha actual
                fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M:%S.000')

                # Crear XML AUTORIZADO
                xml_autorizacion = f"""<?xml version="1.0" encoding="UTF-8"?><autorizacion>
                <estado>AUTORIZADO</estado>
                <numeroAutorizacion>{clave_acceso}</numeroAutorizacion>
                <fechaAutorizacion class="fechaAutorizacion">{fecha_actual}</fechaAutorizacion>
                <comprobante><![CDATA[{contenido_xml}]]></comprobante>
                <mensaje/>
                </autorizacion>"""

                with open(path_autorizado, "w", encoding="utf-8") as f:
                    f.write(xml_autorizacion)

                print(f"✅ XML autorizado guardado en: {path_autorizado}")

            except Exception as e:
                print(f"⚠️ Error guardando AUTORIZADO: {e}")
        else:
            print("❌ Estado no apto para guardar como AUTORIZADO.")


# ================================
# MAIN: FACTURAS + NOTAS DE CRÉDITO
# ================================
def main():
    base = os.getcwd()

    # ----- FACTURAS -----
    carpeta_firmados = os.path.join(base, "FIRMADOS")
    carpeta_autorizados = os.path.join(base, "AUTORIZADOS")
    procesar_carpeta_firmados(carpeta_firmados, carpeta_autorizados)

    # ----- NOTAS DE CRÉDITO -----
    carpeta_firmados_nc = os.path.join(base, "FIRMADOS_NC")
    carpeta_autorizados_nc = os.path.join(base, "AUTORIZADOS_NC")
    procesar_carpeta_firmados(carpeta_firmados_nc, carpeta_autorizados_nc)


if __name__ == "__main__":
    main()