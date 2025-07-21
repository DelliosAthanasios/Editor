"""
Provides automatic backup and recovery mechanisms for workbooks.
Ensures data safety and allows restoration from previous states.
"""

import os
import shutil
import time
import threading
from typing import Any, Dict, List, Optional, Tuple

from core.interfaces import IWorkbook
from .file_format import CellEditorFileFormat


class BackupRecoveryManager:
    """
    Manages automatic backups and provides recovery functionalities.
    """
    
    def __init__(self, workbook: IWorkbook, backup_dir: str, 
                 backup_interval_minutes: int = 5, max_backups: int = 10):
        self.workbook = workbook
        self.backup_dir = os.path.abspath(backup_dir)
        self.backup_interval_minutes = backup_interval_minutes
        self.max_backups = max_backups
        self._lock = threading.RLock()
        self._file_format = CellEditorFileFormat()
        self._backup_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._init_backup_directory()

    def _init_backup_directory(self) -> None:
        """
        Ensures the backup directory exists.
        """
        os.makedirs(self.backup_dir, exist_ok=True)
        print(f"Backup directory initialized at: {self.backup_dir}")

    def start_auto_backup(self) -> None:
        """
        Starts the automatic backup thread.
        """
        with self._lock:
            if self._backup_thread and self._backup_thread.is_alive():
                print("Auto-backup thread is already running.")
                return
            
            self._stop_event.clear()
            self._backup_thread = threading.Thread(target=self._auto_backup_loop)
            self._backup_thread.daemon = True # Allow program to exit even if thread is running
            self._backup_thread.start()
            print(f"Auto-backup started with interval: {self.backup_interval_minutes} minutes.")

    def stop_auto_backup(self) -> None:
        """
        Stops the automatic backup thread.
        """
        with self._lock:
            if self._backup_thread and self._backup_thread.is_alive():
                self._stop_event.set()
                self._backup_thread.join(timeout=self.backup_interval_minutes * 60 + 5) # Wait for thread to finish current cycle
                print("Auto-backup stopped.")
            else:
                print("Auto-backup thread is not running.")

    def _auto_backup_loop(self) -> None:
        """
        The main loop for the automatic backup thread.
        """
        while not self._stop_event.is_set():
            time.sleep(self.backup_interval_minutes * 60)
            if not self._stop_event.is_set(): # Check again after sleep
                self.create_backup()

    def create_backup(self) -> Optional[str]:
        """
        Creates a manual backup of the current workbook state.
        """
        with self._lock:
            timestamp = int(time.time())
            backup_filename = f"workbook_backup_{timestamp}.cef"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            try:
                # Assuming the workbook can be saved to a temporary path first
                # and then moved to the backup directory.
                # Or directly save to the backup path.
                self._file_format.save_workbook(self.workbook, backup_path)
                self._clean_old_backups()
                print(f"Backup created: {backup_path}")
                return backup_path
            except Exception as e:
                print(f"Error creating backup: {e}")
                return None

    def _clean_old_backups(self) -> None:
        """
        Removes old backups, keeping only the 'max_backups' most recent ones.
        """
        backups = []
        for f_name in os.listdir(self.backup_dir):
            f_path = os.path.join(self.backup_dir, f_name)
            if os.path.isfile(f_path) and f_name.startswith("workbook_backup_") and f_name.endswith(".cef"):
                backups.append((os.path.getmtime(f_path), f_path))
        
        backups.sort(key=lambda x: x[0], reverse=True) # Sort by modification time, newest first
        
        if len(backups) > self.max_backups:
            for i in range(self.max_backups, len(backups)):
                old_backup_path = backups[i][1]
                try:
                    os.remove(old_backup_path)
                    print(f"Removed old backup: {old_backup_path}")
                except Exception as e:
                    print(f"Error removing old backup {old_backup_path}: {e}")

    def list_backups(self) -> List[str]:
        """
        Lists all available backup files.
        """
        with self._lock:
            backups = []
            for f_name in os.listdir(self.backup_dir):
                f_path = os.path.join(self.backup_dir, f_name)
                if os.path.isfile(f_path) and f_name.startswith("workbook_backup_") and f_name.endswith(".cef"):
                    backups.append(f_path)
            backups.sort(key=os.path.getmtime, reverse=True)
            return backups

    def restore_from_backup(self, backup_path: str) -> bool:
        """
        Restores the workbook from a specified backup file.
        Warning: This will overwrite the current workbook state.
        """
        with self._lock:
            if not os.path.exists(backup_path):
                print(f"Backup file not found: {backup_path}")
                return False
            
            try:
                print(f"Restoring workbook from backup: {backup_path}")
                # Clear current workbook and load from backup
                # This assumes the workbook has a method to clear all data
                for sheet_name in list(self.workbook.get_sheet_names()):
                    self.workbook.remove_sheet(sheet_name)
                
                self._file_format.load_workbook(backup_path, self.workbook)
                print("Workbook restored successfully.")
                return True
            except Exception as e:
                print(f"Error restoring from backup {backup_path}: {e}")
                return False

    def cleanup(self) -> None:
        """
        Stops the auto-backup thread and cleans up resources.
        """
        self.stop_auto_backup()


# Global instance for BackupRecoveryManager (requires workbook and backup_dir)
_global_backup_recovery_manager: Optional[BackupRecoveryManager] = None

def get_backup_recovery_manager(workbook: IWorkbook, backup_dir: str = "./backups", 
                                backup_interval_minutes: int = 5, max_backups: int = 10) -> BackupRecoveryManager:
    """
    Returns the global BackupRecoveryManager instance.
    """
    global _global_backup_recovery_manager
    if _global_backup_recovery_manager is None:
        _global_backup_recovery_manager = BackupRecoveryManager(workbook, backup_dir, 
                                                                backup_interval_minutes, max_backups)
    return _global_backup_recovery_manager


