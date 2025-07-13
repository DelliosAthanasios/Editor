import os
import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QStyle, QSizePolicy, QToolBar, QAction, QMenu, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QComboBox
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSignal, QSize
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist

class PlaylistDialog(QDialog):
    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Playlist Manager")
        self.setMinimumWidth(400)
        self.playlist = playlist
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Playlist items
        self.list_widget = QListWidget()
        self.update_list()
        layout.addWidget(self.list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Files")
        self.add_button.clicked.connect(self.add_files)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(self.remove_button)
        
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_playlist)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
        
        # Save/Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def update_list(self):
        self.list_widget.clear()
        for i in range(self.playlist.mediaCount()):
            url = self.playlist.media(i).canonicalUrl()
            filename = os.path.basename(url.path())
            self.list_widget.addItem(filename)
    
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "", 
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;All Files (*)"
        )
        
        if files:
            for file in files:
                url = QUrl.fromLocalFile(file)
                self.playlist.addMedia(QMediaContent(url))
            self.update_list()
    
    def remove_selected(self):
        selected = self.list_widget.currentRow()
        if selected >= 0:
            self.playlist.removeMedia(selected)
            self.update_list()
    
    def clear_playlist(self):
        self.playlist.clear()
        self.update_list()

class AudioInfoDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio Information")
        self.file_path = file_path
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout(self)
        
        # Basic file info
        filename = os.path.basename(self.file_path)
        filesize = os.path.getsize(self.file_path) / 1024  # KB
        file_type = os.path.splitext(self.file_path)[1].lower()
        
        layout.addRow("Filename:", QLabel(filename))
        layout.addRow("Path:", QLabel(self.file_path))
        layout.addRow("Size:", QLabel(f"{filesize:.1f} KB"))
        layout.addRow("Type:", QLabel(file_type))
        
        # Try to get audio metadata if available
        try:
            # This is a placeholder - in a real implementation, you would use a library
            # like mutagen to extract audio metadata
            layout.addRow("Note:", QLabel("Detailed audio metadata not available in this version."))
        except:
            pass
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addRow(buttons)

class MusicPlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.init_ui()
        self.init_player()
        
    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Now playing label
        self.now_playing_label = QLabel("No file loaded")
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        self.now_playing_label.setWordWrap(True)
        font = QFont()
        font.setBold(True)
        self.now_playing_label.setFont(font)
        main_layout.addWidget(self.now_playing_label)
        
        # Playback controls
        controls_layout = QHBoxLayout()
        
        # Previous button
        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.prev_button.clicked.connect(self.play_previous)
        controls_layout.addWidget(self.prev_button)
        
        # Play/Pause button
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)
        
        # Stop button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_playback)
        controls_layout.addWidget(self.stop_button)
        
        # Next button
        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_button.clicked.connect(self.play_next)
        controls_layout.addWidget(self.next_button)
        
        main_layout.addLayout(controls_layout)
        
        # Time slider and labels
        time_layout = QHBoxLayout()
        
        self.current_time_label = QLabel("0:00")
        time_layout.addWidget(self.current_time_label)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 0)
        self.time_slider.sliderMoved.connect(self.seek)
        time_layout.addWidget(self.time_slider)
        
        self.total_time_label = QLabel("0:00")
        time_layout.addWidget(self.total_time_label)
        
        main_layout.addLayout(time_layout)
        
        # Volume control
        volume_layout = QHBoxLayout()
        
        volume_label = QLabel("Volume:")
        volume_layout.addWidget(volume_label)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)
        
        main_layout.addLayout(volume_layout)
        
        # Additional controls
        extra_controls = QHBoxLayout()
        
        # Open file button
        self.open_button = QPushButton("Open File")
        self.open_button.clicked.connect(self.open_file)
        extra_controls.addWidget(self.open_button)
        
        # Playlist button
        self.playlist_button = QPushButton("Playlist")
        self.playlist_button.clicked.connect(self.manage_playlist)
        extra_controls.addWidget(self.playlist_button)
        
        # Loop button
        self.loop_button = QPushButton("Loop")
        self.loop_button.setCheckable(True)
        self.loop_button.clicked.connect(self.toggle_loop)
        extra_controls.addWidget(self.loop_button)
        
        # Info button
        self.info_button = QPushButton("Info")
        self.info_button.clicked.connect(self.show_info)
        extra_controls.addWidget(self.info_button)
        
        main_layout.addLayout(extra_controls)
        
        # Playlist display
        self.playlist_label = QLabel("Playlist (0 items)")
        main_layout.addWidget(self.playlist_label)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.setMaximumHeight(100)
        self.playlist_widget.itemDoubleClicked.connect(self.playlist_item_clicked)
        main_layout.addWidget(self.playlist_widget)
    
    def init_player(self):
        # Media player
        self.player = QMediaPlayer()
        self.player.stateChanged.connect(self.player_state_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.mediaStatusChanged.connect(self.media_status_changed)
        
        # Playlist
        self.playlist = QMediaPlaylist()
        self.playlist.currentIndexChanged.connect(self.playlist_position_changed)
        self.player.setPlaylist(self.playlist)
        
        # Set initial volume
        self.set_volume(self.volume_slider.value())
    
    def open_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", "", 
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;All Files (*)"
        )
        
        if file:
            self.current_file = file
            self.playlist.clear()
            self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(file)))
            self.update_playlist_display()
            self.playlist.setCurrentIndex(0)
            self.player.play()
    
    def toggle_playback(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    
    def stop_playback(self):
        self.player.stop()
    
    def play_previous(self):
        self.playlist.previous()
    
    def play_next(self):
        self.playlist.next()
    
    def seek(self, position):
        self.player.setPosition(position)
    
    def set_volume(self, volume):
        self.player.setVolume(volume)
    
    def toggle_loop(self):
        if self.loop_button.isChecked():
            self.playlist.setPlaybackMode(QMediaPlaylist.Loop)
        else:
            self.playlist.setPlaybackMode(QMediaPlaylist.Sequential)
    
    def manage_playlist(self):
        dialog = PlaylistDialog(self.playlist, self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_playlist_display()
    
    def show_info(self):
        if self.current_file:
            dialog = AudioInfoDialog(self.current_file, self)
            dialog.exec_()
    
    def player_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
    
    def position_changed(self, position):
        if not self.time_slider.isSliderDown():
            self.time_slider.setValue(position)
        
        # Update time display
        seconds = position // 1000
        minutes = seconds // 60
        seconds %= 60
        self.current_time_label.setText(f"{minutes}:{seconds:02d}")
    
    def duration_changed(self, duration):
        self.time_slider.setRange(0, duration)
        
        # Update total time display
        seconds = duration // 1000
        minutes = seconds // 60
        seconds %= 60
        self.total_time_label.setText(f"{minutes}:{seconds:02d}")
    
    def media_status_changed(self, status):
        if status == QMediaPlayer.LoadedMedia:
            # Update now playing label
            if self.current_file:
                self.now_playing_label.setText(os.path.basename(self.current_file))
    
    def playlist_position_changed(self, position):
        if position >= 0:
            self.playlist_widget.setCurrentRow(position)
            url = self.playlist.currentMedia().canonicalUrl()
            self.current_file = url.toLocalFile()
    
    def playlist_item_clicked(self, item):
        row = self.playlist_widget.row(item)
        self.playlist.setCurrentIndex(row)
        self.player.play()
    
    def update_playlist_display(self):
        self.playlist_widget.clear()
        count = self.playlist.mediaCount()
        
        for i in range(count):
            url = self.playlist.media(i).canonicalUrl()
            filename = os.path.basename(url.path())
            self.playlist_widget.addItem(filename)
        
        self.playlist_label.setText(f"Playlist ({count} items)")
    
    def add_files_to_playlist(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "", 
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;All Files (*)"
        )
        
        if files:
            for file in files:
                url = QUrl.fromLocalFile(file)
                self.playlist.addMedia(QMediaContent(url))
            
            # If this is the first file, start playing
            if self.playlist.mediaCount() == len(files):
                self.playlist.setCurrentIndex(0)
                self.player.play()
            
            self.update_playlist_display()
