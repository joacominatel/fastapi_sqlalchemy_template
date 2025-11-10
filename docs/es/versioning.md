# Versionado Automático con Hatch-VCS

Este proyecto utiliza **Hatch-VCS** para derivar automáticamente los números de versión desde las etiquetas (tags) de Git, eliminando la necesidad de gestión manual de versiones y asegurando consistencia en todos los entornos.

## Descripción General

**Hatch-VCS** es un plugin de gestión de versiones para Hatch que se integra con sistemas de control de versiones (Git, Mercurial) para determinar automáticamente la versión del proyecto basándose en las etiquetas y commits del repositorio.

### Beneficios

- **Fuente única de verdad**: La versión se deriva de las etiquetas Git, sin actualizaciones manuales
- **Consistencia**: Misma versión en desarrollo, Docker, CI/CD y producción
- **Automatización**: No es necesario editar archivos `.env` ni codificar versiones manualmente
- **Trazabilidad**: La versión corresponde directamente al historial de Git

## Cómo Funciona

### Prioridad de Resolución de Versión

La aplicación determina su versión en el siguiente orden:

1. **Variable de Entorno** (`APP_VERSION`): Usada en entornos Docker/CI
2. **Metadatos del Paquete**: Obtenidos vía `importlib.metadata` (gestionado por Hatch-VCS)
3. **Fallback de Desarrollo**: Retorna `0.0.0-dev` para commits sin etiquetar

### Formato de Versión

