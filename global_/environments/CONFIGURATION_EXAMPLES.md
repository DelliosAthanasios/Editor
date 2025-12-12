# Docker Environment Configuration Examples

## Custom Environment Configurations

These examples show how to create custom environments programmatically or through the UI.

### Example 1: Full-Stack Development Environment

**Dockerfile**:
```dockerfile
FROM ubuntu:22.04

# Install multiple language runtimes
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    nodejs npm \
    curl git \
    build-essential \
    postgresql-client \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Python packages
RUN pip install --no-cache-dir \
    django djangorestframework \
    celery redis \
    sqlalchemy alembic

# Node packages
RUN npm install -g \
    typescript \
    express-generator \
    @angular/cli \
    gatsby-cli

WORKDIR /workspace
EXPOSE 8000 3000 5432 6379

ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=development

CMD ["/bin/bash"]
```

**Python Usage**:
```python
from global_.environment_manager import EnvironmentConfig, get_docker_manager

config = EnvironmentConfig(
    name="Full Stack Dev",
    language="Python/Node.js",
    description="Full-stack development with Django, Express, and PostgreSQL",
    dockerfile=open("Dockerfile").read(),
    image_name="editor-fullstack:latest",
    container_name="editor-fullstack-container",
    ports={
        8000: 8000,  # Django
        3000: 3000,  # Express
        5432: 5432,  # PostgreSQL
        6379: 6379,  # Redis
    },
    env_vars={
        "PYTHONUNBUFFERED": "1",
        "NODE_ENV": "development",
    }
)

docker_manager = get_docker_manager()
docker_manager.build_image(config)
docker_manager.run_container(config)
```

