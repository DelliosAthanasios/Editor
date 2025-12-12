# Docker Environment Management System

A seamless development environment management system for the Third Edit code editor that provides isolated, language-specific coding environments using Docker.

## Overview

This system bridges local editing with containerized execution while maintaining user flexibility. It enables you to:

- Create isolated development environments for different programming languages
- Build and run Docker containers directly from the editor interface
- Execute code within containers
- Access Docker status in the editor status bar
- Manage multiple environments simultaneously

## Quick Start

### Prerequisites

- **Docker Desktop** or Docker CLI installed
  - Windows: https://www.docker.com/products/docker-desktop
  - macOS: https://www.docker.com/products/docker-desktop
  - Linux: https://docs.docker.com/install/

### First-Time Setup

1. Launch the editor and navigate to **Environments** menu
2. Select **Create Environment**
3. Choose from **Pre-configured Environments** or **Custom**
4. The system will automatically:
   - Build the Docker image
   - Create and start a container
   - Mount your project workspace at `/workspace` in the container

## Features

### 1. Pre-configured Environments (10 Language Stacks)

The system includes ready-to-use Dockerfiles for:

#### 1.1 Lisp Machine
- **Tools**: SBCL, Clozure CL, Quicklisp, SLIME
- **Use Case**: Lisp/Scheme development
- **Image Name**: `editor-lisp:latest`

#### 1.2 C Development
- **Tools**: GCC, GDB, Make, Valgrind, CMake
- **Use Case**: C programming, debugging, memory analysis
- **Image Name**: `editor-c:latest`

#### 1.3 C++ Modern
- **Tools**: GCC, Clang, Boost, Catch2, Conan
- **Use Case**: Modern C++ with libraries and testing
- **Image Name**: `editor-cpp:latest`

#### 1.4 Python Data Science
- **Tools**: Python 3.11, NumPy, Pandas, Jupyter, Matplotlib, Scikit-learn
- **Use Case**: Data analysis, machine learning, scientific computing
- **Image Name**: `editor-python-ds:latest`
- **Exposed Ports**: 8888 (Jupyter)

#### 1.5 Web Development
- **Tools**: Node.js 20, npm, yarn, TypeScript, Express.js, Next.js
- **Use Case**: Web application development
- **Image Name**: `editor-web:latest`
- **Exposed Ports**: 3000, 5000, 8080

#### 1.6 Rust Workspace
- **Tools**: Rust, Cargo, Rust-Analyzer, cargo-watch
- **Use Case**: Rust systems programming
- **Image Name**: `editor-rust:latest`

#### 1.7 Go Development
- **Tools**: Go, Delve debugger, Air (hot reload), golangci-lint
- **Use Case**: Go backend development
- **Image Name**: `editor-go:latest`
- **Exposed Ports**: 8080

#### 1.8 Java Enterprise
- **Tools**: OpenJDK 17, Maven, Gradle, Spring Boot
- **Use Case**: Enterprise Java applications
- **Image Name**: `editor-java:latest`
- **Exposed Ports**: 8080, 8443, 5005 (debugging)

#### 1.9 Ruby/Rails
- **Tools**: Ruby 3.2, Rails, Bundler, Node.js, Yarn
- **Use Case**: Ruby and Rails web applications
- **Image Name**: `editor-ruby:latest`
- **Exposed Ports**: 3000, 5432 (PostgreSQL)

#### 1.10 Haskell Stack
- **Tools**: GHC, Cabal, Haskell Stack, HLS
- **Use Case**: Functional programming with Haskell
- **Image Name**: `editor-haskell:latest`

### 2. Custom Environment Builder

Create custom environments by:

1. **Selecting Custom Environment** in the creation dialog
2. **Specifying**:
   - Environment name
   - Base language/framework
   - Base Docker image (e.g., `ubuntu:22.04`, `python:3.11`)
   - Custom Dockerfile content
   - Description

3. **Example Custom Dockerfile**:
```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
CMD ["/bin/bash"]
```

### 3. Docker Status Indicator

The editor displays Docker status in the status bar:
- **Green ●** - Docker is running and available
- **Red ●** - Docker is not installed/available
- Shows count of running environments

## Menu Structure

```
Environments
├── Create Environment
├── Pre-configured Environments
│   ├── Lisp Machine
│   ├── C Development
│   ├── C++ Modern
│   ├── Python Data Science
│   ├── Web Development
│   ├── Rust Workspace
│   ├── Go Development
│   ├── Java Enterprise
│   ├── Ruby/Rails
│   └── Haskell Stack
├── Manage Environments
│   └── (View/Stop/Remove running containers)
└── Environment Settings
    └── (Docker status and workspace info)
```

