"""
Pre-configured Development Environments
Provides 10+ ready-to-use Docker environments for different programming languages and frameworks
"""

import os
from global_.environment_manager import EnvironmentConfig


def _load_dockerfile(filename: str) -> str:
    """Load a Dockerfile from the dockerfiles directory"""
    dockerfile_path = os.path.join(
        os.path.dirname(__file__),
        "environments",
        "dockerfiles",
        filename
    )
    if os.path.exists(dockerfile_path):
        with open(dockerfile_path, 'r') as f:
            return f.read()
    else:
        # Fallback simple dockerfile
        return f"FROM ubuntu:22.04\nRUN apt-get update\nWORKDIR /workspace\nCMD [\"/bin/bash\"]"


# 1. Lisp Machine - SBCL/Clozure CL with Quicklisp
LISP_MACHINE = EnvironmentConfig(
    name="Lisp Machine",
    language="Lisp",
    description="SBCL with Quicklisp for Lisp/Scheme development",
    dockerfile=_load_dockerfile("Dockerfile.lisp"),
    image_name="editor-lisp:latest",
    container_name="editor-lisp-container",
    env_vars={},
    ports={},
    volumes={}
)

# 2. C Development - GCC, GDB, Make, Valgrind, CMake
C_DEVELOPMENT = EnvironmentConfig(
    name="C Development",
    language="C",
    description="GCC, GDB, Make, Valgrind, CMake for C development",
    dockerfile=_load_dockerfile("Dockerfile.c"),
    image_name="editor-c:latest",
    container_name="editor-c-container",
    env_vars={},
    ports={},
    volumes={}
)

# 3. C++ Modern - Latest GCC/Clang, Boost, Catch2, Conan
CPP_DEVELOPMENT = EnvironmentConfig(
    name="C++ Modern",
    language="C++",
    description="Modern C++ with GCC, Clang, and build tools",
    dockerfile=_load_dockerfile("Dockerfile.cpp"),
    image_name="editor-cpp:latest",
    container_name="editor-cpp-container",
    env_vars={},
    ports={},
    volumes={}
)

# 4. Python Data Science - Python 3.11, NumPy, Pandas, Jupyter
PYTHON_DATA_SCIENCE = EnvironmentConfig(
    name="Python Data Science",
    language="Python",
    description="Python 3.11 with NumPy, Pandas, Jupyter, Matplotlib, Scikit-learn",
    dockerfile=_load_dockerfile("Dockerfile.python-ds"),
    image_name="editor-python-ds:latest",
    container_name="editor-python-ds-container",
    env_vars={},
    ports={8888: 8888},
    volumes={}
)

# 5. Web Development - Node.js, npm/yarn, TypeScript, Express
WEB_DEVELOPMENT = EnvironmentConfig(
    name="Web Development",
    language="JavaScript/TypeScript",
    description="Node.js, npm, yarn, TypeScript, Express.js",
    dockerfile=_load_dockerfile("Dockerfile.web"),
    image_name="editor-web:latest",
    container_name="editor-web-container",
    env_vars={},
    ports={3000: 3000, 5000: 5000, 8080: 8080},
    volumes={}
)

# 6. Rust Workspace - Rust, Cargo, Rust-Analyzer
RUST_WORKSPACE = EnvironmentConfig(
    name="Rust Workspace",
    language="Rust",
    description="Rust toolchain with Cargo, Rust-Analyzer, and build tools",
    dockerfile=_load_dockerfile("Dockerfile.rust"),
    image_name="editor-rust:latest",
    container_name="editor-rust-container",
    env_vars={},
    ports={},
    volumes={}
)

# 7. Go Development - Latest Go, Delve debugger, Gin
GO_DEVELOPMENT = EnvironmentConfig(
    name="Go Development",
    language="Go",
    description="Go with development tools and hot reload",
    dockerfile=_load_dockerfile("Dockerfile.go"),
    image_name="editor-go:latest",
    container_name="editor-go-container",
    env_vars={"GOPATH": "/workspace/go"},
    ports={8080: 8080},
    volumes={}
)

# 8. Java Enterprise - OpenJDK 17, Maven, Spring Boot
JAVA_ENTERPRISE = EnvironmentConfig(
    name="Java Enterprise",
    language="Java",
    description="OpenJDK 17, Maven, Gradle, Spring Boot framework",
    dockerfile=_load_dockerfile("Dockerfile.java"),
    image_name="editor-java:latest",
    container_name="editor-java-container",
    env_vars={"JAVA_HOME": "/usr/local/openjdk-17"},
    ports={8080: 8080, 8443: 8443, 5005: 5005},
    volumes={}
)

# 9. Ruby/Rails - Ruby 3.2, Rails, Bundler
RUBY_RAILS = EnvironmentConfig(
    name="Ruby/Rails",
    language="Ruby",
    description="Ruby 3.2, Rails, Bundler, and development tools",
    dockerfile=_load_dockerfile("Dockerfile.ruby"),
    image_name="editor-ruby:latest",
    container_name="editor-ruby-container",
    env_vars={},
    ports={3000: 3000, 5432: 5432},
    volumes={}
)

# 10. Haskell Stack - GHC, Cabal, Stack, HLS
HASKELL_STACK = EnvironmentConfig(
    name="Haskell Stack",
    language="Haskell",
    description="GHC, Cabal, Haskell Stack, and Haskell Language Server",
    dockerfile=_load_dockerfile("Dockerfile.haskell"),
    image_name="editor-haskell:latest",
    container_name="editor-haskell-container",
    env_vars={},
    ports={},
    volumes={}
)

# Collection of all predefined environments
PREDEFINED_ENVIRONMENTS = {
    "Lisp Machine": LISP_MACHINE,
    "C Development": C_DEVELOPMENT,
    "C++ Modern": CPP_DEVELOPMENT,
    "Python Data Science": PYTHON_DATA_SCIENCE,
    "Web Development": WEB_DEVELOPMENT,
    "Rust Workspace": RUST_WORKSPACE,
    "Go Development": GO_DEVELOPMENT,
    "Java Enterprise": JAVA_ENTERPRISE,
    "Ruby/Rails": RUBY_RAILS,
    "Haskell Stack": HASKELL_STACK,
}

def get_environment_by_name(name: str) -> EnvironmentConfig:
    """Get an environment configuration by name"""
    return PREDEFINED_ENVIRONMENTS.get(name)

def list_environments() -> list:
    """List all available predefined environments"""
    return list(PREDEFINED_ENVIRONMENTS.keys())

def get_environment_description(name: str) -> str:
    """Get description of an environment"""
    env = PREDEFINED_ENVIRONMENTS.get(name)
    return env.description if env else ""
