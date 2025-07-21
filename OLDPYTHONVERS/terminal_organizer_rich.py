#!/usr/bin/env python3
"""
Terminal Environment Organizer - Rich CLI Version
Interactive terminal-based interface for managing terminal environments.
"""

import os
import sys
import subprocess
import json
import platform
import time
import shlex
import signal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Rich imports
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns
from rich.tree import Tree
from rich.status import Status
from rich import box
from rich.align import Align

@dataclass
class TerminalEnvironment:
    name: str
    path: str
    type: str
    version: str = ""
    description: str = ""
    is_available: bool = True
    launch_command: str = ""
    process_id: Optional[int] = None

class TerminalScanner:
    def __init__(self):
        self.system = platform.system()
        self.environments = []
        
    def scan_all_environments(self) -> List[TerminalEnvironment]:
        """Scan for all available terminal environments"""
        self.environments = []
        
        # Core system terminals
        self._scan_system_terminals()
        
        # Development environments
        self._scan_development_environments()
        
        # Virtualization and containers
        self._scan_virtualization_environments()
        
        # Cloud shells
        self._scan_cloud_shells()
        
        # Text editors with terminal support
        self._scan_editor_terminals()
        
        return self.environments
    
    def _add_environment(self, name: str, path: str, env_type: str, 
                        description: str = "", launch_cmd: str = ""):
        """Add environment if it exists and is accessible"""
        if os.path.exists(path) or self._command_exists(path):
            try:
                version = self._get_version(path, name)
                launch_command = launch_cmd or path
                env = TerminalEnvironment(
                    name=name,
                    path=path,
                    type=env_type,
                    version=version,
                    description=description,
                    launch_command=launch_command
                )
                self.environments.append(env)
            except Exception:
                pass
    
    def _get_version(self, path: str, name: str) -> str:
        """Get version information for a terminal environment"""
        try:
            version_commands = {
                'python': [path, '--version'],
                'julia': [path, '--version'],
                'node': [path, '--version'],
                'powershell': ['powershell', '-Command', '$PSVersionTable.PSVersion'],
                'pwsh': ['pwsh', '-Command', '$PSVersionTable.PSVersion'],
                'git': ['git', '--version'],
                'docker': ['docker', '--version'],
                'wsl': ['wsl', '--version']
            }
            
            for key, cmd in version_commands.items():
                if key.lower() in name.lower():
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return result.stdout.strip().split('\n')[0]
                    break
        except:
            pass
        return "Unknown"
    
    def _scan_system_terminals(self):
        """Scan for system terminal environments"""
        if self.system == "Windows":
            # Windows terminals
            self._add_environment("Command Prompt", "cmd.exe", "System Shell", 
                                "Windows Command Prompt", "cmd")
            
            # PowerShell variants
            ps_paths = [
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                r"C:\Program Files\PowerShell\7\pwsh.exe",
                r"C:\Program Files (x86)\PowerShell\7\pwsh.exe"
            ]
            
            for ps_path in ps_paths:
                if os.path.exists(ps_path):
                    ps_name = "PowerShell Core" if "pwsh" in ps_path else "Windows PowerShell"
                    self._add_environment(ps_name, ps_path, "PowerShell", 
                                        "Microsoft PowerShell Environment")
            
            # Windows Terminal
            wt_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"),
            ]
            
            for wt_path in wt_paths:
                if os.path.exists(wt_path):
                    self._add_environment("Windows Terminal", wt_path, "Terminal Emulator",
                                        "Modern Windows Terminal")
            
            # Git Bash
            git_bash_paths = [
                r"C:\Program Files\Git\bin\bash.exe",
                r"C:\Program Files (x86)\Git\bin\bash.exe"
            ]
            
            for gb_path in git_bash_paths:
                if os.path.exists(gb_path):
                    self._add_environment("Git Bash", gb_path, "Unix Shell",
                                        "Git Bash Unix-like shell")
        
        elif self.system == "Linux":
            # Common Linux shells
            shells = [
                ("/bin/bash", "Bash", "Unix Shell"),
                ("/bin/zsh", "Zsh", "Unix Shell"),
                ("/bin/fish", "Fish", "Unix Shell"),
                ("/bin/sh", "Bourne Shell", "Unix Shell"),
                ("/usr/bin/bash", "Bash", "Unix Shell"),
                ("/usr/bin/zsh", "Zsh", "Unix Shell")
            ]
            
            for path, name, shell_type in shells:
                if os.path.exists(path):
                    self._add_environment(name, path, shell_type, f"{name} shell environment")
        
        elif self.system == "Darwin":  # macOS
            # macOS shells
            shells = [
                ("/bin/bash", "Bash", "Unix Shell"),
                ("/bin/zsh", "Zsh", "Unix Shell"),
                ("/usr/local/bin/fish", "Fish", "Unix Shell"),
                ("/opt/homebrew/bin/fish", "Fish (Homebrew)", "Unix Shell")
            ]
            
            for path, name, shell_type in shells:
                if os.path.exists(path):
                    self._add_environment(name, path, shell_type, f"{name} shell environment")
    
    def _scan_development_environments(self):
        """Scan for development environment terminals"""
        # Python environments
        python_paths = self._find_executables("python")
        python_paths.extend(self._find_executables("python3"))
        for path in set(python_paths):
            self._add_environment(f"Python ({os.path.basename(path)})", path, "Interpreter",
                                "Python interactive interpreter")
        
        # Julia
        julia_paths = self._find_executables("julia")
        for path in julia_paths:
            self._add_environment(f"Julia", path, "Interpreter",
                                "Julia interactive environment")
        
        # Node.js
        node_paths = self._find_executables("node")
        for path in node_paths:
            self._add_environment(f"Node.js", path, "Interpreter",
                                "Node.js JavaScript runtime")
        
        # R
        r_paths = self._find_executables("R")
        for path in r_paths:
            self._add_environment(f"R", path, "Statistical Environment",
                                "R statistical computing environment")
    
    def _scan_virtualization_environments(self):
        """Scan for virtualization and container environments"""
        # Docker
        docker_paths = self._find_executables("docker")
        for path in docker_paths:
            self._add_environment("Docker", path, "Container Platform",
                                "Docker container management")
        
        # WSL (Windows Subsystem for Linux)
        if self.system == "Windows":
            wsl_path = self._find_executable("wsl")
            if wsl_path:
                self._add_environment("WSL", wsl_path, "Linux Subsystem",
                                    "Windows Subsystem for Linux")
        
        # Conda environments
        conda_path = self._find_executable("conda")
        if conda_path:
            self._add_environment("Conda", conda_path, "Package Manager",
                                "Conda package and environment manager")
    
    def _scan_cloud_shells(self):
        """Scan for cloud shell environments"""
        # Azure CLI
        az_path = self._find_executable("az")
        if az_path:
            self._add_environment("Azure CLI", az_path, "Cloud Shell",
                                "Azure Command Line Interface")
        
        # AWS CLI
        aws_path = self._find_executable("aws")
        if aws_path:
            self._add_environment("AWS CLI", aws_path, "Cloud Shell",
                                "Amazon Web Services CLI")
        
        # Google Cloud SDK
        gcloud_path = self._find_executable("gcloud")
        if gcloud_path:
            self._add_environment("Google Cloud SDK", gcloud_path, "Cloud Shell",
                                "Google Cloud Platform CLI")
    
    def _scan_editor_terminals(self):
        """Scan for text editors with integrated terminals"""
        # VS Code
        if self._command_exists("code"):
            self._add_environment("VS Code", "code", "Editor with Terminal",
                                "Visual Studio Code integrated terminal",
                                "code --new-window")
        
        # Other editors
        editors = [
            ("vim", "Vim", "Text Editor"),
            ("nvim", "Neovim", "Text Editor"),
            ("emacs", "Emacs", "Text Editor"),
            ("nano", "Nano", "Text Editor")
        ]
        
        for cmd, name, editor_type in editors:
            if self._command_exists(cmd):
                path = self._find_executable(cmd)
                if path:
                    self._add_environment(name, path, editor_type, f"{name} text editor")
    
    def _find_executables(self, name: str) -> List[str]:
        """Find all instances of an executable in PATH"""
        paths = []
        
        if self.system == "Windows":
            extensions = [".exe", ".cmd", ".bat", ""]
            search_paths = os.environ.get("PATH", "").split(os.pathsep)
            
            for path in search_paths:
                for ext in extensions:
                    full_path = os.path.join(path, name + ext)
                    if os.path.exists(full_path):
                        paths.append(full_path)
        else:
            # Unix-like systems
            try:
                result = subprocess.run(["which", "-a", name], capture_output=True, text=True)
                if result.returncode == 0:
                    paths = [p.strip() for p in result.stdout.split('\n') if p.strip()]
            except:
                pass
        
        return list(set(paths))  # Remove duplicates
    
    def _find_executable(self, name: str) -> Optional[str]:
        """Find first instance of executable"""
        paths = self._find_executables(name)
        return paths[0] if paths else None
    
    def _command_exists(self, command: str) -> bool:
        """Check if command exists in PATH"""
        try:
            if self.system == "Windows":
                subprocess.run(["where", command], capture_output=True, timeout=2, check=True)
            else:
                subprocess.run(["which", command], capture_output=True, timeout=2, check=True)
            return True
        except:
            return False

