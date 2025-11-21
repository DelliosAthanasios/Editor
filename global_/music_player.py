import os
import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QStyle, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QFrame, QShortcut
)
from PyQt5.QtGui import QIcon, QFont, QKeySequence
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from .theme_manager import theme_manager_singleton

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
        self.setObjectName("MusicPlayerWidget")
        self.setAcceptDrops(True)
        self.shortcuts = []
        self.init_ui()
        self.init_player()
        self.apply_theme(theme_manager_singleton.get_theme())
        theme_manager_singleton.themeChanged.connect(self.apply_theme)
        self.setup_shortcuts()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header / now playing card
        self.header_card = QFrame()
        self.header_card.setObjectName("PlayerCard")
        header_layout = QVBoxLayout(self.header_card)
        header_layout.setContentsMargins(16, 16, 16, 16)

        self.now_playing_label = QLabel("No file loaded")
        self.now_playing_label.setObjectName("NowPlayingLabel")
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        self.now_playing_label.setWordWrap(True)
        font = QFont()
        font.setBold(True)
        self.now_playing_label.setFont(font)
        header_layout.addWidget(self.now_playing_label)

        self.hint_label = QLabel("Tip: Drag & drop audio files or folders to build your playlist.")
        self.hint_label.setWordWrap(True)
        self.hint_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.hint_label)

        main_layout.addWidget(self.header_card)

        # Controls card
        self.controls_card = QFrame()
        self.controls_card.setObjectName("PlayerCard")
        controls_card_layout = QVBoxLayout(self.controls_card)
        controls_card_layout.setContentsMargins(16, 16, 16, 16)
        controls_card_layout.setSpacing(10)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.prev_button.clicked.connect(self.play_previous)
        controls_layout.addWidget(self.prev_button)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)

        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_playback)
        controls_layout.addWidget(self.stop_button)

        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_button.clicked.connect(self.play_next)
        controls_layout.addWidget(self.next_button)

        controls_layout.addStretch()
        controls_card_layout.addLayout(controls_layout)

        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        time_layout.addWidget(self.current_time_label)

        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 0)
        self.time_slider.sliderMoved.connect(self.seek)
        time_layout.addWidget(self.time_slider)

        self.total_time_label = QLabel("0:00")
        time_layout.addWidget(self.total_time_label)
        controls_card_layout.addLayout(time_layout)

        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        volume_layout.addWidget(volume_label)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)

        controls_card_layout.addLayout(volume_layout)

        speed_layout = QHBoxLayout()
        self.speed_label = QLabel("Speed 1.0x")
        speed_layout.addWidget(self.speed_label)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 150)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self.update_playback_speed)
        speed_layout.addWidget(self.speed_slider)
        controls_card_layout.addLayout(speed_layout)

        extra_controls = QHBoxLayout()
        extra_controls.setSpacing(8)

        self.open_button = QPushButton("Open File")
        self.open_button.clicked.connect(self.open_file)
        extra_controls.addWidget(self.open_button)

        self.add_folder_button = QPushButton("Add Folder")
        self.add_folder_button.clicked.connect(self.add_folder_to_playlist)
        extra_controls.addWidget(self.add_folder_button)

        self.playlist_button = QPushButton("Playlist")
        self.playlist_button.clicked.connect(self.manage_playlist)
        extra_controls.addWidget(self.playlist_button)

        self.loop_button = QPushButton("Loop")
        self.loop_button.setCheckable(True)
        self.loop_button.clicked.connect(self.toggle_loop)
        extra_controls.addWidget(self.loop_button)

        self.shuffle_button = QPushButton("Shuffle")
        self.shuffle_button.setCheckable(True)
        self.shuffle_button.clicked.connect(self.toggle_shuffle)
        extra_controls.addWidget(self.shuffle_button)

        self.info_button = QPushButton("Info")
        self.info_button.clicked.connect(self.show_info)
        extra_controls.addWidget(self.info_button)

        extra_controls.addStretch()
        controls_card_layout.addLayout(extra_controls)

        main_layout.addWidget(self.controls_card)

        # Playlist card
        self.playlist_card = QFrame()
        self.playlist_card.setObjectName("PlayerCard")
        playlist_layout = QVBoxLayout(self.playlist_card)
        playlist_layout.setContentsMargins(16, 16, 16, 16)
        playlist_layout.setSpacing(10)

        playlist_header = QHBoxLayout()
        self.playlist_label = QLabel("Playlist (0 items)")
        playlist_header.addWidget(self.playlist_label)
        playlist_header.addStretch()
        self.playlist_filter = QLineEdit()
        self.playlist_filter.setObjectName("PlaylistFilter")
        self.playlist_filter.setPlaceholderText("Filter playlist...")
        self.playlist_filter.textChanged.connect(self.filter_playlist)
        playlist_header.addWidget(self.playlist_filter)
        playlist_layout.addLayout(playlist_header)

        self.playlist_widget = QListWidget()
        self.playlist_widget.setObjectName("PlaylistView")
        self.playlist_widget.setAlternatingRowColors(True)
        self.playlist_widget.setMinimumHeight(140)
        self.playlist_widget.itemDoubleClicked.connect(self.playlist_item_clicked)
        playlist_layout.addWidget(self.playlist_widget)

        main_layout.addWidget(self.playlist_card)
    
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
        self.update_playback_mode()
        self.update_playback_speed(self.speed_slider.value())
    
    def open_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", "", 
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;All Files (*)"
        )
        
        if file:
            self.current_file = file
            self.add_media_files([file], replace=True, autoplay=True)
    
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
            self.shuffle_button.setChecked(False)
        self.update_playback_mode()
    
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
        self.filter_playlist(self.playlist_filter.text())
    
    def add_files_to_playlist(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "", 
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac);;All Files (*)"
        )
        
        if files:
            autoplay = self.playlist.mediaCount() == 0
            self.add_media_files(files, replace=False, autoplay=autoplay)

    def add_media_files(self, files, replace=False, autoplay=False):
        audio_files = [f for f in files if self.is_audio_file(f)]
        if not audio_files:
            return

        was_empty = self.playlist.mediaCount() == 0
        if replace:
            self.playlist.clear()
            was_empty = True

        for file in audio_files:
            url = QUrl.fromLocalFile(file)
            self.playlist.addMedia(QMediaContent(url))

        if was_empty:
            self.playlist.setCurrentIndex(0)

        self.update_playlist_display()
        if autoplay or was_empty or replace:
            self.player.play()

    def is_audio_file(self, path):
        audio_extensions = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac")
        return os.path.isfile(path) and path.lower().endswith(audio_extensions)

    def add_folder_to_playlist(self):
        folder = QFileDialog.getExistingDirectory(self, "Add Audio Folder", "")
        if folder:
            files = self.collect_audio_files(folder)
            if not files:
                QMessageBox.information(self, "Folder Empty", "No audio files found in the selected folder.")
                return
            autoplay = self.playlist.mediaCount() == 0
            self.add_media_files(files, replace=False, autoplay=autoplay)

    def collect_audio_files(self, folder):
        collected = []
        for root, _, filenames in os.walk(folder):
            for name in filenames:
                path = os.path.join(root, name)
                if self.is_audio_file(path):
                    collected.append(path)
        return collected

    def toggle_shuffle(self):
        if self.shuffle_button.isChecked():
            self.loop_button.setChecked(False)
        self.update_playback_mode()

    def update_playback_mode(self):
        if self.shuffle_button.isChecked():
            mode = QMediaPlaylist.Random
        elif self.loop_button.isChecked():
            mode = QMediaPlaylist.Loop
        else:
            mode = QMediaPlaylist.Sequential
        self.playlist.setPlaybackMode(mode)

    def update_playback_speed(self, value):
        rate = max(0.5, min(1.5, value / 100))
        self.player.setPlaybackRate(rate)
        self.speed_label.setText(f"Speed {rate:.1f}x")

    def filter_playlist(self, text):
        text = text.lower().strip()
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            item.setHidden(bool(text) and text not in item.text().lower())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path) or self.is_audio_file(path):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        paths = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    paths.extend(self.collect_audio_files(path))
                elif self.is_audio_file(path):
                    paths.append(path)
        if paths:
            autoplay = self.playlist.mediaCount() == 0
            self.add_media_files(paths, replace=False, autoplay=autoplay)
            event.acceptProposedAction()
        else:
            event.ignore()

    def setup_shortcuts(self):
        for seq, handler in [
            ("Space", self.toggle_playback),
            ("Ctrl+O", self.open_file),
            ("Ctrl+L", self.manage_playlist),
            ("Ctrl+Left", self.play_previous),
            ("Ctrl+Right", self.play_next)
        ]:
            shortcut = QShortcut(QKeySequence(seq), self)
            shortcut.activated.connect(handler)
            self.shortcuts.append(shortcut)

    def apply_theme(self, theme_data):
        palette = theme_data["palette"]
        editor = theme_data["editor"]
        accent = palette.get("highlight", editor["selection_background"])
        accent_text = palette.get("highlight_text", editor["selection_foreground"])
        border = palette.get("alternate_base", "#3a3a3a")
        button_bg = palette.get("button", accent)
        button_text = palette.get("button_text", palette["window_text"])

        self.setStyleSheet(f"""
            QWidget#MusicPlayerWidget {{
                background: {palette['window']};
                color: {palette['window_text']};
            }}
            QFrame#PlayerCard {{
                background: {palette['base']};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel#NowPlayingLabel {{
                font-size: 16px;
            }}
            QPushButton {{
                background: {button_bg};
                color: {button_text};
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:checked {{
                background: {accent};
                color: {accent_text};
            }}
            QPushButton:hover {{
                background: {accent};
                color: {accent_text};
            }}
            QListWidget#PlaylistView {{
                border: none;
                background: {editor['background']};
                color: {editor['foreground']};
                alternate-background-color: {palette['alternate_base']};
            }}
            QLineEdit#PlaylistFilter {{
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 8px;
                background: {editor['background']};
                color: {editor['foreground']};
            }}
        """)
