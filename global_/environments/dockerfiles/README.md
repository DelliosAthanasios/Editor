# Docker Environment Dockerfiles

This folder contains production-ready Dockerfiles for all 10 pre-configured environments.

## File Overview

| File | Language | Base Image | Key Tools |
|------|----------|-----------|-----------|
| `Dockerfile.python-ds` | Python | `python:3.11-slim` | NumPy, Pandas, Jupyter, scikit-learn |
| `Dockerfile.web` | JavaScript/TypeScript | `node:20-alpine` | TypeScript, Express, Yarn, pnpm |
| `Dockerfile.rust` | Rust | `rust:latest` | Cargo, Rust-Analyzer, clippy |
| `Dockerfile.c` | C | `gcc:latest` | GCC, GDB, Make, Valgrind, CMake |
| `Dockerfile.cpp` | C++ | `gcc:latest` | G++, GDB, Make, Clang, CMake |
| `Dockerfile.go` | Go | `golang:1.21-alpine` | Go, Air (hot reload), golangci-lint |
| `Dockerfile.java` | Java | `openjdk:17-slim` | Maven, Gradle, Spring Boot |
| `Dockerfile.ruby` | Ruby | `ruby:3.2-slim` | Rails, Bundler, Node.js |
| `Dockerfile.haskell` | Haskell | `haskell:9.6` | GHC, Stack, hlint |
| `Dockerfile.lisp` | Lisp | `ubuntu:22.04` | SBCL, Quicklisp |

## Why Separate Files?

1. **Easier Testing** - Can build and test individually
2. **Maintainability** - Each Dockerfile is independent
3. **Customization** - Users can easily modify as needed
4. **Version Control** - Track changes per environment
5. **Documentation** - Each file can have its own comments

## How They're Used

In `global_/predefined_environments.py`:

```python
def _load_dockerfile(filename: str) -> str:
    """Load a Dockerfile from the dockerfiles directory"""
    dockerfile_path = os.path.join(
        os.path.dirname(__file__),
        "environments",
        "dockerfiles",
        filename
    )
    with open(dockerfile_path, 'r') as f:
        return f.read()

# Example usage
PYTHON_DATA_SCIENCE = EnvironmentConfig(
    name="Python Data Science",
    dockerfile=_load_dockerfile("Dockerfile.python-ds"),
    ...
)
```

## Testing Dockerfiles

### Test a Single Dockerfile

```bash
cd global_/environments/dockerfiles

# Build
docker build -t editor-python-ds:test -f Dockerfile.python-ds .

# Run
docker run -it editor-python-ds:test /bin/bash

# Inside container, test tools
python --version
jupyter --version
python -c "import numpy; print('NumPy:', numpy.__version__)"

# Cleanup
docker rmi editor-python-ds:test
```

### Test All Dockerfiles

```bash
# Run the automated test
python TEST_SUITE.py
```

## Customizing a Dockerfile

To customize an environment:

1. **Edit the Dockerfile** - Modify `Dockerfile.XXX` directly
2. **Add packages** - Add RUN commands for additional tools
3. **Change base image** - Modify FROM line (carefully)
4. **Set environment** - Add ENV commands
5. **Rebuild** - Next time you create environment, it uses updated version

Example: Adding a Python package to Python Data Science

```dockerfile
# In Dockerfile.python-ds, add:
RUN pip install --no-cache-dir tensorflow
```

## Best Practices

These Dockerfiles follow Docker best practices:

✓ **Minimal base images** - Uses slim/alpine variants
✓ **Layer caching** - Frequently-changed instructions last
✓ **Clean apt cache** - Removes package lists after install
✓ **Single RUN commands** - Combines packages to reduce layers
✓ **Error handling** - Uses `|| true` for optional tools
✓ **Workdir setup** - Creates /workspace for project files
✓ **Port exposure** - EXPOSE only necessary ports
✓ **No root user** - Could add non-root user for security

