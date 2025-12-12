# Docker Environment System - Implementation Guide

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Third Edit Editor                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ main.py ────────────────────────────────────────────┐   │
│  │  - Menu integration                                  │   │
│  │  - Environment creation/management UI calls          │   │
│  └────────────────────────────────────────────────────┘   │
│                      │                                      │
│                      ↓                                      │
│  ┌─ global_/environment_ui.py ──────────────────────┐   │
│  │  - EnvironmentSelectionDialog                    │   │
│  │  - EnvironmentBuildDialog                        │   │
│  │  - EnvironmentManagerDialog                      │   │
│  │  - EnvironmentStatusWidget (status bar)          │   │
│  └─────────────────────────────────────────────────┘   │
│          │                      │                        │
│          ↓                      ↓                        │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ Predefined Envs  │  │ Container Exec   │            │
│  │ .py              │  │ .py              │            │
│  └──────────────────┘  └──────────────────┘            │
│          │                      │                        │
└──────────┼──────────────────────┼────────────────────────┘
           │                      │
           ↓                      ↓
┌──────────────────────────────────────────────────────────┐
│          global_/environment_manager.py                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │         DockerManager (Core)                    │  │
│  │                                                  │  │
│  │  - _detect_docker()         Docker detection   │  │
│  │  - build_image()            Build images       │  │
│  │  - run_container()          Start containers   │  │
│  │  - stop_container()         Stop containers    │  │
│  │  - execute_in_container()   Run commands       │  │
│  │  - get_container_status()   Status checking    │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────────────────────┐
│              Docker (External)                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Images | Containers | Volumes | Networks       │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Module Descriptions

### 1. `environment_manager.py` (Core)

**Key Classes**:
- `EnvironmentStatus`: Enum tracking container lifecycle
- `EnvironmentConfig`: Configuration data class
- `DockerManager`: Main orchestration class

**Key Methods**:
```python
# Detection
is_docker_available() -> bool
_detect_docker() -> Tuple[bool, str]

# Building
build_image(config: EnvironmentConfig, progress_callback) -> bool

# Container Lifecycle
run_container(config: EnvironmentConfig, progress_callback) -> Optional[str]
stop_container(env_name: str) -> bool
remove_container(env_name: str) -> bool

# Execution
execute_in_container(env_name: str, command: str, working_dir: str) -> Tuple[int, str, str]

# State Management
_load_containers_state()
_save_containers_state()

# Utilities
get_docker_install_instruction() -> str
get_container_status(env_name: str) -> EnvironmentStatus
```

**Data Flow**:
```
User creates environment
    ↓
EnvironmentConfig created
    ↓
DockerManager.build_image()
    → docker build command
    → Dockerfile parsed
    → Image built
    ↓
DockerManager.run_container()
    → docker run command
    → Container started
    → State saved to .editor_containers.json
    ↓
Container ready for code execution
```

### 2. `predefined_environments.py`

**Contains**:
- 10 pre-configured `EnvironmentConfig` instances
- Helper functions to access configurations
- Centralized environment management

**Usage Pattern**:
```python
from global_.predefined_environments import (
    list_environments,
    get_environment_by_name,
    get_environment_description,
    PREDEFINED_ENVIRONMENTS
)
```

### 3. `environment_ui.py` (PyQt5 UI)

**Key Components**:

#### EnvironmentSelectionDialog
- Shows Docker status
- Lists pre-configured environments
- Form for custom environment creation
- Triggers environment build process

#### EnvironmentBuildDialog
- Shows build/run progress
- Real-time status updates
- Handles success/failure states

#### EnvironmentManagerDialog
- Table view of all containers
- Container status display
- Action buttons (Start/Stop/Remove)
- Refresh functionality

#### EnvironmentStatusWidget
- Status bar indicator
- Docker availability
- Running container count
- Auto-refresh every 5 seconds

#### EnvironmentWorker
- Background thread for long operations
- Prevents UI blocking
- Emits progress signals

**Threading Model**:
```
UI Thread                Worker Thread
─────────────────────────────────────
User clicks button  →
                    → EnvironmentWorker created
                    → docker build/run executed
                    ← progress signals emitted
Update progress ←
                    ← finished signal emitted
Enable button ←
```

### 4. `container_executor.py`

**Key Classes**:

#### ContainerExecutor
- Command execution wrapper
- File execution dispatcher
- Build/test command runners

#### ExecutionWorker
- Background execution thread
- Captures stdout/stderr
- Handles timeouts

#### ContainerTerminalWidget
- Interactive terminal display
- Output management
- Clear/close functionality

#### ContainerExecutionPanel
- Environment selector
- Command buttons (Run/Build/Test)
- Output display

**Execution Flow**:
```
User selects file
    ↓
ContainerExecutor.execute_file()
    → Detects file type
    → Maps to command
    → execute_in_container()
    ↓
Command runs in container
    ↓
Output captured and displayed
```

## Integration Flow

### Creating an Environment

```
1. Menu: Environments → Create Environment
   ↓
2. EnvironmentSelectionDialog opens
   ↓
3. User selects:
   a) Pre-configured environment OR
   b) Creates custom environment
   ↓
4. Click "Create Environment"
   ↓
5. EnvironmentBuildDialog shows:
   a) Building Docker image
   b) Running container
   ↓
6. State saved to .editor_containers.json
   ↓
7. Environment ready for use
```

### Executing Code

