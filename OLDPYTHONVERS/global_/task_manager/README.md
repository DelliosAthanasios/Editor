# Task Manager Module

A modular, optimized task manager system for Third Edit with improved performance and architecture.

## Architecture Overview

The task manager has been redesigned with a modular architecture to improve performance and maintainability:

```
global_/task_manager/
├── __init__.py              # Main module interface
├── system_monitor.py        # System resource monitoring
├── ui_components.py         # Optimized UI widgets
├── task_manager_widget.py   # Main widget integration
├── legacy_task_manager.py   # Original implementation (for reference)
└── README.md               # This file
```

## Key Improvements

### 1. **Performance Optimizations**
- **Caching System**: Intelligent caching with configurable timeouts to reduce system calls
- **Batch Processing**: Process monitoring in batches to prevent UI blocking
- **Efficient Updates**: Only update UI when data actually changes
- **Threading**: Separate monitoring threads to keep UI responsive

### 2. **Modular Design**
- **Separation of Concerns**: Each component has a single responsibility
- **Reusable Components**: UI widgets can be used independently
- **Clean Interfaces**: Well-defined APIs between components
- **Easy Testing**: Each module can be tested in isolation

### 3. **Memory Management**
- **Resource Cleanup**: Proper cleanup of monitoring threads and timers
- **Efficient Data Structures**: Use of dataclasses for better memory usage
- **Limited Process List**: Only show top 100 processes to reduce memory usage

## Components

### SystemMonitor (`system_monitor.py`)
Handles system resource monitoring with intelligent caching:

```python
from global_.task_manager.system_monitor import SystemMonitor

monitor = SystemMonitor(update_interval=1000)  # 1 second updates
monitor.stats_updated.connect(on_stats_update)
monitor.start_monitoring()
```

**Features:**
- CPU usage (total and per-core)
- Memory usage (RAM and swap)
- Disk usage
- Network statistics
- Caching with configurable timeouts

### ProcessMonitor (`system_monitor.py`)
Optimized process monitoring with filtering:

```python
from global_.task_manager.system_monitor import ProcessMonitor

process_monitor = ProcessMonitor(update_interval=3000)  # 3 second updates
process_monitor.processes_updated.connect(on_processes_update)
process_monitor.start_monitoring()
```

**Features:**
- Batch processing to prevent UI blocking
- Process termination and killing
- Memory-efficient process list management
- Error handling for inaccessible processes

### UI Components (`ui_components.py`)
Optimized widgets for displaying system information:

- **PerformanceWidget**: Real-time performance displays
- **ProcessTableWidget**: Efficient process table with context menus
- **DiskTableWidget**: Disk usage information
- **NetworkTableWidget**: Network interface statistics
- **SensorsTreeWidget**: System sensors display

### TaskManagerWidget (`task_manager_widget.py`)
Main integration widget that combines all components:

```python
from global_.task_manager import create_task_manager_tab

task_manager = create_task_manager_tab()
```

## Usage

### In Third Edit
The task manager is integrated into the main editor and can be accessed via:
- **Tools → Process Manager** menu item
- Opens in a new tab within the editor

### Standalone Usage
```python
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from global_.task_manager import create_task_manager_tab

app = QApplication(sys.argv)
window = QMainWindow()
central_widget = QWidget()
layout = QVBoxLayout(central_widget)

task_manager = create_task_manager_tab()
layout.addWidget(task_manager)

window.setCentralWidget(central_widget)
window.show()
sys.exit(app.exec_())
```

## Performance Features

### Caching Strategy
- **Fast Data** (CPU, Memory): 500ms cache
- **Medium Data** (Network): 1 second cache  
- **Slow Data** (Disk): 5 second cache
- **Static Data** (System Info): 60 second cache

### Update Intervals
- **System Stats**: 1 second (configurable)
- **Process List**: 3 seconds (configurable)
- **UI Updates**: Only when data changes

### Memory Optimization
- Limited to top 100 processes by default
- Efficient data structures using dataclasses
- Proper cleanup of resources

## Error Handling

The system includes comprehensive error handling:
- Graceful degradation when system calls fail
- User-friendly error messages
- Fallback values for missing data
- Logging of errors for debugging

## Configuration

### Update Intervals
```python
# Custom update intervals
system_monitor = SystemMonitor(update_interval=2000)  # 2 seconds
process_monitor = ProcessMonitor(update_interval=5000)  # 5 seconds
```

### Cache Timeouts
```python
# Custom cache timeouts (in seconds)
monitor._cache_timeout = 1.0  # 1 second for fast data
```

## Migration from Legacy

The original `task_man.py` has been moved to `legacy_task_manager.py` for reference. The new system provides:

- **Better Performance**: Significantly reduced lag
- **Modular Architecture**: Easier to maintain and extend
- **Better Integration**: Seamless integration with Third Edit
- **Improved UI**: More responsive and user-friendly

## Dependencies

- **PyQt5**: UI framework
- **psutil**: System monitoring
- **platform**: System information
- **subprocess**: System commands (Linux/Windows)

## Future Enhancements

Potential improvements for future versions:
- **Charts and Graphs**: Historical data visualization
- **Process Filtering**: Search and filter processes
- **Service Management**: Start/stop system services
- **Performance Alerts**: Configurable alerts for high resource usage
- **Export Features**: Export data to CSV/JSON
- **Custom Metrics**: User-defined monitoring metrics 