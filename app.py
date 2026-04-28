from Generador_de_XML_a_Excel import main
from generador_notas_de_credito import main_nc
from guardar_autorizados import main as procesar_autorizados

if __name__ == "__main__":
    print("\n=== SISTEMA DE FACTURACIÓN ELECTRÓNICA ===")
    print("1. Generar FACTURAS (XML + firmar)")
    print("2. Generar NOTAS DE CRÉDITO (XML + firmar)")
    print("3. Enviar TODO lo firmado al SRI y guardar AUTORIZADOS (FACTURAS + NC)")

    opcion = input("Seleccione una opción: ").strip()

    if opcion == "1":
        main()
    elif opcion == "2":
        main_nc()
    elif opcion == "3":
        procesar_autorizados()   # llama al main() de guardar_autorizados.py
    else:
        print("Opción inválida.")