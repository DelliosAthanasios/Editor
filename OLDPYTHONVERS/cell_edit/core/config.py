"""
Configuration system for performance tuning and customization.
Provides centralized configuration management with validation and defaults.
"""

import os
import json
from typing import Any, Dict, Optional, Union, Type
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MemoryConfig:
    """Memory management configuration."""
    max_cells_in_memory: int = 1_000_000  # Maximum cells to keep in memory
    cell_cache_size: int = 100_000  # Size of cell cache
    gc_threshold: float = 0.8  # Trigger GC when memory usage exceeds this ratio
    lazy_loading_enabled: bool = True  # Enable lazy loading of cells
    memory_pool_size: int = 10_000  # Size of object memory pool
    compression_enabled: bool = True  # Enable cell data compression


@dataclass
class PerformanceConfig:
    """Performance optimization configuration."""
    parallel_calculation: bool = True  # Enable parallel formula calculation
    max_worker_threads: int = 4  # Maximum number of worker threads
    calculation_timeout: float = 30.0  # Timeout for formula calculation (seconds)
    dependency_cache_size: int = 50_000  # Size of dependency cache
    formula_cache_size: int = 10_000  # Size of formula result cache
    incremental_calculation: bool = True  # Enable incremental recalculation
    batch_size: int = 1000  # Batch size for bulk operations


@dataclass
class UIConfig:
    """User interface configuration."""
    virtual_scrolling: bool = True  # Enable virtual scrolling
    viewport_buffer_rows: int = 50  # Number of buffer rows in viewport
    viewport_buffer_cols: int = 20  # Number of buffer columns in viewport
    smooth_scrolling: bool = True  # Enable smooth scrolling
    animation_duration: float = 0.2  # Animation duration (seconds)
    theme: str = "default"  # UI theme
    font_family: str = "Arial"  # Default font family
    font_size: int = 11  # Default font size
    scroll_sensitivity: float = 1.0  # Sensitivity for scroll speed
    enable_momentum_scrolling: bool = True  # Enable momentum scrolling
    enable_smooth_scrolling: bool = True  # Enable smooth scrolling (for UI)
    target_fps: int = 60  # Target frames per second for UI updates


@dataclass
class StorageConfig:
    """Storage and persistence configuration."""
    auto_save_enabled: bool = True  # Enable auto-save
    auto_save_interval: int = 300  # Auto-save interval (seconds)
    backup_enabled: bool = True  # Enable backup creation
    max_backup_files: int = 10  # Maximum number of backup files
    compression_level: int = 6  # Compression level (0-9)
    file_format_version: str = "1.0"  # File format version
    temp_directory: Optional[str] = None  # Temporary directory path


@dataclass
class PluginConfig:
    """Plugin system configuration."""
    plugins_enabled: bool = True  # Enable plugin system
    plugin_directory: str = "plugins"  # Plugin directory path
    auto_load_plugins: bool = True  # Auto-load plugins on startup
    plugin_timeout: float = 10.0  # Plugin operation timeout (seconds)
    sandbox_enabled: bool = True  # Enable plugin sandboxing
    max_plugin_memory: int = 100_000_000  # Maximum memory per plugin (bytes)


