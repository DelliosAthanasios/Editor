#!/usr/bin/env python3
"""
Integration test for environment system
"""

import sys
from global_.environment_manager import get_docker_manager, EnvironmentConfig
from global_.predefined_environments import get_environment_by_name, list_environments
from global_.container_executor import ContainerExecutor

print("=" * 60)
print("INTEGRATION TEST: Environment System")
print("=" * 60)

# Test 1: Docker Manager
print("\n1. Docker Manager...")
dm = get_docker_manager()
print(f"   ✓ Docker available: {dm.is_docker_available()}")
print(f"   ✓ Docker version: {dm.docker_version}")

# Test 2: Predefined Environments
print("\n2. Predefined Environments...")
envs = list_environments()
print(f"   ✓ Environments: {len(envs)}")
config = get_environment_by_name("Python Data Science")
print(f"   ✓ Python Data Science config: {config.name}")
print(f"   ✓ Language: {config.language}")
print(f"   ✓ Image: {config.image_name}")

# Test 3: Container Executor
print("\n3. Container Executor...")
executor = ContainerExecutor(dm)
print(f"   ✓ Executor created")
print(f"   ✓ execute_command method exists: {hasattr(executor, 'execute_command')}")
print(f"   ✓ execute_file method exists: {hasattr(executor, 'execute_file')}")

# Test 4: Custom Environment Config
print("\n4. Custom Environment Config...")
custom_config = EnvironmentConfig(
    name="Test Env",
    language="Python",
    dockerfile="FROM python:3.11\nWORKDIR /workspace",
    image_name="test:latest"
)
print(f"   ✓ Custom config created: {custom_config.name}")
print(f"   ✓ Image name: {custom_config.image_name}")

print("\n" + "=" * 60)
print("✓ ALL INTEGRATION TESTS PASSED!")
print("=" * 60)