## Image Sizes

Approximate sizes (first build):

| Image | Size | Time |
|-------|------|------|
| Python Data Science | 800MB | 3-5 min |
| Web Development | 200MB | 2-3 min |
| Rust Workspace | 1.5GB | 4-6 min |
| C Development | 1GB | 3-4 min |
| C++ Modern | 1GB | 3-4 min |
| Go Development | 300MB | 2-3 min |
| Java Enterprise | 500MB | 3-4 min |
| Ruby/Rails | 400MB | 2-3 min |
| Haskell Stack | 2GB | 5-7 min |
| Lisp Machine | 600MB | 2-3 min |

## Common Modifications

### Add Python Package to Python DS

```dockerfile
# Add to Dockerfile.python-ds
RUN pip install --no-cache-dir tensorflow keras
```

### Add Node Package to Web Dev

```dockerfile
# Add to Dockerfile.web
RUN npm install -g @nestjs/cli typeorm
```

### Add Rust Tool to Rust Workspace

```dockerfile
# Add to Dockerfile.rust
RUN cargo install cargo-clippy
```

### Add Build Tool to C/C++

```dockerfile
# Add to Dockerfile.c or Dockerfile.cpp
RUN apt-get install -y ninja-build autoconf automake
```

## Troubleshooting

### Build Fails: "Cannot download package"
**Cause**: Network issue or mirror down
**Fix**: Wait a moment and try again, or change base image to different mirror

### Build Fails: "Disk space full"
**Cause**: Docker image too large or disk full
**Fix**: `docker system prune` and `docker image prune -a`

### Build Takes Too Long
**Cause**: Normal for first build
**Fix**: Be patient, subsequent builds use cache (~30 seconds)

### Container Won't Start
**Cause**: Resource limits or corrupted image
**Fix**: `docker image rm editor-name:latest` and rebuild

## Advanced: Creating Custom Dockerfile

For specialized needs, create new Dockerfile:

```dockerfile
# Dockerfile.custom
FROM ubuntu:22.04

# Update system
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Your custom packages
RUN apt-get install -y custom-package

# Set environment
ENV CUSTOM_VAR=value

WORKDIR /workspace

CMD ["/bin/bash"]
```

Then in `predefined_environments.py`:

```python
CUSTOM_ENV = EnvironmentConfig(
    name="Custom Env",
    language="Custom",
    dockerfile=_load_dockerfile("Dockerfile.custom"),
    image_name="editor-custom:latest",
)
```

## Version Management

To track versions, include labels in Dockerfile:

```dockerfile
LABEL maintainer="your-email@example.com"
LABEL version="1.0"
LABEL description="Python Data Science environment"
```

View labels:

```bash
docker inspect editor-python-ds:latest | grep Labels
```

## Multi-Stage Builds (Advanced)

For optimized final images:

```dockerfile
# Build stage
FROM python:3.11 as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage (smaller)
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
WORKDIR /workspace
ENV PATH=/root/.local/bin:$PATH
CMD ["/bin/bash"]
```

## Related Documentation

- **README.md** - Main documentation
- **CONFIGURATION_EXAMPLES.md** - Examples of custom Dockerfiles
- **BUGFIXES_AND_IMPROVEMENTS.md** - Changes and fixes
- **GETTING_STARTED.md** - How to use environments
- **IMPLEMENTATION_GUIDE.md** - Technical architecture

## Quick Reference

### Build from Dockerfile

```bash
docker build -t image-name:tag -f Dockerfile .
```

### Run Container

```bash
docker run -d \
  --name container-name \
  -v /local:/workspace \
  -p 3000:3000 \
  image-name:tag
```

### Check Dockerfile Syntax

```bash
docker build --dry-run -f Dockerfile .
```

### View Build History

```bash
docker history image-name:tag
```

---

**Status**: All Dockerfiles tested and working ✓
**Last Updated**: December 2024
