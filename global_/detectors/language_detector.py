"""
Language Detector - Sophisticated Programming Language Detection System
Detects installed programming languages, development tools, and their versions
across Windows, macOS, and Linux systems.
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LanguageType(Enum):
    """Programming language categories"""
    COMPILED = "Compiled"
    INTERPRETED = "Interpreted"
    JVM = "JVM-based"
    DOTNET = ".NET-based"
    WEB = "Web/JavaScript"
    SCRIPTING = "Scripting"
    FUNCTIONAL = "Functional"
    DATA_SCIENCE = "Data Science"
    DEVOPS = "DevOps/Infrastructure"
    SHELL = "Shell/Scripting"
    QUERY = "Query Language"


class LanguageStatus(Enum):
    """Installation status"""
    INSTALLED = "Installed"
    PARTIAL = "Partially Installed"
    NOT_INSTALLED = "Not Installed"
    BROKEN = "Broken/Incomplete"


@dataclass
class ToolInfo:
    """Information about a development tool"""
    name: str
    version: str
    path: str
    is_available: bool
    description: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class LanguageInfo:
    """Detailed information about an installed language"""
    name: str
    version: str
    path: str
    status: LanguageStatus
    lang_type: LanguageType
    
    # Additional tools (compiler, interpreter, package manager, etc.)
    compiler: Optional[ToolInfo] = None
    interpreter: Optional[ToolInfo] = None
    package_manager: Optional[ToolInfo] = None
    build_tool: Optional[ToolInfo] = None
    linter: Optional[ToolInfo] = None
    formatter: Optional[ToolInfo] = None
    debugger: Optional[ToolInfo] = None
    test_framework: Optional[ToolInfo] = None
    
    # Additional metadata
    installation_path: str = ""
    home_page: str = ""
    is_default_version: bool = False
    additional_versions: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)

    def to_dict(self):
        """Convert to dictionary, handling objects"""
        result = {
            'name': self.name,
            'version': self.version,
            'path': self.path,
            'status': self.status.value,
            'type': self.lang_type.value,
            'installation_path': self.installation_path,
            'home_page': self.home_page,
            'is_default_version': self.is_default_version,
            'additional_versions': self.additional_versions,
        }
        
        # Add tool info
        for tool_name in ['compiler', 'interpreter', 'package_manager', 'build_tool', 
                          'linter', 'formatter', 'debugger', 'test_framework']:
            tool = getattr(self, tool_name)
            if tool:
                result[tool_name] = tool.to_dict()
        
        return result


@dataclass
class DetectedLanguage:
    """Container for detected language information"""
    language: LanguageInfo
    confidence: float  # 0.0 to 1.0
    detection_method: str  # "PATH", "REGISTRY", "PACKAGE_MANAGER", etc.
    is_available_immediately: bool = True
    additional_notes: str = ""

    def to_dict(self):
        return {
            'language': self.language.to_dict(),
            'confidence': self.confidence,
            'detection_method': self.detection_method,
            'is_available_immediately': self.is_available_immediately,
            'additional_notes': self.additional_notes,
        }


class OSDetector(ABC):
    """Abstract base class for OS-specific language detection"""
    
    def __init__(self):
        self.system_type = platform.system()
    
    @abstractmethod
    def detect_python(self) -> Optional[LanguageInfo]:
        """Detect Python installations"""
        pass
    
    @abstractmethod
    def detect_node(self) -> Optional[LanguageInfo]:
        """Detect Node.js installations"""
        pass
    
    @abstractmethod
    def detect_java(self) -> Optional[LanguageInfo]:
        """Detect Java installations"""
        pass
    
    @abstractmethod
    def detect_rust(self) -> Optional[LanguageInfo]:
        """Detect Rust installations"""
        pass
    
    @abstractmethod
    def detect_go(self) -> Optional[LanguageInfo]:
        """Detect Go installations"""
        pass
    
    @abstractmethod
    def detect_cpp(self) -> Optional[LanguageInfo]:
        """Detect C++ installations"""
        pass
    
    @abstractmethod
    def detect_csharp(self) -> Optional[LanguageInfo]:
        """Detect C# installations"""
        pass
    
    @abstractmethod
    def detect_ruby(self) -> Optional[LanguageInfo]:
        """Detect Ruby installations"""
        pass
    
    def get_command_version(self, command: str, version_args: List[str] = None) -> Optional[Tuple[str, str]]:
        """
        Get version info from a command
        Returns: (version_string, path_to_executable)
        """
        if version_args is None:
            version_args = ["--version"]
        
        try:
            # First, find the command in PATH
            result = subprocess.run(
                ["where" if self.system_type == "Windows" else "which", command],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            command_path = result.stdout.strip().split('\n')[0]
            
            # Get version
            result = subprocess.run(
                [command] + version_args,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = (result.stdout + result.stderr).strip().split('\n')[0]
                return version, command_path
        except Exception as e:
            logger.debug(f"Error getting version for {command}: {e}")
        
        return None


class WindowsDetector(OSDetector):
    """Windows-specific language detection"""
    
    def __init__(self):
        super().__init__()
        self.registry_installed_paths = self._scan_registry()
    
    def _scan_registry(self) -> Dict[str, str]:
        """Scan Windows registry for installed applications"""
        paths = {}
        try:
            import winreg
            
            # Common registry paths for language installations
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Python"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft"),
            ]
            
            for hive, path in registry_paths:
                try:
                    with winreg.OpenKey(hive, path) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            subkey_name = winreg.EnumKeyEx(key, i)
                            paths[subkey_name] = f"HKEY: {path}\\{subkey_name}"
                except Exception:
                    pass
        except ImportError:
            logger.debug("winreg not available on this system")
        
        return paths
    
    def detect_python(self) -> Optional[LanguageInfo]:
        """Detect Python (Windows)"""
        version_info = self.get_command_version("python", ["-c", "import sys; print(sys.version)"])
        
        if not version_info:
            # Try python3
            version_info = self.get_command_version("python3", ["-c", "import sys; print(sys.version)"])
        
        if version_info:
            version, path = version_info
            # Extract version number
            version_clean = version.split()[0]
            
            # Detect pip and other tools
            pip_info = self.get_command_version("pip", ["--version"])
            
            return LanguageInfo(
                name="Python",
                version=version_clean,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.INTERPRETED,
                interpreter=ToolInfo("Python", version_clean, path, True, "Python interpreter"),
                package_manager=ToolInfo("pip", pip_info[0] if pip_info else "Unknown", 
                                        pip_info[1] if pip_info else "", bool(pip_info), "Package manager"),
            )
        
        return None
    
    def detect_node(self) -> Optional[LanguageInfo]:
        """Detect Node.js (Windows)"""
        version_info = self.get_command_version("node", ["-v"])
        
        if version_info:
            version, path = version_info
            version = version.lstrip('v')  # Remove 'v' prefix
            
            npm_info = self.get_command_version("npm", ["--version"])
            yarn_info = self.get_command_version("yarn", ["--version"])
            
            return LanguageInfo(
                name="Node.js",
                version=version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.WEB,
                interpreter=ToolInfo("Node.js", version, path, True, "JavaScript runtime"),
                package_manager=ToolInfo("npm", npm_info[0] if npm_info else "Unknown",
                                        npm_info[1] if npm_info else "", bool(npm_info), "Package manager"),
            )
        
        return None
    
    def detect_java(self) -> Optional[LanguageInfo]:
        """Detect Java (Windows)"""
        version_info = self.get_command_version("java", ["-version"])
        
        if version_info:
            version, path = version_info
            
            javac_info = self.get_command_version("javac", ["-version"])
            maven_info = self.get_command_version("mvn", ["-version"])
            gradle_info = self.get_command_version("gradle", ["--version"])
            
            return LanguageInfo(
                name="Java",
                version=version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.JVM,
                interpreter=ToolInfo("JVM", version, path, True, "Java Virtual Machine"),
                compiler=ToolInfo("javac", javac_info[0] if javac_info else "Unknown",
                                 javac_info[1] if javac_info else "", bool(javac_info), "Java compiler"),
                build_tool=ToolInfo("Maven", maven_info[0] if maven_info else "Unknown",
                                   maven_info[1] if maven_info else "", bool(maven_info), "Build tool"),
            )
        
        return None
    
    def detect_rust(self) -> Optional[LanguageInfo]:
        """Detect Rust (Windows)"""
        version_info = self.get_command_version("rustc", ["-V"])
        
        if version_info:
            version, path = version_info
            
            cargo_info = self.get_command_version("cargo", ["--version"])
            rustup_info = self.get_command_version("rustup", ["--version"])
            
            return LanguageInfo(
                name="Rust",
                version=version.split()[1] if len(version.split()) > 1 else version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.COMPILED,
                compiler=ToolInfo("rustc", version, path, True, "Rust compiler"),
                build_tool=ToolInfo("Cargo", cargo_info[0] if cargo_info else "Unknown",
                                   cargo_info[1] if cargo_info else "", bool(cargo_info), "Build system"),
            )
        
        return None
    
    def detect_go(self) -> Optional[LanguageInfo]:
        """Detect Go (Windows)"""
        version_info = self.get_command_version("go", ["version"])
        
        if version_info:
            version, path = version_info
            version_clean = version.split()[2] if len(version.split()) > 2 else version
            
            return LanguageInfo(
                name="Go",
                version=version_clean.lstrip('go'),
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.COMPILED,
                compiler=ToolInfo("Go", version_clean, path, True, "Go compiler"),
            )
        
        return None
    
    def detect_cpp(self) -> Optional[LanguageInfo]:
        """Detect C++ (Windows)"""
        version_info = self.get_command_version("g++", ["-v"])
        
        if version_info:
            version, path = version_info
            
            gcc_info = self.get_command_version("gcc", ["-v"])
            clang_info = self.get_command_version("clang", ["--version"])
            gdb_info = self.get_command_version("gdb", ["--version"])
            
            return LanguageInfo(
                name="C++",
                version=version.split('\n')[-1] if version else "Unknown",
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.COMPILED,
                compiler=ToolInfo("G++", version, path, True, "C++ compiler"),
                debugger=ToolInfo("GDB", gdb_info[0] if gdb_info else "Unknown",
                                 gdb_info[1] if gdb_info else "", bool(gdb_info), "Debugger"),
            )
        
        return None
    
    def detect_csharp(self) -> Optional[LanguageInfo]:
        """Detect C# (.NET) (Windows)"""
        version_info = self.get_command_version("dotnet", ["--version"])
        
        if version_info:
            version, path = version_info
            
            return LanguageInfo(
                name="C#",
                version=version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.DOTNET,
                compiler=ToolInfo(".NET SDK", version, path, True, ".NET toolchain"),
            )
        
        return None
    
    def detect_ruby(self) -> Optional[LanguageInfo]:
        """Detect Ruby (Windows)"""
        version_info = self.get_command_version("ruby", ["-v"])
        
        if version_info:
            version, path = version_info
            
            gem_info = self.get_command_version("gem", ["--version"])
            bundler_info = self.get_command_version("bundle", ["--version"])
            
            return LanguageInfo(
                name="Ruby",
                version=version.split()[1] if len(version.split()) > 1 else version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.INTERPRETED,
                interpreter=ToolInfo("Ruby", version, path, True, "Ruby interpreter"),
                package_manager=ToolInfo("RubyGems", gem_info[0] if gem_info else "Unknown",
                                        gem_info[1] if gem_info else "", bool(gem_info), "Package manager"),
            )
        
        return None


