## Gestión de Base de Datos

### Flujo de trabajo completo:
1. **Comparar**: Ejecuta la comparación con modelos (Opción 4)
2. **Verificar**: Revisa el reporte de diferencias
3. **Corregir**: Si hay diferencias, aplica correcciones (Opción 5)
4. **Respaldar**: Crea un backup antes de cambios importantes (Opción 1)

### Características del menú:
- **Persistente**: Permanece activo hasta seleccionar "Salir"
- **Inteligente**: 
  - La opción de correcciones solo está habilitada cuando hay diferencias detectadas
  - Muestra estado claro (disponible/no disponible)
- **Seguro**: 
  - Siempre pide confirmación para operaciones críticas
  - Recomienda respaldos antes de cambios

### Scripts disponibles:
1. `db_manager.sh` - Menú principal para todas las operaciones
```bash
./db_manager.sh
```

2. `compare_with_models.py` - Compara la BD con modelos Django
```bash
python compare_with_models.py
```

### Características de la comparación:
- Detecta tablas faltantes/extra
- Identifica diferencias en campos:
  - Tipos de datos
  - Nulabilidad
  - Campos faltantes/extra
- Genera:
  - Reporte JSON con diferencias detalladas
  - Script SQL con correcciones

### Carpetas:
- `respaldos/` - Almacena backups SQL
- `results/` - Almacena reportes de verificación y comparación

### Función de limpieza mejorada (Opción 6):
- **Modo interactivo**:
  1. Selecciona qué archivos limpiar:
     - Respaldos de base de datos
     - Resultados de verificaciones
     - Reportes de comparaciones
     - Todos los anteriores
  2. Configura:
     - Antigüedad mínima (días)
     - Archivos recientes a conservar
- **Modo automático**:
  - Usa políticas predeterminadas:
    | Categoría         | Patrones de archivos                     | Conservar | Eliminar después |
    |-------------------|------------------------------------------|-----------|------------------|
    | Respaldos         | `*.sql`                                  | 5 files   | 30 días          |
    | Verificaciones    | `schema_verification_*.json`, `id_verification_*.json` | 5 files   | 15 días          |
    | Comparaciones     | `comparison_report_*.json`, `*_corrections.sql` | 5 files   | 15 días          |
