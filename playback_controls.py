import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QIcon
from qfluentwidgets import (
    ToolButton, BodyLabel, Slider, setCustomStyleSheet
)
from font_manager import get_font_manager, MaterialIcon

# Configure logging
logger = logging.getLogger(__name__)

class PlaybackControls(QWidget):
    """
    Playback controls widget for the WAVFin Sample Manager.
    Includes play/pause button, progress bar, time display, and volume control.
    """
    
    # Signals
    file_loaded = pyqtSignal(str)  # Emitted when a new file is loaded
    playback_error = pyqtSignal(str)  # Emitted when playback error occurs
    
    def __init__(self, parent=None, audio_player=None):
        super().__init__(parent)
        
        self.audio_player = audio_player
        self.current_sample_path = None
        self.is_seeking = False  # Flag to prevent feedback during seeking
        self.previous_volume = 0.7  # Store previous volume for unmute
        self.is_muted = False  # Track mute state
        
        self.init_ui()
        if self.audio_player:
            self.setup_connections()
        self.setup_keyboard_shortcuts()
        
        # Update timer for smooth progress updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # Update every 100ms
        
        logger.info("PlaybackControls initialized")
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setFixedHeight(60)  # Reduced height for more compact design
        
        # Main layout - two rows for more compact design
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)  # Smaller margins all around
        main_layout.setSpacing(8)  # Increased spacing between rows
        
        # Top row: Play button, progress bar, and volume control all in one line
        top_row = QHBoxLayout()
        top_row.setSpacing(12)  # Good spacing between elements
        
        # Play button - positioned closer to left
        self.play_button = ToolButton(self)
        self.play_button.setIcon(MaterialIcon('PLAY', 24).icon())
        self.play_button.setFixedSize(32, 32)  # Slightly larger for better usability
        self.play_button.setToolTip("Play/Pause (Spacebar)")
        self.play_button.clicked.connect(self.toggle_playback)
        self.setup_play_button_style()
        top_row.addWidget(self.play_button)
        
        # Progress bar - takes up most of the space
        self.progress_slider = Slider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setToolTip("Seek Position")
        self.progress_slider.sliderPressed.connect(self.on_seek_start)
        self.progress_slider.sliderReleased.connect(self.on_seek_end)
        self.progress_slider.valueChanged.connect(self.on_seek_position)
        top_row.addWidget(self.progress_slider, 1)  # Give it stretch factor of 1
        
        # Volume control - compact on the right
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(6)  # Tighter spacing for volume controls
        
        # Volume icon
        self.volume_icon = ToolButton(self)
        self.volume_icon.setIcon(MaterialIcon('VOLUME', 18).icon())
        self.volume_icon.setFixedSize(22, 22)  # Slightly smaller
        self.volume_icon.setToolTip("Volume")
        self.volume_icon.clicked.connect(self.toggle_mute)
        volume_layout.addWidget(self.volume_icon)
        
        # Volume slider
        self.volume_slider = Slider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(65)  # Slightly smaller width
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setToolTip("Volume Control")
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        
        # Initialize volume icon based on default volume
        self.update_volume_icon(0.7)
        
        top_row.addLayout(volume_layout)
        main_layout.addLayout(top_row)
        
        # Bottom row: Time display and sample info - more compact
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)  # Good spacing between time and sample info
        info_layout.setContentsMargins(2, 0, 2, 0)  # Small horizontal margins
        
        # Time display - smaller font
        self.time_label = BodyLabel("00:00 / 00:00")
        self.time_label.setFont(get_font_manager().get_font(8))  # Smaller font
        self.time_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        info_layout.addWidget(self.time_label)
        
        # Sample info - smaller font and more subtle
        self.sample_info_label = BodyLabel("No sample loaded")
        self.sample_info_label.setFont(get_font_manager().get_light_font(7))  # Even smaller font
        self.sample_info_label.setStyleSheet("color: rgba(255, 255, 255, 0.5);")
        info_layout.addWidget(self.sample_info_label)
        
        # Add stretch to push everything to the left
        info_layout.addStretch()
        
        main_layout.addLayout(info_layout)
        
        # Initially disabled
        self.set_enabled(False)
    
    def setup_play_button_style(self):
        """Setup custom styling for the play button."""
        qss = """
            ToolButton {
                border-radius: 16px;
                border: 2px solid transparent;
                background-color: rgba(94, 129, 172, 0.9);
                color: white;
                outline: none;
            }
            ToolButton:hover {
                background-color: rgba(94, 129, 172, 1.0);
                border: 2px solid rgba(94, 129, 172, 0.4);
                outline: none;
            }
            ToolButton:pressed {
                background-color: rgba(94, 129, 172, 0.7);
                outline: none;
            }
            ToolButton:disabled {
                background-color: rgba(94, 129, 172, 0.3);
                color: rgba(255, 255, 255, 0.5);
                outline: none;
            }
            ToolButton:focus {
                outline: none;
            }
        """
        setCustomStyleSheet(self.play_button, qss, qss)
    
    def setup_connections(self):
        """Setup connections to the audio player."""
        self.audio_player.position_changed.connect(self.on_position_changed)
        self.audio_player.duration_changed.connect(self.on_duration_changed)
        self.audio_player.playback_state_changed.connect(self.on_playback_state_changed)
        self.audio_player.volume_changed.connect(self.on_audio_volume_changed)
        self.audio_player.error_occurred.connect(self.on_playback_error)
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for playback control."""
        # Spacebar for play/pause
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.activated.connect(self.toggle_playback)
        
        # Arrow keys for seeking (when focused)
        self.left_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.left_shortcut.activated.connect(lambda: self.seek_relative(-5000))  # -5 seconds
        
        self.right_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.right_shortcut.activated.connect(lambda: self.seek_relative(5000))  # +5 seconds
    
    def load_sample(self, file_path: str) -> bool:
        """
        Load a sample for playback.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            bool: True if loaded successfully
        """
        if not self.audio_player.load_file(file_path):
            self.current_sample_path = None
            self.sample_info_label.setText("Failed to load sample")
            self.set_enabled(False)
            return False
            
        self.current_sample_path = file_path
        self.sample_info_label.setText(f"Loaded: {Path(file_path).name}")
        self.set_enabled(True)
        self.file_loaded.emit(file_path)
        logger.info(f"Sample loaded in playback controls: {Path(file_path).name}")
        return True
    
    def toggle_playback(self):
        """Toggle play/pause."""
        if self.current_sample_path:
            self.audio_player.toggle_playback()
    
    def stop_playback(self):
        """Stop playback."""
        self.audio_player.stop()
    
    def seek_relative(self, offset_ms: int):
        """
        Seek relative to current position.
        
        Args:
            offset_ms: Offset in milliseconds (positive or negative)
        """
        if self.current_sample_path:
            current_pos = self.audio_player.get_position()
            new_pos = max(0, current_pos + offset_ms)
            self.audio_player.set_position(new_pos)
    
    def set_enabled(self, enabled: bool):
        """Enable or disable playback controls."""
        self.play_button.setEnabled(enabled)
        self.progress_slider.setEnabled(enabled)
        self.volume_slider.setEnabled(True)  # Volume always enabled
    
    def on_position_changed(self, position_ms: int):
        """Handle position changes from audio player."""
        if not self.is_seeking:
            duration = self.audio_player.get_duration()
            if duration > 0:
                progress = int((position_ms / duration) * 1000)
                self.progress_slider.setValue(progress)
    
    def on_duration_changed(self, duration_ms: int):
        """Handle duration changes from audio player."""
        # Duration is now available, update display
        self.update_display()
    
    def on_playback_state_changed(self, state):
        """Handle playback state changes."""
        from PyQt6.QtMultimedia import QMediaPlayer
        
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setIcon(MaterialIcon('PAUSE', 24).icon())
            self.play_button.setToolTip("Pause (Spacebar)")
        else:
            self.play_button.setIcon(MaterialIcon('PLAY', 24).icon())
            self.play_button.setToolTip("Play (Spacebar)")
    
    def on_volume_changed(self, value: int):
        """Handle volume slider changes."""
        volume = value / 100.0
        self.audio_player.set_volume(volume)
        
        # Reset mute state if volume is changed via slider
        if value > 0:
            self.is_muted = False
        
        # Update volume icon based on level
        self.update_volume_icon(volume)
    
    def on_audio_volume_changed(self, volume: float):
        """Handle volume changes from audio player."""
        # Update slider without triggering signal
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(int(volume * 100))
        self.volume_slider.blockSignals(False)
        
        # Update volume icon based on level
        self.update_volume_icon(volume)
    
    def on_seek_start(self):
        """Handle start of seeking."""
        self.is_seeking = True
    
    def on_seek_end(self):
        """Handle end of seeking."""
        self.is_seeking = False
        # Apply the seek position
        duration = self.audio_player.get_duration()
        if duration > 0:
            progress = self.progress_slider.value() / 1000.0
            new_position = int(progress * duration)
            self.audio_player.set_position(new_position)
    
    def on_seek_position(self, value: int):
        """Handle seeking position changes."""
        if self.is_seeking:
            # Update time display during seeking
            duration = self.audio_player.get_duration()
            if duration > 0:
                progress = value / 1000.0
                position = int(progress * duration)
                self.update_time_display(position, duration)
    
    def on_playback_error(self, error_message: str):
        """Handle playback errors."""
        logger.error(f"Playback error: {error_message}")
        self.sample_info_label.setText(f"Error: {error_message}")
        self.playback_error.emit(error_message)
    
    def toggle_mute(self):
        """Toggle mute/unmute."""
        current_volume = self.audio_player.get_volume()
        if not self.is_muted and current_volume > 0:
            # Mute
            self.previous_volume = current_volume
            self.is_muted = True
            volume_to_set = 0
            slider_value = 0
        else:
            # Unmute
            self.is_muted = False
            volume_to_set = getattr(self, 'previous_volume', 0.7)
            slider_value = int(volume_to_set * 100)
        
        self.audio_player.set_volume(volume_to_set)
        self.volume_slider.setValue(slider_value)
        
        # Update volume icon based on mute state
        restore_volume = getattr(self, 'previous_volume', 0.7) if not self.is_muted else current_volume
        self.update_volume_icon(0 if self.is_muted else restore_volume)
    
    def update_display(self):
        """Update time display and other UI elements."""
        if self.current_sample_path and not self.is_seeking:
            position = self.audio_player.get_position()
            duration = self.audio_player.get_duration()
            self.update_time_display(position, duration)
    
    def update_time_display(self, position_ms: int, duration_ms: int):
        """Update the time display label."""
        position_str = self.audio_player.format_time(position_ms)
        duration_str = self.audio_player.format_time(duration_ms)
        self.time_label.setText(f"{position_str} / {duration_str}")
    
    def get_current_sample(self) -> str:
        """Get the currently loaded sample path."""
        return self.current_sample_path
    
    def _get_volume_icon_path(self, volume_level):
        """Get the appropriate volume icon path based on volume level."""
        if self.is_muted or volume_level == 0:
            return "Icons/VolumeZero.svg"
        elif volume_level <= 0.33:
            return "Icons/VolumeLowIcon.svg"
        else:
            return "Icons/VolumeMidHighIcon.svg"

    def update_volume_icon(self, volume_level):
        """Update volume icon based on volume level."""
        import os
        
        icon_path = self._get_volume_icon_path(volume_level)
        
        # Use custom icon if available, otherwise fallback to MaterialIcon
        if os.path.exists(icon_path):
            self.volume_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback to MaterialIcon based on volume level
            if self.is_muted or volume_level == 0:
                self.volume_icon.setIcon(MaterialIcon('VOLUME_MUTE', 18).icon())
            else:
                self.volume_icon.setIcon(MaterialIcon('VOLUME', 18).icon()) 