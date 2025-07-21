"""
Provides mechanisms for handling streaming data from various sources.
Enables real-time updates to the spreadsheet from live data feeds.
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from core.interfaces import IWorkbook
from core.coordinates import CellCoordinate
from core.events import get_event_manager, EventType


class StreamSourceType(Enum):
    """Types of streaming data sources."""
    WEBSOCKET = "websocket"
    KAFKA = "kafka"
    MQTT = "mqtt"
    CUSTOM = "custom"


@dataclass
class StreamInfo:
    """
    Represents information about a streaming data source.
    """
    stream_id: str
    source_type: StreamSourceType
    source_config: Dict[str, Any]
    target_sheet: str
    target_cell: CellCoordinate
    is_active: bool = False
    last_update: float = 0.0
    error: Optional[str] = None
    
    # The thread that runs the streaming client
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)


class StreamingDataManager:
    """
    Manages the lifecycle of streaming data connections.
    Handles starting, stopping, and updating streams.
    """
    
    def __init__(self, workbook: IWorkbook):
        self.workbook = workbook
        self._streams: Dict[str, StreamInfo] = {}
        self._lock = threading.RLock()

    def add_stream(self, stream_info: StreamInfo) -> bool:
        """
        Adds and starts a new data stream.
        """
        with self._lock:
            if stream_info.stream_id in self._streams:
                print(f"Stream with ID \'{stream_info.stream_id}\' already exists.")
                return False
            
            self._streams[stream_info.stream_id] = stream_info
            return self.start_stream(stream_info.stream_id)

    def start_stream(self, stream_id: str) -> bool:
        """
        Starts a specific data stream.
        """
        with self._lock:
            stream_info = self._streams.get(stream_id)
            if not stream_info:
                print(f"Stream \'{stream_id}\' not found.")
                return False
            
            if stream_info.is_active:
                print(f"Stream \'{stream_id}\' is already active.")
                return True
            
            # Create and start the streaming client in a separate thread
            stream_info._stop_event.clear()
            stream_info._thread = threading.Thread(
                target=self._run_stream_client,
                args=(stream_info,)
            )
            stream_info._thread.daemon = True
            stream_info._thread.start()
            
            stream_info.is_active = True
            print(f"Stream \'{stream_id}\' started.")
            return True

    def stop_stream(self, stream_id: str) -> bool:
        """
        Stops a specific data stream.
        """
        with self._lock:
            stream_info = self._streams.get(stream_id)
            if not stream_info:
                print(f"Stream \'{stream_id}\' not found.")
                return False
            
            if not stream_info.is_active:
                print(f"Stream \'{stream_id}\' is already stopped.")
                return True
            
            # Signal the thread to stop
            stream_info._stop_event.set()
            if stream_info._thread and stream_info._thread.is_alive():
                stream_info._thread.join(timeout=5.0)
            
            stream_info.is_active = False
            print(f"Stream \'{stream_id}\' stopped.")
            return True

    def remove_stream(self, stream_id: str) -> bool:
        """
        Stops and removes a data stream.
        """
        with self._lock:
            if stream_id not in self._streams:
                return False
            
            self.stop_stream(stream_id)
            del self._streams[stream_id]
            print(f"Stream \'{stream_id}\' removed.")
            return True

    def get_stream(self, stream_id: str) -> Optional[StreamInfo]:
        """
        Retrieves information about a specific stream.
        """
        with self._lock:
            return self._streams.get(stream_id)

    def get_all_streams(self) -> List[StreamInfo]:
        """
        Returns a list of all configured streams.
        """
        with self._lock:
            return list(self._streams.values())

    def _run_stream_client(self, stream_info: StreamInfo) -> None:
        """
        The main loop for the streaming client thread.
        This is a placeholder for actual client implementations (e.g., WebSocket, Kafka).
        """
        print(f"Starting client for stream \'{stream_info.stream_id}\' of type {stream_info.source_type.value}")
        
        # Example: A simple counter for demonstration
        counter = 0
        while not stream_info._stop_event.is_set():
            try:
                # In a real implementation, this would be where you receive data from the source
                # For now, we just generate some data
                new_value = f"Stream Data: {counter}"
                counter += 1
                
                # Update the target cell in the spreadsheet
                self._update_sheet_cell(stream_info, new_value)
                
                # Simulate receiving data every second
                time.sleep(1.0)
                
            except Exception as e:
                stream_info.error = str(e)
                print(f"Error in stream \'{stream_info.stream_id}\": {e}")
                # Stop the stream on error
                break
        
        print(f"Stopping client for stream \'{stream_info.stream_id}\".")

    def _update_sheet_cell(self, stream_info: StreamInfo, value: Any) -> None:
        """
        Updates the target cell in the sheet with the new value from the stream.
        """
        sheet = self.workbook.get_sheet(stream_info.target_sheet)
        if not sheet:
            print(f"Target sheet \'{stream_info.target_sheet}\' not found for stream \'{stream_info.stream_id}\".")
            return
        
        # Set the cell value
        sheet.set_cell_value(stream_info.target_cell, value)
        stream_info.last_update = time.time()
        
        # Publish an event to notify the UI and other components
        get_event_manager().publish(
            EventType.CELL_VALUE_CHANGED,
            sheet_name=stream_info.target_sheet,
            coordinate=stream_info.target_cell,
            new_value=value,
            old_value=None # For simplicity, we don't track old value here
        )

    def cleanup(self) -> None:
        """
        Stops all active streams and cleans up resources.
        """
        with self._lock:
            for stream_id in list(self._streams.keys()):
                self.stop_stream(stream_id)
            self._streams.clear()


# Global instance for StreamingDataManager
_global_streaming_data_manager: Optional[StreamingDataManager] = None

def get_streaming_data_manager(workbook: IWorkbook) -> StreamingDataManager:
    """
    Returns the global StreamingDataManager instance.
    """
    global _global_streaming_data_manager
    if _global_streaming_data_manager is None:
        _global_streaming_data_manager = StreamingDataManager(workbook)
    return _global_streaming_data_manager