@dataclass
class Config:
    """Main configuration class."""
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)
    
    # Application-level settings
    debug_mode: bool = False
    log_level: str = "INFO"
    max_undo_levels: int = 100
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'Config':
        """Load configuration from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            return cls()  # Return default config if file doesn't exist
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config from {path}: {e}")
            return cls()  # Return default config on error
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from a dictionary."""
        config = cls()
        
        # Update memory config
        if 'memory' in data:
            memory_data = data['memory']
            for key, value in memory_data.items():
                if hasattr(config.memory, key):
                    setattr(config.memory, key, value)
        
        # Update performance config
        if 'performance' in data:
            perf_data = data['performance']
            for key, value in perf_data.items():
                if hasattr(config.performance, key):
                    setattr(config.performance, key, value)
        
        # Update UI config
        if 'ui' in data:
            ui_data = data['ui']
            for key, value in ui_data.items():
                if hasattr(config.ui, key):
                    setattr(config.ui, key, value)
        
        # Update storage config
        if 'storage' in data:
            storage_data = data['storage']
            for key, value in storage_data.items():
                if hasattr(config.storage, key):
                    setattr(config.storage, key, value)
        
        # Update plugin config
        if 'plugins' in data:
            plugin_data = data['plugins']
            for key, value in plugin_data.items():
                if hasattr(config.plugins, key):
                    setattr(config.plugins, key, value)
        
        # Update application-level settings
        for key in ['debug_mode', 'log_level', 'max_undo_levels']:
            if key in data:
                setattr(config, key, data[key])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary."""
        return {
            'memory': {
                'max_cells_in_memory': self.memory.max_cells_in_memory,
                'cell_cache_size': self.memory.cell_cache_size,
                'gc_threshold': self.memory.gc_threshold,
                'lazy_loading_enabled': self.memory.lazy_loading_enabled,
                'memory_pool_size': self.memory.memory_pool_size,
                'compression_enabled': self.memory.compression_enabled,
            },
            'performance': {
                'parallel_calculation': self.performance.parallel_calculation,
                'max_worker_threads': self.performance.max_worker_threads,
                'calculation_timeout': self.performance.calculation_timeout,
                'dependency_cache_size': self.performance.dependency_cache_size,
                'formula_cache_size': self.performance.formula_cache_size,
                'incremental_calculation': self.performance.incremental_calculation,
                'batch_size': self.performance.batch_size,
            },
            'ui': {
                'virtual_scrolling': self.ui.virtual_scrolling,
                'viewport_buffer_rows': self.ui.viewport_buffer_rows,
                'viewport_buffer_cols': self.ui.viewport_buffer_cols,
                'smooth_scrolling': self.ui.smooth_scrolling,
                'animation_duration': self.ui.animation_duration,
                'theme': self.ui.theme,
                'font_family': self.ui.font_family,
                'font_size': self.ui.font_size,
                'scroll_sensitivity': self.ui.scroll_sensitivity,
                'enable_momentum_scrolling': self.ui.enable_momentum_scrolling,
                'enable_smooth_scrolling': self.ui.enable_smooth_scrolling,
                'target_fps': self.ui.target_fps,
            },
            'storage': {
                'auto_save_enabled': self.storage.auto_save_enabled,
                'auto_save_interval': self.storage.auto_save_interval,
                'backup_enabled': self.storage.backup_enabled,
                'max_backup_files': self.storage.max_backup_files,
                'compression_level': self.storage.compression_level,
                'file_format_version': self.storage.file_format_version,
                'temp_directory': self.storage.temp_directory,
            },
            'plugins': {
                'plugins_enabled': self.plugins.plugins_enabled,
                'plugin_directory': self.plugins.plugin_directory,
                'auto_load_plugins': self.plugins.auto_load_plugins,
                'plugin_timeout': self.plugins.plugin_timeout,
                'sandbox_enabled': self.plugins.sandbox_enabled,
                'max_plugin_memory': self.plugins.max_plugin_memory,
            },
            'debug_mode': self.debug_mode,
            'log_level': self.log_level,
            'max_undo_levels': self.max_undo_levels,
        }
    
    def save_to_file(self, file_path: Union[str, Path]) -> bool:
        """Save configuration to a JSON file."""
        path = Path(file_path)
        try:
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving config to {path}: {e}")
            return False
    
    def validate(self) -> bool:
        """Validate configuration values."""
        errors = []
        
        # Validate memory config
        if self.memory.max_cells_in_memory <= 0:
            errors.append("max_cells_in_memory must be positive")
        if self.memory.cell_cache_size <= 0:
            errors.append("cell_cache_size must be positive")
        if not 0 < self.memory.gc_threshold <= 1:
            errors.append("gc_threshold must be between 0 and 1")
        
        # Validate performance config
        if self.performance.max_worker_threads <= 0:
            errors.append("max_worker_threads must be positive")
        if self.performance.calculation_timeout <= 0:
            errors.append("calculation_timeout must be positive")
        
        # Validate UI config
        if self.ui.viewport_buffer_rows < 0:
            errors.append("viewport_buffer_rows must be non-negative")
        if self.ui.viewport_buffer_cols < 0:
            errors.append("viewport_buffer_cols must be non-negative")
        if self.ui.font_size <= 0:
            errors.append("font_size must be positive")
        
        # Validate storage config
        if self.storage.auto_save_interval <= 0:
            errors.append("auto_save_interval must be positive")
        if not 0 <= self.storage.compression_level <= 9:
            errors.append("compression_level must be between 0 and 9")
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def get_default_config_path(self) -> Path:
        """Get the default configuration file path."""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '')) / 'CellEditor'
        else:  # Unix-like
            config_dir = Path.home() / '.config' / 'celleditor'
        
        return config_dir / 'config.json'


# Global configuration instance
_global_config = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = Config()
        # Try to load from default location
        default_path = _global_config.get_default_config_path()
        if default_path.exists():
            _global_config = Config.load_from_file(default_path)
    return _global_config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _global_config
    _global_config = config


def save_config() -> bool:
    """Save the global configuration to the default location."""
    config = get_config()
    return config.save_to_file(config.get_default_config_path())