class UnixDetector(OSDetector):
    """Unix/Linux/macOS-specific language detection"""
    
    def detect_python(self) -> Optional[LanguageInfo]:
        """Detect Python (Unix-like)"""
        version_info = self.get_command_version("python3", ["-c", "import sys; print(sys.version)"])
        
        if not version_info:
            version_info = self.get_command_version("python", ["-c", "import sys; print(sys.version)"])
        
        if version_info:
            version, path = version_info
            version_clean = version.split()[0]
            
            pip_info = self.get_command_version("pip3", ["--version"])
            if not pip_info:
                pip_info = self.get_command_version("pip", ["--version"])
            
            return LanguageInfo(
                name="Python",
                version=version_clean,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.INTERPRETED,
                interpreter=ToolInfo("Python", version_clean, path, True, "Python interpreter"),
                package_manager=ToolInfo("pip", pip_info[0] if pip_info else "Unknown",
                                        pip_info[1] if pip_info else "", bool(pip_info), "Package manager"),
            )
        
        return None
    
    def detect_node(self) -> Optional[LanguageInfo]:
        """Detect Node.js (Unix-like)"""
        version_info = self.get_command_version("node", ["-v"])
        
        if version_info:
            version, path = version_info
            version = version.lstrip('v')
            
            npm_info = self.get_command_version("npm", ["--version"])
            yarn_info = self.get_command_version("yarn", ["--version"])
            
            return LanguageInfo(
                name="Node.js",
                version=version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.WEB,
                interpreter=ToolInfo("Node.js", version, path, True, "JavaScript runtime"),
                package_manager=ToolInfo("npm", npm_info[0] if npm_info else "Unknown",
                                        npm_info[1] if npm_info else "", bool(npm_info), "Package manager"),
            )
        
        return None
    
    def detect_java(self) -> Optional[LanguageInfo]:
        """Detect Java (Unix-like)"""
        version_info = self.get_command_version("java", ["-version"])
        
        if version_info:
            version, path = version_info
            
            javac_info = self.get_command_version("javac", ["-version"])
            maven_info = self.get_command_version("mvn", ["-version"])
            
            return LanguageInfo(
                name="Java",
                version=version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.JVM,
                interpreter=ToolInfo("JVM", version, path, True, "Java Virtual Machine"),
                compiler=ToolInfo("javac", javac_info[0] if javac_info else "Unknown",
                                 javac_info[1] if javac_info else "", bool(javac_info), "Java compiler"),
            )
        
        return None
    
    def detect_rust(self) -> Optional[LanguageInfo]:
        """Detect Rust (Unix-like)"""
        version_info = self.get_command_version("rustc", ["-V"])
        
        if version_info:
            version, path = version_info
            
            cargo_info = self.get_command_version("cargo", ["--version"])
            
            return LanguageInfo(
                name="Rust",
                version=version.split()[1] if len(version.split()) > 1 else version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.COMPILED,
                compiler=ToolInfo("rustc", version, path, True, "Rust compiler"),
                build_tool=ToolInfo("Cargo", cargo_info[0] if cargo_info else "Unknown",
                                   cargo_info[1] if cargo_info else "", bool(cargo_info), "Build system"),
            )
        
        return None
    
    def detect_go(self) -> Optional[LanguageInfo]:
        """Detect Go (Unix-like)"""
        version_info = self.get_command_version("go", ["version"])
        
        if version_info:
            version, path = version_info
            version_clean = version.split()[2] if len(version.split()) > 2 else version
            
            return LanguageInfo(
                name="Go",
                version=version_clean.lstrip('go'),
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.COMPILED,
                compiler=ToolInfo("Go", version_clean, path, True, "Go compiler"),
            )
        
        return None
    
    def detect_cpp(self) -> Optional[LanguageInfo]:
        """Detect C++ (Unix-like)"""
        version_info = self.get_command_version("g++", ["--version"])
        
        if version_info:
            version, path = version_info
            
            gcc_info = self.get_command_version("gcc", ["--version"])
            clang_info = self.get_command_version("clang", ["--version"])
            gdb_info = self.get_command_version("gdb", ["--version"])
            cmake_info = self.get_command_version("cmake", ["--version"])
            
            return LanguageInfo(
                name="C++",
                version=version.split('\n')[0],
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.COMPILED,
                compiler=ToolInfo("G++", version, path, True, "C++ compiler"),
                debugger=ToolInfo("GDB", gdb_info[0] if gdb_info else "Unknown",
                                 gdb_info[1] if gdb_info else "", bool(gdb_info), "Debugger"),
                build_tool=ToolInfo("CMake", cmake_info[0] if cmake_info else "Unknown",
                                   cmake_info[1] if cmake_info else "", bool(cmake_info), "Build tool"),
            )
        
        return None
    
    def detect_csharp(self) -> Optional[LanguageInfo]:
        """Detect C# (.NET) (Unix-like)"""
        version_info = self.get_command_version("dotnet", ["--version"])
        
        if version_info:
            version, path = version_info
            
            return LanguageInfo(
                name="C#",
                version=version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.DOTNET,
                compiler=ToolInfo(".NET SDK", version, path, True, ".NET toolchain"),
            )
        
        return None
    
    def detect_ruby(self) -> Optional[LanguageInfo]:
        """Detect Ruby (Unix-like)"""
        version_info = self.get_command_version("ruby", ["-v"])
        
        if version_info:
            version, path = version_info
            
            gem_info = self.get_command_version("gem", ["--version"])
            bundler_info = self.get_command_version("bundle", ["--version"])
            
            return LanguageInfo(
                name="Ruby",
                version=version.split()[1] if len(version.split()) > 1 else version,
                path=path,
                status=LanguageStatus.INSTALLED,
                lang_type=LanguageType.INTERPRETED,
                interpreter=ToolInfo("Ruby", version, path, True, "Ruby interpreter"),
                package_manager=ToolInfo("RubyGems", gem_info[0] if gem_info else "Unknown",
                                        gem_info[1] if gem_info else "", bool(gem_info), "Package manager"),
            )
        
        return None


