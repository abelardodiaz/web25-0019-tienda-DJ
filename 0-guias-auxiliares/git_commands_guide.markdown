# Guía de Comandos Git para Gestionar Versiones del Proyecto web25-0019-tienda-DJ

Este instructivo resume los comandos Git utilizados para gestionar las versiones 0.2.2, 0.2.3 y 0.2.4 del proyecto, creando ramas como puntos de control ("checkpoints"), actualizando la rama `main`, y marcando versiones con tags. Los comandos están organizados por tarea y son aplicables al repositorio `https://github.com/abelardodiaz/web25-0019-tienda-DJ`.

## 1. Verificar el Estado del Repositorio
Comandos para inspeccionar ramas, commits y estado actual.

- **Ver ramas locales y sus commits**:
  ```bash
  git branch -v
  ```
  Muestra las ramas locales y el commit al que apuntan (por ejemplo, `main`, `version-0.2.2`).

- **Ver historial de commits**:
  ```bash
  git log --oneline
  ```
  Muestra el historial de commits en una línea, útil para confirmar versiones (por ejemplo, `eab711e` para 0.2.4).

- **Ver estado del directorio**:
  ```bash
  git status
  ```
  Indica si hay cambios sin guardar y si la rama está atrasada respecto al remoto (por ejemplo, "behind 2").

- **Ver historial del remoto**:
  ```bash
  git fetch origin
  git log origin/main --oneline
  ```
  Actualiza datos del remoto y muestra el historial de `origin/main`.

- **Ver tags locales**:
  ```bash
  git tag
  ```
  Lista los tags creados (por ejemplo, `v0.2.2`, `v0.2.3`, `v0.2.4`).

## 2. Eliminar Rama Incorrecta
Eliminamos la rama `version-0.2.3` creada por error.

- **Eliminar rama local**:
  ```bash
  git branch -d version-0.2.3
  ```
  Usa `-d` para ramas fusionadas. Si no está fusionada, usa:
  ```bash
  git branch -D version-0.2.3
  ```

## 3. Crear Ramas como Puntos de Control
Creamos ramas para las versiones 0.2.2, 0.2.3 y 0.2.4, y las subimos a GitHub.

- **Crear y subir rama `version-0.2.2`** (commit `eb9646f`):
  ```bash
  git branch version-0.2.2
  git push origin version-0.2.2
  ```
  Apunta a `eb9646f` ("0.2.2 fixes en busqueda instantanea full y movil").

- **Crear y subir rama `version-0.2.3`** (commit `e49cb19`):
  ```bash
  git fetch origin
  git branch version-0.2.3 e49cb19
  git push origin version-0.2.3
  ```
  Apunta a `e49cb19` ("0.2.3 fixes en add canasta productos en firefox y edge").

- **Crear y subir rama `version-0.2.4`** (commit `eab711e`):
  ```bash
  git branch version-0.2.4 eab711e
  git push origin version-0.2.4
  ```
  Apunta a `eab711e` ("0.2.4 registro y login, con validacion por whatsaap API modo SANDBOX").

- **Verificar ramas creadas**:
  ```bash
  git branch -v
  ```
  Confirma que las ramas apuntan a los commits correctos.

- **Verificar en GitHub**:
  Visita `https://github.com/abelardodiaz/web25-0019-tienda-DJ/branches` para confirmar que las ramas están presentes.

## 4. Actualizar la Rama `main` a la Versión 0.2.4
Actualizamos `main` al commit `eab711e` (versión 0.2.4).

- **Verificar cambios sin guardar**:
  ```bash
  git status
  ```
  Si hay cambios, confírmalos:
  ```bash
  git add .
  git commit -m "Guardando cambios locales antes de actualizar a 0.2.4"
  ```
  O guárdalos temporalmente:
  ```bash
  git stash
  ```

- **Actualizar `main`**:
  ```bash
  git checkout main
  git pull origin main
  ```