## Workflow Sequence

### Creating and Running an Environment

```
1. User selects environment from menu
   ↓
2. Editor checks Docker status
   ├─ If Docker not available → Show installation guide
   └─ If Docker available → Continue
   ↓
3. Build Docker image
   └─ Uses Dockerfile from configuration
   ↓
4. Start container
   ├─ Maps workspace to /workspace
   ├─ Configures port mappings
   └─ Sets environment variables
   ↓
5. Container running
   └─ Ready for code execution and terminal access
```

## File Structure

```
global_/
├── environment_manager.py      # Core Docker management
├── predefined_environments.py   # 10 pre-configured environments
├── environment_ui.py            # PyQt5 dialogs and widgets
├── container_executor.py        # Code execution in containers
└── environments/
    ├── README.md               # This file
    └── templates/              # Optional custom templates
```

## Configuration Files

### Container State Storage

Container information is automatically saved to:
```
.editor_containers.json
```

This file tracks:
- Container ID
- Environment configuration
- Container status
- Volume mounts
- Port mappings

### Example State File
```json
{
  "Python Data Science": {
    "status": "running",
    "container_id": "abc123def456...",
    "config": {
      "name": "Python Data Science",
      "language": "Python",
      "image_name": "editor-python-ds:latest",
      "container_name": "editor-python-ds-container",
      "volumes": {
        "/project": "/workspace"
      },
      "ports": {
        "8888": 8888
      }
    }
  }
}
```

## API Usage

### Python Integration

#### DockerManager
```python
from global_.environment_manager import get_docker_manager, EnvironmentConfig

docker_manager = get_docker_manager()

# Check Docker availability
if docker_manager.is_docker_available():
    print(docker_manager.docker_version)

# Create custom environment
config = EnvironmentConfig(
    name="My Environment",
    language="Python",
    dockerfile="FROM python:3.11\nRUN pip install jupyter",
    image_name="my-custom:latest"
)

# Build image
docker_manager.build_image(config)

# Run container
container_id = docker_manager.run_container(config)

# Execute command
return_code, stdout, stderr = docker_manager.execute_in_container(
    "My Environment",
    "python script.py"
)

# Stop container
docker_manager.stop_container("My Environment")
```

#### ContainerExecutor
```python
from global_.container_executor import ContainerExecutor
from global_.environment_manager import get_docker_manager

executor = ContainerExecutor(get_docker_manager())

# Execute Python file
return_code, stdout, stderr = executor.execute_file(
    "Python Data Science",
    "/workspace/analysis.py"
)

# Run build command
executor.run_build_command("Rust Workspace", "Rust")

# Run tests
executor.run_test_command("Python Data Science", "Python")
```

### Environment Selection Dialog
```python
from global_.environment_ui import EnvironmentSelectionDialog

dialog = EnvironmentSelectionDialog(parent_widget)
if dialog.exec_():
    print("Environment created successfully")
```

### Environment Manager Dialog
```python
from global_.environment_ui import EnvironmentManagerDialog

manager = EnvironmentManagerDialog(parent_widget)
manager.exec_()  # View and manage all environments
```

## Container Lifecycle

### Stopping a Container

To stop a running container:
1. Go to **Environments** → **Manage Environments**
2. Select the environment
3. Click **Actions** → **Stop**

Stopped containers retain:
- All file changes
- Installed packages
- Configuration

### Removing a Container

1. Go to **Environments** → **Manage Environments**
2. Select a stopped environment
3. Click **Actions** → **Remove**

⚠️ **Note**: Removing a container deletes all its state. The image remains available for recreation.

## Advanced Features

### Volume Mounts

By default, your project workspace is mounted at `/workspace` in containers. You can add custom mounts:

```python
config = EnvironmentConfig(
    name="Custom",
    language="Python",
    dockerfile="FROM python:3.11",
    volumes={
        "/home/user/data": "/data",
        "/home/user/scripts": "/scripts"
    }
)
```

### Port Mappings

Expose container ports to your host machine:

```python
config.ports = {
    3000: 3000,    # Host:Container
    5432: 5432,
}
```

### Environment Variables

Set environment variables for your container:

```python
config.env_vars = {
    "DATABASE_URL": "postgresql://localhost/mydb",
    "API_KEY": "your-key-here",
}
```

## Troubleshooting

### Docker Not Found

