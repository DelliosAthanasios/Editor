"""
Language Detector CLI - Rich Terminal Tool
Detect programming languages installed on the system with Rich formatting
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
import os
import sys
import platform
import subprocess
from typing import Dict, Optional, List

console = Console()


class LanguageDetectorCLI:
    """CLI tool for detecting programming languages"""
    
    def __init__(self):
        self.system = platform.system()
        self.detected = {}
    
    def detect_all(self):
        """Detect all installed languages"""
        console.print(Panel("🔍 Programming Language Detector", style="bold blue"))
        
        languages = [
            ("Python", self._detect_python),
            ("Node.js", self._detect_node),
            ("Java", self._detect_java),
            ("Rust", self._detect_rust),
            ("Go", self._detect_go),
            ("C++", self._detect_cpp),
            ("Ruby", self._detect_ruby),
            ("C#", self._detect_csharp),
            ("PHP", self._detect_php),
            ("Haskell", self._detect_haskell),
        ]
        
        console.print("[cyan]Scanning system for installed languages...[/cyan]\n")
        
        for name, detect_func in languages:
            result = detect_func()
            if result:
                self.detected[name] = result
        
        self._display_results()
    
    def _get_version(self, cmd: str, args: List[str] = None) -> Optional[str]:
        """Get version for a command"""
        if args is None:
            args = ["--version"]
        
        try:
            result = subprocess.run(
                [cmd] + args,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                output = (result.stdout + result.stderr).strip()
                return output.split('\n')[0]
        except Exception:
            pass
        return None
    
    def _command_exists(self, cmd: str) -> str:
        """Check if command exists and return path"""
        try:
            if self.system == "Windows":
                result = subprocess.run(
                    ["where", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ["which", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
        return None
    
    def _detect_python(self) -> Optional[Dict]:
        """Detect Python"""
        path = self._command_exists("python3") or self._command_exists("python")
        if not path:
            return None
        
        version = self._get_version("python3" if self._command_exists("python3") else "python", 
                                   ["-c", "import sys; print(sys.version.split()[0])"])
        pip = self._get_version("pip3" if self._command_exists("pip3") else "pip", ["--version"])
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": ["pip/pip3", "virtualenv", "poetry"],
            "package_manager": "pip" if pip else None
        }
    
    def _detect_node(self) -> Optional[Dict]:
        """Detect Node.js"""
        path = self._command_exists("node")
        if not path:
            return None
        
        version = self._get_version("node", ["-v"])
        npm = self._get_version("npm", ["--version"])
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": ["npm", "yarn", "pnpm"],
            "package_manager": "npm" if npm else None
        }
    
    def _detect_java(self) -> Optional[Dict]:
        """Detect Java"""
        path = self._command_exists("java")
        if not path:
            return None
        
        version = self._get_version("java", ["-version"])
        javac = self._command_exists("javac")
        maven = self._command_exists("mvn")
        gradle = self._command_exists("gradle")
        
        tools = []
        if javac:
            tools.append("javac")
        if maven:
            tools.append("maven")
        if gradle:
            tools.append("gradle")
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": tools,
            "build_tools": ["Maven", "Gradle"]
        }
    
    def _detect_rust(self) -> Optional[Dict]:
        """Detect Rust"""
        path = self._command_exists("rustc")
        if not path:
            return None
        
        version = self._get_version("rustc", ["-V"])
        cargo = self._command_exists("cargo")
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": ["cargo", "rustup"],
            "package_manager": "cargo" if cargo else None
        }
    
    def _detect_go(self) -> Optional[Dict]:
        """Detect Go"""
        path = self._command_exists("go")
        if not path:
            return None
        
        version = self._get_version("go", ["version"])
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": ["go modules", "go fmt"],
            "package_manager": "go get"
        }
    
    def _detect_cpp(self) -> Optional[Dict]:
        """Detect C++"""
        path = self._command_exists("g++") or self._command_exists("clang++")
        if not path:
            return None
        
        version = self._get_version("g++" if self._command_exists("g++") else "clang++", ["-v"])
        gcc = self._command_exists("gcc")
        cmake = self._command_exists("cmake")
        
        tools = []
        if gcc:
            tools.append("gcc")
        if cmake:
            tools.append("cmake")
        tools.extend(["make", "gdb"])
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": tools,
            "compiler": "g++/gcc" if gcc else "clang++"
        }
    
    def _detect_ruby(self) -> Optional[Dict]:
        """Detect Ruby"""
        path = self._command_exists("ruby")
        if not path:
            return None
        
        version = self._get_version("ruby", ["-v"])
        gem = self._command_exists("gem")
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": ["gem", "bundler", "rails"],
            "package_manager": "gem" if gem else None
        }
    
    def _detect_csharp(self) -> Optional[Dict]:
        """Detect C#/.NET"""
        path = self._command_exists("dotnet")
        if not path:
            return None
        
        version = self._get_version("dotnet", ["--version"])
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": ["dotnet CLI", "nuget"],
            "framework": ".NET"
        }
    
    def _detect_php(self) -> Optional[Dict]:
        """Detect PHP"""
        path = self._command_exists("php")
        if not path:
            return None
        
        version = self._get_version("php", ["-v"])
        composer = self._command_exists("composer")
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": ["composer", "laravel"],
            "package_manager": "composer" if composer else None
        }
    
    def _detect_haskell(self) -> Optional[Dict]:
        """Detect Haskell"""
        path = self._command_exists("ghc")
        if not path:
            return None
        
        version = self._get_version("ghc", ["-v"])
        stack = self._command_exists("stack")
        
        return {
            "version": version or "Unknown",
            "path": path,
            "tools": ["stack", "cabal"],
            "build_tool": "stack" if stack else "cabal"
        }
    
    def _display_results(self):
        """Display detection results"""
        if not self.detected:
            console.print("[red]No programming languages detected![/red]")
            return
        
        # Summary table
        table = Table(title="Detected Languages", box=box.ROUNDED)
        table.add_column("Language", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Path", style="green")
        table.add_column("Package Manager", style="yellow")
        
        for lang, info in sorted(self.detected.items()):
            pm = info.get("package_manager", "-")
            table.add_row(
                f"✓ {lang}",
                info.get("version", "Unknown"),
                info.get("path", "Unknown")[:50],
                pm if pm else "-"
            )
        
        console.print(table)
        
        # Detailed information
        console.print("\n[bold cyan]Detailed Information:[/bold cyan]\n")
        
        for lang, info in sorted(self.detected.items()):
            panel_content = f"[bold]Version:[/bold] {info.get('version', 'Unknown')}\n"
            panel_content += f"[bold]Path:[/bold] {info.get('path', 'Unknown')}\n"
            
            if info.get("tools"):
                panel_content += f"[bold]Tools:[/bold] {', '.join(info['tools'])}\n"
            
            if info.get("package_manager"):
                panel_content += f"[bold]Package Manager:[/bold] {info['package_manager']}\n"
            
            if info.get("build_tools"):
                panel_content += f"[bold]Build Tools:[/bold] {', '.join(info['build_tools'])}\n"
            
            console.print(Panel(panel_content, title=f"[bold green]{lang}[/bold green]"))
        
        # Summary
        console.print(f"\n[bold green]Total languages detected: {len(self.detected)}[/bold green]")
        console.print(f"[cyan]System: {self.system} {platform.release()}[/cyan]\n")


def main():
    """Main entry point"""
    detector = LanguageDetectorCLI()
    detector.detect_all()


if __name__ == "__main__":
    main()
