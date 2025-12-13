"""
Docker-based Environment Management System
Provides isolated, language-specific coding environments through Docker containers.
"""

import os
import json
import subprocess
import platform
import tempfile
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnvironmentStatus(Enum):
    """Container lifecycle status"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    IMAGE_MISSING = "image_missing"
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class EnvironmentConfig:
    """Configuration for a development environment"""
    name: str
    language: str
    dockerfile: str  # Path to Dockerfile or inline content
    docker_compose: Optional[str] = None  # Path to docker-compose.yml or inline
    volumes: Dict[str, str] = None  # {host_path: container_path}
    ports: Dict[int, int] = None  # {host_port: container_port}
    env_vars: Dict[str, str] = None  # Environment variables
    image_name: Optional[str] = None  # Docker image name
    container_name: Optional[str] = None  # Running container name
    description: str = ""
    
    def __post_init__(self):
        if self.volumes is None:
            self.volumes = {}
        if self.ports is None:
            self.ports = {}
        if self.env_vars is None:
            self.env_vars = {}
        if self.image_name is None:
            self.image_name = f"editor-{self.language.lower()}:latest"
        if self.container_name is None:
            self.container_name = f"editor-{self.language.lower()}-container"


class DockerManager:
    """Manages Docker operations and environment containers"""
    
    def __init__(self):
        self.docker_available = False
        self.docker_version = None
        self.containers: Dict[str, Dict] = {}  # {env_name: {status, container_id, config}}
        self.workspace_dir = os.getcwd()
        
        # Initialize
        self._detect_docker()
        self._load_containers_state()
    
    def _detect_docker(self) -> None:
        """Detect Docker installation and version"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.docker_available = True
                self.docker_version = result.stdout.strip()
                logger.info(f"Docker detected: {self.docker_version}")
            else:
                logger.warning("Docker command exists but failed")
        except FileNotFoundError:
            logger.warning("Docker not found on system")
        except subprocess.TimeoutExpired:
            logger.warning("Docker detection timed out")
        except Exception as e:
            logger.error(f"Error detecting Docker: {e}")
            return False, str(e)
    
    def check_docker_daemon_running(self) -> bool:
        """Check if Docker daemon is actually running"""
        if not self.docker_available:
            return False
        
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Docker daemon check failed: {e}")
            return False
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available"""
        return self.docker_available
    
    def get_docker_install_instruction(self) -> str:
        """Get platform-specific Docker installation instructions"""
        system = platform.system()
        
        instructions = {
            "Windows": (
                "1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop\n"
                "2. Run the installer and follow the setup wizard\n"
                "3. Enable WSL 2 (Windows Subsystem for Linux) if prompted\n"
                "4. Restart your computer\n"
                "5. Launch Docker Desktop from the Start menu"
            ),
            "Darwin": (
                "1. Download Docker Desktop for Mac from: https://www.docker.com/products/docker-desktop\n"
                "2. Open the .dmg file and drag Docker to Applications\n"
                "3. Launch Docker from Applications\n"
                "4. Complete the setup wizard"
            ),
            "Linux": (
                "1. Update package list: sudo apt-get update\n"
                "2. Install Docker: sudo apt-get install docker.io docker-compose\n"
                "3. Add user to docker group: sudo usermod -aG docker $USER\n"
                "4. Log out and log back in for changes to take effect"
            )
        }
        
        return instructions.get(system, "Please visit: https://docs.docker.com/install/")
    
    def build_image(self, config: EnvironmentConfig, progress_callback=None) -> bool:
        """Build Docker image from Dockerfile"""
        if not self.docker_available:
            logger.error("Docker not available")
            return False
        
        try:
            # Determine Dockerfile location
            if os.path.isfile(config.dockerfile):
                dockerfile_path = config.dockerfile
            else:
                # It's inline content, write to temp file
                dockerfile_path = self._create_temp_dockerfile(config.dockerfile)
            
            # Build image
            cmd = [
                "docker", "build",
                "-t", config.image_name,
                "-f", dockerfile_path,
                "."
            ]
            
            logger.info(f"Building image: {config.image_name}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(dockerfile_path) or self.workspace_dir
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully built image: {config.image_name}")
                return True
            else:
                logger.error(f"Failed to build image: {result.stderr}")
                if progress_callback:
                    progress_callback(f"Build failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error building image: {e}")
            if progress_callback:
                progress_callback(f"Build error: {str(e)}")
            return False
    
    def run_container(self, config: EnvironmentConfig, progress_callback=None) -> Optional[str]:
        """Run a Docker container with the specified configuration"""
        if not self.docker_available:
            logger.error("Docker not available")
            return None
        
        try:
            # Check if container already exists and remove it
            try:
                result = subprocess.run(
                    ["docker", "ps", "-a", "-q", "-f", f"name={config.container_name}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.stdout.strip():
                    # Container exists, remove it
                    logger.info(f"Removing existing container: {config.container_name}")
                    subprocess.run(
                        ["docker", "rm", "-f", config.container_name],
                        capture_output=True,
                        timeout=10
                    )
            except Exception as e:
                logger.warning(f"Could not check for existing container: {e}")
            
            # Build command
            cmd = ["docker", "run", "-d"]
            
            # Add name
            cmd.extend(["--name", config.container_name])
            
            # Add volumes (with workspace auto-mount)
            volumes = config.volumes.copy()
            if "/workspace" not in volumes.values():
                volumes[self.workspace_dir] = "/workspace"
            
            for host_path, container_path in volumes.items():
                if os.path.exists(host_path):
                    cmd.extend(["-v", f"{host_path}:{container_path}"])
            
            # Add port mappings
            for host_port, container_port in config.ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])
            
            # Add environment variables
            for key, value in config.env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])
            
            # Add image name and default command
            cmd.append(config.image_name)
            cmd.extend(["/bin/bash", "-c", "sleep infinity"])
            
            logger.info(f"Starting container: {config.container_name}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                logger.info(f"Container started: {container_id}")
                
                # Store container info (convert enum to string for JSON serialization)
                self.containers[config.name] = {
                    "status": EnvironmentStatus.RUNNING.value,
                    "container_id": container_id,
                    "config": asdict(config)
                }
                
                self._save_containers_state()
                
                if progress_callback:
                    progress_callback(f"Container running: {container_id[:12]}")
                
                return container_id
            else:
                logger.error(f"Failed to start container: {result.stderr}")
                if progress_callback:
                    progress_callback(f"Start failed: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Error running container: {e}")
            if progress_callback:
                progress_callback(f"Container error: {str(e)}")
            return None
    
    def stop_container(self, env_name: str) -> bool:
        """Stop a running container"""
        if env_name not in self.containers:
            logger.warning(f"Unknown environment: {env_name}")
            return False
        
        try:
            container_id = self.containers[env_name]["container_id"]
            result = subprocess.run(
                ["docker", "stop", container_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.containers[env_name]["status"] = EnvironmentStatus.STOPPED.value
                self._save_containers_state()
                logger.info(f"Container stopped: {container_id}")
                return True
            else:
                logger.error(f"Failed to stop container: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return False
    
    def remove_container(self, env_name: str) -> bool:
        """Remove a container"""
        if env_name not in self.containers:
            return False
        
        try:
            container_id = self.containers[env_name]["container_id"]
            
            # Stop if running
            subprocess.run(
                ["docker", "stop", container_id],
                capture_output=True,
                timeout=10
            )
            
            # Remove
            result = subprocess.run(
                ["docker", "remove", "-f", container_id],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                del self.containers[env_name]
                self._save_containers_state()
                logger.info(f"Container removed: {container_id}")
                return True
            else:
                logger.error(f"Failed to remove container: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error removing container: {e}")
            return False
    
    def get_container_status(self, env_name: str) -> EnvironmentStatus:
        """Get the status of a container"""
        if env_name not in self.containers:
            return EnvironmentStatus.IMAGE_MISSING
        
        try:
            container_id = self.containers[env_name]["container_id"]
            result = subprocess.run(
                ["docker", "ps", "-a", "-q", "-f", f"id={container_id}"],
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                self.containers[env_name]["status"] = EnvironmentStatus.IMAGE_MISSING.value
                return EnvironmentStatus.IMAGE_MISSING
            
            # Check if running
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"id={container_id}"],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                self.containers[env_name]["status"] = EnvironmentStatus.RUNNING.value
                return EnvironmentStatus.RUNNING
            else:
                self.containers[env_name]["status"] = EnvironmentStatus.STOPPED.value
                return EnvironmentStatus.STOPPED
        except Exception as e:
            logger.error(f"Error checking container status: {e}")
            return EnvironmentStatus.ERROR
    
    def execute_in_container(self, env_name: str, command: str, working_dir: str = "/workspace") -> Tuple[int, str, str]:
        """Execute a command in a container"""
        if env_name not in self.containers:
            return 1, "", "Container not found"
        
        try:
            container_id = self.containers[env_name]["container_id"]
            
            cmd = [
                "docker", "exec",
                "-w", working_dir,
                container_id,
                "/bin/bash", "-c", command
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timeout"
        except Exception as e:
            return 1, "", str(e)
    
    def copy_file_to_container(self, env_name: str, host_path: str, container_path: str) -> bool:
        """Copy a file from host PC to container"""
        if env_name not in self.containers:
            logger.error(f"Container not found for environment: {env_name}")
            return False
        
        if not os.path.exists(host_path):
            logger.error(f"Host file not found: {host_path}")
            return False
        
        try:
            container_id = self.containers[env_name]["container_id"]
            
            # Use docker cp to copy file
            cmd = ["docker", "cp", host_path, f"{container_id}:{container_path}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Copied {host_path} to {container_path}")
                return True
            else:
                logger.error(f"Failed to copy file: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error copying file to container: {e}")
            return False
    
    def copy_file_from_container(self, env_name: str, container_path: str, host_path: str) -> bool:
        """Copy a file from container to host PC"""
        if env_name not in self.containers:
            logger.error(f"Container not found for environment: {env_name}")
            return False
        
        try:
            container_id = self.containers[env_name]["container_id"]
            
            # Create host directory if needed
            os.makedirs(os.path.dirname(host_path) or '.', exist_ok=True)
            
            # Use docker cp to copy file
            cmd = ["docker", "cp", f"{container_id}:{container_path}", host_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Copied {container_path} to {host_path}")
                return True
            else:
                logger.error(f"Failed to copy file from container: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error copying file from container: {e}")
            return False
    
    def list_container_files(self, env_name: str, container_path: str = "/workspace") -> Optional[List[str]]:
        """List files in container"""
        if env_name not in self.containers:
            return None
        
        try:
            returncode, stdout, stderr = self.execute_in_container(
                env_name,
                f"ls -la {container_path}",
                container_path
            )
            
            if returncode == 0:
                return [line for line in stdout.split('\n') if line.strip()]
            else:
                logger.error(f"Failed to list files: {stderr}")
                return None
        except Exception as e:
            logger.error(f"Error listing container files: {e}")
            return None
    
    def get_container_workspace_files(self, env_name: str) -> Optional[Dict[str, str]]:
        """Get all files in container workspace for editing"""
        files = self.list_container_files(env_name, "/workspace")
        if not files:
            return None
        
        file_dict = {}
        for line in files:
            parts = line.split()
            if len(parts) >= 9:
                # Extract filename (last part)
                filename = parts[-1]
                if filename not in ['.', '..']:
                    file_dict[filename] = f"/workspace/{filename}"
        
        return file_dict
    
    def _create_temp_dockerfile(self, content: str) -> str:
        """Create a temporary Dockerfile from inline content"""
        fd, path = tempfile.mkstemp(prefix="Dockerfile.", suffix="", text=True)
        os.write(fd, content.encode())
        os.close(fd)
        return path
    
    def _load_containers_state(self):
        """Load container state from disk"""
        state_file = os.path.join(self.workspace_dir, ".editor_containers.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    self.containers = json.load(f)
                logger.info(f"Loaded {len(self.containers)} container states")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in container state: {e}")
                self.containers = {}
            except Exception as e:
                logger.error(f"Error loading container state: {e}")
                self.containers = {}
    
    def _save_containers_state(self):
        """Save container state to disk"""
        state_file = os.path.join(self.workspace_dir, ".editor_containers.json")
        try:
            with open(state_file, 'w') as f:
                json.dump(self.containers, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving container state: {e}")


# Global instance
_docker_manager_instance = None

def get_docker_manager() -> DockerManager:
    """Get or create the global DockerManager instance"""
    global _docker_manager_instance
    if _docker_manager_instance is None:
        _docker_manager_instance = DockerManager()
    return _docker_manager_instance
