"""
Provides integration with a version control system (e.g., Git-like functionality).
Enables tracking changes, committing versions, and rolling back to previous states.
"""

import os
import json
import hashlib
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from core.interfaces import IWorkbook, ISheet
from core.coordinates import CellCoordinate
from core.events import get_event_manager, EventType, CellChangeEvent
from .file_format import CellEditorFileFormat


@dataclass
class CommitInfo:
    """
    Represents a single commit in the version history.
    """
    commit_id: str
    timestamp: float
    message: str
    author: str
    parent_commit_id: Optional[str] = None
    snapshot_path: str = "" # Path to the full workbook snapshot for this commit


class VersionControlManager:
    """
    Manages version control for a workbook.
    Simulates Git-like operations (commit, checkout, history).
    """
    
    def __init__(self, workbook: IWorkbook, repo_path: str, author: str = "System"):
        self.workbook = workbook
        self.repo_path = os.path.abspath(repo_path)
        self.author = author
        self._commits: Dict[str, CommitInfo] = {}
        self._head: Optional[str] = None # Points to the latest commit ID
        self._lock = threading.RLock()
        self._file_format = CellEditorFileFormat()

        self._init_repository()
        self._load_history()

        # Subscribe to changes to track for potential commits
        get_event_manager().subscribe(EventType.CELL_VALUE_CHANGED, self._on_workbook_change)
        get_event_manager().subscribe(EventType.CELL_FORMULA_CHANGED, self._on_workbook_change)
        get_event_manager().subscribe(EventType.SHEET_ADDED, self._on_workbook_change)
        get_event_manager().subscribe(EventType.SHEET_REMOVED, self._on_workbook_change)

        self._has_uncommitted_changes = False

    def _init_repository(self) -> None:
        """
        Initializes the version control repository structure.
        """
        os.makedirs(self.repo_path, exist_ok=True)
        os.makedirs(os.path.join(self.repo_path, "snapshots"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_path, "logs"), exist_ok=True)
        print(f"Version control repository initialized at: {self.repo_path}")

    def _load_history(self) -> None:
        """
        Loads commit history from the repository logs.
        """
        log_file = os.path.join(self.repo_path, "logs", "commits.json")
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                log_data = json.load(f)
                for commit_dict in log_data.get("commits", []):
                    commit = CommitInfo(**commit_dict)
                    self._commits[commit.commit_id] = commit
                self._head = log_data.get("head")
            print(f"Loaded {len(self._commits)} commits from history.")

    def _save_history(self) -> None:
        """
        Saves the current commit history to the repository logs.
        """
        log_file = os.path.join(self.repo_path, "logs", "commits.json")
        with open(log_file, "w") as f:
            json.dump({
                "head": self._head,
                "commits": [c.__dict__ for c in self._commits.values()]
            }, f, indent=2)

    def _on_workbook_change(self, *args, **kwargs) -> None:
        """
        Marks that there are uncommitted changes in the workbook.
        """
        with self._lock:
            self._has_uncommitted_changes = True
            print("VersionControl: Uncommitted changes detected.")

    def has_uncommitted_changes(self) -> bool:
        """
        Checks if there are any uncommitted changes in the workbook.
        """
        with self._lock:
            return self._has_uncommitted_changes

    def commit(self, message: str) -> Optional[str]:
        """
        Creates a new commit, saving the current state of the workbook.
        """
        with self._lock:
            # Save a full snapshot of the current workbook state
            timestamp = time.time()
            commit_id = hashlib.sha1(f"{timestamp}-{message}-{self.author}-{self._head}".encode()).hexdigest()
            snapshot_filename = f"{commit_id}.cef"
            snapshot_path = os.path.join(self.repo_path, "snapshots", snapshot_filename)
            
            try:
                self._file_format.save_workbook(self.workbook, snapshot_path)
            except Exception as e:
                print(f"Error saving workbook snapshot for commit: {e}")
                return None

            commit_info = CommitInfo(
                commit_id=commit_id,
                timestamp=timestamp,
                message=message,
                author=self.author,
                parent_commit_id=self._head,
                snapshot_path=snapshot_path
            )
            
            self._commits[commit_id] = commit_info
            self._head = commit_id
            self._has_uncommitted_changes = False
            self._save_history()
            
            print(f"Committed changes: {message} (ID: {commit_id[:8]})")
            get_event_manager().publish(EventType.VERSION_CONTROL_COMMIT, commit_id=commit_id, message=message)
            return commit_id

    def checkout(self, commit_id: str) -> bool:
        """
        Loads a previous version of the workbook from a commit snapshot.
        Warning: This will overwrite the current workbook state.
        """
        with self._lock:
            if commit_id not in self._commits:
                print(f"Commit ID \'{commit_id}\' not found.")
                return False
            
            if self.has_uncommitted_changes():
                print("Warning: Uncommitted changes exist. Please commit or discard them before checking out.")
                return False

            commit_info = self._commits[commit_id]
            snapshot_path = commit_info.snapshot_path
            
            if not os.path.exists(snapshot_path):
                print(f"Snapshot file not found for commit {commit_id}: {snapshot_path}")
                return False

            try:
                # Clear current workbook and load from snapshot
                # This assumes the workbook has a method to clear all data
                # For a real implementation, you might need to re-initialize the workbook object
                # or provide a deep clear method.
                print(f"Checking out commit {commit_id[:8]}...")
                # Temporarily unsubscribe to avoid recording checkout as changes
                get_event_manager().unsubscribe(EventType.CELL_VALUE_CHANGED, self._on_workbook_change)
                get_event_manager().unsubscribe(EventType.CELL_FORMULA_CHANGED, self._on_workbook_change)
                get_event_manager().unsubscribe(EventType.SHEET_ADDED, self._on_workbook_change)
                get_event_manager().unsubscribe(EventType.SHEET_REMOVED, self._on_workbook_change)

                # Assuming workbook has a method to load from a file path directly
                # Or we manually clear and load sheet by sheet
                # For now, let's simulate clearing and loading
                for sheet_name in list(self.workbook.get_sheet_names()):
                    self.workbook.remove_sheet(sheet_name)
                
                # Load the snapshot into the current workbook instance
                self._file_format.load_workbook(snapshot_path, self.workbook)
                
                self._head = commit_id # Update HEAD to the checked out commit
                self._has_uncommitted_changes = False # No uncommitted changes after checkout
                self._save_history()

                print(f"Successfully checked out commit {commit_id[:8]}.")
                get_event_manager().publish(EventType.VERSION_CONTROL_CHECKOUT, commit_id=commit_id)
                return True
            except Exception as e:
                print(f"Error during checkout of commit {commit_id}: {e}")
                return False
            finally:
                # Re-subscribe to events
                get_event_manager().subscribe(EventType.CELL_VALUE_CHANGED, self._on_workbook_change)
                get_event_manager().subscribe(EventType.CELL_FORMULA_CHANGED, self._on_workbook_change)
                get_event_manager().subscribe(EventType.SHEET_ADDED, self._on_workbook_change)
                get_event_manager().subscribe(EventType.SHEET_REMOVED, self._on_workbook_change)

    def get_history(self) -> List[CommitInfo]:
        """
        Returns the commit history, ordered from newest to oldest.
        """
        with self._lock:
            # Sort by timestamp descending
            return sorted(self._commits.values(), key=lambda c: c.timestamp, reverse=True)

    def get_head_commit(self) -> Optional[CommitInfo]:
        """
        Returns the information for the current HEAD commit.
        """
        with self._lock:
            if self._head and self._head in self._commits:
                return self._commits[self._head]
            return None

    def cleanup(self) -> None:
        """
        Unsubscribes from events and cleans up resources.
        """
        get_event_manager().unsubscribe(EventType.CELL_VALUE_CHANGED, self._on_workbook_change)
        get_event_manager().unsubscribe(EventType.CELL_FORMULA_CHANGED, self._on_workbook_change)
        get_event_manager().unsubscribe(EventType.SHEET_ADDED, self._on_workbook_change)
        get_event_manager().unsubscribe(EventType.SHEET_REMOVED, self._on_workbook_change)


# Global instance for VersionControlManager (requires workbook and repo_path)
_global_version_control_manager: Optional[VersionControlManager] = None

def get_version_control_manager(workbook: IWorkbook, repo_path: str, author: str = "System") -> VersionControlManager:
    """
    Returns the global VersionControlManager instance.
    """
    global _global_version_control_manager
    if _global_version_control_manager is None:
        _global_version_control_manager = VersionControlManager(workbook, repo_path, author)
    return _global_version_control_manager


