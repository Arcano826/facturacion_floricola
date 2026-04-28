-- Script de inicialización para MySQL
CREATE TABLE IF NOT EXISTS conciliacion_dae (
    id INT AUTO_INCREMENT PRIMARY KEY,
    num_factura VARCHAR(50) NOT NULL,
    cliente VARCHAR(100),
    tallos DECIMAL(10, 2),
    precio_unitario DECIMAL(10, 6),
    estado_sri VARCHAR(20) DEFAULT 'PENDIENTE',
    fecha_emision DATE
);

CREATE TABLE IF NOT EXISTS bitacora_sri (
    id INT AUTO_INCREMENT PRIMARY KEY,
    factura_id INT,
    clave_acceso VARCHAR(100),
    mensaje_error TEXT,
    fecha_intento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (factura_id) REFERENCES conciliacion_dae(id)
);