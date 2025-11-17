import os
import sys
import json
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from PyQt5.QtCore import QThread, pyqtSignal, QObject

# Configuration
def load_config():
    """Load configuration from JSON file"""
    try:
        with open('advanced_loading_config.json', 'r') as f:
            config = json.load(f)
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default configuration if file not found or invalid
        return {
            "line_threshold": 1000,
            "chunk_size": 1000,
            "memory_limit_mb": 50,
            "supported_encodings": ["utf-8", "latin-1", "cp1252", "iso-8859-1"],
            "performance": {
                "max_preview_lines": 100,
                "chunk_size_min": 100,
                "chunk_size_max": 10000
            }
        }

# Load configuration
CONFIG = load_config()
DEFAULT_LINE_THRESHOLD = CONFIG.get("line_threshold", 1000)
DEFAULT_CHUNK_SIZE = CONFIG.get("chunk_size", 1000)
DEFAULT_MEMORY_LIMIT = CONFIG.get("memory_limit_mb", 50) * 1024 * 1024

class FileAnalyzer(QObject):
    """Analyzes file size and determines if advanced loading is needed"""
    
    def __init__(self):
        super().__init__()
        self.line_threshold = CONFIG.get("line_threshold", DEFAULT_LINE_THRESHOLD)
        self.memory_limit = CONFIG.get("memory_limit_mb", 50) * 1024 * 1024
        self.supported_encodings = CONFIG.get("supported_encodings", ["utf-8", "latin-1", "cp1252", "iso-8859-1"])
    
    def should_use_advanced_loading(self, file_path: str) -> tuple[bool, Dict[str, Any]]:
        """
        Determines if a file should use advanced loading
        Returns: (should_use_advanced, file_info)
        """
        try:
            file_size = os.path.getsize(file_path)
            file_info = {
                'path': file_path,
                'size': file_size,
                'size_mb': file_size / (1024 * 1024),
                'lines': 0,
                'encoding': 'utf-8'
            }
            
            # Check file size first
            if file_size > self.memory_limit:
                return True, file_info
            
            # Count lines efficiently
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
                file_info['lines'] = line_count
                
                if line_count > self.line_threshold:
                    return True, file_info
                    
            except UnicodeDecodeError:
                # Try different encodings from configuration
                for encoding in self.supported_encodings[1:]:  # Skip utf-8 as it was already tried
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            line_count = sum(1 for _ in f)
                        file_info['lines'] = line_count
                        file_info['encoding'] = encoding
                        
                        if line_count > self.line_threshold:
                            return True, file_info
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # If all encodings fail, treat as binary
                    return True, file_info
            
            return False, file_info
            
        except Exception as e:
            return False, {'error': str(e)}

class FastFileLoader(QThread):
    """Fast file loader that loads content in background thread"""
    
    loading_finished = pyqtSignal(str)  # content
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path: str, encoding: str = 'utf-8'):
        super().__init__()
        self.file_path = file_path
        self.encoding = encoding
    
    def run(self):
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                content = f.read()
            self.loading_finished.emit(content)
        except Exception as e:
            self.error_occurred.emit(str(e))

def should_use_advanced_loading(file_path: str, threshold: int = DEFAULT_LINE_THRESHOLD) -> tuple[bool, Dict[str, Any]]:
    """Convenience function to check if advanced loading should be used"""
    analyzer = FileAnalyzer()
    analyzer.line_threshold = threshold
    return analyzer.should_use_advanced_loading(file_path)

def load_file_content(file_path: str, encoding: str = 'utf-8') -> str:
    """
    Load file content with automatic encoding detection
    Returns the file content as a string
    """
    # Try the specified encoding first
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # Try other supported encodings
        supported_encodings = CONFIG.get("supported_encodings", ["utf-8", "latin-1", "cp1252", "iso-8859-1"])
        for enc in supported_encodings:
            if enc != encoding:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
        
        # If all encodings fail, try with error handling
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Failed to read file with any encoding: {str(e)}")

def load_large_file_sync(file_path: str, encoding: str = 'utf-8') -> str:
    """
    Synchronously load a large file with optimized reading
    This is the main function to use for loading files into the normal text buffer
    """
    try:
        return load_file_content(file_path, encoding)
    except Exception as e:
        raise Exception(f"Failed to load file: {str(e)}")

def load_large_file_async(file_path: str, callback: Callable[[str], None], 
                         error_callback: Callable[[str], None] = None, 
                         encoding: str = 'utf-8') -> FastFileLoader:
    """
    Asynchronously load a large file
    Returns the loader thread object
    """
    loader = FastFileLoader(file_path, encoding)
    loader.loading_finished.connect(callback)
    if error_callback:
        loader.error_occurred.connect(error_callback)
    loader.start()
    return loader

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get basic file information"""
    try:
        file_size = os.path.getsize(file_path)
        encoding = 'utf-8'
        line_count = 0
        
        # Try to count lines
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                line_count = sum(1 for _ in f)
        except UnicodeDecodeError:
            # Try other encodings
            supported_encodings = CONFIG.get("supported_encodings", ["utf-8", "latin-1", "cp1252", "iso-8859-1"])
            for enc in supported_encodings[1:]:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        line_count = sum(1 for _ in f)
                    encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
        
        return {
            'path': file_path,
            'size': file_size,
            'size_mb': file_size / (1024 * 1024),
            'lines': line_count,
            'encoding': encoding
        }
    except Exception as e:
        return {'error': str(e)} 