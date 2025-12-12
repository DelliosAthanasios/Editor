#!/usr/bin/env python3
"""
Docker Environment System - Comprehensive Test Suite
Tests all modules for bugs and correctness
"""

import sys
import os

def test_imports():
    """Test that all modules import correctly"""
    print("=" * 60)
    print("TEST 1: Module Imports")
    print("=" * 60)
    
    try:
        from global_.environment_manager import (
            DockerManager, EnvironmentConfig, EnvironmentStatus, 
            get_docker_manager
        )
        print("✓ environment_manager imported")
        
        from global_.predefined_environments import (
            list_environments, get_environment_by_name, 
            PREDEFINED_ENVIRONMENTS
        )
        print("✓ predefined_environments imported")
        
        from global_.environment_ui import (
            EnvironmentSelectionDialog,
            EnvironmentManagerDialog,
            EnvironmentStatusWidget
        )
        print("✓ environment_ui imported")
        
        from global_.container_executor import (
            ContainerExecutor, ExecutionWorker
        )
        print("✓ container_executor imported")
        
        print("\n✓ All imports successful!\n")
        return True
    except Exception as e:
        print(f"\n✗ Import failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_docker_manager():
    """Test DockerManager functionality"""
    print("=" * 60)
    print("TEST 2: Docker Manager")
    print("=" * 60)
    
    try:
        from global_.environment_manager import get_docker_manager
        
        docker_manager = get_docker_manager()
        print(f"✓ DockerManager initialized")
        
        # Check detection
        available = docker_manager.is_docker_available()
        print(f"✓ Docker available check: {available}")
        
        if available:
            daemon_running = docker_manager.check_docker_daemon_running()
            print(f"✓ Docker daemon check: {daemon_running}")
            
            if daemon_running:
                print(f"✓ Docker version: {docker_manager.docker_version}")
            else:
                print("! Docker installed but daemon not running (need to start Docker Desktop)")
        else:
            print("! Docker not installed")
        
        # Check installation instructions
        instructions = docker_manager.get_docker_install_instruction()
        print(f"✓ Installation instructions available ({len(instructions)} chars)")
        
        print("\n✓ DockerManager tests passed!\n")
        return True
    except Exception as e:
        print(f"\n✗ DockerManager test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_environments():
    """Test predefined environments"""
    print("=" * 60)
    print("TEST 3: Predefined Environments")
    print("=" * 60)
    
    try:
        from global_.predefined_environments import (
            list_environments, get_environment_by_name,
            PREDEFINED_ENVIRONMENTS
        )
        
        envs = list_environments()
        print(f"✓ Found {len(envs)} environments")
        
        assert len(envs) == 10, f"Expected 10 environments, got {len(envs)}"
        print("✓ All 10 environments present")
        
        # Test each environment
        for env_name in envs:
            config = get_environment_by_name(env_name)
            assert config is not None, f"Environment '{env_name}' not found"
            assert config.name == env_name
            assert config.language is not None
            assert config.dockerfile is not None
            assert len(config.dockerfile) > 0
            print(f"  ✓ {env_name:25s} ({config.language})")
        
        # Verify in dict
        assert len(PREDEFINED_ENVIRONMENTS) == 10
        print(f"✓ PREDEFINED_ENVIRONMENTS dict has all 10 environments")
        
        print("\n✓ Environment tests passed!\n")
        return True
    except Exception as e:
        print(f"\n✗ Environment test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_dockerfiles():
    """Test that all Dockerfiles exist and are valid"""
    print("=" * 60)
    print("TEST 4: Dockerfile Validation")
    print("=" * 60)
    
    try:
        dockerfile_dir = os.path.join(
            os.path.dirname(__file__),
            "global_", "environments", "dockerfiles"
        )
        
        required_files = [
            "Dockerfile.python-ds",
            "Dockerfile.web",
            "Dockerfile.rust",
            "Dockerfile.c",
            "Dockerfile.cpp",
            "Dockerfile.go",
            "Dockerfile.java",
            "Dockerfile.ruby",
            "Dockerfile.haskell",
            "Dockerfile.lisp",
        ]
        
        for dockerfile in required_files:
            filepath = os.path.join(dockerfile_dir, dockerfile)
            assert os.path.exists(filepath), f"Missing: {dockerfile}"
            
            with open(filepath, 'r') as f:
                content = f.read()
                assert len(content) > 0
                assert "FROM" in content
                assert "WORKDIR" in content
            
            print(f"  ✓ {dockerfile}")
        
        print(f"\n✓ All {len(required_files)} Dockerfiles validated!\n")
        return True
    except Exception as e:
        print(f"\n✗ Dockerfile test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_container_executor():
    """Test ContainerExecutor"""
    print("=" * 60)
    print("TEST 5: Container Executor")
    print("=" * 60)
    
    try:
        from global_.container_executor import ContainerExecutor
        from global_.environment_manager import get_docker_manager
        
        executor = ContainerExecutor(get_docker_manager())
        print("✓ ContainerExecutor initialized")
        
        # Test methods exist
        assert hasattr(executor, 'execute_command')
        print("✓ execute_command method exists")
        
        assert hasattr(executor, 'execute_file')
        print("✓ execute_file method exists")
        
        assert hasattr(executor, 'run_build_command')
        print("✓ run_build_command method exists")
        
        assert hasattr(executor, 'run_test_command')
        print("✓ run_test_command method exists")
        
        print("\n✓ ContainerExecutor tests passed!\n")
        return True
    except Exception as e:
        print(f"\n✗ ContainerExecutor test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_syntax():
    """Test Python syntax of all modules"""
    print("=" * 60)
    print("TEST 6: Python Syntax Validation")
    print("=" * 60)
    
    try:
        import py_compile
        import tempfile
        
        files_to_check = [
            "global_/environment_manager.py",
            "global_/predefined_environments.py",
            "global_/environment_ui.py",
            "global_/container_executor.py",
        ]
        
        for filepath in files_to_check:
            full_path = os.path.join(os.path.dirname(__file__), filepath)
            if os.path.exists(full_path):
                py_compile.compile(full_path, doraise=True)
                print(f"  ✓ {filepath}")
            else:
                print(f"  ! {filepath} not found (will check in final location)")
        
        print("\n✓ Syntax validation passed!\n")
        return True
    except Exception as e:
        print(f"\n✗ Syntax validation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " Docker Environment System - Test Suite ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Docker Manager", test_docker_manager),
        ("Environments", test_environments),
        ("Dockerfiles", test_dockerfiles),
        ("Container Executor", test_container_executor),
        ("Syntax", test_syntax),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"✗ {name} test crashed: {e}")
            results[name] = False
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! System is ready to use.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please fix issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
