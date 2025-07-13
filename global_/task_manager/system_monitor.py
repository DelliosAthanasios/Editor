"""
System Monitor Module
Handles efficient system resource monitoring with caching and threading
"""

import psutil
import platform
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker

# Try to import sensors_temperatures from psutil or fallback to None
try:
    from psutil import sensors_temperatures
except ImportError:
    sensors_temperatures = None

@dataclass
class SystemStats:
    """Container for system statistics"""
    cpu_percent: float = 0.0
    cpu_per_core: List[float] = None
    memory_percent: float = 0.0
    memory_used: int = 0
    memory_total: int = 0
    swap_percent: float = 0.0
    disk_usage: Dict[str, Dict] = None
    network_stats: Dict[str, Dict] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.cpu_per_core is None:
            self.cpu_per_core = []
        if self.disk_usage is None:
            self.disk_usage = {}
        if self.network_stats is None:
            self.network_stats = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class ProcessInfo:
    """Container for process information"""
    pid: int
    name: str
    cpu_percent: float
    memory_rss: int
    memory_percent: float
    status: str
    create_time: float
    exe: str
    cmdline: List[str]

class SystemMonitor(QObject):
    """Optimized system monitor with caching and efficient updates"""
    
    stats_updated = pyqtSignal(object)  # Emits SystemStats
    error_occurred = pyqtSignal(str)
    
    def __init__(self, update_interval: int = 1000):
        super().__init__()
        self.update_interval = update_interval
        self._cache = {}
        self._cache_timeout = 0.5  # Cache for 500ms
        self._last_update = 0
        self._mutex = QMutex()
        self._running = False
        
        # Initialize CPU baseline
        self._init_cpu_baseline()
        
        # Network tracking
        self._prev_net_io = psutil.net_io_counters()
        self._initial_net_io = psutil.net_io_counters()
        
        # Timer for updates
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_stats)
        
    def _init_cpu_baseline(self):
        """Initialize CPU baseline for accurate measurements"""
        try:
            psutil.cpu_percent(interval=0.1)
        except Exception:
            pass
    
    def start_monitoring(self):
        """Start the monitoring timer"""
        if not self._running:
            self._running = True
            self._timer.start(self.update_interval)
    
    def stop_monitoring(self):
        """Stop the monitoring timer"""
        self._running = False
        self._timer.stop()
    
    def _get_cached_or_fetch(self, key: str, fetch_func, timeout: float = None):
        """Get cached value or fetch new one"""
        if timeout is None:
            timeout = self._cache_timeout
            
        current_time = time.time()
        
        with QMutexLocker(self._mutex):
            if key in self._cache:
                cached_time, cached_value = self._cache[key]
                if current_time - cached_time < timeout:
                    return cached_value
            
            try:
                value = fetch_func()
                self._cache[key] = (current_time, value)
                return value
            except Exception as e:
                self.error_occurred.emit(f"Error fetching {key}: {str(e)}")
                return None
    
    def _update_stats(self):
        """Update system statistics"""
        try:
            stats = SystemStats()
            
            # CPU stats
            stats.cpu_percent = self._get_cached_or_fetch(
                'cpu_percent',
                lambda: psutil.cpu_percent(interval=None)
            ) or 0.0
            
            stats.cpu_per_core = self._get_cached_or_fetch(
                'cpu_per_core',
                lambda: psutil.cpu_percent(percpu=True)
            ) or []
            
            # Memory stats
            memory = self._get_cached_or_fetch(
                'memory',
                lambda: psutil.virtual_memory()
            )
            if memory:
                stats.memory_percent = memory.percent
                stats.memory_used = memory.used
                stats.memory_total = memory.total
            
            # Swap stats
            try:
                swap = self._get_cached_or_fetch(
                    'swap',
                    lambda: psutil.swap_memory()
                )
                if swap:
                    stats.swap_percent = swap.percent
            except Exception:
                stats.swap_percent = 0.0
            
            # Disk stats (cached for longer as they don't change frequently)
            stats.disk_usage = self._get_cached_or_fetch(
                'disk_usage',
                self._get_disk_usage,
                timeout=5.0  # Cache for 5 seconds
            ) or {}
            
            # Network stats
            stats.network_stats = self._get_cached_or_fetch(
                'network_stats',
                self._get_network_stats,
                timeout=1.0  # Cache for 1 second
            ) or {}
            
            stats.timestamp = datetime.now()
            self.stats_updated.emit(stats)
            
        except Exception as e:
            self.error_occurred.emit(f"Error updating stats: {str(e)}")
    
    def _get_disk_usage(self) -> Dict[str, Dict]:
        """Get disk usage information"""
        disk_info = {}
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[partition.device] = {
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    }
                except (PermissionError, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return disk_info
    
    def _get_network_stats(self) -> Dict[str, Dict]:
        """Get network statistics"""
        network_info = {}
        try:
            current_net = psutil.net_io_counters()
            interfaces = psutil.net_io_counters(pernic=True)
            
            # Calculate rates
            time_diff = 1.0  # Assume 1 second interval
            sent_rate = (current_net.bytes_sent - self._prev_net_io.bytes_sent) / time_diff
            recv_rate = (current_net.bytes_recv - self._prev_net_io.bytes_recv) / time_diff
            
            network_info['total'] = {
                'sent_rate': sent_rate,
                'recv_rate': recv_rate,
                'sent_total': current_net.bytes_sent,
                'recv_total': current_net.bytes_recv,
                'packets_sent': current_net.packets_sent,
                'packets_recv': current_net.packets_recv
            }
            
            # Per-interface stats
            for name, data in interfaces.items():
                network_info[name] = {
                    'sent_total': data.bytes_sent,
                    'recv_total': data.bytes_recv,
                    'packets_sent': data.packets_sent,
                    'packets_recv': data.packets_recv,
                    'active': data.bytes_sent + data.bytes_recv > 0
                }
            
            self._prev_net_io = current_net
            
        except Exception:
            pass
        return network_info
    
    def get_system_info(self) -> Dict:
        """Get static system information"""
        return self._get_cached_or_fetch(
            'system_info',
            self._get_system_info_internal,
            timeout=60.0  # Cache for 1 minute
        ) or {}
    
    def _get_system_info_internal(self) -> Dict:
        """Get static system information"""
        info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'cpu_count_physical': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total': psutil.virtual_memory().total
        }
        
        # Try to get more detailed CPU info
        try:
            if platform.system() == 'Linux':
                output = subprocess.check_output(['lscpu'], text=True, timeout=2)
                for line in output.splitlines():
                    if "Model name" in line and not info['processor']:
                        info['processor'] = line.split(":", 1)[1].strip()
            elif platform.system() == 'Windows':
                try:
                    import wmi
                    c = wmi.WMI()
                    for processor in c.Win32_Processor():
                        info['processor'] = processor.Name
                        break
                except Exception:
                    pass
        except Exception:
            pass
        
        return info

