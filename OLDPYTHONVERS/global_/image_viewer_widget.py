import os
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QSlider, QToolBar, QAction, QFileDialog,
    QSplitter, QMessageBox, QSizePolicy, QFrame, QGraphicsOpacityEffect
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QIcon, QFont, QPalette, QColor, QTransform
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve

class FloatingButton(QPushButton):
    """Custom floating button with transparency and hover effects."""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(40, 40)
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 120);
                border: none;
                border-radius: 20px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 180);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 200);
            }
        """)
        
        # Set opacity effect
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.7)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Animation for hover effects
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def enterEvent(self, event):
        """Handle mouse enter event."""
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(self.opacity_effect.opacity())
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event."""
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(self.opacity_effect.opacity())
        self.opacity_animation.setEndValue(0.7)
        self.opacity_animation.start()
        super().leaveEvent(event)

class FloatingZoomSlider(QSlider):
    """Custom floating zoom slider."""
    
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setFixedSize(120, 30)
        self.setStyleSheet("""
            QSlider {
                background-color: rgba(0, 0, 0, 120);
                border-radius: 15px;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: rgba(255, 255, 255, 100);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: none;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #f0f0f0;
            }
        """)
        
        # Set opacity effect
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.7)
        self.setGraphicsEffect(self.opacity_effect)

