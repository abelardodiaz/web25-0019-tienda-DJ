


### #################################
######    CREDENCIALES
### ###############################-#

DB_USER=web25017_0004_us
DB_PASSWORD="xCgtrfRe53$3a#2xz99xh"
DB_NAME=web25017_0004_db

### #################################
### ###    CONEXION ROOT
### ###############################-#

mysql -u root -p


### #################################
### ###    ELIMINAR BD
### ###############################-#

    DROP DATABASE web25017_0005_db;


### #################################
### ###    CHECAR SI EXISTE USUARIO
### ###############################-#
SELECT User, Host FROM mysql.user WHERE User = 'web25017_0005_us';

### #################################
### ###    ELIMINAR USUARIO
### ################################
DROP USER 'web25017_0005_us'@'localhost';
DROP USER 'web25017_0005_us'@'%';
FLUSH PRIVILEGES;

### #################################
######    CREAR BD
### ################################
CREATE DATABASE web25017_0005_db;

### #################################
### ###    crear el usuario y darle permisos en la BD, solo con CONEXION LOCALCREAR BD
### ################################

CREATE USER 'web25017_0005_us'@'localhost' IDENTIFIED BY 'xCgtrfRe53$3a#2xz99xh';
GRANT ALL PRIVILEGES ON web25017_0005_db.* TO 'web25017_0005_us'@'localhost';
FLUSH PRIVILEGES;

### #################################
### ###  crear el usuario y darle permisos en la BD, INCLUYE  CONEXIONES REMOTAS
### ##################################
CREATE USER 'web25017_0005_us'@'%' IDENTIFIED BY 'xCgtrfRe53$3a#2xz99xh';
GRANT ALL PRIVILEGES ON web25017_0005_db.* TO 'web25017_0005_us'@'%';
FLUSH PRIVILEGES;

### #################################
### ###   MOSTRAR TABLAS PARA LA BD
### ##################################
SHOW TABLES FROM web25017_0005_db;

### #################################
### ###    Listar los campos de todas las tablas especificadas
### ##################################

SELECT 
    'Campos' AS Tipo,
    c.TABLE_NAME AS Tabla,
    c.COLUMN_NAME AS Columna,
    c.DATA_TYPE AS Tipo_Dato,
    c.CHARACTER_MAXIMUM_LENGTH AS Longitud,
    c.IS_NULLABLE AS Es_Nulo,
    c.COLUMN_KEY AS Clave,
    c.COLUMN_DEFAULT AS Valor_Por_Defecto,
    c.EXTRA AS Extra
FROM 
    information_schema.COLUMNS c
WHERE 
    c.TABLE_SCHEMA = 'web25017_0002_db'
    AND c.TABLE_NAME IN (
        'categorias', 
        'exchange_rate', 
        'historial_cambios', 
        'marcas', 
        'product_category', 
        'producto_imagenes', 
        'productos', 
        'syscom_credentials', 
        'users'
    )

UNION ALL

### #################################
### ###    -- Listar las claves foráneas (relaciones)
### ##################################

SELECT 
    'Claves Foráneas' AS Tipo,
    k.TABLE_NAME AS Tabla,
    k.COLUMN_NAME AS Columna,
    k.CONSTRAINT_NAME AS Nombre_Constraint,
    k.REFERENCED_TABLE_NAME AS Tabla_Referenciada,
    k.REFERENCED_COLUMN_NAME AS Columna_Referenciada,
    '' AS Tipo_Dato,
    '' AS Longitud,
    '' AS Extra
FROM 
    information_schema.KEY_COLUMN_USAGE k
WHERE 
    k.TABLE_SCHEMA = 'web25017_0002_db'
    AND k.TABLE_NAME IN (
        'categorias', 
        'exchange_rate', 
        'historial_cambios', 
        'marcas', 
        'product_category', 
        'producto_imagenes', 
        'productos', 
        'syscom_credentials', 
        'users'
    )
    AND k.REFERENCED_TABLE_NAME IS NOT NULL

ORDER BY 
    Tabla, Tipo, Columna;