class TerminalOrganizerCLI:
    def __init__(self):
        self.console = Console()
        self.scanner = TerminalScanner()
        self.environments = []
        self.running_processes = {}
        self.current_filter = ""
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.console.print("\n[yellow]Shutting down Terminal Organizer...[/yellow]")
        self._cleanup_processes()
        sys.exit(0)
    
    def _cleanup_processes(self):
        """Clean up any running processes"""
        for name, process in self.running_processes.copy().items():
            if process.poll() is None:  # Process is still running
                process.terminate()
                self.console.print(f"[yellow]Terminated {name}[/yellow]")
        self.running_processes.clear()
    
    def show_banner(self):
        """Display the application banner"""
        banner = Text("Terminal Environment Organizer", style="bold blue")
        subtitle = Text("Rich CLI Version", style="italic cyan")
        
        banner_panel = Panel(
            Align.center(f"{banner}\n{subtitle}"),
            box=box.DOUBLE,
            padding=(1, 2),
            style="blue"
        )
        
        self.console.print(banner_panel)
        self.console.print()
    
    def show_help(self):
        """Display help information"""
        help_table = Table(title="Available Commands", box=box.ROUNDED)
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        help_table.add_column("Usage", style="yellow")
        
        commands = [
            ("lt", "List all terminal environments", "lt [filter]"),
            ("open", "Open a terminal environment", "open <number|name>"),
            ("refresh", "Refresh the environment list", "refresh"),
            ("help", "Show this help message", "help"),
            ("borg", "Back to organizer (close terminals)", "borg"),
            ("kill", "Kill a running terminal", "kill <number|name>"),
            ("status", "Show running terminals", "status"),
            ("info", "Show detailed environment info", "info <number|name>"),
            ("export", "Export configuration to JSON", "export [filename]"),
            ("search", "Search environments by name/type", "search <query>"),
            ("quit", "Exit the organizer", "quit"),
            ("clear", "Clear the screen", "clear")
        ]
        
        for cmd, desc, usage in commands:
            help_table.add_row(cmd, desc, usage)
        
        self.console.print(help_table)
        self.console.print()
    
    def load_environments(self):
        """Load terminal environments with progress indicator"""
        with self.console.status("[bold green]Scanning for terminal environments...") as status:
            self.environments = self.scanner.scan_all_environments()
        
        self.console.print(f"[green]✓[/green] Found {len(self.environments)} terminal environments")
        self.console.print()
    
    def list_terminals(self, filter_term: str = ""):
        """List all available terminal environments"""
        if not self.environments:
            self.console.print("[red]No terminal environments found. Try running 'refresh' first.[/red]")
            return
        
        # Filter environments if filter term provided
        filtered_envs = self.environments
        if filter_term:
            filtered_envs = [
                env for env in self.environments 
                if filter_term.lower() in env.name.lower() or 
                   filter_term.lower() in env.type.lower()
            ]
        
        if not filtered_envs:
            self.console.print(f"[yellow]No environments found matching '{filter_term}'[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Terminal Environments{' (Filtered)' if filter_term else ''}", 
                     box=box.ROUNDED)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Name", style="white", min_width=20)
        table.add_column("Type", style="yellow", width=15)
        table.add_column("Version", style="green", width=15)
        table.add_column("Status", style="magenta", width=10)
        
        for i, env in enumerate(filtered_envs, 1):
            # Check if this environment is currently running
            status = "🟢 Ready" if env.is_available else "🔴 Error"
            if env.name in self.running_processes:
                process = self.running_processes[env.name]
                if process.poll() is None:
                    status = "🟡 Running"
                else:
                    # Process finished, remove from tracking
                    del self.running_processes[env.name]
                    status = "🟢 Ready"
            
            table.add_row(
                str(i),
                env.name,
                env.type,
                env.version[:15] if env.version else "Unknown",
                status
            )
        
        self.console.print(table)
        self.console.print()
    
    def show_environment_info(self, identifier: str):
        """Show detailed information about an environment"""
        env = self._find_environment(identifier)
        if not env:
            self.console.print(f"[red]Environment '{identifier}' not found[/red]")
            return
        
        # Create info panel
        info_text = f"""[bold cyan]Name:[/bold cyan] {env.name}
[bold cyan]Type:[/bold cyan] {env.type}
[bold cyan]Path:[/bold cyan] {env.path}
[bold cyan]Version:[/bold cyan] {env.version}
[bold cyan]Description:[/bold cyan] {env.description}
[bold cyan]Launch Command:[/bold cyan] {env.launch_command}
[bold cyan]Available:[/bold cyan] {'Yes' if env.is_available else 'No'}

[bold yellow]System Information:[/bold yellow]
[cyan]Platform:[/cyan] {platform.system()} {platform.release()}
[cyan]Architecture:[/cyan] {platform.machine()}
[cyan]Python Version:[/cyan] {platform.python_version()}"""
        
        panel = Panel(info_text, title=f"Environment Details: {env.name}", 
                     box=box.ROUNDED, padding=(1, 2))
        self.console.print(panel)
        self.console.print()
    
    def open_terminal(self, identifier: str):
        """Open a terminal environment"""
        env = self._find_environment(identifier)
        if not env:
            self.console.print(f"[red]Environment '{identifier}' not found[/red]")
            return
        
        if env.name in self.running_processes:
            process = self.running_processes[env.name]
            if process.poll() is None:
                self.console.print(f"[yellow]'{env.name}' is already running[/yellow]")
                return
            else:
                # Process finished, remove from tracking
                del self.running_processes[env.name]
        
        try:
            self.console.print(f"[green]Launching {env.name}...[/green]")
            
            # Launch the environment
            if platform.system() == "Windows":
                process = subprocess.Popen(env.launch_command, shell=True)
            else:
                # Use shlex to properly split the command
                cmd_parts = shlex.split(env.launch_command)
                process = subprocess.Popen(cmd_parts)
            
            # Track the process
            self.running_processes[env.name] = process
            
            self.console.print(f"[green]✓[/green] {env.name} launched successfully (PID: {process.pid})")
            
        except Exception as e:
            self.console.print(f"[red]Failed to launch {env.name}: {str(e)}[/red]")
    
    def show_status(self):
        """Show status of running terminals"""
        if not self.running_processes:
            self.console.print("[yellow]No terminals currently running[/yellow]")
            return
        
        table = Table(title="Running Terminals", box=box.ROUNDED)
        table.add_column("Name", style="white")
        table.add_column("PID", style="cyan")
        table.add_column("Status", style="green")
        
        # Clean up finished processes
        finished = []
        for name, process in self.running_processes.items():
            if process.poll() is None:
                table.add_row(name, str(process.pid), "Running")
            else:
                finished.append(name)
        
        # Remove finished processes
        for name in finished:
            del self.running_processes[name]
        
        if table.row_count == 0:
            self.console.print("[yellow]No terminals currently running[/yellow]")
        else:
            self.console.print(table)
        self.console.print()
    
    def kill_terminal(self, identifier: str):
        """Kill a running terminal"""
        env = self._find_environment(identifier)
        if not env:
            self.console.print(f"[red]Environment '{identifier}' not found[/red]")
            return
        
        if env.name not in self.running_processes:
            self.console.print(f"[yellow]'{env.name}' is not currently running[/yellow]")
            return
        
        process = self.running_processes[env.name]
        if process.poll() is not None:
            # Process already finished
            del self.running_processes[env.name]
            self.console.print(f"[yellow]'{env.name}' was not running[/yellow]")
            return
        
        try:
            process.terminate()
            # Wait a bit for graceful termination
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()  # Force kill if it doesn't terminate gracefully
            
            del self.running_processes[env.name]
            self.console.print(f"[green]✓[/green] Terminated '{env.name}'")
            
        except Exception as e:
            self.console.print(f"[red]Failed to kill '{env.name}': {str(e)}[/red]")
    
    def back_to_organizer(self):
        """Close all running terminals and return to organizer"""
        if not self.running_processes:
            self.console.print("[yellow]No terminals to close[/yellow]")
            return
        
        if Confirm.ask("Close all running terminals?"):
            self._cleanup_processes()
            self.console.print("[green]✓[/green] All terminals closed")
    
    def export_config(self, filename: str = ""):
        """Export environment configuration to JSON"""
        if not filename:
            filename = f"terminal_environments_{time.strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            config = {
                "environments": [asdict(env) for env in self.environments],
                "system_info": {
                    "platform": platform.system(),
                    "architecture": platform.machine(),
                    "python_version": platform.python_version()
                },
                "export_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.console.print(f"[green]✓[/green] Configuration exported to {filename}")
            
        except Exception as e:
            self.console.print(f"[red]Failed to export configuration: {str(e)}[/red]")
    
    def search_environments(self, query: str):
        """Search environments by name or type"""
        if not query:
            self.console.print("[yellow]Please provide a search query[/yellow]")
            return
        
        self.list_terminals(query)
    
    def _find_environment(self, identifier: str) -> Optional[TerminalEnvironment]:
        """Find environment by number or name"""
        # Try as number first
        try:
            index = int(identifier) - 1
            if 0 <= index < len(self.environments):
                return self.environments[index]
        except ValueError:
            pass
        
        # Try as name
        for env in self.environments:
            if env.name.lower() == identifier.lower():
                return env
        
        # Try partial name match
        matches = [env for env in self.environments if identifier.lower() in env.name.lower()]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            self.console.print(f"[yellow]Multiple matches found for '{identifier}':[/yellow]")
            for i, env in enumerate(matches, 1):
                self.console.print(f"  {i}. {env.name}")
            return None
        
        return None
    
    def run(self):
        """Main application loop"""
        self.show_banner()
        
        # Initial scan
        self.load_environments()
        
        # Show initial list
        self.list_terminals()
        
        while True:
            try:
                # Get user input
                command_input = Prompt.ask("[bold cyan]organizer[/bold cyan]", default="help")
                command_parts = command_input.strip().split()
                
                if not command_parts:
                    continue
                
                command = command_parts[0].lower()
                args = command_parts[1:] if len(command_parts) > 1 else []
                
                # Process commands
                if command in ['quit', 'exit', 'q']:
                    if self.running_processes:
                        if Confirm.ask("You have running terminals. Close them and exit?"):
                            self._cleanup_processes()
                            break
                        else:
                            continue
                    else:
                        break
                
                elif command == 'help':
                    self.show_help()
                
                elif command == 'lt':
                    filter_term = ' '.join(args) if args else ""
                    self.list_terminals(filter_term)
                
                elif command == 'open':
                    if args:
                        self.open_terminal(' '.join(args))
                    else:
                        self.console.print("[yellow]Usage: open <number|name>[/yellow]")
                
                elif command == 'refresh':
                    self.load_environments()
                    self.list_terminals()
                
                elif command == 'status':
                    self.show_status()
                
                elif command == 'info':
                    if args:
                        self.show_environment_info(' '.join(args))
                    else:
                        self.console.print("[yellow]Usage: info <number|name>[/yellow]")
                
                elif command == 'kill':
                    if args:
                        self.kill_terminal(' '.join(args))
                    else:
                        self.console.print("[yellow]Usage: kill <number|name>[/yellow]")
                
                elif command == 'borg':
                    self.back_to_organizer()
                
                elif command == 'export':
                    filename = ' '.join(args) if args else ""
                    self.export_config(filename)
                
                elif command == 'search':
                    if args:
                        self.search_environments(' '.join(args))
                    else:
                        self.console.print("[yellow]Usage: search <query>[/yellow]")
                
                elif command == 'clear':
                    self.console.clear()
                    self.show_banner()
                
                else:
                    self.console.print(f"[red]Unknown command: {command}[/red]")
                    self.console.print("Type 'help' for available commands")
            
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'quit' to exit or Ctrl+C again to force exit[/yellow]")
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    self._cleanup_processes()
                    break
            except EOFError:
                break
        
        self.console.print("\n[green]Thank you for using Terminal Environment Organizer![/green]")

def main():
    """Main entry point"""
    try:
        app = TerminalOrganizerCLI()
        app.run()
    except ImportError as e:
        print("Error: Missing required dependency.")
        print("Please install the Rich library:")
        print("pip install rich")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
