"""
Provides mechanisms for real-time multi-user collaboration on workbooks.
This involves change synchronization, conflict resolution, and user presence.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from core.coordinates import CellCoordinate
from core.interfaces import IWorkbook, ISheet
from core.events import get_event_manager, EventType, CellChangeEvent


class CollaborationEventType(Enum):
    """
    Types of collaboration events.
    """
    CELL_CHANGE = "cell_change"
    SHEET_ADD = "sheet_add"
    SHEET_REMOVE = "sheet_remove"
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    SELECTION_CHANGE = "selection_change"


@dataclass
class CollaborationEvent:
    """
    Represents a single collaboration event.
    """
    event_type: CollaborationEventType
    user_id: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPresence:
    """
    Information about a collaborating user.
    """
    user_id: str
    username: str
    current_sheet: Optional[str] = None
    current_selection: Optional[CellRange] = None
    last_active: float = field(default_factory=time.time)


class CollaborationManager:
    """
    Manages real-time collaboration features.
    This is a client-side component that interacts with a (hypothetical) collaboration server.
    """
    
    def __init__(self, workbook: IWorkbook, user_id: str, username: str):
        self.workbook = workbook
        self.user_id = user_id
        self.username = username
        self._connected = False
        self._current_presence = UserPresence(user_id, username)
        self._active_users: Dict[str, UserPresence] = {user_id: self._current_presence}
        self._event_queue: List[CollaborationEvent] = []
        self._lock = threading.RLock()
        
        # Subscribe to local changes to send to server
        get_event_manager().subscribe(EventType.CELL_VALUE_CHANGED, self._on_local_cell_change)
        get_event_manager().subscribe(EventType.CELL_FORMULA_CHANGED, self._on_local_cell_change)
        get_event_manager().subscribe(EventType.SHEET_ADDED, self._on_local_sheet_add)
        get_event_manager().subscribe(EventType.SHEET_REMOVED, self._on_local_sheet_remove)
        # TODO: Subscribe to selection changes from UI

        # Simulate server connection/disconnection
        self._server_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def connect(self, server_url: str) -> None:
        """
        Connects to the collaboration server.
        """
        with self._lock:
            if self._connected:
                print("Already connected to collaboration server.")
                return
            
            print(f"Connecting to collaboration server at {server_url}...")
            self._connected = True
            self._stop_event.clear()
            self._server_thread = threading.Thread(target=self._simulate_server_interaction, args=(server_url,))
            self._server_thread.daemon = True
            self._server_thread.start()
            
            # Send initial join event
            self._send_event(CollaborationEventType.USER_JOIN, {"username": self.username})
            print("Connected to collaboration server.")

    def disconnect(self) -> None:
        """
        Disconnects from the collaboration server.
        """
        with self._lock:
            if not self._connected:
                print("Not connected to collaboration server.")
                return
            
            print("Disconnecting from collaboration server...")
            self._send_event(CollaborationEventType.USER_LEAVE, {})
            self._stop_event.set()
            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=5.0)
            self._connected = False
            self._active_users.clear()
            self._active_users[self.user_id] = self._current_presence # Re-add self
            print("Disconnected from collaboration server.")

    def _send_event(self, event_type: CollaborationEventType, payload: Dict[str, Any]) -> None:
        """
        Adds an event to the outgoing queue to be sent to the server.
        """
        event = CollaborationEvent(event_type, self.user_id, time.time(), payload)
        with self._lock:
            self._event_queue.append(event)
            print(f"Queued outgoing event: {event_type.value}")

    def _simulate_server_interaction(self, server_url: str) -> None:
        """
        Simulates interaction with a collaboration server.
        In a real application, this would be WebSocket or similar.
        """
        print(f"Simulating server interaction for {self.user_id}...")
        while not self._stop_event.is_set():
            # Simulate sending events to server
            with self._lock:
                if self._event_queue:
                    event = self._event_queue.pop(0)
                    print(f"Simulating SEND: {event.event_type.value} from {event.user_id}")
                    # In a real app, send event over network
                    
                    # Simulate receiving events from other users/server
                    # For demonstration, let's simulate a remote cell change
                    if event.event_type == CollaborationEventType.USER_JOIN and event.user_id != self.user_id:
                        # Simulate another user joining
                        remote_user_id = "remote_user_1"
                        remote_username = "RemoteUser"
                        remote_event = CollaborationEvent(
                            CollaborationEventType.USER_JOIN,
                            remote_user_id,
                            time.time(),
                            {"username": remote_username}
                        )
                        self._process_incoming_event(remote_event)
                        
                        # Simulate a remote cell change after a delay
                        time.sleep(0.5)
                        remote_change_event = CollaborationEvent(
                            CollaborationEventType.CELL_CHANGE,
                            remote_user_id,
                            time.time(),
                            {
                                "sheet_name": "Sheet1",
                                "row": 0,
                                "col": 2,
                                "value": f"Remote Update {time.time():.0f}"
                            }
                        )
                        self._process_incoming_event(remote_change_event)

            # Simulate receiving events from server
            # This part would be driven by actual network events
            time.sleep(0.1) # Small delay to simulate network latency

    def _process_incoming_event(self, event: CollaborationEvent) -> None:
        """
        Processes an incoming collaboration event from the server.
        """
        with self._lock:
            if event.user_id == self.user_id: # Ignore events originating from self
                return

            print(f"Processing incoming event: {event.event_type.value} from {event.user_id}")
            
            if event.event_type == CollaborationEventType.USER_JOIN:
                self._active_users[event.user_id] = UserPresence(
                    event.user_id, event.payload.get("username", "Unknown"), last_active=event.timestamp
                )
                get_event_manager().publish(EventType.COLLABORATION_USER_JOIN, user_id=event.user_id, username=event.payload.get("username"))
                print(f"User {event.payload.get("username")} joined.")

            elif event.event_type == CollaborationEventType.USER_LEAVE:
                if event.user_id in self._active_users:
                    del self._active_users[event.user_id]
                get_event_manager().publish(EventType.COLLABORATION_USER_LEAVE, user_id=event.user_id)
                print(f"User {event.user_id} left.")

            elif event.event_type == CollaborationEventType.CELL_CHANGE:
                sheet_name = event.payload.get("sheet_name")
                row = event.payload.get("row")
                col = event.payload.get("col")
                value = event.payload.get("value")
                formula = event.payload.get("formula")

                sheet = self.workbook.get_sheet(sheet_name)
                if sheet:
                    coord = CellCoordinate(row, col)
                    # Apply change to local workbook
                    # This is where conflict resolution logic would go in a real system
                    sheet.set_cell_value(coord, value)
                    if formula:
                        sheet.set_cell_formula(coord, formula)
                    print(f"Applied remote change to {sheet_name}!{coord.to_a1()} = {value}")
                    # Notify UI of remote change
                    get_event_manager().publish(EventType.CELL_VALUE_CHANGED, sheet_name=sheet_name, coordinate=coord, new_value=value, old_value=None, is_remote=True)
                else:
                    print(f"Sheet {sheet_name} not found for remote cell change.")

            elif event.event_type == CollaborationEventType.SHEET_ADD:
                sheet_name = event.payload.get("sheet_name")
                if not self.workbook.get_sheet(sheet_name):
                    self.workbook.add_sheet(sheet_name)
                    get_event_manager().publish(EventType.SHEET_ADDED, sheet_name=sheet_name, is_remote=True)
                    print(f"Applied remote sheet add: {sheet_name}")

            elif event.event_type == CollaborationEventType.SHEET_REMOVE:
                sheet_name = event.payload.get("sheet_name")
                if self.workbook.get_sheet(sheet_name):
                    self.workbook.remove_sheet(sheet_name)
                    get_event_manager().publish(EventType.SHEET_REMOVED, sheet_name=sheet_name, is_remote=True)
                    print(f"Applied remote sheet remove: {sheet_name}")

            # Update user presence last active time
            if event.user_id in self._active_users:
                self._active_users[event.user_id].last_active = event.timestamp

    def get_active_users(self) -> List[UserPresence]:
        """
        Returns a list of currently active collaborating users.
        """
        with self._lock:
            return list(self._active_users.values())

    def update_presence(self, sheet_name: Optional[str] = None, selection: Optional[CellRange] = None) -> None:
        """
        Updates the current user's presence information and sends it to the server.
        """
        with self._lock:
            if sheet_name is not None:
                self._current_presence.current_sheet = sheet_name
            if selection is not None:
                self._current_presence.current_selection = selection
            self._current_presence.last_active = time.time()
            
            # Send presence update to server (e.g., every few seconds or on significant change)
            # For simplicity, we'll just queue it immediately here.
            self._send_event(CollaborationEventType.SELECTION_CHANGE, {
                "sheet_name": self._current_presence.current_sheet,
                "selection": selection.to_a1() if selection else None
            })

    def _on_local_cell_change(self, event: CellChangeEvent) -> None:
        """
        Handler for local cell changes, to be sent to the server.
        """
        if not event.is_remote: # Only send local changes
            payload = {
                "sheet_name": event.sheet_name,
                "row": event.coordinate.row,
                "col": event.coordinate.col,
                "value": event.new_value,
                "formula": event.new_formula
            }
            self._send_event(CollaborationEventType.CELL_CHANGE, payload)

    def _on_local_sheet_add(self, event: SheetChangeEvent) -> None:
        """
        Handler for local sheet additions, to be sent to the server.
        """
        if not event.is_remote:
            payload = {"sheet_name": event.sheet_name}
            self._send_event(CollaborationEventType.SHEET_ADD, payload)

    def _on_local_sheet_remove(self, event: SheetChangeEvent) -> None:
        """
        Handler for local sheet removals, to be sent to the server.
        """
        if not event.is_remote:
            payload = {"sheet_name": event.sheet_name}
            self._send_event(CollaborationEventType.SHEET_REMOVE, payload)

    def cleanup(self) -> None:
        """
        Cleans up resources and unsubscribes from events.
        """
        self.disconnect()
        get_event_manager().unsubscribe(EventType.CELL_VALUE_CHANGED, self._on_local_cell_change)
        get_event_manager().unsubscribe(EventType.CELL_FORMULA_CHANGED, self._on_local_cell_change)
        get_event_manager().unsubscribe(EventType.SHEET_ADDED, self._on_local_sheet_add)
        get_event_manager().unsubscribe(EventType.SHEET_REMOVED, self._on_local_sheet_remove)


# Global instance for CollaborationManager (requires workbook, user_id, username)
_global_collaboration_manager: Optional[CollaborationManager] = None

def get_collaboration_manager(workbook: IWorkbook, user_id: str = "local_user", username: str = "Local User") -> CollaborationManager:
    """
    Returns the global CollaborationManager instance.
    """
    global _global_collaboration_manager
    if _global_collaboration_manager is None:
        _global_collaboration_manager = CollaborationManager(workbook, user_id, username)
    return _global_collaboration_manager


