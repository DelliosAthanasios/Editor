"""
System Resources Monitor CLI - Rich Terminal Tool
Monitor system resources, CPU, memory, disk usage with Rich formatting
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, DownloadColumn, TextColumn, TimeRemainingColumn
from rich.text import Text
from rich import box
import os
import platform
import psutil
from typing import Dict
import datetime

console = Console()


class SystemMonitorCLI:
    """CLI tool for monitoring system resources"""
    
    def __init__(self):
        self.system = platform.system()
        self.hostname = platform.node()
    
    def show_summary(self):
        """Show system summary"""
        console.print(Panel("💻 System Resources Monitor", style="bold green"))
        
        # System info
        self._show_system_info()
        
        # CPU info
        self._show_cpu_info()
        
        # Memory info
        self._show_memory_info()
        
        # Disk info
        self._show_disk_info()
        
        # Network info
        self._show_network_info()
        
        # Process info
        self._show_process_info()
    
    def _show_system_info(self):
        """Show system information"""
        console.print("[bold cyan]System Information:[/bold cyan]")
        
        table = Table(box=box.SIMPLE)
        table.add_column("Property", style="magenta")
        table.add_column("Value", style="green")
        
        table.add_row("Hostname", self.hostname)
        table.add_row("System", self.system)
        table.add_row("Release", platform.release())
        table.add_row("Version", platform.version())
        table.add_row("Architecture", platform.machine())
        table.add_row("Processor", platform.processor() or "N/A")
        table.add_row("Boot Time", datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Uptime", self._get_uptime())
        
        console.print(table)
        console.print()
    
    def _get_uptime(self) -> str:
        """Get system uptime"""
        uptime_seconds = int(datetime.datetime.now().timestamp() - psutil.boot_time())
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        return f"{days}d {hours}h {minutes}m"
    
    def _show_cpu_info(self):
        """Show CPU information"""
        console.print("[bold cyan]CPU Information:[/bold cyan]")
        
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        table = Table(box=box.SIMPLE)
        table.add_column("Property", style="magenta")
        table.add_column("Value", style="green")
        
        table.add_row("Physical Cores", str(cpu_count_physical))
        table.add_row("Logical Cores", str(cpu_count_logical))
        table.add_row("Current Frequency", f"{cpu_freq.current:.2f} MHz")
        table.add_row("Min Frequency", f"{cpu_freq.min:.2f} MHz")
        table.add_row("Max Frequency", f"{cpu_freq.max:.2f} MHz")
        
        console.print(table)
        
        # CPU usage per core
        console.print("\n[bold]Per-Core Usage:[/bold]")
        per_cpu = psutil.cpu_percent(interval=0, percpu=True)
        
        for i, usage in enumerate(per_cpu):
            bar_length = 20
            filled = int(bar_length * usage / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            if usage > 80:
                color = "red"
            elif usage > 50:
                color = "yellow"
            else:
                color = "green"
            
            console.print(f"Core {i:2d}: [bold {color}]{bar}[/bold {color}] {usage:5.1f}%")
        
        console.print(f"\n[bold green]Total CPU Usage: {cpu_percent:.1f}%[/bold green]\n")
    
    def _show_memory_info(self):
        """Show memory information"""
        console.print("[bold cyan]Memory Information:[/bold cyan]")
        
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        table = Table(box=box.SIMPLE)
        table.add_column("Property", style="magenta")
        table.add_column("Value", style="green")
        
        table.add_row("Total RAM", self._format_bytes(mem.total))
        table.add_row("Available RAM", self._format_bytes(mem.available))
        table.add_row("Used RAM", self._format_bytes(mem.used))
        table.add_row("Memory %", f"{mem.percent:.1f}%")
        table.add_row("Total Swap", self._format_bytes(swap.total))
        table.add_row("Used Swap", self._format_bytes(swap.used))
        table.add_row("Swap %", f"{swap.percent:.1f}%")
        
        console.print(table)
        
        # Memory bar
        bar_length = 30
        filled = int(bar_length * mem.percent / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        color = "red" if mem.percent > 80 else "yellow" if mem.percent > 50 else "green"
        console.print(f"\nMemory: [bold {color}]{bar}[/bold {color}] {mem.percent:.1f}%\n")
    
    def _show_disk_info(self):
        """Show disk information"""
        console.print("[bold cyan]Disk Information:[/bold cyan]")
        
        table = Table(box=box.SIMPLE)
        table.add_column("Partition", style="magenta")
        table.add_column("Total", style="green")
        table.add_column("Used", style="yellow")
        table.add_column("Free", style="cyan")
        table.add_column("Usage %", style="red")
        
        for disk in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(disk.mountpoint)
                table.add_row(
                    disk.device,
                    self._format_bytes(usage.total),
                    self._format_bytes(usage.used),
                    self._format_bytes(usage.free),
                    f"{usage.percent:.1f}%"
                )
            except PermissionError:
                continue
        
        console.print(table)
        console.print()
    
    def _show_network_info(self):
        """Show network information"""
        console.print("[bold cyan]Network Information:[/bold cyan]")
        
        net_if = psutil.net_if_addrs()
        
        for interface, addrs in net_if.items():
            console.print(f"\n[bold magenta]{interface}[/bold magenta]")
            for addr in addrs:
                console.print(f"  {addr.family.name}: {addr.address}")
        
        # Network stats
        net_io = psutil.net_io_counters()
        console.print(f"\n[bold]Total Network Stats:[/bold]")
        console.print(f"  Bytes sent: {self._format_bytes(net_io.bytes_sent)}")
        console.print(f"  Bytes received: {self._format_bytes(net_io.bytes_recv)}")
        console.print(f"  Packets sent: {net_io.packets_sent}")
        console.print(f"  Packets received: {net_io.packets_recv}\n")
    
    def _show_process_info(self):
        """Show top processes"""
        console.print("[bold cyan]Top Processes by Memory:[/bold cyan]\n")
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                processes.append((proc.info['name'], proc.info['memory_percent'], proc.info['pid']))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by memory usage
        processes.sort(key=lambda x: x[1], reverse=True)
        
        table = Table(box=box.SIMPLE)
        table.add_column("Process Name", style="cyan")
        table.add_column("Memory %", style="magenta")
        table.add_column("PID", style="green")
        
        for name, mem_percent, pid in processes[:10]:
            table.add_row(
                name[:40],
                f"{mem_percent:.2f}%",
                str(pid)
            )
        
        console.print(table)
        console.print()
    
    @staticmethod
    def _format_bytes(bytes_value: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"


def main():
    """Main entry point"""
    monitor = SystemMonitorCLI()
    monitor.show_summary()


if __name__ == "__main__":
    main()