- **Confirmar actualización**:
  ```bash
  git log --oneline
  ```
  Verifica que `eab711e` es el commit más reciente en `main`.

## 5. Crear y Subir Tags para Versiones
Marcamos las versiones con tags para puntos de control permanentes.

- **Crear tags**:
  ```bash
  git tag v0.2.2 eb9646f
  git tag v0.2.3 e49cb19
  git tag v0.2.4 eab711e
  ```

- **Subir tags a GitHub**:
  ```bash
  git push origin v0.2.2 v0.2.3 v0.2.4
  ```

- **Verificar tags**:
  ```bash
  git tag
  ```
  Confirma que los tags existen localmente. Revisa `https://github.com/abelardodiaz/web25-0019-tienda-DJ/tags` para verlos en GitHub.

## 6. Cambiar Entre Versiones
Comandos para moverte entre versiones usando ramas o tags.

- **Cambiar a una rama**:
  ```bash
  git checkout version-0.2.2  # o version-0.2.3, version-0.2.4
  ```

- **Cambiar a un tag** (crea un estado "detached HEAD"):
  ```bash
  git checkout v0.2.2  # o v0.2.3, v0.2.4
  ```

- **Crear una rama temporal desde un tag** (si necesitas trabajar en él):
  ```bash
  git checkout -b temp-v0.2.2 v0.2.2
  ```

- **Volver a `main`**:
  ```bash
  git checkout main
  ```

## 7. Verificar Cambios en una Versión
Comandos para inspeccionar el código o cambios en una versión específica.

- **Ver cambios en un commit**:
  ```bash
  git show eab711e  # Ejemplo para 0.2.4
  ```

- **Ver un archivo en una rama o commit**:
  ```bash
  git show version-0.2.4:users/views.py  # Ejemplo para un archivo específico
  ```

## 8. Probar la Aplicación Django
Comandos para verificar que la versión funciona correctamente.

- **Iniciar el servidor Django**:
  ```bash
  python manage.py runserver 8009
  ```
  Accede a `http://127.0.0.1:8009/` para probar funcionalidades (por ejemplo, login, registro, WhatsApp API en 0.2.4).

## 9. Manejo de Posibles Conflictos
Si `git pull` genera conflictos:

- **Resolver manualmente**:
  Edita los archivos conflictivos, luego:
  ```bash
  git add .
  git commit
  ```

- **Descartar cambios locales** (si no son importantes):
  ```bash
  git reset --hard origin/main
  ```
  **Precaución**: Esto elimina cambios no confirmados en `main`.

## 10. Opcional: Agregar un Archivo `VERSION`
Si quieres un archivo explícito para rastrear la versión:

- **Crear archivo `VERSION`**:
  ```bash
  echo "0.2.4" > VERSION
  git add VERSION
  git commit -m "Agregar archivo VERSION para 0.2.4"
  git push origin main
  ```

- **Verificar versión**:
  ```bash
  cat VERSION
  ```

## 11. Limpieza de Ramas (Opcional)
Si las ramas ya no son necesarias (porque los tags preservan las versiones):

- **Eliminar rama local**:
  ```bash
  git branch -d version-0.2.2
  ```

- **Eliminar rama remota**:
  ```bash
  git push origin --delete version-0.2.2
  ```

## Notas
- **Ramas como checkpoints**: Las ramas `version-0.2.2`, `version-0.2.3`, y `version-0.2.4` funcionan como puntos de control. Los tags `v0.2.2`, `v0.2.3`, y `v0.2.4` son más ligeros y estándar para versiones estables.
- **GitHub**: Las ramas y tags están en `https://github.com/abelardodiaz/web25-0019-tienda-DJ`.
- **Advertencias Django**:
  - Si ves `Not Found: /favicon.ico`, agrega un favicon en `static/favicon.ico`.
  - Si ves `NoCssSanitizerWarning` de `bleach`, considera configurar `BLEACH_CSS_SANITIZER = True` en `settings.py`.