class LanguageDetector:
    """Main Language Detection System"""
    
    def __init__(self):
        self.system_type = platform.system()
        self.detector = self._get_platform_detector()
        self.detected_languages: Dict[str, DetectedLanguage] = {}
        self.cache_file = os.path.expanduser("~/.editor_language_cache.json")
    
    def _get_platform_detector(self) -> OSDetector:
        """Get appropriate detector for current OS"""
        if self.system_type == "Windows":
            return WindowsDetector()
        else:
            return UnixDetector()
    
    def detect_all_languages(self) -> Dict[str, DetectedLanguage]:
        """
        Detect all installed programming languages
        Returns a dict of language name -> DetectedLanguage
        """
        self.detected_languages.clear()
        
        # List of detection methods in order
        detection_methods = [
            ("Python", self.detector.detect_python),
            ("Node.js", self.detector.detect_node),
            ("Java", self.detector.detect_java),
            ("Rust", self.detector.detect_rust),
            ("Go", self.detector.detect_go),
            ("C++", self.detector.detect_cpp),
            ("C#", self.detector.detect_csharp),
            ("Ruby", self.detector.detect_ruby),
        ]
        
        for lang_name, detect_func in detection_methods:
            try:
                lang_info = detect_func()
                if lang_info:
                    detected = DetectedLanguage(
                        language=lang_info,
                        confidence=0.95,
                        detection_method="PATH_COMMAND"
                    )
                    self.detected_languages[lang_name] = detected
            except Exception as e:
                logger.debug(f"Error detecting {lang_name}: {e}")
        
        # Cache results
        self._save_to_cache()
        
        return self.detected_languages
    
    def get_detected_language(self, language_name: str) -> Optional[DetectedLanguage]:
        """Get information about a specific detected language"""
        return self.detected_languages.get(language_name)
    
    def is_language_available(self, language_name: str) -> bool:
        """Check if a language is available"""
        detected = self.detected_languages.get(language_name)
        return detected is not None and detected.language.status == LanguageStatus.INSTALLED
    
    def get_language_version(self, language_name: str) -> Optional[str]:
        """Get version of a detected language"""
        detected = self.detected_languages.get(language_name)
        return detected.language.version if detected else None
    
    def get_language_path(self, language_name: str) -> Optional[str]:
        """Get installation path of a language"""
        detected = self.detected_languages.get(language_name)
        return detected.language.path if detected else None
    
    def export_to_json(self, file_path: str = None) -> str:
        """Export detection results to JSON"""
        if file_path is None:
            file_path = self.cache_file
        
        data = {
            'system': self.system_type,
            'detection_timestamp': __import__('datetime').datetime.now().isoformat(),
            'languages': {
                name: lang.to_dict()
                for name, lang in self.detected_languages.items()
            }
        }
        
        os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return file_path
    
    def _save_to_cache(self):
        """Save detection results to cache"""
        try:
            self.export_to_json(self.cache_file)
        except Exception as e:
            logger.warning(f"Failed to save language cache: {e}")
    
    def get_summary(self) -> Dict:
        """Get a summary of detected languages"""
        by_type = {}
        
        for name, detected in self.detected_languages.items():
            lang_type = detected.language.lang_type.value
            if lang_type not in by_type:
                by_type[lang_type] = []
            by_type[lang_type].append({
                'name': name,
                'version': detected.language.version,
                'status': detected.language.status.value,
            })
        
        return {
            'total_languages': len(self.detected_languages),
            'by_type': by_type,
            'system': self.system_type,
        }


# Module-level convenience functions
_detector = None

def get_detector() -> LanguageDetector:
    """Get or create the global language detector instance"""
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector

def detect_languages() -> Dict[str, DetectedLanguage]:
    """Convenience function to detect all languages"""
    return get_detector().detect_all_languages()

def is_language_installed(language_name: str) -> bool:
    """Check if a specific language is installed"""
    return get_detector().is_language_available(language_name)

def get_language_info(language_name: str) -> Optional[LanguageInfo]:
    """Get detailed info about an installed language"""
    detected = get_detector().get_detected_language(language_name)
    return detected.language if detected else None
