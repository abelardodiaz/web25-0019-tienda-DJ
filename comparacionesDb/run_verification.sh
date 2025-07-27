#!/bin/bash

# Activar entorno virtual
source ../venv/bin/activate

# Ejecutar verificación completa
echo "Ejecutando verificación de esquema..."
python verify_db_schema.py

echo ""

# Ejecutar verificación de IDs
echo "Ejecutando verificación de IDs..."
python verify_ids.py

echo ""

# Generar reporte interpretado
echo "Generando reporte interpretado..."
python interpret_results.py

echo ""
echo "Proceso completo! Verifica los archivos en comparacionesDb/results" 