**Error**: "Docker not installed or not running"

**Solution**:
1. Install Docker Desktop from https://www.docker.com/products/docker-desktop
2. Start Docker Desktop
3. Restart the editor

### Container Failed to Start

**Error**: "Failed to start container"

**Solutions**:
1. Check Docker is running: `docker ps`
2. Free up disk space
3. Check port conflicts
4. View logs: **Environments** → **Manage Environments** → Select environment → View logs

### Permission Denied (Linux)

**Error**: "Permission denied while trying to connect to Docker daemon"

**Solution**:
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Out of Disk Space

Build image fails due to disk space.

**Solution**:
```bash
# Clean up unused images
docker image prune -a

# Clean up unused containers
docker container prune

# Check disk usage
docker system df
```

## Performance Tips

1. **Image Caching**: First build is slower; subsequent runs use cached layers
2. **Layer Optimization**: Add frequently-changed instructions later in Dockerfile
3. **Multi-stage Builds**: Reduce final image size with multi-stage builds
4. **Resource Limits**: Limit container memory:
   ```python
   config.env_vars["MEMORY_LIMIT"] = "2g"
   ```

## Security Best Practices

1. **Source Control**: Don't commit `.editor_containers.json` with sensitive data
2. **Environment Variables**: Use environment variables for secrets, not hardcoded values
3. **Image Scanning**: Check images for vulnerabilities
4. **Read-only Volumes**: Mount config files as read-only:
   ```python
   volumes={"/config/readonly:/config:ro"}
   ```

## Examples

### Example 1: Python Data Science Workflow

```python
# Create environment
from global_.predefined_environments import get_environment_by_name
from global_.environment_manager import get_docker_manager

config = get_environment_by_name("Python Data Science")
docker_manager = get_docker_manager()

# Build and run
docker_manager.build_image(config)
docker_manager.run_container(config)

# Install additional packages
docker_manager.execute_in_container(
    "Python Data Science",
    "pip install tensorflow opencv-python"
)

# Run analysis script
return_code, stdout, stderr = docker_manager.execute_in_container(
    "Python Data Science",
    "python /workspace/analysis.py"
)
```

### Example 2: Web Development Stack

```python
# Create Node.js environment
from global_.predefined_environments import get_environment_by_name

config = get_environment_by_name("Web Development")
# Ports 3000, 5000, 8080 are already mapped

# Run development server
docker_manager.execute_in_container(
    "Web Development",
    "cd /workspace && npm install && npm start"
)

# Access at http://localhost:3000
```

### Example 3: Custom Rust Environment

```python
from global_.environment_manager import EnvironmentConfig, get_docker_manager

config = EnvironmentConfig(
    name="Rust Custom",
    language="Rust",
    dockerfile="""FROM rust:latest
RUN cargo install cargo-watch
WORKDIR /workspace
CMD ["/bin/bash"]
""",
    image_name="my-rust:latest"
)

docker_manager = get_docker_manager()
docker_manager.build_image(config)
docker_manager.run_container(config)

# Watch mode
docker_manager.execute_in_container(
    "Rust Custom",
    "cargo watch -x run"
)
```

## Limitations & Future Improvements

### Current Limitations
- Single-container per environment (no docker-compose orchestration yet)
- Manual port management
- No built-in debugging interface (Delve, GDB still require manual setup)

### Planned Features
- Docker Compose support for multi-container stacks
- GUI debugging integration
- Environment variable editor
- Automated backup/export of environments
- Container resource monitoring
- Build step optimization suggestions
- Container registry integration

## Contributing

To add new pre-configured environments:

1. Edit `global_/predefined_environments.py`
2. Add new `EnvironmentConfig` instance
3. Add to `PREDEFINED_ENVIRONMENTS` dictionary
4. Update this README

Example:
```python
MY_LANGUAGE = EnvironmentConfig(
    name="My Language",
    language="MyLang",
    description="Description of this environment",
    dockerfile="""FROM ubuntu:22.04
# Your Dockerfile content
""",
    image_name="editor-mylanag:latest",
    container_name="editor-mylang-container",
    env_vars={},
    ports={},
    volumes={}
)

PREDEFINED_ENVIRONMENTS["My Language"] = MY_LANGUAGE
```

## License

This Docker environment management system is part of Third Edit.

## Support

For issues, feature requests, or questions:
- Check the Troubleshooting section above
- Review Docker documentation: https://docs.docker.com/
- Check editor logs for detailed error messages

---

**Last Updated**: December 2024
**Version**: 1.0.0
