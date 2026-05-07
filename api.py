from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
import sys
import io

from Generador_de_XML_a_Excel import procesar_excel_automatico
from guardar_autorizados import main as procesar_autorizados

# --- MEJORA DE INTERFAZ SWAGGER ---
descripcion_api = """
### API REST para el Sistema Distribuido "Endless" 🌸
Este microservicio orquesta la **ingesta de datos de exportación (DAE)**, la generación asíncrona de comprobantes XML y la comunicación segura con los **Web Services del SRI**.

* **Módulo 1:** Conciliación y Firma Electrónica.
* **Módulo 2:** Sincronización y Autorización SRI.
"""

app = FastAPI(
    title="SISTEMA DISTRIBUIDO ENDLESS",
    description=descripcion_api,
    version="1.0.0",
    contact={
        "name": "Jeremy Burgos Pazmiño",
        "url": "https://github.com/",
    },
    openapi_tags=[
        {"name": "Procesamiento Core", "description": "Carga de Excel y generación de facturas XML."},
        {"name": "Sincronización SRI", "description": "Comunicación con el Web Service del Gobierno."}
    ]
)
UPLOAD_DIR = "UPLOADS"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Ahora, en tus rutas, añade el parámetro "tags" para que se organicen bonito:

@app.post("/api/conciliar-facturar", tags=["Procesamiento Core"])
async def subir_y_procesar_excel(
    file_excel: UploadFile = File(...), 
    file_p12: UploadFile = File(...), 
    password_p12: str = Form(...),
    # Datos Fijos de la Finca
    razon_social: str = Form("CANDO CHANGO TATIANA ELIZABETH"),
    ruc_finca: str = Form("0503847147001"),
    establecimiento: str = Form("001"),
    punto_emision: str = Form("002"),
    direccion_matriz: str = Form("COTOPAXI / SAQUISILI / CHANTILIN / SAN FRANCISCO S/N"),
    es_exportador: bool = Form(True, description="¿Agregar leyenda de EXPORTADOR HABITUAL DE BIENES?"),
    # Puertos por defecto (Cambiables desde la web)
    lugar_incoterm: str = Form("QUITO", description="Lugar IncoTerm por defecto"),
    puerto_embarque: str = Form("QUITO", description="Puerto de Embarque por defecto"),
    # Switches
    incluir_direccion_comprador: bool = Form(False, description="¿Incluir Dirección del Comprador?"),
    es_rimpe: bool = Form(False, description="¿Es contribuyente RIMPE?")
):
    if not file_excel.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .xlsx")
    if not file_p12.filename.endswith('.p12'):
        raise HTTPException(status_code=400, detail="El archivo de firma debe ser un .p12")

    # Guardar el Excel subido
    excel_path = os.path.join(UPLOAD_DIR, file_excel.filename)
    with open(excel_path, "wb") as buffer:
        shutil.copyfileobj(file_excel.file, buffer)

    # Guardar la Firma .p12 subida
    p12_path = os.path.join(UPLOAD_DIR, file_p12.filename)
    with open(p12_path, "wb") as buffer:
        shutil.copyfileobj(file_p12.file, buffer)

    captura_consola = io.StringIO()
    salida_original = sys.stdout
    sys.stdout = captura_consola
    config_finca = {
        "razonSocial": razon_social,
        "nombreComercial": razon_social,
        "ruc": ruc_finca,
        "estab": establecimiento,
        "ptoEmi": punto_emision,
        "dirMatriz": direccion_matriz,
        "esExportador": es_exportador, # Pasamos el switch al generador
        "lugarIncoTerm": lugar_incoterm,
        "puertoEmbarque": puerto_embarque,
        "ambiente": "2",
        "tipoEmision": "1"
    }

    try:
        procesar_excel_automatico(
            excel_path, p12_path, password_p12, 
            config_finca, incluir_direccion_comprador, es_rimpe
        )
    except Exception as e:
        print(f"Error crítico durante procesamiento: {str(e)}")
    finally:
        sys.stdout = salida_original

    log_limpio = [linea for linea in captura_consola.getvalue().split("\n") if linea.strip()]
    return JSONResponse(content={
        "mensaje": "Procesamiento y Firma Finalizado.",
        "archivo_procesado": file_excel.filename,
        "detalles_consola": log_limpio
    })

@app.get("/api/sincronizar-sri", tags=["Sincronización SRI"], summary="Enviar documentos firmados al SRI")
async def sincronizar_autorizados():
    # TRUCO: Capturar prints del proceso de SRI
    captura_consola = io.StringIO()
    salida_original = sys.stdout
    sys.stdout = captura_consola

    try:
        procesar_autorizados()
    except Exception as e:
        print(f"Error crítico enviando al SRI: {str(e)}")
    finally:
        sys.stdout = salida_original

    log_limpio = [linea for linea in captura_consola.getvalue().split("\n") if linea.strip()]

    return JSONResponse(content={
        "mensaje": "Proceso de Sincronización con el SRI ejecutado.",
        "detalles_consola": log_limpio
    })