Hatch-VCS sigue el versionado [PEP 440](https://peps.python.org/pep-0440/):

- **Release etiquetado**: `1.2.3` (desde tag `v1.2.3` o `1.2.3`)
- **Versión de desarrollo**: `1.2.3.dev4+g1234567` (4 commits después del tag v1.2.3)
- **Sin etiqueta**: `0.0.0-dev` (fallback)

## Configuración

### pyproject.toml

El proyecto está configurado para usar Hatch-VCS para versionado dinámico:

```toml
[project]
name = "fastapi-template"
dynamic = ["version"]  # La versión se determina dinámicamente

[tool.hatch.version]
source = "vcs"  # Usar sistema de control de versiones

[tool.hatch.build.hooks.vcs]
version-file = "app/_version.py"  # Generar archivo de versión durante build

[tool.hatch.build.targets.sdist]
include = ["app", "main.py", "pyproject.toml", "README.md", "alembic", "alembic.ini"]
```

### Código de la Aplicación

La obtención de versión está centralizada en `app/core/version.py`:

```python
from importlib.metadata import version, PackageNotFoundError
import os

def get_app_version() -> str:
    # Verificar variable de entorno primero
    env_version = os.getenv("APP_VERSION")
    if env_version:
        return env_version
    
    # Intentar obtener desde metadatos del paquete (Hatch-VCS)
    try:
        return version("fastapi-template")
    except PackageNotFoundError:
        return "0.0.0-dev"
```

La versión se expone a través de:
- **Settings**: `from app.core.config import settings; settings.VERSION`
- **Endpoint Health**: `GET /api/health` retorna `{"version": "1.2.3", ...}`

## Uso

### Crear un Nuevo Release

1. **Confirmar los cambios**:
   ```bash
   git add .
   git commit -m "feat: implementar nueva funcionalidad"
   ```

2. **Crear y enviar una etiqueta de versión**:
   ```bash
   # Crear una etiqueta anotada (recomendado)
   git tag -a v1.2.3 -m "Release versión 1.2.3"
   
   # O una etiqueta ligera
   git tag v1.2.3
   
   # Enviar la etiqueta al remoto
   git push origin v1.2.3
   ```

3. **Verificar la versión**:
   ```bash
   # Verificar que Hatch-VCS detecta la versión
   uv run hatch version
   # Salida: 1.2.3
   ```

### Flujo de Trabajo de Desarrollo

#### Desarrollo Local

Al trabajar en commits sin etiquetar:

```bash
# Iniciar el servidor de desarrollo
uvicorn main:app --reload

# Verificar versión en otra terminal
curl http://localhost:8000/api/health
# Salida: {"status": "ok", "version": "0.0.0-dev", ...}
```

Después de crear una etiqueta:

```bash
git tag v1.0.0
uv run hatch version
# Salida: 1.0.0

# Reiniciar el servidor
uvicorn main:app --reload

curl http://localhost:8000/api/health
# Salida: {"status": "ok", "version": "1.0.0", ...}
```

#### Build Docker

Construir imágenes Docker con propagación de versión:

```bash
# Obtener la etiqueta Git actual
GIT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0-dev")

# Construir con versión
docker build --build-arg APP_VERSION=$GIT_TAG -t fastapi-template:$GIT_TAG .

# Ejecutar el contenedor
docker run -p 8000:8000 fastapi-template:$GIT_TAG

# Verificar versión
curl http://localhost:8000/api/health
# Salida: {"status": "ok", "version": "1.0.0", ...}
```

### Integración CI/CD

#### Ejemplo con GitHub Actions

```yaml
name: Build and Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Obtener todo el historial para etiquetas
      
      - name: Obtener versión desde tag
        id: version
        run: |
          VERSION=$(git describe --tags --always)
          echo "VERSION=${VERSION}" >> $GITHUB_ENV
          echo "Versión: ${VERSION}"
      
      - name: Construir imagen Docker
        run: |
          docker build \
            --build-arg APP_VERSION=${{ env.VERSION }} \
            -t fastapi-template:${{ env.VERSION }} \
            .
      
      - name: Probar endpoint de versión
        run: |
          docker run -d -p 8000:8000 --name test-app fastapi-template:${{ env.VERSION }}
          sleep 5
          RESPONSE=$(curl -s http://localhost:8000/api/health)
          echo "Respuesta health: $RESPONSE"
          docker stop test-app
```

#### Ejemplo con GitLab CI

```yaml
variables:
  APP_VERSION: ""

before_script:
  - export APP_VERSION=$(git describe --tags --always)
  - echo "Construyendo versión $APP_VERSION"

build:
  stage: build
  script:
    - docker build --build-arg APP_VERSION=$APP_VERSION -t $CI_REGISTRY_IMAGE:$APP_VERSION .
    - docker push $CI_REGISTRY_IMAGE:$APP_VERSION
  only:
    - tags
```

## Acceder a la Versión

### En Código Python

```python
from app.core.config import settings

# Obtener versión
version = settings.VERSION
print(f"Ejecutando versión: {version}")
```

### Vía API

```bash
# Endpoint health
curl http://localhost:8000/api/health

# Respuesta
{
  "status": "ok",
  "app": "FastAPI Template",
  "version": "1.2.3",
  "environment": "production"
}
```

### En Docker

```bash
# Verificar versión en contenedor en ejecución
docker exec <container_id> printenv APP_VERSION

# O vía Python
docker exec <container_id> uv run python -c "from app.core.config import settings; print(settings.VERSION)"
```

## Solución de Problemas

### Problema: La versión muestra "0.0.0-dev" inesperadamente

**Causas**:
- No hay etiquetas Git en el repositorio
- Clon superficial (falta historial Git)
- Paquete no instalado en modo editable

**Soluciones**:
```bash
# Verificar si existen etiquetas
git tag -l

# Crear una etiqueta si no existe ninguna
git tag v0.1.0

# Para CI: asegurar clon completo
git fetch --unshallow
git fetch --tags

# Verificar que Hatch-VCS puede leer la versión
uv run hatch version
```

### Problema: "PackageNotFoundError: No package metadata"

**Causa**: Paquete no instalado o no en modo editable

**Solución**:
```bash
# Instalar en modo editable con uv
uv pip install -e .

# O sincronizar el proyecto
uv sync
```

### Problema: La versión en Docker no coincide con el tag Git

**Causa**: No se pasó el argumento de build `APP_VERSION`

**Solución**:
```bash
# Siempre pasar el argumento de build
docker build --build-arg APP_VERSION=$(git describe --tags) -t myapp .
```

### Problema: Clones superficiales en CI/CD faltan etiquetas

**Causa**: Historial Git no obtenido en entorno CI

**Solución (GitHub Actions)**:
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Obtener historial completo
```

**Solución (GitLab CI)**:
```yaml
variables:
  GIT_DEPTH: 0  # Deshabilitar clon superficial
```

## Estrategias de Versionado

### Versionado Semántico

Seguir los principios de [SemVer](https://semver.org/):

- **MAJOR** (`1.0.0` → `2.0.0`): Cambios que rompen compatibilidad
- **MINOR** (`1.0.0` → `1.1.0`): Nuevas funcionalidades, retrocompatibles
- **PATCH** (`1.0.0` → `1.0.1`): Correcciones de errores

```bash
# Cambio que rompe compatibilidad
git tag v2.0.0 -m "feat!: rediseño de API (breaking)"

# Nueva funcionalidad
git tag v1.1.0 -m "feat: agregar autenticación de usuarios"

# Corrección de error
git tag v1.0.1 -m "fix: corregir manejo de zona horaria"

git push --tags
```

### Versiones Pre-release

Para versiones alpha, beta, o release candidates:

```bash
# Release alpha
git tag v2.0.0-alpha.1 -m "Release versión alpha"

# Release beta
git tag v2.0.0-beta.1 -m "Release versión beta"

# Release candidate
git tag v2.0.0-rc.1 -m "Release candidate"

git push --tags
```

## Mejores Prácticas

1. **Usar siempre etiquetas anotadas**: `git tag -a v1.0.0 -m "mensaje"` (almacena autor, fecha, mensaje)
2. **Seguir versionado semántico**: Hace el historial de versiones predecible
3. **Etiquetar después de builds CI exitosos**: Asegurar que las pruebas pasan antes de etiquetar
4. **No eliminar etiquetas publicadas**: Rompe el historial de versiones
5. **Usar `fetch-depth: 0` en CI**: Asegura que todas las etiquetas estén disponibles
6. **Documentar cambios que rompen compatibilidad**: En mensajes de etiquetas y CHANGELOG

## Integración con Otras Herramientas

### Migraciones Alembic

Etiquetar releases después de generar migraciones:

```bash
# Generar migración
alembic revision --autogenerate -m "agregar roles de usuario"
alembic upgrade head

# Probar migración
pytest

# Etiquetar release
git tag v1.1.0 -m "feat: agregar sistema de roles de usuario"
git push origin v1.1.0
```

### Generación de Changelog

Usar herramientas como `git-cliff` o `conventional-changelog`:

```bash
# Instalar git-cliff
cargo install git-cliff

# Generar changelog desde etiquetas
git-cliff > CHANGELOG.md
```

## Referencias

- [Documentación Hatch-VCS](https://github.com/ofek/hatch-vcs)
- [Sistema de Build Hatch](https://hatch.pypa.io/)
- [PEP 440 – Identificación de Versiones](https://peps.python.org/pep-0440/)
- [Versionado Semántico](https://semver.org/)
- [Fundamentos de Etiquetado Git](https://git-scm.com/book/es/v2/Fundamentos-de-Git-Etiquetado)
