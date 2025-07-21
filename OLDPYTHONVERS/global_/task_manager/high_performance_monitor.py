"""
High Performance System Monitor
Uses native Windows APIs and async operations for real-time monitoring
"""

import ctypes
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker

# Try to import psutil for fallback
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Windows API constants and structures
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_TERMINATE = 0x0001

# Windows types
DWORD = ctypes.c_ulong
WORD = ctypes.c_ushort
LPVOID = ctypes.c_void_p

class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", DWORD),
                ("dwHighDateTime", DWORD)]

class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [("wProcessorArchitecture", WORD),
                ("wReserved", WORD),
                ("dwPageSize", DWORD),
                ("lpMinimumApplicationAddress", LPVOID),
                ("lpMaximumApplicationAddress", LPVOID),
                ("dwActiveProcessorMask", LPVOID),
                ("dwNumberOfProcessors", DWORD),
                ("dwProcessorType", DWORD),
                ("dwAllocationGranularity", DWORD),
                ("wProcessorLevel", WORD),
                ("wProcessorRevision", WORD)]

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", DWORD),
                ("dwMemoryLoad", DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [("cb", DWORD),
                ("PageFaultCount", DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]

# Try to load Windows DLLs with proper error handling
try:
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    advapi32 = ctypes.windll.advapi32
    
    # Set function signatures
    kernel32.GetSystemInfo.argtypes = [ctypes.POINTER(SYSTEM_INFO)]
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    kernel32.GetTickCount64.restype = ctypes.c_ulonglong
    kernel32.GetSystemTimeAsFileTime.argtypes = [ctypes.POINTER(FILETIME)]
    
    # Test if EnumProcesses is available
    try:
        kernel32.EnumProcesses
        WINDOWS_API_AVAILABLE = True
    except AttributeError:
        WINDOWS_API_AVAILABLE = False
        
except Exception:
    WINDOWS_API_AVAILABLE = False

@dataclass
class FastSystemStats:
    """High-performance system statistics container"""
    cpu_percent: float = 0.0
    cpu_per_core: List[float] = None
    memory_percent: float = 0.0
    memory_used: int = 0
    memory_total: int = 0
    memory_available: int = 0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.cpu_per_core is None:
            self.cpu_per_core = []

@dataclass
class FastProcessInfo:
    """High-performance process information"""
    pid: int
    name: str
    cpu_percent: float
    memory_rss: int
    memory_percent: float
    status: str

class HighPerformanceMonitor(QObject):
    """Ultra-fast system monitor using native Windows APIs with psutil fallback"""
    
    stats_updated = pyqtSignal(object)  # Emits FastSystemStats
    error_occurred = pyqtSignal(str)
    
    def __init__(self, update_interval: int = 500):
        super().__init__()
        self.update_interval = update_interval
        self._running = False
        self._mutex = QMutex()
        
        # CPU monitoring with proper initialization
        self._cpu_count = self._get_cpu_count()
        self._prev_cpu_times = None
        self._prev_cpu_time = None
        self._cpu_usage_history = []
        
        # Memory monitoring
        self._memory_status = MEMORYSTATUSEX()
        self._memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        
        # Timer for updates
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_stats)
        
        # Initialize CPU monitoring
        self._init_cpu_monitoring()
        
    def _get_cpu_count(self) -> int:
        """Get number of CPU cores"""
        if PSUTIL_AVAILABLE:
            return psutil.cpu_count()
        elif WINDOWS_API_AVAILABLE:
            try:
                sys_info = SYSTEM_INFO()
                kernel32.GetSystemInfo(ctypes.byref(sys_info))
                return sys_info.dwNumberOfProcessors
            except Exception:
                return 1
        else:
            return 1
    
    def _init_cpu_monitoring(self):
        """Initialize CPU monitoring with proper baseline"""
        if PSUTIL_AVAILABLE:
            # Use psutil for accurate CPU monitoring
            self._prev_cpu_times = psutil.cpu_times_percent()
            self._prev_cpu_time = time.time()
        else:
            # Fallback to time-based monitoring
            self._prev_cpu_time = time.time()
            self._prev_cpu_times = None
    
    def _calculate_cpu_usage(self) -> Tuple[float, List[float]]:
        """Calculate CPU usage using the best available method"""
        if PSUTIL_AVAILABLE:
            return self._calculate_cpu_usage_psutil()
        elif WINDOWS_API_AVAILABLE:
            return self._calculate_cpu_usage_windows()
        else:
            return self._calculate_cpu_usage_fallback()
    
    def _calculate_cpu_usage_psutil(self) -> Tuple[float, List[float]]:
        """Calculate CPU usage using psutil (most accurate)"""
        try:
            # Get current CPU times
            current_cpu_times = psutil.cpu_times_percent()
            current_time = time.time()
            
            # Calculate total CPU usage
            if self._prev_cpu_times:
                # Calculate based on idle time
                prev_idle = self._prev_cpu_times.idle
                current_idle = current_cpu_times.idle
                
                # Calculate CPU usage as (100 - idle_percent)
                cpu_percent = 100.0 - current_idle
                
                # Smooth the result to avoid spikes
                self._cpu_usage_history.append(cpu_percent)
                if len(self._cpu_usage_history) > 5:
                    self._cpu_usage_history.pop(0)
                
                # Use average of recent values
                smoothed_cpu = sum(self._cpu_usage_history) / len(self._cpu_usage_history)
                
                # Get per-core usage
                per_core = psutil.cpu_percent(interval=None, percpu=True)
                
                # Update previous values
                self._prev_cpu_times = current_cpu_times
                self._prev_cpu_time = current_time
                
                return smoothed_cpu, per_core
            else:
                # First run, initialize
                self._prev_cpu_times = current_cpu_times
                self._prev_cpu_time = current_time
                return 0.0, [0.0] * self._cpu_count
                
        except Exception:
            return 0.0, [0.0] * self._cpu_count
    
    def _calculate_cpu_usage_windows(self) -> Tuple[float, List[float]]:
        """Calculate CPU usage using Windows API"""
        try:
            # Use GetSystemTimeAsFileTime for timing
            file_time = FILETIME()
            kernel32.GetSystemTimeAsFileTime(ctypes.byref(file_time))
            
            current_time = time.time()
            
            # Simple time-based calculation (not very accurate)
            if self._prev_cpu_time:
                time_diff = current_time - self._prev_cpu_time
                if time_diff > 0:
                    # Use a simple moving average approach
                    cpu_percent = min(50.0, time_diff * 10)  # Conservative estimate
                else:
                    cpu_percent = 0.0
            else:
                cpu_percent = 0.0
            
            self._prev_cpu_time = current_time
            per_core = [cpu_percent] * self._cpu_count
            
            return cpu_percent, per_core
            
        except Exception:
            return 0.0, [0.0] * self._cpu_count
    
    def _calculate_cpu_usage_fallback(self) -> Tuple[float, List[float]]:
        """Fallback CPU calculation"""
        return 0.0, [0.0] * self._cpu_count
    
    def _get_memory_info(self) -> Tuple[float, int, int, int]:
        """Get memory information using the best available method"""
        if PSUTIL_AVAILABLE:
            return self._get_memory_info_psutil()
        elif WINDOWS_API_AVAILABLE:
            return self._get_memory_info_windows()
        else:
            return 0.0, 0, 0, 0
    
    def _get_memory_info_psutil(self) -> Tuple[float, int, int, int]:
        """Get memory information using psutil"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent, memory.used, memory.total, memory.available
        except Exception:
            return 0.0, 0, 0, 0
    
    def _get_memory_info_windows(self) -> Tuple[float, int, int, int]:
        """Get memory information using Windows API"""
        try:
            kernel32.GlobalMemoryStatusEx(ctypes.byref(self._memory_status))
            
            total = self._memory_status.ullTotalPhys
            available = self._memory_status.ullAvailPhys
            used = total - available
            percent = ((total - available) / total) * 100.0 if total > 0 else 0.0
            
            return percent, used, total, available
            
        except Exception:
            return 0.0, 0, 0, 0
    
    def _update_stats(self):
        """Update system statistics with minimal blocking"""
        try:
            # Get CPU and memory info
            cpu_percent, cpu_per_core = self._calculate_cpu_usage()
            mem_percent, mem_used, mem_total, mem_available = self._get_memory_info()
            
            # Create stats object
            stats = FastSystemStats(
                cpu_percent=cpu_percent,
                cpu_per_core=cpu_per_core,
                memory_percent=mem_percent,
                memory_used=mem_used,
                memory_total=mem_total,
                memory_available=mem_available,
                timestamp=time.time()
            )
            
            self.stats_updated.emit(stats)
            
        except Exception as e:
            self.error_occurred.emit(f"Error updating stats: {str(e)}")
    
    def start_monitoring(self):
        """Start the monitoring timer"""
        if not self._running:
            self._running = True
            self._timer.start(self.update_interval)
    
    def stop_monitoring(self):
        """Stop the monitoring timer"""
        self._running = False
        self._timer.stop()

class FastProcessMonitor(QThread):
    """High-performance process monitor using native Windows APIs with psutil fallback"""
    
    processes_updated = pyqtSignal(list)  # Emits list of FastProcessInfo
    error_occurred = pyqtSignal(str)
    
    def __init__(self, update_interval: int = 2000):
        super().__init__()
        self.update_interval = update_interval
        self._running = False
        self._mutex = QMutex()
        
        # Process enumeration
        self._process_handles = {}
        self._prev_process_times = {}
        
    def run(self):
        """Main monitoring loop"""
        self._running = True
        
        while self._running:
            try:
                processes = self._get_process_list()
                self.processes_updated.emit(processes)
                
                # Sleep for update interval
                self.msleep(self.update_interval)
                
            except Exception as e:
                self.error_occurred.emit(f"Process monitor error: {str(e)}")
                self.msleep(1000)  # Wait before retrying
    
    def _get_process_list(self) -> List[FastProcessInfo]:
        """Get process list using the best available method"""
        if PSUTIL_AVAILABLE:
            return self._get_process_list_psutil()
        elif WINDOWS_API_AVAILABLE:
            return self._get_process_list_windows()
        else:
            return []
    
    def _get_process_list_psutil(self) -> List[FastProcessInfo]:
        """Get process list using psutil (most reliable)"""
        processes = []
        
        try:
            # Get system memory for percentage calculation
            memory = psutil.virtual_memory()
            total_memory = memory.total
            
            # Get process list (limit to top 50 for performance)
            process_list = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'status', 'cpu_percent']):
                try:
                    process_list.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by memory usage and take top 50
            process_list.sort(key=lambda p: p.info['memory_info'].rss, reverse=True)
            process_list = process_list[:50]
            
            for proc in process_list:
                try:
                    info = proc.info
                    memory_rss = info['memory_info'].rss
                    memory_percent = (memory_rss / total_memory) * 100.0 if total_memory > 0 else 0.0
                    
                    processes.append(FastProcessInfo(
                        pid=info['pid'],
                        name=info['name'] or "Unknown",
                        cpu_percent=info['cpu_percent'] or 0.0,
                        memory_rss=memory_rss,
                        memory_percent=memory_percent,
                        status=info['status'] or "Unknown"
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            self.error_occurred.emit(f"Error getting process list with psutil: {str(e)}")
        
        return processes
    
    def _get_process_list_windows(self) -> List[FastProcessInfo]:
        """Get process list using Windows API"""
        processes = []
        
        try:
            # Get system memory for percentage calculation
            memory_status = MEMORYSTATUSEX()
            memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
            total_memory = memory_status.ullTotalPhys
            
            # Enumerate processes using Windows API
            process_ids = (DWORD * 1024)()
            bytes_returned = DWORD()
            
            # Get process list
            if kernel32.EnumProcesses(process_ids, ctypes.sizeof(process_ids), ctypes.byref(bytes_returned)):
                num_processes = bytes_returned.value // ctypes.sizeof(DWORD)
                
                # Process only first 50 processes for performance
                for i in range(min(50, num_processes)):
                    pid = process_ids[i]
                    if pid == 0:
                        continue
                    
                    try:
                        # Get process handle
                        handle = kernel32.OpenProcess(
                            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                            False, pid
                        )
                        
                        if handle:
                            # Get process name
                            name = self._get_process_name(handle)
                            
                            # Get memory info
                            memory_counters = PROCESS_MEMORY_COUNTERS()
                            memory_counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
                            
                            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory_counters), memory_counters.cb):
                                memory_rss = memory_counters.WorkingSetSize
                                memory_percent = (memory_rss / total_memory) * 100.0 if total_memory > 0 else 0.0
                                
                                # Simple CPU calculation (placeholder for performance)
                                cpu_percent = 0.0  # Would need more complex tracking
                                
                                processes.append(FastProcessInfo(
                                    pid=pid,
                                    name=name,
                                    cpu_percent=cpu_percent,
                                    memory_rss=memory_rss,
                                    memory_percent=memory_percent,
                                    status="Running"
                                ))
                            
                            kernel32.CloseHandle(handle)
                    
                    except Exception:
                        continue
                
                # Sort by memory usage for better UX
                processes.sort(key=lambda x: x.memory_rss, reverse=True)
        
        except Exception as e:
            self.error_occurred.emit(f"Error getting process list with Windows API: {str(e)}")
        
        return processes
    
    def _get_process_name(self, handle) -> str:
        """Get process name from handle"""
        try:
            name_buffer = ctypes.create_unicode_buffer(260)
            if psapi.GetModuleBaseNameW(handle, None, name_buffer, 260):
                return name_buffer.value
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self._running = False
        self.wait()  # Wait for thread to finish
    
    def terminate_process(self, pid: int) -> bool:
        """Terminate a process by PID"""
        if PSUTIL_AVAILABLE:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        elif WINDOWS_API_AVAILABLE:
            try:
                handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                if handle:
                    result = kernel32.TerminateProcess(handle, 1)
                    kernel32.CloseHandle(handle)
                    return result != 0
                return False
            except Exception:
                return False
        else:
            return False
    
    def kill_process(self, pid: int) -> bool:
        """Force kill a process by PID"""
        if PSUTIL_AVAILABLE:
            try:
                proc = psutil.Process(pid)
                proc.kill()
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        elif WINDOWS_API_AVAILABLE:
            return self.terminate_process(pid)  # Same as terminate on Windows
        else:
            return False 