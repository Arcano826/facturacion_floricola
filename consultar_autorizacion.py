# consultar_autorizacion.py
# -*- coding: utf-8 -*-
from zeep import Client, Settings
from zeep.transports import Transport

def consultar_autorizacion(clave_acceso, ambiente="1", timeout=30):
    """
    Consulta si un comprobante fue autorizado por el SRI.

    Retorna: (estado, mensaje, autorizaciones) -> Ej: ('AUTORIZADO', '...', [autorizacion_xml_str, ...])
    """
    try:
        if ambiente not in ("1", "2"):
            raise ValueError("Ambiente debe ser '1' (pruebas) o '2' (producción)")

        wsdl_url = (
            "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
            if ambiente == "1" else
            "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
        )

        settings = Settings(strict=False, xml_huge_tree=True)
        transport = Transport(timeout=timeout, operation_timeout=timeout)
        client = Client(wsdl_url, settings=settings, transport=transport)

        response = client.service.autorizacionComprobante(clave_acceso)

        autorizaciones = []
        if hasattr(response, "autorizaciones") and response.autorizaciones:
            for a in response.autorizaciones.autorizacion:
                autorizaciones.append(str(a.comprobante))
            estado = response.autorizaciones.autorizacion[0].estado
            mensaje = f"{estado}"

        return (estado, mensaje, autorizaciones)

    except Exception as e:
        return ("ERROR", str(e), [])