```
1. User opens file in editor
   ↓
2. Right-click → Execute in Container
   OR Menu → Tools → Execute
   ↓
3. Select target environment
   ↓
4. ContainerExecutor:
   a) Detects file type
   b) Selects execution command
   c) Runs in container
   ↓
5. Output displayed in console
```

## Configuration Data Flow

### File Persistence

```
.editor_containers.json (Root Directory)
    ↓
    Contains:
    - env_name → container_id mapping
    - configuration for each environment
    - last_status of each container
    ↓
    Loaded on editor startup
    Updated after each state change
```

**JSON Structure**:
```json
{
  "Python Data Science": {
    "status": "running",
    "container_id": "abc123...",
    "config": {
      "name": "Python Data Science",
      "language": "Python",
      "image_name": "editor-python-ds:latest",
      "container_name": "editor-python-ds-container",
      "volumes": { "/workspace": "/workspace" },
      "ports": { "8888": 8888 },
      "env_vars": {}
    }
  }
}
```

### Environment Variables

Passed to containers via `-e` flag:

```python
docker run ... \
  -e DATABASE_URL=postgresql://localhost/db \
  -e API_KEY=secret \
  ... container-image
```

### Volume Mounts

Project workspace automatically mounted:

```python
docker run ... \
  -v /local/project:/workspace \
  -v /local/data:/data \
  ... container-image
```

## Docker Commands Generated

### Building Image

```bash
docker build -t editor-python-ds:latest -f Dockerfile .
```

### Running Container

```bash
docker run -d \
  --name editor-python-ds-container \
  -v /local/workspace:/workspace \
  -p 8888:8888 \
  -e PYTHONUNBUFFERED=1 \
  editor-python-ds:latest \
  /bin/bash -c "sleep infinity"
```

### Executing Command

```bash
docker exec -w /workspace editor-python-ds-container \
  /bin/bash -c "python script.py"
```

### Stopping Container

```bash
docker stop editor-python-ds-container
```

### Removing Container

```bash
docker rm -f editor-python-ds-container
```

## Error Handling

### Docker Not Available

```
is_docker_available() → False
    ↓
Show installation instructions
    ↓
Check platform (Windows/Mac/Linux)
    ↓
Display platform-specific steps
```

### Build Failure

```
build_image() → return False
    ↓
progress_callback emits error message
    ↓
EnvironmentBuildDialog shows failure
    ↓
User can view detailed error logs
```

### Container Start Failure

```
run_container() → return None
    ↓
Check error: port conflict / insufficient resources / image issues
    ↓
Emit error message
    ↓
Dialog shows failure reason
```

## Performance Considerations

### Image Caching

- Docker caches build layers
- First build takes 2-5 minutes
- Subsequent builds use cache (~30 seconds)
- Large images (ML stacks) take longer

### Memory Usage

- Base Python image: ~100MB
- Python ML stack: ~1-2GB
- Node.js + dependencies: ~500MB-1GB
- Multiple containers: Sum of sizes

### Network

- Initial pull may require network
- Dockerfile RUN commands download packages
- Large ML packages can take time

## Extensibility

### Adding New Pre-configured Environment

```python
# In predefined_environments.py

MY_ENV = EnvironmentConfig(
    name="My Environment",
    language="MyLang",
    description="Description",
    dockerfile="""FROM base:latest
...""",
    image_name="editor-myenv:latest",
    container_name="editor-myenv-container",
)

PREDEFINED_ENVIRONMENTS["My Environment"] = MY_ENV
```

### Custom Environment Configurations

```python
# Programmatic creation

from global_.environment_manager import EnvironmentConfig, get_docker_manager

config = EnvironmentConfig(
    name="Custom Dev",
    language="Custom",
    dockerfile=open("my-dockerfile").read(),
    volumes={"/code": "/workspace"},
    ports={3000: 3000},
    env_vars={"DEBUG": "1"}
)

docker_manager = get_docker_manager()
docker_manager.build_image(config)
docker_manager.run_container(config)
```

### Executing Custom Commands

```python
executor = ContainerExecutor(docker_manager)

# Run arbitrary command
return_code, stdout, stderr = executor.execute_command(
    "My Environment",
    "python -m pytest --cov"
)

# Execute file
return_code, stdout, stderr = executor.execute_file(
    "My Environment",
    "/workspace/main.py"
)

# Run language-specific build
return_code, stdout, stderr = executor.run_build_command(
    "Rust Workspace",
    "Rust"
)
```

## Testing & Debugging

### Check Docker Status

```bash
docker --version
docker ps          # Running containers
docker images      # Available images
docker system df   # Disk usage
```

### View Container Logs

```bash
docker logs editor-python-ds-container
```

### Interactive Container Shell

```bash
docker exec -it editor-python-ds-container /bin/bash
```

### Inspect Environment

```python
from global_.environment_manager import get_docker_manager

dm = get_docker_manager()
print(dm.is_docker_available())
print(dm.docker_version)
print(dm.containers)  # All saved containers
```

## Troubleshooting Guide

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| Docker not detected | Docker not installed or PATH issue | Install Docker, restart shell |
| Build hangs | Network issues downloading packages | Check internet, try again |
| Port conflict | Port already in use | Change port mapping or close conflicting app |
| Permission denied | Docker daemon permission | Linux: `sudo usermod -aG docker $USER` |
| Out of memory | Container memory limits | Increase system RAM or limit container |
| Container won't start | Image corrupted or dependency missing | Remove image, rebuild |

---

**Document Version**: 1.0  
**Last Updated**: December 2024