class ProcessMonitor(QObject):
    """Optimized process monitoring with filtering and sorting"""
    
    processes_updated = pyqtSignal(list)  # Emits list of ProcessInfo
    error_occurred = pyqtSignal(str)
    
    def __init__(self, update_interval: int = 3000):
        super().__init__()
        self.update_interval = update_interval
        self._running = False
        self._mutex = QMutex()
        self._process_cache = {}
        self._last_update = 0
        
        # Timer for updates
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_processes)
    
    def start_monitoring(self):
        """Start process monitoring"""
        if not self._running:
            self._running = True
            self._timer.start(self.update_interval)
    
    def stop_monitoring(self):
        """Stop process monitoring"""
        self._running = False
        self._timer.stop()
    
    def _update_processes(self):
        """Update process list"""
        try:
            processes = []
            total_memory = psutil.virtual_memory().total
            
            # Get all processes with minimal info first
            process_list = list(psutil.process_iter(['pid', 'name', 'status']))
            
            # Process in batches to avoid blocking
            batch_size = 50
            for i in range(0, len(process_list), batch_size):
                batch = process_list[i:i + batch_size]
                
                for proc in batch:
                    try:
                        # Get basic info
                        info = proc.info
                        pid = info['pid']
                        name = info['name']
                        status = info.get('status', 'N/A')
                        
                        # Get detailed info only for visible processes
                        if len(processes) < 100:  # Limit to top 100 processes
                            try:
                                cpu_percent = proc.cpu_percent()
                                memory_info = proc.memory_info()
                                memory_rss = memory_info.rss
                                memory_percent = (memory_rss / total_memory) * 100 if total_memory else 0
                                
                                processes.append(ProcessInfo(
                                    pid=pid,
                                    name=name,
                                    cpu_percent=cpu_percent,
                                    memory_rss=memory_rss,
                                    memory_percent=memory_percent,
                                    status=status,
                                    create_time=proc.create_time(),
                                    exe=proc.exe(),
                                    cmdline=proc.cmdline()
                                ))
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # Add basic info for processes we can't access
                                processes.append(ProcessInfo(
                                    pid=pid,
                                    name=name,
                                    cpu_percent=0.0,
                                    memory_rss=0,
                                    memory_percent=0.0,
                                    status=status,
                                    create_time=0,
                                    exe="",
                                    cmdline=[]
                                ))
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Small delay to prevent blocking
                time.sleep(0.01)
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.cpu_percent, reverse=True)
            
            self.processes_updated.emit(processes)
            
        except Exception as e:
            self.error_occurred.emit(f"Error updating processes: {str(e)}")
    
    def terminate_process(self, pid: int) -> bool:
        """Terminate a process by PID"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def kill_process(self, pid: int) -> bool:
        """Force kill a process by PID"""
        try:
            process = psutil.Process(pid)
            process.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False 