class FloatingZoomLabel(QLabel):
    """Custom floating zoom percentage label."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 120);
                color: white;
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        
        # Set opacity effect
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.7)
        self.setGraphicsEffect(self.opacity_effect)

class ImageViewerWidget(QWidget):
    """Enhanced Image Viewer widget with minimalistic floating controls."""
    
    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)
        self.file_path = file_path
        self.zoom = 1.0
        self.rotation = 0
        self.is_fullscreen = False
        self.fit_mode = 'best'
        self.dragging = False
        self.drag_start_pos = None
        self.last_pan_pos = None
        
        # Auto-hide timer for controls
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.hide_controls)
        self.hide_timer.setSingleShot(True)
        
        self.init_ui()
        
        if file_path:
            self.load_image(file_path)
    
    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create main container
        self.container = QWidget()
        self.container.setStyleSheet("background-color: black;")
        
        # Scroll area for image
        self.scroll_area = QScrollArea(self.container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: black;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 50);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 150);
                border-radius: 4px;
            }
            QScrollBar:horizontal {
                background: rgba(255, 255, 255, 50);
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255, 255, 255, 150);
                border-radius: 4px;
            }
        """)
        
        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setStyleSheet("background-color: black;")
        
        self.scroll_area.setWidget(self.image_label)
        
        # Create floating controls
        self.create_floating_controls()
        
        # Set main layout
        self.main_layout.addWidget(self.container)
        
        # Initialize image variables
        self.original_pixmap = None
        self.current_pixmap = None
        
        # Enable mouse tracking for auto-hide
        self.setMouseTracking(True)
        self.container.setMouseTracking(True)
        self.scroll_area.setMouseTracking(True)
        self.image_label.setMouseTracking(True)
        
        # Install event filters
        self.scroll_area.installEventFilter(self)
        self.image_label.installEventFilter(self)
    
    def create_floating_controls(self):
        """Create floating control buttons positioned like Windows Photo Viewer."""
        
        # Zoom controls (bottom right)
        self.zoom_in_btn = FloatingButton("+", self.container)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        
        self.zoom_out_btn = FloatingButton("−", self.container)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        
        self.zoom_reset_btn = FloatingButton("1:1", self.container)
        self.zoom_reset_btn.clicked.connect(self.zoom_reset)
        self.zoom_reset_btn.setToolTip("Actual Size (Ctrl+0)")
        self.zoom_reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 120);
                border: none;
                border-radius: 20px;
                color: white;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 180);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 200);
            }
        """)
        
        # Zoom slider and label
        self.zoom_slider = FloatingZoomSlider(self.container)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.zoom_slider_changed)
        
        self.zoom_label = FloatingZoomLabel(self.container)
        self.zoom_label.setText("100%")
        
        # Fit controls (bottom left)
        self.fit_width_btn = FloatingButton("⟷", self.container)
        self.fit_width_btn.clicked.connect(self.fit_width)
        self.fit_width_btn.setToolTip("Fit Width")
        
        self.fit_height_btn = FloatingButton("⟵", self.container)
        self.fit_height_btn.clicked.connect(self.fit_height)
        self.fit_height_btn.setToolTip("Fit Height")
        self.fit_height_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 120);
                border: none;
                border-radius: 20px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                transform: rotate(90deg);
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 180);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 200);
            }
        """)
        
        self.fit_best_btn = FloatingButton("⌸", self.container)
        self.fit_best_btn.clicked.connect(self.fit_best)
        self.fit_best_btn.setToolTip("Fit to Window")
        
        # Rotation controls (top right)
        self.rotate_left_btn = FloatingButton("↶", self.container)
        self.rotate_left_btn.clicked.connect(self.rotate_left)
        self.rotate_left_btn.setToolTip("Rotate Left (Ctrl+L)")
        
        self.rotate_right_btn = FloatingButton("↷", self.container)
        self.rotate_right_btn.clicked.connect(self.rotate_right)
        self.rotate_right_btn.setToolTip("Rotate Right (Ctrl+R)")
        
        # Fullscreen toggle (top left)
        self.fullscreen_btn = FloatingButton("⛶", self.container)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_btn.setToolTip("Toggle Fullscreen (F11)")
        
        # Navigation buttons (center sides)
        self.prev_btn = FloatingButton("❮", self.container)
        self.prev_btn.clicked.connect(self.previous_image)
        self.prev_btn.setToolTip("Previous Image (Left Arrow)")
        
        self.next_btn = FloatingButton("❯", self.container)
        self.next_btn.clicked.connect(self.next_image)
        self.next_btn.setToolTip("Next Image (Right Arrow)")
        
        # Store all floating controls for easy access
        self.floating_controls = [
            self.zoom_in_btn, self.zoom_out_btn, self.zoom_reset_btn,
            self.zoom_slider, self.zoom_label,
            self.fit_width_btn, self.fit_height_btn, self.fit_best_btn,
            self.rotate_left_btn, self.rotate_right_btn,
            self.fullscreen_btn, self.prev_btn, self.next_btn
        ]
        
        # Initially hide controls
        self.show_controls()
    
    def resizeEvent(self, event):
        """Handle resize events and reposition floating controls."""
        super().resizeEvent(event)
        self.scroll_area.setGeometry(0, 0, self.container.width(), self.container.height())
        self.position_floating_controls()
        
        # Reapply fit mode when resized
        if hasattr(self, 'fit_mode') and self.fit_mode == 'best':
            self.fit_best()
    
    def position_floating_controls(self):
        """Position floating controls like Windows Photo Viewer."""
        if not self.container:
            return
            
        w = self.container.width()
        h = self.container.height()
        
        # Bottom right - zoom controls
        self.zoom_in_btn.move(w - 50, h - 120)
        self.zoom_out_btn.move(w - 50, h - 70)
        self.zoom_reset_btn.move(w - 50, h - 170)
        
        # Bottom center - zoom slider and label
        self.zoom_slider.move(w//2 - 60, h - 50)
        self.zoom_label.move(w//2 - 20, h - 80)
        
        # Bottom left - fit controls
        self.fit_width_btn.move(20, h - 120)
        self.fit_height_btn.move(20, h - 70)
        self.fit_best_btn.move(20, h - 170)
        
        # Top right - rotation controls
        self.rotate_left_btn.move(w - 100, 20)
        self.rotate_right_btn.move(w - 50, 20)
        
        # Top left - fullscreen
        self.fullscreen_btn.move(20, 20)
        
        # Center sides - navigation
        self.prev_btn.move(20, h//2 - 20)
        self.next_btn.move(w - 50, h//2 - 20)
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for auto-hide controls."""
        super().mouseMoveEvent(event)
        self.show_controls()
        self.reset_hide_timer()
    
    def eventFilter(self, obj, event):
        """Event filter for mouse tracking and panning."""
        if obj in [self.scroll_area, self.image_label]:
            if event.type() == event.MouseMove:
                self.show_controls()
                self.reset_hide_timer()
                
                # Handle panning
                if self.dragging and self.drag_start_pos:
                    delta = event.pos() - self.drag_start_pos
                    h_bar = self.scroll_area.horizontalScrollBar()
                    v_bar = self.scroll_area.verticalScrollBar()
                    
                    h_bar.setValue(h_bar.value() - delta.x())
                    v_bar.setValue(v_bar.value() - delta.y())
                    
                    self.drag_start_pos = event.pos()
                    
            elif event.type() == event.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.dragging = True
                    self.drag_start_pos = event.pos()
                    self.scroll_area.setCursor(Qt.ClosedHandCursor)
                    
            elif event.type() == event.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self.dragging = False
                    self.drag_start_pos = None
                    self.scroll_area.setCursor(Qt.ArrowCursor)
                    
            elif event.type() == event.Wheel:
                # Handle zoom with mouse wheel
                if event.modifiers() & Qt.ControlModifier:
                    if event.angleDelta().y() > 0:
                        self.zoom_in()
                    else:
                        self.zoom_out()
                    return True
        
        return super().eventFilter(obj, event)
    
    def show_controls(self):
        """Show floating controls."""
        for control in self.floating_controls:
            control.show()
    
    def hide_controls(self):
        """Hide floating controls."""
        for control in self.floating_controls:
            control.hide()
    
    def reset_hide_timer(self):
        """Reset the auto-hide timer."""
        self.hide_timer.stop()
        self.hide_timer.start(3000)  # Hide after 3 seconds of inactivity
    
    def load_image(self, file_path):
        """Load an image file."""
        try:
            self.file_path = file_path
            
            # Load image
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                QMessageBox.critical(self, "Error", f"Failed to load image: {file_path}")
                return False
            
            # Store original pixmap
            self.original_pixmap = pixmap
            self.current_pixmap = pixmap
            
            # Reset transformations
            self.zoom = 1.0
            self.rotation = 0
            
            # Update display
            self.update_display()
            
            # Reset zoom slider and label
            self.zoom_slider.setValue(100)
            self.zoom_label.setText("100%")
            
            # Fit best by default
            self.fit_mode = 'best'
            self.fit_best()
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open image: {str(e)}")
            return False
    
    def update_display(self):
        """Update the image display with current transformations."""
        if not self.original_pixmap:
            return
        
        # Apply rotation
        if self.rotation != 0:
            from PyQt5.QtGui import QTransform
            transform = QTransform()
            transform.rotate(self.rotation)
            rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
        else:
            rotated_pixmap = self.original_pixmap
        
        # Apply zoom
        if self.zoom != 1.0:
            new_width = int(rotated_pixmap.width() * self.zoom)
            new_height = int(rotated_pixmap.height() * self.zoom)
            
            self.current_pixmap = rotated_pixmap.scaled(
                new_width, new_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        else:
            self.current_pixmap = rotated_pixmap
        
        # Update image label
        self.image_label.setPixmap(self.current_pixmap)
        self.image_label.resize(self.current_pixmap.size())
        
        # Update zoom display
        zoom_percent = int(self.zoom * 100)
        self.zoom_slider.setValue(zoom_percent)
        self.zoom_label.setText(f"{zoom_percent}%")
    
    def zoom_in(self):
        """Increase zoom level."""
        self.zoom = min(self.zoom * 1.2, 5.0)
        self.fit_mode = None
        self.update_display()
    
    def zoom_out(self):
        """Decrease zoom level."""
        self.zoom = max(self.zoom / 1.2, 0.1)
        self.fit_mode = None
        self.update_display()
    
    def zoom_reset(self):
        """Reset zoom to 100%."""
        self.zoom = 1.0
        self.fit_mode = None
        self.update_display()
    
    def zoom_slider_changed(self, value):
        """Handle zoom slider changes."""
        self.zoom = value / 100.0
        self.fit_mode = None
        self.update_display()
    
    def fit_width(self):
        """Fit image to width of scroll area."""
        if not self.original_pixmap:
            return
        
        scroll_width = self.scroll_area.width() - 20
        
        # Get the current pixmap dimensions (accounting for rotation)
        if self.rotation != 0:
            transform = QTransform()
            transform.rotate(self.rotation)
            rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
            image_width = rotated_pixmap.width()
        else:
            image_width = self.original_pixmap.width()
        
        if image_width > 0:
            self.zoom = scroll_width / image_width
            self.fit_mode = 'width'
            self.update_display()
    
    def fit_height(self):
        """Fit image to height of scroll area."""
        if not self.original_pixmap:
            return
        
        scroll_height = self.scroll_area.height() - 20
        
        # Get the current pixmap dimensions (accounting for rotation)
        if self.rotation != 0:
            transform = QTransform()
            transform.rotate(self.rotation)
            rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
            image_height = rotated_pixmap.height()
        else:
            image_height = self.original_pixmap.height()
        
        if image_height > 0:
            self.zoom = scroll_height / image_height
            self.fit_mode = 'height'
            self.update_display()
    
    def fit_best(self):
        """Fit image to best view in scroll area."""
        if not self.original_pixmap:
            return
        
        scroll_width = self.scroll_area.width() - 20
        scroll_height = self.scroll_area.height() - 20
        
        # Get the current pixmap dimensions (accounting for rotation)
        if self.rotation != 0:
            transform = QTransform()
            transform.rotate(self.rotation)
            rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
            image_width = rotated_pixmap.width()
            image_height = rotated_pixmap.height()
        else:
            image_width = self.original_pixmap.width()
            image_height = self.original_pixmap.height()
        
        if image_width > 0 and image_height > 0:
            width_ratio = scroll_width / image_width
            height_ratio = scroll_height / image_height
            
            self.zoom = min(width_ratio, height_ratio)
            self.fit_mode = 'best'
            self.update_display()
    
    def rotate_left(self):
        """Rotate image 90 degrees counter-clockwise."""
        self.rotation = (self.rotation - 90) % 360
        self.update_display()
        
        # Reapply fit mode after rotation
        if self.fit_mode == 'best':
            self.fit_best()
        elif self.fit_mode == 'width':
            self.fit_width()
        elif self.fit_mode == 'height':
            self.fit_height()
    
    def rotate_right(self):
        """Rotate image 90 degrees clockwise."""
        self.rotation = (self.rotation + 90) % 360
        self.update_display()
        
        # Reapply fit mode after rotation
        if self.fit_mode == 'best':
            self.fit_best()
        elif self.fit_mode == 'width':
            self.fit_width()
        elif self.fit_mode == 'height':
            self.fit_height()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
        else:
            self.showFullScreen()
            self.is_fullscreen = True
    
    def previous_image(self):
        """Navigate to previous image in directory."""
        if not self.file_path:
            return
        
        directory = os.path.dirname(self.file_path)
        current_file = os.path.basename(self.file_path)
        
        # Get all image files in directory
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
        image_files = [f for f in os.listdir(directory) 
                      if f.lower().endswith(image_extensions)]
        image_files.sort()
        
        if current_file in image_files:
            current_index = image_files.index(current_file)
            prev_index = (current_index - 1) % len(image_files)
            prev_file = os.path.join(directory, image_files[prev_index])
            self.load_image(prev_file)
    
    def next_image(self):
        """Navigate to next image in directory."""
        if not self.file_path:
            return
        
        directory = os.path.dirname(self.file_path)
        current_file = os.path.basename(self.file_path)
        
        # Get all image files in directory
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
        image_files = [f for f in os.listdir(directory) 
                      if f.lower().endswith(image_extensions)]
        image_files.sort()
        
        if current_file in image_files:
            current_index = image_files.index(current_file)
            next_index = (current_index + 1) % len(image_files)
            next_file = os.path.join(directory, image_files[next_index])
            self.load_image(next_file)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_Left:
            self.previous_image()
        elif event.key() == Qt.Key_Right:
            self.next_image()
        elif event.key() == Qt.Key_Plus and event.modifiers() & Qt.ControlModifier:
            self.zoom_in()
        elif event.key() == Qt.Key_Minus and event.modifiers() & Qt.ControlModifier:
            self.zoom_out()
        elif event.key() == Qt.Key_0 and event.modifiers() & Qt.ControlModifier:
            self.zoom_reset()
        elif event.key() == Qt.Key_L and event.modifiers() & Qt.ControlModifier:
            self.rotate_left()
        elif event.key() == Qt.Key_R and event.modifiers() & Qt.ControlModifier:
            self.rotate_right()
        elif event.key() == Qt.Key_Escape:
            if self.is_fullscreen:
                self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)
