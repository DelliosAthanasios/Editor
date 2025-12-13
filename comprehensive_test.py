#!/usr/bin/env python3
"""
Comprehensive system test - all modules and features
"""

import sys
from global_.environment_manager import get_docker_manager
from global_.predefined_environments import list_environments, get_environment_by_name
from global_.container_executor import ContainerExecutor
from global_.cli_tools.language_detector_cli import LanguageDetectorCLI
from terminal_organizer_rich import TerminalOrganizerCLI

print("\n" + "=" * 70)
print(" COMPREHENSIVE SYSTEM TEST - ALL MODULES ".center(70))
print("=" * 70)

passed = 0
failed = 0

# Test 1: Docker Manager
print("\n[1/5] Docker Manager...")
try:
    dm = get_docker_manager()
    assert dm.is_docker_available()
    assert dm.docker_version is not None
    print("     ✓ PASS")
    passed += 1
except Exception as e:
    print(f"     ✗ FAIL: {e}")
    failed += 1

# Test 2: Environments
print("[2/5] Predefined Environments...")
try:
    envs = list_environments()
    assert len(envs) == 10
    config = get_environment_by_name("Python Data Science")
    assert config.name == "Python Data Science"
    print("     ✓ PASS")
    passed += 1
except Exception as e:
    print(f"     ✗ FAIL: {e}")
    failed += 1

# Test 3: Container Executor
print("[3/5] Container Executor...")
try:
    executor = ContainerExecutor(dm)
    assert hasattr(executor, 'execute_command')
    assert hasattr(executor, 'execute_file')
    assert hasattr(executor, 'run_build_command')
    print("     ✓ PASS")
    passed += 1
except Exception as e:
    print(f"     ✗ FAIL: {e}")
    failed += 1

# Test 4: CLI Tools
print("[4/5] CLI Tools (Language Detector)...")
try:
    detector = LanguageDetectorCLI()
    detector.detect_all()
    assert len(detector.detected) > 0
    print("     ✓ PASS")
    passed += 1
except Exception as e:
    print(f"     ✗ FAIL: {e}")
    failed += 1

# Test 5: Terminal Organizer
print("[5/5] Terminal Organizer...")
try:
    organizer = TerminalOrganizerCLI()
    assert organizer.console is not None
    print("     ✓ PASS")
    passed += 1
except Exception as e:
    print(f"     ✗ FAIL: {e}")
    failed += 1

# Summary
print("\n" + "=" * 70)
print(f" RESULTS: {passed} passed, {failed} failed ".center(70))
if failed == 0:
    print(" ✓ ALL TESTS PASSED - SYSTEM READY ".center(70))
else:
    print(f" ✗ {failed} TEST(S) FAILED ".center(70))
print("=" * 70 + "\n")

sys.exit(0 if failed == 0 else 1)
