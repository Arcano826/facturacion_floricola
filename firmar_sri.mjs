import fs from 'fs';
import path from 'path';
import { signInvoiceXml, signCreditNoteXml } from 'ec-sri-invoice-signer';

async function main() {
  // Ahora recibimos 5 parámetros
  const [, , tipo, xmlPath, outPath, p12Path, p12Password] = process.argv;

  if (!tipo || !xmlPath || !outPath || !p12Path || !p12Password) {
    console.error('Uso: node firmar_sri.mjs <factura|nc> <xmlEntrada> <xmlSalida> <ruta_p12> <contraseña>');
    process.exit(1);
  }

  if (!fs.existsSync(p12Path)) {
    console.error("ERROR: No se encontró el archivo de firma en la ruta especificada:", p12Path);
    process.exit(1);
  }

  const xml = fs.readFileSync(xmlPath, 'utf8');
  const p12Data = fs.readFileSync(p12Path);

  let signedXml;

  if (tipo === 'factura') {
    signedXml = signInvoiceXml(xml, p12Data, { pkcs12Password: p12Password });
  } else if (tipo === 'nc') {
    signedXml = signCreditNoteXml(xml, p12Data, { pkcs12Password: p12Password });
  } else {
    console.error('Tipo inválido. Usa: factura o nc');
    process.exit(1);
  }

  fs.writeFileSync(outPath, signedXml, 'utf8');
  console.log('XML firmado correctamente →', outPath);
}

main().catch(err => {
  console.error('ERROR FIRMANDO:', err);
  process.exit(1);
});