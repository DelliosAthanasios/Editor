import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QSlider, QToolBar, QAction, QFileDialog,
    QSplitter, QMessageBox, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QIcon
from PyQt5.QtCore import Qt, QSize, pyqtSignal

class ImageViewerWidget(QWidget):
    """Image Viewer widget for integration with the main editor."""
    
    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)
        self.file_path = file_path
        self.zoom = 1.0
        self.init_ui()
        
        if file_path:
            self.load_image(file_path)
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Toolbar for controls
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
        
        # Zoom actions
        self.zoom_in_action = QAction("Zoom In", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.toolbar.addAction(self.zoom_in_action)
        
        self.zoom_out_action = QAction("Zoom Out", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.toolbar.addAction(self.zoom_out_action)
        
        self.zoom_reset_action = QAction("Reset Zoom", self)
        self.zoom_reset_action.triggered.connect(self.zoom_reset)
        self.toolbar.addAction(self.zoom_reset_action)
        
        self.zoom_label = QLabel("Zoom: 100%")
        self.toolbar.addWidget(self.zoom_label)
        
        self.toolbar.addSeparator()
        
        # Fit actions
        self.fit_width_action = QAction("Fit Width", self)
        self.fit_width_action.triggered.connect(self.fit_width)
        self.toolbar.addAction(self.fit_width_action)
        
        self.fit_height_action = QAction("Fit Height", self)
        self.fit_height_action.triggered.connect(self.fit_height)
        self.toolbar.addAction(self.fit_height_action)
        
        self.fit_best_action = QAction("Fit Best", self)
        self.fit_best_action.triggered.connect(self.fit_best)
        self.toolbar.addAction(self.fit_best_action)
        
        layout.addWidget(self.toolbar)
        
        # Scroll area for image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setScaledContents(True)
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        # Set layout
        self.setLayout(layout)
        
        # Initialize image
        self.original_pixmap = None
        self.current_pixmap = None
    
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
            
            # Display image
            self.image_label.setPixmap(pixmap)
            self.image_label.adjustSize()
            
            # Reset zoom
            self.zoom = 1.0
            self.zoom_label.setText("Zoom: 100%")
            
            # Fit best by default
            self.fit_best()
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open image: {str(e)}")
            return False
    
    def zoom_in(self):
        """Increase zoom level."""
        self.zoom *= 1.2
        self.update_zoom()
    
    def zoom_out(self):
        """Decrease zoom level."""
        self.zoom /= 1.2
        self.update_zoom()
    
    def zoom_reset(self):
        """Reset zoom to 100%."""
        self.zoom = 1.0
        self.update_zoom()
    
    def update_zoom(self):
        """Update the image display with current zoom level."""
        if not self.original_pixmap:
            return
            
        # Update zoom label
        self.zoom_label.setText(f"Zoom: {int(self.zoom * 100)}%")
        
        # Calculate new size
        new_width = int(self.original_pixmap.width() * self.zoom)
        new_height = int(self.original_pixmap.height() * self.zoom)
        
        # Scale pixmap
        self.current_pixmap = self.original_pixmap.scaled(
            new_width, new_height, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        # Update image
        self.image_label.setPixmap(self.current_pixmap)
        self.image_label.resize(new_width, new_height)
    
    def fit_width(self):
        """Fit image to width of scroll area."""
        if not self.original_pixmap:
            return
            
        # Calculate zoom to fit width
        scroll_width = self.scroll_area.width() - 20  # Account for scrollbar
        image_width = self.original_pixmap.width()
        
        if image_width > 0:
            self.zoom = scroll_width / image_width
            self.update_zoom()
    
    def fit_height(self):
        """Fit image to height of scroll area."""
        if not self.original_pixmap:
            return
            
        # Calculate zoom to fit height
        scroll_height = self.scroll_area.height() - 20  # Account for scrollbar
        image_height = self.original_pixmap.height()
        
        if image_height > 0:
            self.zoom = scroll_height / image_height
            self.update_zoom()
    
    def fit_best(self):
        """Fit image to best view in scroll area."""
        if not self.original_pixmap:
            return
            
        # Calculate zoom to fit both width and height
        scroll_width = self.scroll_area.width() - 20
        scroll_height = self.scroll_area.height() - 20
        image_width = self.original_pixmap.width()
        image_height = self.original_pixmap.height()
        
        if image_width > 0 and image_height > 0:
            width_ratio = scroll_width / image_width
            height_ratio = scroll_height / image_height
            
            # Use the smaller ratio to ensure image fits completely
            self.zoom = min(width_ratio, height_ratio)
            self.update_zoom()
    
    def resizeEvent(self, event):
        """Handle resize events to maintain fit if needed."""
        super().resizeEvent(event)
        
        # Reapply fit best when resized
        if hasattr(self, 'fit_mode') and self.fit_mode == 'best':
            self.fit_best()
