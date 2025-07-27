#!/bin/bash

# Get absolute path of the project root
PROJECT_ROOT=$(cd $(dirname "${BASH_SOURCE[0]}")/.. && pwd)

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

# Output directory
OUTPUT_DIR="$PROJECT_ROOT/comparacionesDb/results/schema_inspection"
mkdir -p "$OUTPUT_DIR"

# List of tables to inspect
TABLES=(
    "products_brand"
    "products_category"
    "products_price"
    "products_product"
    "users_customuser"
)

# Run DESCRIBE for each table
for TABLE in "${TABLES[@]}"; do
    echo "Inspecting table: $TABLE"
    echo "DESCRIBE $TABLE;" | python "$PROJECT_ROOT/manage.py" dbshell > "$OUTPUT_DIR/${TABLE}_describe.txt"
    echo "SHOW CREATE TABLE $TABLE;" | python "$PROJECT_ROOT/manage.py" dbshell > "$OUTPUT_DIR/${TABLE}_create_table.txt"
done

echo "✅ Schema inspection complete. Results saved to $OUTPUT_DIR" 