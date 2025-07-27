#!/bin/bash

# Configurar rutas
SCRIPT_DIR=$(dirname "$0")
BACKUP_SCRIPT="$SCRIPT_DIR/backup_database.py"
CLEAN_SCRIPT="$SCRIPT_DIR/clean_database.py"
COMPARE_SCRIPT="$SCRIPT_DIR/compare_with_models.py"
CORRECTIONS_SCRIPT="$SCRIPT_DIR/run_corrections.py"
VERIFICATION_SCRIPT="$SCRIPT_DIR/run_verification.sh"

# Nueva función para limpieza interactiva
run_cleanup() {
    echo "🧹 Limpiando archivos antiguos..."
    python -u "$CLEANUP_SCRIPT" --interactive  # Added -u for unbuffered output
}

# Configurar rutas (añadir al inicio)
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup_files.py"

# Función para verificar si hay correcciones disponibles
corrections_available() {
    results_dir="$SCRIPT_DIR/results"
    [ -n "$(find "$results_dir" -name '*_corrections.sql' -mtime -1)" ]
}

# Menú principal
while true; do
    echo ""
    echo "🛠️  Gestor de Base de Datos"
    echo "1. Crear respaldo completo"
    echo "2. Limpiar tablas del sistema"
    echo "3. Verificar esquema"
    echo "4. Comparar con modelos de Django"
    
    # Mostrar opción de correcciones solo si están disponibles
    if corrections_available; then
        echo "5. 🔧 Aplicar correcciones (disponible)"
        CORRECTIONS_ENABLED=true
    else
        echo "5. Aplicar correcciones (no disponible)"
        CORRECTIONS_ENABLED=false
    fi
    
    echo "6. 🧹 Limpiar archivos antiguos"  # Nueva opción
    echo "7. Salir"  # Actualizar número de salida
    echo ""

    read -p "Selecciona una opción: " choice

    case $choice in
        1)
            echo "⏳ Creando respaldo..."
            python $BACKUP_SCRIPT
            ;;
        2)
            echo "⚠️  ADVERTENCIA: Esto borrará datos de tablas del sistema"
            python $CLEAN_SCRIPT
            ;;
        3)
            echo "⏳ Ejecutando verificación..."
            $VERIFICATION_SCRIPT
            ;;
        4)
            echo "🔍 Comparando base de datos con modelos..."
            python $COMPARE_SCRIPT
            ;;
        5)
            if $CORRECTIONS_ENABLED; then
                echo "🔧 Aplicando correcciones..."
                python $CORRECTIONS_SCRIPT
            else
                echo "❌ No hay correcciones disponibles. Ejecuta primero la comparación."
            fi
            ;;
        6)
            run_cleanup
            ;;
        7)
            echo "👋 Hasta luego!"
            exit 0
            ;;
        *)
            echo "❌ Opción inválida"
            ;;
    esac
    
    # Pausa para continuar
    read -p "Presiona Enter para continuar..."
done 