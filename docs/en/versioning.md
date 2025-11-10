# Automatic Versioning with Hatch-VCS

This project uses **Hatch-VCS** to automatically derive version numbers from Git tags, eliminating the need for manual version management and ensuring consistency across all environments.

## Overview

**Hatch-VCS** is a version management plugin for Hatch that integrates with version control systems (Git, Mercurial) to automatically determine the project version based on repository tags and commits.

### Benefits

- **Single Source of Truth**: Version is derived from Git tags, no manual updates required
- **Consistency**: Same version across development, Docker, CI/CD, and production
- **Automation**: No need to edit `.env` files or hardcode versions
- **Traceability**: Version directly corresponds to Git history

## How It Works

### Version Resolution Priority

The application determines its version in the following order:

1. **Environment Variable** (`APP_VERSION`): Used in Docker/CI environments
2. **Package Metadata**: Retrieved via `importlib.metadata` (managed by Hatch-VCS)
3. **Development Fallback**: Returns `0.0.0-dev` for untagged commits

### Version Format

Hatch-VCS follows [PEP 440](https://peps.python.org/pep-0440/) versioning:

- **Tagged release**: `1.2.3` (from tag `v1.2.3` or `1.2.3`)
- **Development version**: `1.2.3.dev4+g1234567` (4 commits after tag v1.2.3)
- **Untagged**: `0.0.0-dev` (fallback)

## Configuration

### pyproject.toml

The project is configured to use Hatch-VCS for dynamic versioning:

```toml
[project]
name = "fastapi-template"
dynamic = ["version"]  # Version is dynamically determined

[tool.hatch.version]
source = "vcs"  # Use version control system

[tool.hatch.build.hooks.vcs]
version-file = "app/_version.py"  # Generate version file during build

[tool.hatch.build.targets.sdist]
include = ["app", "main.py", "pyproject.toml", "README.md", "alembic", "alembic.ini"]
```

### Application Code

Version retrieval is centralized in `app/core/version.py`:

```python
from importlib.metadata import version, PackageNotFoundError
import os

def get_app_version() -> str:
    # Check environment variable first
    env_version = os.getenv("APP_VERSION")
    if env_version:
        return env_version
    
    # Try package metadata (Hatch-VCS)
    try:
        return version("fastapi-template")
    except PackageNotFoundError:
        return "0.0.0-dev"
```

The version is exposed through:
- **Settings**: `from app.core.config import settings; settings.VERSION`
- **Health Endpoint**: `GET /api/health` returns `{"version": "1.2.3", ...}`

## Usage

### Creating a New Release

1. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: implement new feature"
   ```

2. **Create and push a version tag**:
   ```bash
   # Create an annotated tag (recommended)
   git tag -a v1.2.3 -m "Release version 1.2.3"
   
   # Or a lightweight tag
   git tag v1.2.3
   
   # Push the tag to remote
   git push origin v1.2.3
   ```

3. **Verify the version**:
   ```bash
   # Check Hatch-VCS detects the version
   uv run hatch version
   # Output: 1.2.3
   ```

### Development Workflow

#### Local Development

When working on untagged commits:

```bash
# Start the development server
uvicorn main:app --reload

# Check version in another terminal
curl http://localhost:8000/api/health
# Output: {"status": "ok", "version": "0.0.0-dev", ...}
```

After creating a tag:

```bash
git tag v1.0.0
uv run hatch version
# Output: 1.0.0

# Restart the server
uvicorn main:app --reload

curl http://localhost:8000/api/health
# Output: {"status": "ok", "version": "1.0.0", ...}
```

#### Docker Build

Build Docker images with version propagation:

```bash
# Get the current Git tag
GIT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0-dev")

# Build with version
docker build --build-arg APP_VERSION=$GIT_TAG -t fastapi-template:$GIT_TAG .

# Run the container
docker run -p 8000:8000 fastapi-template:$GIT_TAG

# Verify version
curl http://localhost:8000/api/health
# Output: {"status": "ok", "version": "1.0.0", ...}
```

### CI/CD Integration

#### GitHub Actions Example

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
          fetch-depth: 0  # Fetch all history for tags
      
      - name: Get version from tag
        id: version
        run: |
          VERSION=$(git describe --tags --always)
          echo "VERSION=${VERSION}" >> $GITHUB_ENV
          echo "Version: ${VERSION}"
      
      - name: Build Docker image
        run: |
          docker build \
            --build-arg APP_VERSION=${{ env.VERSION }} \
            -t fastapi-template:${{ env.VERSION }} \
            .
      
      - name: Test version endpoint
        run: |
          docker run -d -p 8000:8000 --name test-app fastapi-template:${{ env.VERSION }}
          sleep 5
          RESPONSE=$(curl -s http://localhost:8000/api/health)
          echo "Health response: $RESPONSE"
          docker stop test-app
```

#### GitLab CI Example

```yaml
variables:
  APP_VERSION: ""

before_script:
  - export APP_VERSION=$(git describe --tags --always)
  - echo "Building version $APP_VERSION"

build:
  stage: build
  script:
    - docker build --build-arg APP_VERSION=$APP_VERSION -t $CI_REGISTRY_IMAGE:$APP_VERSION .
    - docker push $CI_REGISTRY_IMAGE:$APP_VERSION
  only:
    - tags
```

## Accessing the Version

### In Python Code

```python
from app.core.config import settings

# Get version
version = settings.VERSION
print(f"Running version: {version}")
```

### Via API

```bash
# Health endpoint
curl http://localhost:8000/api/health

# Response
{
  "status": "ok",
  "app": "FastAPI Template",
  "version": "1.2.3",
  "environment": "production"
}
```

### In Docker

```bash
# Check version in running container
docker exec <container_id> printenv APP_VERSION

# Or via Python
docker exec <container_id> uv run python -c "from app.core.config import settings; print(settings.VERSION)"
```

## Troubleshooting

### Issue: Version shows "0.0.0-dev" unexpectedly

**Causes**:
- No Git tags in the repository
- Shallow clone (missing Git history)
- Package not installed in editable mode

**Solutions**:
```bash
# Check if tags exist
git tag -l

# Create a tag if none exist
git tag v0.1.0

# For CI: ensure full clone
git fetch --unshallow
git fetch --tags

# Verify Hatch-VCS can read version
uv run hatch version
```

### Issue: "PackageNotFoundError: No package metadata"

**Cause**: Package not installed or not in editable mode

**Solution**:
```bash
# Install in editable mode with uv
uv pip install -e .

# Or sync the project
uv sync
```

### Issue: Docker version doesn't match Git tag

**Cause**: `APP_VERSION` build argument not passed

**Solution**:
```bash
# Always pass the build argument
docker build --build-arg APP_VERSION=$(git describe --tags) -t myapp .
```

### Issue: CI/CD shallow clones missing tags

**Cause**: Git history not fetched in CI environment

**Solution (GitHub Actions)**:
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Fetch complete history
```

**Solution (GitLab CI)**:
```yaml
variables:
  GIT_DEPTH: 0  # Disable shallow clone
```

## Version Strategies

### Semantic Versioning

Follow [SemVer](https://semver.org/) principles:

- **MAJOR** (`1.0.0` → `2.0.0`): Breaking changes
- **MINOR** (`1.0.0` → `1.1.0`): New features, backward compatible
- **PATCH** (`1.0.0` → `1.0.1`): Bug fixes

```bash
# Breaking change
git tag v2.0.0 -m "feat!: redesign API (breaking)"

# New feature
git tag v1.1.0 -m "feat: add user authentication"

# Bug fix
git tag v1.0.1 -m "fix: correct timezone handling"

git push --tags
```

### Pre-release Versions

For alpha, beta, or release candidates:

```bash
# Alpha release
git tag v2.0.0-alpha.1 -m "Release alpha version"

# Beta release
git tag v2.0.0-beta.1 -m "Release beta version"

# Release candidate
git tag v2.0.0-rc.1 -m "Release candidate"

git push --tags
```

## Best Practices

1. **Always use annotated tags**: `git tag -a v1.0.0 -m "message"` (stores tagger, date, message)
2. **Follow semantic versioning**: Makes version history predictable
3. **Tag after successful CI builds**: Ensure tests pass before tagging
4. **Don't delete published tags**: Breaks version history
5. **Use `fetch-depth: 0` in CI**: Ensures all tags are available
6. **Document breaking changes**: In tag messages and CHANGELOG

## Integration with Other Tools

### Alembic Migrations

Tag releases after generating migrations:

```bash
# Generate migration
alembic revision --autogenerate -m "add user roles"
alembic upgrade head

# Test migration
pytest

# Tag release
git tag v1.1.0 -m "feat: add user role system"
git push origin v1.1.0
```

### Changelog Generation

Use tools like `git-cliff` or `conventional-changelog`:

```bash
# Install git-cliff
cargo install git-cliff

# Generate changelog from tags
git-cliff > CHANGELOG.md
```

## References

- [Hatch-VCS Documentation](https://github.com/ofek/hatch-vcs)
- [Hatch Build System](https://hatch.pypa.io/)
- [PEP 440 – Version Identification](https://peps.python.org/pep-0440/)
- [Semantic Versioning](https://semver.org/)
- [Git Tagging Basics](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