### Example 2: Machine Learning Environment

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    graphviz \
    git \
    && rm -rf /var/lib/apt/lists/*

# ML Libraries
RUN pip install --no-cache-dir \
    jupyter jupyterlab \
    numpy pandas scipy \
    scikit-learn \
    tensorflow \
    torch torchvision \
    matplotlib seaborn plotly \
    xgboost lightgbm \
    optuna \
    mlflow

WORKDIR /workspace
EXPOSE 8888 5000

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root"]
```

**Usage**:
```python
config = EnvironmentConfig(
    name="ML Workshop",
    language="Python",
    description="Machine learning with TensorFlow, PyTorch, and Jupyter",
    dockerfile="FROM python:3.11-slim\nRUN pip install ...",
    ports={8888: 8888, 5000: 5000},
)

docker_manager.build_image(config)
docker_manager.run_container(config)

# Access Jupyter at http://localhost:8888
```

### Example 3: Microservices Development

**Dockerfile**:
```dockerfile
FROM golang:1.21-alpine

RUN apk add --no-cache \
    git \
    curl \
    postgresql-client \
    protobuf \
    gcc musl-dev

# Install Go tools
RUN go install github.com/cosmtrek/air@latest && \
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest && \
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

WORKDIR /workspace

ENV GOPROXY=https://proxy.golang.org,direct
ENV CGO_ENABLED=1

EXPOSE 8080 8081 50051

CMD ["/bin/sh"]
```

### Example 4: Cloud-Native Development

**Dockerfile**:
```dockerfile
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    curl git build-essential \
    python3 python3-pip \
    nodejs npm \
    docker.io \
    kubectl \
    terraform \
    && rm -rf /var/lib/apt/lists/*

# AWS CLI
RUN pip install awscli boto3

# Kubernetes tools
RUN curl -LO https://github.com/kubernetes-sigs/kustomize/releases/latest/download/kustomize_linux_amd64 && \
    chmod +x kustomize_linux_amd64 && \
    mv kustomize_linux_amd64 /usr/local/bin/kustomize

WORKDIR /workspace

ENV AWS_DEFAULT_REGION=us-east-1

CMD ["/bin/bash"]
```

### Example 5: Database Development

**Dockerfile**:
```dockerfile
FROM postgres:15-alpine

RUN apk add --no-cache \
    python3 python3-pip \
    nodejs npm \
    curl git

# Tools for database development
RUN pip install --no-cache-dir \
    psycopg2-binary \
    sqlalchemy \
    alembic \
    pgcli

RUN npm install -g \
    sequelize-cli \
    knex

WORKDIR /workspace
EXPOSE 5432

ENV POSTGRES_PASSWORD=dev
ENV POSTGRES_USER=developer
ENV POSTGRES_DB=dev_database

CMD ["postgres"]
```

### Example 6: Documentation & Blogging

**Dockerfile**:
```dockerfile
FROM node:20-alpine

RUN apk add --no-cache \
    git \
    python3 \
    cairo-dev jpeg-dev pango-dev giflib-dev

# Static site generators
RUN npm install -g \
    @docusaurus/docusaurus-init \
    gatsby-cli \
    hugo \
    next

# Documentation tools
RUN npm install -g \
    markdownlint-cli \
    markdown-to-html \
    mermaid-cli

WORKDIR /workspace
EXPOSE 3000 8000

CMD ["/bin/sh"]
```

### Example 7: Embedded Systems Development

**Dockerfile**:
```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc-arm-none-eabi \
    gdb-arm-none-eabi \
    libnewlib-arm-none-eabi \
    python3 python3-pip \
    openocd \
    git \
    && rm -rf /var/lib/apt/lists/*

# Embedded tools
RUN pip install --no-cache-dir \
    pyserial \
    platformio

WORKDIR /workspace

ENV ARM_TOOLCHAIN=/usr

CMD ["/bin/bash"]
```

## Docker Compose Integration (Planned)

Future support for docker-compose.yml:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    working_dir: /workspace
    volumes:
      - .:/workspace
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
      - DATABASE_URL=postgresql://db:5432/myapp
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=dev
      - POSTGRES_USER=developer
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

## Advanced Configurations

### Multi-Stage Build for Smaller Images

```dockerfile
# Stage 1: Builder
FROM golang:1.21 as builder
WORKDIR /app
COPY . .
RUN go build -o myapp .

# Stage 2: Runtime (minimal)
FROM alpine:latest
COPY --from=builder /app/myapp /usr/local/bin/
EXPOSE 8080
CMD ["myapp"]
```

### Environment-Specific Configurations

```python
import os
from global_.environment_manager import EnvironmentConfig

# Development
dev_config = EnvironmentConfig(
    name="Dev Environment",
    language="Python",
    dockerfile="FROM python:3.11\nRUN pip install -e .",
    env_vars={
        "ENVIRONMENT": "development",
        "DEBUG": "1",
        "LOG_LEVEL": "DEBUG",
    }
)

# Production
prod_config = EnvironmentConfig(
    name="Prod Environment",
    language="Python",
    dockerfile="FROM python:3.11-slim\nRUN pip install .",
    env_vars={
        "ENVIRONMENT": "production",
        "DEBUG": "0",
        "LOG_LEVEL": "WARNING",
    }
)
```

### Networking Between Containers

```python
# Container 1: Database
db_config = EnvironmentConfig(
    name="Database",
    language="PostgreSQL",
    container_name="my-db",
    image_name="postgres:15",
)

# Container 2: Application
app_config = EnvironmentConfig(
    name="Application",
    language="Python",
    container_name="my-app",
    dockerfile="FROM python:3.11\nRUN pip install psycopg2",
    env_vars={
        "DATABASE_HOST": "my-db",
        "DATABASE_PORT": "5432",
    }
)

# In your app, use DATABASE_HOST=my-db for internal communication
```

## Best Practices

### 1. Use .dockerignore

```
# .dockerignore
__pycache__
*.pyc
.git
.gitignore
node_modules
npm-debug.log
*.swp
.DS_Store
venv/
env/
.env
```

### 2. Minimal Base Images

```dockerfile
# Good - Alpine Linux (5MB base)
FROM alpine:latest

# OK - Slim variant (30MB)
FROM python:3.11-slim

# Avoid - Full image (300MB+)
FROM python:3.11
```

### 3. Layer Caching

```dockerfile
# Place frequently-changing instructions last
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y base-packages
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .  # Your code (changes frequently)
```

### 4. Non-Root User

```dockerfile
FROM ubuntu:22.04
RUN useradd -m -u 1000 developer
USER developer
WORKDIR /home/developer/workspace
```

---

For more examples and configurations, check the main README documentation.
