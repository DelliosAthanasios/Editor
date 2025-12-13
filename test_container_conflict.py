#!/usr/bin/env python3
"""
Test container creation with conflict resolution
"""

from global_.environment_manager import get_docker_manager
from global_.predefined_environments import get_environment_by_name

print("=" * 60)
print("CONTAINER CONFLICT RESOLUTION TEST")
print("=" * 60)

dm = get_docker_manager()

if not dm.is_docker_available():
    print("✗ Docker not available")
    exit(1)

print("\n1. Testing with Lisp Machine (known to have existing container)...")
config = get_environment_by_name("Lisp Machine")

print(f"\n   Container name: {config.container_name}")
print(f"   Image name: {config.image_name}")

# Try to run it - the fix should handle the existing container
print("\n2. Attempting to run container (should auto-remove old one)...")
try:
    result = dm.run_container(config, progress_callback=print)
    if result:
        print(f"\n✓ SUCCESS: Container started with ID: {result[:12]}")
    else:
        print(f"\n✗ FAILED: Could not start container")
except Exception as e:
    print(f"\n✗ ERROR: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
