"""
Virtual scroller for smooth scrolling through millions of cells.
Implements momentum scrolling, smooth animations, and efficient updates.
"""

import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from core.config import get_config
from ui.viewport import Viewport, ViewportMetrics


class ScrollDirection(Enum):
    """Scroll directions."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOTH = "both"


class ScrollMode(Enum):
    """Scroll modes."""
    INSTANT = "instant"
    SMOOTH = "smooth"
    MOMENTUM = "momentum"


@dataclass
class ScrollEvent:
    """Scroll event data."""
    delta_x: int
    delta_y: int
    direction: ScrollDirection
    timestamp: float
    is_touch: bool = False
    is_wheel: bool = False


@dataclass
class ScrollState:
    """Current scroll state."""
    position_x: int
    position_y: int
    velocity_x: float
    velocity_y: float
    is_scrolling: bool
    last_update: float


class ScrollAnimation:
    """Smooth scroll animation handler."""
    
    def __init__(self, duration: float = 0.3, easing: str = "ease_out"):
        self.duration = duration
        self.easing = easing
        self.start_time: Optional[float] = None
        self.start_x: int = 0
        self.start_y: int = 0
        self.target_x: int = 0
        self.target_y: int = 0
        self.is_active = False
    
    def start(self, start_x: int, start_y: int, target_x: int, target_y: int) -> None:
        """Start a new animation."""
        self.start_time = time.time()
        self.start_x = start_x
        self.start_y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.is_active = True
    
    def update(self) -> Tuple[int, int, bool]:
        """Update animation and return current position and completion status."""
        if not self.is_active or self.start_time is None:
            return self.target_x, self.target_y, True
        
        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / self.duration)
        
        # Apply easing
        if self.easing == "ease_out":
            progress = 1 - (1 - progress) ** 3
        elif self.easing == "ease_in":
            progress = progress ** 3
        elif self.easing == "ease_in_out":
            if progress < 0.5:
                progress = 2 * progress ** 3
            else:
                progress = 1 - 2 * (1 - progress) ** 3
        
        # Calculate current position
        current_x = int(self.start_x + (self.target_x - self.start_x) * progress)
        current_y = int(self.start_y + (self.target_y - self.start_y) * progress)
        
        # Check if animation is complete
        is_complete = progress >= 1.0
        if is_complete:
            self.is_active = False
            current_x = self.target_x
            current_y = self.target_y
        
        return current_x, current_y, is_complete
    
    def stop(self) -> None:
        """Stop the animation."""
        self.is_active = False


class MomentumScroller:
    """Momentum scrolling implementation."""
    
    def __init__(self, friction: float = 0.95, min_velocity: float = 1.0):
        self.friction = friction
        self.min_velocity = min_velocity
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.is_active = False
        self.last_update = time.time()
    
    def add_velocity(self, delta_x: float, delta_y: float) -> None:
        """Add velocity from user input."""
        self.velocity_x += delta_x
        self.velocity_y += delta_y
        self.is_active = True
        self.last_update = time.time()
    
    def update(self) -> Tuple[float, float, bool]:
        """Update momentum and return velocity and active status."""
        if not self.is_active:
            return 0.0, 0.0, False
        
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # Apply friction
        self.velocity_x *= self.friction
        self.velocity_y *= self.friction
        
        # Stop if velocity is too low
        if (abs(self.velocity_x) < self.min_velocity and 
            abs(self.velocity_y) < self.min_velocity):
            self.velocity_x = 0.0
            self.velocity_y = 0.0
            self.is_active = False
            return 0.0, 0.0, False
        
        return self.velocity_x, self.velocity_y, True
    
    def stop(self) -> None:
        """Stop momentum scrolling."""
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.is_active = False


class VirtualScroller:
    """
    Virtual scroller for handling smooth scrolling through large datasets.
    Supports momentum scrolling, smooth animations, and efficient viewport updates.
    """
    
    def __init__(self, viewport: Viewport, update_callback: Optional[Callable] = None):
        self.viewport = viewport
        self.update_callback = update_callback
        
        # Scroll state
        self.state = ScrollState(
            position_x=0,
            position_y=0,
            velocity_x=0.0,
            velocity_y=0.0,
            is_scrolling=False,
            last_update=time.time()
        )
        
        # Animation and momentum
        self.animation = ScrollAnimation()
        self.momentum = MomentumScroller()
        
        # Configuration
        self.scroll_sensitivity = get_config().ui.scroll_sensitivity
        self.enable_momentum = get_config().ui.enable_momentum_scrolling
        self.enable_smooth_scrolling = get_config().ui.enable_smooth_scrolling
        
        # Threading
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Performance tracking
        self._scroll_events = 0
        self._update_count = 0
        self._last_fps_check = time.time()
        self._fps_counter = 0
        self._current_fps = 0.0
        
        # Start update thread
        self._start_update_thread()
    
    def handle_scroll(self, event: ScrollEvent) -> None:
        """Handle a scroll event."""
        with self._lock:
            self._scroll_events += 1
            
            # Apply sensitivity
            delta_x = event.delta_x * self.scroll_sensitivity
            delta_y = event.delta_y * self.scroll_sensitivity
            
            # Update state
            self.state.is_scrolling = True
            self.state.last_update = event.timestamp
            
            if event.is_wheel and self.enable_momentum:
                # Add to momentum for wheel events
                self.momentum.add_velocity(delta_x, delta_y)
            else:
                # Direct scroll for touch/drag events
                self._scroll_direct(delta_x, delta_y)
    
    def scroll_to(self, x: int, y: int, mode: ScrollMode = ScrollMode.SMOOTH) -> None:
        """Scroll to a specific position."""
        with self._lock:
            current_x = self.state.position_x
            current_y = self.state.position_y
            
            # Clamp to valid range
            max_x = self._get_max_scroll_x()
            max_y = self._get_max_scroll_y()
            
            target_x = max(0, min(x, max_x))
            target_y = max(0, min(y, max_y))
            
            if mode == ScrollMode.INSTANT:
                self._update_position(target_x, target_y)
            elif mode == ScrollMode.SMOOTH and self.enable_smooth_scrolling:
                self.animation.start(current_x, current_y, target_x, target_y)
            else:
                self._update_position(target_x, target_y)
    
    def scroll_by(self, delta_x: int, delta_y: int, mode: ScrollMode = ScrollMode.INSTANT) -> None:
        """Scroll by a relative amount."""
        current_x = self.state.position_x
        current_y = self.state.position_y
        self.scroll_to(current_x + delta_x, current_y + delta_y, mode)
    
    def scroll_to_cell(self, row: int, col: int, mode: ScrollMode = ScrollMode.SMOOTH) -> None:
        """Scroll to make a specific cell visible."""
        metrics = self.viewport.metrics
        
        # Calculate target scroll position
        target_x = col * metrics.cell_width
        target_y = row * metrics.cell_height
        
        # Adjust to center the cell if possible
        center_x = target_x - (metrics.content_width // 2)
        center_y = target_y - (metrics.content_height // 2)
        
        self.scroll_to(center_x, center_y, mode)
    
    def page_up(self) -> None:
        """Scroll up by one page."""
        page_height = self.viewport.metrics.content_height
        self.scroll_by(0, -page_height, ScrollMode.SMOOTH)
    
    def page_down(self) -> None:
        """Scroll down by one page."""
        page_height = self.viewport.metrics.content_height
        self.scroll_by(0, page_height, ScrollMode.SMOOTH)
    
    def page_left(self) -> None:
        """Scroll left by one page."""
        page_width = self.viewport.metrics.content_width
        self.scroll_by(-page_width, 0, ScrollMode.SMOOTH)
    
    def page_right(self) -> None:
        """Scroll right by one page."""
        page_width = self.viewport.metrics.content_width
        self.scroll_by(page_width, 0, ScrollMode.SMOOTH)
    
    def home(self) -> None:
        """Scroll to the top-left corner."""
        self.scroll_to(0, 0, ScrollMode.SMOOTH)
    
    def end(self) -> None:
        """Scroll to the bottom-right corner."""
        max_x = self._get_max_scroll_x()
        max_y = self._get_max_scroll_y()
        self.scroll_to(max_x, max_y, ScrollMode.SMOOTH)
    
    def _scroll_direct(self, delta_x: float, delta_y: float) -> None:
        """Apply direct scrolling without momentum."""
        new_x = self.state.position_x + int(delta_x)
        new_y = self.state.position_y + int(delta_y)
        self._update_position(new_x, new_y)
    
    def _update_position(self, x: int, y: int) -> None:
        """Update scroll position and viewport."""
        # Clamp to valid range
        max_x = self._get_max_scroll_x()
        max_y = self._get_max_scroll_y()
        
        x = max(0, min(x, max_x))
        y = max(0, min(y, max_y))
        
        # Update state
        old_x = self.state.position_x
        old_y = self.state.position_y
        
        self.state.position_x = x
        self.state.position_y = y
        
        # Update viewport if position changed
        if x != old_x or y != old_y:
            new_metrics = ViewportMetrics(
                width=self.viewport.metrics.width,
                height=self.viewport.metrics.height,
                scroll_x=x,
                scroll_y=y,
                cell_width=self.viewport.metrics.cell_width,
                cell_height=self.viewport.metrics.cell_height,
                header_height=self.viewport.metrics.header_height,
                row_header_width=self.viewport.metrics.row_header_width
            )
            
            self.viewport.update_metrics(new_metrics)
            
            # Notify callback
            if self.update_callback:
                self.update_callback(x, y)
    
    def _get_max_scroll_x(self) -> int:
        """Get maximum horizontal scroll position."""
        total_width = get_config().limits.max_columns * self.viewport.metrics.cell_width
        return max(0, total_width - self.viewport.metrics.content_width)
    
    def _get_max_scroll_y(self) -> int:
        """Get maximum vertical scroll position."""
        total_height = get_config().limits.max_rows * self.viewport.metrics.cell_height
        return max(0, total_height - self.viewport.metrics.content_height)
    
    def _start_update_thread(self) -> None:
        """Start the update thread for animations and momentum."""
        if self._update_thread and self._update_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
    
    def _update_loop(self) -> None:
        """Main update loop for animations and momentum."""
        target_fps = get_config().ui.target_fps
        frame_time = 1.0 / target_fps
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            with self._lock:
                needs_update = False
                
                # Update animation
                if self.animation.is_active:
                    x, y, complete = self.animation.update()
                    self._update_position(x, y)
                    needs_update = True
                    
                    if complete:
                        self.state.is_scrolling = False
                
                # Update momentum
                if self.momentum.is_active and self.enable_momentum:
                    vel_x, vel_y, active = self.momentum.update()
                    if active:
                        self._scroll_direct(vel_x, vel_y)
                        needs_update = True
                    else:
                        self.state.is_scrolling = False
                
                # Update FPS counter
                self._fps_counter += 1
                current_time = time.time()
                if current_time - self._last_fps_check >= 1.0:
                    self._current_fps = self._fps_counter / (current_time - self._last_fps_check)
                    self._fps_counter = 0
                    self._last_fps_check = current_time
                
                if needs_update:
                    self._update_count += 1
            
            # Sleep to maintain target FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def stop(self) -> None:
        """Stop the scroller and cleanup resources."""
        self._stop_event.set()
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)
        
        self.animation.stop()
        self.momentum.stop()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scroller statistics."""
        with self._lock:
            return {
                'state': {
                    'position_x': self.state.position_x,
                    'position_y': self.state.position_y,
                    'velocity_x': self.state.velocity_x,
                    'velocity_y': self.state.velocity_y,
                    'is_scrolling': self.state.is_scrolling
                },
                'performance': {
                    'scroll_events': self._scroll_events,
                    'update_count': self._update_count,
                    'current_fps': self._current_fps,
                    'target_fps': get_config().ui.target_fps
                },
                'features': {
                    'momentum_enabled': self.enable_momentum,
                    'smooth_scrolling_enabled': self.enable_smooth_scrolling,
                    'animation_active': self.animation.is_active,
                    'momentum_active': self.momentum.is_active
                },
                'limits': {
                    'max_scroll_x': self._get_max_scroll_x(),
                    'max_scroll_y': self._get_max_scroll_y()
                }
            }

