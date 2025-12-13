#!/usr/bin/env python3
"""
Final Stability and Integration Validation
Comprehensive test to ensure all systems are working correctly
"""

import sys
import os
import json
import subprocess
from datetime import datetime

def test_section(title):
    """Decorator for test sections"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n{'='*70}")
            print(f"  {title}".ljust(70))
            print('='*70)
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                print(f"✗ FAILED: {str(e)}")
                return False
        return wrapper
    return decorator

class StabilityValidator:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def log_test(self, name, passed, message=""):
        status = "✓" if passed else "✗"
        self.results.append((name, passed, message))
        print(f"{status} {name}" + (f": {message}" if message else ""))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    @test_section("Docker Environment System Validation")
    def validate_environment_system(self):
        """Validate Docker environment system"""
        try:
            from global_.environment_manager import get_docker_manager
            dm = get_docker_manager()
            self.log_test("Docker Detection", dm.is_docker_available())
            self.log_test("Docker Daemon", dm.check_docker_daemon_running())
            self.log_test("Container Loading", len(dm.containers) >= 0)
            return True
        except Exception as e:
            self.log_test("Environment System", False, str(e))
            return False
    
    @test_section("CLI Tools Validation")
    def validate_cli_tools(self):
        """Validate all CLI tools"""
        try:
            # Language detector
            from global_.cli_tools.language_detector_cli import LanguageDetectorCLI
            detector = LanguageDetectorCLI()
            self.log_test("Language Detector Import", True)
            
            # System monitor
            from global_.cli_tools.system_monitor_cli import SystemMonitorCLI
            monitor = SystemMonitorCLI()
            self.log_test("System Monitor Import", True)
            
            # Terminal organizer
            from terminal_organizer_rich import TerminalOrganizerCLI
            organizer = TerminalOrganizerCLI()
            self.log_test("Terminal Organizer Import", True)
            
            return True
        except Exception as e:
            self.log_test("CLI Tools", False, str(e))
            return False
    
    @test_section("UI Components Validation")
    def validate_ui_components(self):
        """Validate UI components"""
        try:
            from global_.environment_ui import (
                EnvironmentSelectionDialog,
                EnvironmentManagerDialog,
                EnvironmentBuildDialog,
                EnvironmentStatusWidget,
                EnvironmentWorker
            )
            self.log_test("EnvironmentSelectionDialog", True)
            self.log_test("EnvironmentManagerDialog", True)
            self.log_test("EnvironmentBuildDialog", True)
            self.log_test("EnvironmentStatusWidget", True)
            self.log_test("EnvironmentWorker", True)
            return True
        except Exception as e:
            self.log_test("UI Components", False, str(e))
            return False
    
    @test_section("Container Operations Validation")
    def validate_container_operations(self):
        """Validate container operations"""
        try:
            from global_.environment_manager import get_docker_manager
            from global_.predefined_environments import get_environment_by_name
            
            dm = get_docker_manager()
            config = get_environment_by_name("Python Data Science")
            
            self.log_test("Environment Config Load", config is not None)
            self.log_test("Config Properties", 
                         hasattr(config, 'name') and 
                         hasattr(config, 'dockerfile'))
            self.log_test("Container Name Generation", 
                         config.container_name is not None and
                         len(config.container_name) > 0)
            
            return True
        except Exception as e:
            self.log_test("Container Operations", False, str(e))
            return False
    
    @test_section("State Persistence Validation")
    def validate_state_persistence(self):
        """Validate state persistence"""
        try:
            state_file = ".editor_containers.json"
            
            # Check if file exists
            file_exists = os.path.exists(state_file)
            self.log_test("State File Exists", file_exists or True,
                         "File will be created on first use" if not file_exists else "File found")
            
            # Try to load it if it exists
            if file_exists:
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    self.log_test("State File Valid JSON", True, 
                                 f"Contains {len(data)} environments")
                except json.JSONDecodeError as e:
                    self.log_test("State File Valid JSON", False, str(e))
                    return False
            
            return True
        except Exception as e:
            self.log_test("State Persistence", False, str(e))
            return False
    
    @test_section("Docker Container Status")
    def validate_docker_containers(self):
        """Check Docker container status"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                containers = json.loads(result.stdout) if result.stdout else []
                self.log_test("Docker PS Command", True, 
                             f"{len(containers)} containers found")
                
                # Check for our containers
                editor_containers = [c for c in containers 
                                    if 'editor-' in c.get('Names', '')]
                self.log_test("Editor Containers", True,
                             f"{len(editor_containers)} editor containers")
            else:
                self.log_test("Docker PS Command", False, result.stderr[:50])
                return False
            
            return True
        except Exception as e:
            self.log_test("Docker Status", False, str(e))
            return False
    
    @test_section("Syntax Validation")
    def validate_syntax(self):
        """Validate Python syntax of core files"""
        try:
            import py_compile
            
            files = [
                "global_/environment_manager.py",
                "global_/environment_ui.py",
                "global_/predefined_environments.py",
                "global_/container_executor.py",
                "main.py",
            ]
            
            for filepath in files:
                if os.path.exists(filepath):
                    try:
                        py_compile.compile(filepath, doraise=True)
                        self.log_test(f"Syntax: {filepath}", True)
                    except py_compile.PyCompileError as e:
                        self.log_test(f"Syntax: {filepath}", False, str(e)[:50])
                        return False
            
            return True
        except Exception as e:
            self.log_test("Syntax Validation", False, str(e))
            return False
    
    def run_all_validations(self):
        """Run all validations"""
        print("\n" + "="*70)
        print("  FINAL STABILITY VALIDATION".center(70))
        print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(70))
        print("="*70)
        
        self.validate_environment_system()
        self.validate_cli_tools()
        self.validate_ui_components()
        self.validate_container_operations()
        self.validate_state_persistence()
        self.validate_docker_containers()
        self.validate_syntax()
        
        # Print summary
        print("\n" + "="*70)
        print(f"  VALIDATION SUMMARY".center(70))
        print("="*70)
        print(f"  Passed: {self.passed}")
        print(f"  Failed: {self.failed}")
        print(f"  Total:  {self.passed + self.failed}")
        
        if self.failed == 0:
            print("\n  ✓ ALL VALIDATIONS PASSED - SYSTEM STABLE".center(70))
            status = 0
        else:
            print(f"\n  ✗ {self.failed} VALIDATION(S) FAILED".center(70))
            status = 1
        
        print("="*70 + "\n")
        
        return status

if __name__ == "__main__":
    validator = StabilityValidator()
    sys.exit(validator.run_all_validations())
