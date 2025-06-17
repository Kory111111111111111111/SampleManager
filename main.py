import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFrame, QFileDialog, QDialog, QGridLayout, QScrollArea,
    QMessageBox, QMenu, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QPixmap, QShortcut, QKeySequence, QColor, QAction, QSurfaceFormat
from PyQt6.QtWidgets import QLabel

# FluentWidgets imports
from qfluentwidgets import (
    TreeWidget, ListWidget, ToolButton,
    PushButton, BodyLabel, TitleLabel, SplitFluentWindow,
    setTheme, Theme, NavigationItemPosition,
    FluentBackgroundTheme, setFont, setCustomStyleSheet,
    MessageBox, InfoBar, InfoBarPosition,
    ScrollArea, LineEdit, ComboBox
)

# Import TreeWidgetItem and ListWidgetItem from PyQt6.QtWidgets
from PyQt6.QtWidgets import QTreeWidgetItem as TreeWidgetItem, QListWidgetItem as ListWidgetItem

from sample_manager_universal import universal_sample_manager
from audio_analysis_universal import universal_audio_analyzer
from font_manager import get_font_manager, MaterialIcon
from audio_player import AudioPlayer
from playback_controls import PlaybackControls

# Configure logging
logger = logging.getLogger(__name__)

# 120Hz Display Optimization
def setup_high_refresh_display():
    """Setup Qt application for high refresh rate displays (120Hz+)."""
    try:
        # Set Qt application attributes BEFORE QApplication is created
        # These must be set before creating QApplication
        if hasattr(Qt.ApplicationAttribute, 'AA_UseOpenGLES'):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseOpenGLES)
        
        # High DPI support is automatic in PyQt6, no need to set AA_UseHighDpiPixmaps
        
        # Enable OpenGL acceleration for smoother animations
        fmt = QSurfaceFormat()
        fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        fmt.setSwapInterval(0)  # Disable vsync to allow 120Hz
        QSurfaceFormat.setDefaultFormat(fmt)
        
        logger.info("High refresh rate display optimization enabled")
        return True
    except Exception as e:
        logger.warning(f"Failed to setup high refresh display optimization: {e}")
        return False

class ManualCategoryDialog(QDialog):
    """Dialog for manually setting sample category and key."""
    
    def __init__(self, current_category="Unknown", current_subcategory="Unknown", 
                 current_key="Unknown", parent=None):
        super().__init__(parent)
        self.current_category = current_category
        self.current_subcategory = current_subcategory  
        self.current_key = current_key
        self.init_ui()
    
    def init_ui(self):
        """Initialize the manual category dialog UI."""
        self.setWindowTitle("Manual Category & Key Override")
        self.setMinimumSize(400, 300)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = TitleLabel("Manual Category & Key Override")
        title.setFont(get_font_manager().get_semibold_font(16))
        layout.addWidget(title)
        
        # Info text
        info_label = BodyLabel(
            "Override the automatic categorization and key detection with your manual selections. "
            "This will take precedence over the automatic analysis."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Category selection
        category_label = BodyLabel("Category:")
        category_label.setFont(get_font_manager().get_medium_font(12))
        layout.addWidget(category_label)
        
        self.category_combo = ComboBox()
        categories = ["Bass", "Drums", "FX", "Melodic", "Vocals"]
        self.category_combo.addItems(categories)
        if self.current_category in categories:
            self.category_combo.setCurrentText(self.current_category)
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        layout.addWidget(self.category_combo)
        
        # Subcategory selection
        subcategory_label = BodyLabel("Subcategory:")
        subcategory_label.setFont(get_font_manager().get_medium_font(12))
        layout.addWidget(subcategory_label)
        
        self.subcategory_combo = ComboBox()
        self.update_subcategories()
        if self.current_subcategory != "Unknown":
            index = self.subcategory_combo.findText(self.current_subcategory)
            if index >= 0:
                self.subcategory_combo.setCurrentIndex(index)
        layout.addWidget(self.subcategory_combo)
        
        # Key selection
        key_label = BodyLabel("Key:")
        key_label.setFont(get_font_manager().get_medium_font(12))
        layout.addWidget(key_label)
        
        self.key_combo = ComboBox()
        keys = ["Unknown", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        key_modes = []
        for key in keys[1:]:  # Skip "Unknown"
            key_modes.extend([f"{key} Major", f"{key} Minor"])
        
        all_keys = ["Unknown"] + key_modes
        self.key_combo.addItems(all_keys)
        if self.current_key in all_keys:
            self.key_combo.setCurrentText(self.current_key)
        layout.addWidget(self.key_combo)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = PushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setFixedWidth(100)
        
        apply_button = PushButton("Apply Override")
        apply_button.clicked.connect(self.accept)
        apply_button.setFixedWidth(120)
        
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(apply_button)
        layout.addLayout(button_layout)
    
    def on_category_changed(self):
        """Update subcategories when category changes."""
        self.update_subcategories()
    
    def update_subcategories(self):
        """Update subcategory dropdown based on selected category."""
        self.subcategory_combo.clear()
        
        category = self.category_combo.currentText()
        subcategories = {
            "Bass": ["808", "Bass Loops", "Electric Bass", "Synth Bass"],
            "Drums": ["Claps", "Cymbals", "Full Loops", "Hi-Hats", "Kicks", "Percussion", "Snares"],
            "FX": ["Ambient", "Downlifters", "Foley", "Impacts", "Risers"],
            "Melodic": ["Keys", "Melodic Loops", "Pads", "Plucks", "Synth Leads"],
            "Vocals": ["Chops", "One-Shots", "Phrases", "Vocal Loops"]
        }
        
        if category in subcategories:
            self.subcategory_combo.addItems(subcategories[category])
    
    def get_selections(self):
        """Get the selected category, subcategory, and key."""
        return (
            self.category_combo.currentText(),
            self.subcategory_combo.currentText(),
            self.key_combo.currentText()
        )

class NotificationWindow(QDialog):
    """Notification window to show system messages and organization results."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifications = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize the notification window UI."""
        self.setWindowTitle("Notifications")
        self.setMinimumSize(500, 400)
        self.setMaximumSize(600, 600)
        self.setModal(False)
        
        # Make window stay on top but not modal
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = TitleLabel("System Notifications")
        title.setFont(get_font_manager().get_semibold_font(16))
        layout.addWidget(title)
        
        # Scroll area for notifications
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Content widget for notifications
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(10)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Add empty state message
        self.empty_label = BodyLabel("No notifications")
        self.empty_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-style: italic;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.empty_label)
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        clear_button = PushButton("Clear All")
        clear_button.clicked.connect(self.clear_notifications)
        clear_button.setFixedWidth(100)
        
        close_button = PushButton("Close")
        close_button.clicked.connect(self.hide)
        close_button.setFixedWidth(100)
        
        button_layout.addWidget(clear_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def add_notification(self, title, message, notification_type="info"):
        """Add a notification to the window."""
        # Create notification widget
        notification_widget = QWidget()
        notification_layout = QVBoxLayout(notification_widget)
        notification_layout.setContentsMargins(15, 10, 15, 10)
        
        # Style based on type
        type_colors = {
            "info": "rgba(94, 129, 172, 0.2)",
            "success": "rgba(163, 190, 140, 0.2)", 
            "warning": "rgba(235, 203, 139, 0.2)",
            "error": "rgba(191, 97, 106, 0.2)"
        }
        
        type_text_colors = {
            "info": "rgba(94, 129, 172, 1.0)",
            "success": "rgba(163, 190, 140, 1.0)",
            "warning": "rgba(235, 203, 139, 1.0)", 
            "error": "rgba(191, 97, 106, 1.0)"
        }
        
        notification_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {type_colors.get(notification_type, type_colors["info"])};
                border-radius: 8px;
                border: 1px solid {type_text_colors.get(notification_type, type_text_colors["info"])};
            }}
        """)
        
        # Title
        title_label = BodyLabel(title)
        title_label.setFont(get_font_manager().get_medium_font(12))
        title_label.setStyleSheet(f"color: {type_text_colors.get(notification_type, type_text_colors['info'])}; font-weight: bold;")
        notification_layout.addWidget(title_label)
        
        # Message
        message_label = BodyLabel(message)
        message_label.setFont(get_font_manager().get_font(11))
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        notification_layout.addWidget(message_label)
        
        # Timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = BodyLabel(timestamp)
        time_label.setFont(get_font_manager().get_light_font(10))
        time_label.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        notification_layout.addWidget(time_label)
        
        # Remove empty state if this is first notification
        if len(self.notifications) == 0:
            self.empty_label.hide()
        
        # Add to layout (newest at top)
        self.content_layout.insertWidget(0, notification_widget)
        self.notifications.insert(0, notification_widget)
        
        # Limit to 50 notifications
        if len(self.notifications) > 50:
            old_notification = self.notifications.pop()
            old_notification.deleteLater()
        
        # Auto-scroll to top with 120Hz optimization
        def scroll_to_top():
            scrollbar = self.scroll_area.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(0)
        QTimer.singleShot(16, scroll_to_top)  # 60FPS timing, allows for higher refresh rates
    
    def clear_notifications(self):
        """Clear all notifications."""
        for notification in self.notifications:
            notification.deleteLater()
        self.notifications.clear()
        self.empty_label.show()
    
    def show_and_raise(self):
        """Show the window and bring it to front."""
        self.show()
        self.raise_()
        self.activateWindow()

class AnalysisResultsDialog(QDialog):
    """Dialog to display comprehensive analysis results."""
    
    def __init__(self, analysis_data, parent=None):
        super().__init__(parent)
        self.analysis_data = analysis_data
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Sample Analysis Results")
        self.setMinimumSize(500, 600)
        self.setModal(True)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = TitleLabel("Analysis Results")
        title.setFont(get_font_manager().get_extrabold_font(18))
        layout.addWidget(title)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        
        # Basic Info Section
        self.add_section(content_layout, "Basic Information", {
            "File Name": self.analysis_data.get("file_name", "Unknown"),
            "Duration": f"{self.analysis_data.get('duration', 0):.2f} seconds",
            "Sample Rate": f"{self.analysis_data.get('sample_rate', 0)} Hz",
            "File Size": f"{self.analysis_data.get('file_size', 0) / 1024:.1f} KB"
        })
        
        # Analysis Results Section
        self.add_section(content_layout, "Analysis Results", {
            "Sample Type": self.analysis_data.get("sample_type", "Unknown").title(),
            "Category": self.analysis_data.get("category", "Unknown").title(),
            "BPM": f"{self.analysis_data.get('bpm', 0):.1f}",
            "Key": self.analysis_data.get("key", "Unknown"),
            "Overall Confidence": f"{self.analysis_data.get('overall_confidence', 0):.1%}"
        })
        
        # Characteristics Section
        if characteristics := self.analysis_data.get("characteristics", {}):
            char_display = {
                key.replace('_', ' ').title(): f"{value:.3f}" if isinstance(value, (int, float)) else str(value)
                for key, value in characteristics.items()
            }
            
            self.add_section(content_layout, "Audio Characteristics", char_display)
        
        # Technical Info Section
        self.add_section(content_layout, "Technical Information", {
            "CPU Type": self.analysis_data.get("cpu_type", "Unknown"),
            "Analysis Methods": ", ".join(self.analysis_data.get("analysis_methods", [])),
            "Analyzer Version": self.analysis_data.get("analyzer_version", "Unknown")
        })
        
        # Error info if present
        if self.analysis_data.get("error"):
            self.add_section(content_layout, "Errors", {
                "Error Message": self.analysis_data.get("error", "None")
            })
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Close button
        close_button = PushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setFixedWidth(100)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def add_section(self, layout, title, data):
        """Add a section with title and data to the layout."""
        # Section title
        section_title = BodyLabel(title)
        section_title.setFont(get_font_manager().get_semibold_font(14))
        section_title.setStyleSheet("color: rgba(94, 129, 172, 1.0); font-weight: bold; margin-top: 10px;")
        layout.addWidget(section_title)
        
        # Data grid
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(10, 5, 10, 5)
        
        row = 0
        for row, (key, value) in enumerate(data.items()):
            # Key label
            key_label = BodyLabel(f"{key}:")
            key_label.setFont(get_font_manager().get_medium_font(11))
            key_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-weight: bold;")
            grid_layout.addWidget(key_label, row, 0, Qt.AlignmentFlag.AlignTop)
            
            # Value label
            value_label = BodyLabel(str(value))
            value_label.setFont(get_font_manager().get_font(11))
            value_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
            value_label.setWordWrap(True)
            grid_layout.addWidget(value_label, row, 1, Qt.AlignmentFlag.AlignTop)
        
        # Set column stretch
        grid_layout.setColumnStretch(0, 0)  # Key column - fixed width
        grid_layout.setColumnStretch(1, 1)  # Value column - stretch
        
        layout.addWidget(grid_widget)

class SettingsDialog(QDialog):
    """Comprehensive settings dialog for WAVFin Sample Manager."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()
    
    def init_ui(self):
        """Initialize the settings dialog UI."""
        self.setWindowTitle("WAVFin Settings")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = TitleLabel("WAVFin Settings")
        title.setFont(get_font_manager().get_semibold_font(16))
        layout.addWidget(title)
        
        # Settings sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(15)
        
        # Audio Settings Section
        self.add_section(settings_layout, "Audio Settings", [
            ("Sample Rate", "Preferred sample rate for audio playback", "48000 Hz"),
            ("Audio Device", "Current audio output device", "Default System Device"),
            ("Bass Enhancement", "Enhanced low-frequency reproduction", "Enabled")
        ])
        
        # Analysis Settings Section
        self.add_section(settings_layout, "Analysis Settings", [
            ("Auto-Analyze", "Automatically analyze samples when scanning", "Enabled"),
            ("Analysis Engine", "Current analysis engine", f"{self.parent_window.cached_system_info['cpu_type']} Optimized"),
            ("Available Methods", "Analysis methods available", self.parent_window.cached_available_methods)
        ])
        
        # Cache Management Section
        cache_section = QWidget()
        cache_layout = QVBoxLayout(cache_section)
        cache_layout.setContentsMargins(0, 0, 0, 10)
        
        cache_title = BodyLabel("Cache Management")
        cache_title.setFont(get_font_manager().get_semibold_font(14))
        cache_title.setStyleSheet("color: rgba(94, 129, 172, 1.0); font-weight: bold; margin-bottom: 10px;")
        cache_layout.addWidget(cache_title)
        
        cache_info_layout = QGridLayout()
        cache_info_layout.setSpacing(8)
        
        # Cache statistics
        cache_count = len(self.parent_window.sample_manager.sample_cache)
        directory_count = len(self.parent_window.sample_manager.tracked_directories)
        
        self.add_info_row(cache_info_layout, 0, "Cached Samples", f"{cache_count} samples")
        self.add_info_row(cache_info_layout, 1, "Tracked Directories", f"{directory_count} directories")
        
        cache_layout.addLayout(cache_info_layout)
        
        # Cache management buttons
        cache_button_layout = QHBoxLayout()
        
        self.reset_cache_button = PushButton("Reset Sample Cache")
        self.reset_cache_button.clicked.connect(self.reset_sample_cache)
        self.reset_cache_button.setToolTip("Clear all cached analysis data and force re-analysis")
        
        self.cleanup_cache_button = PushButton("Cleanup Missing Files")
        self.cleanup_cache_button.clicked.connect(self.cleanup_cache)
        self.cleanup_cache_button.setToolTip("Remove entries for files that no longer exist")
        
        cache_button_layout.addWidget(self.reset_cache_button)
        cache_button_layout.addWidget(self.cleanup_cache_button)
        cache_button_layout.addStretch()
        
        cache_layout.addLayout(cache_button_layout)
        settings_layout.addWidget(cache_section)
        
        # Display Settings Section
        self.add_section(settings_layout, "Display Settings", [
            ("Refresh Rate Optimization", "High refresh rate display support", "120Hz+ Optimized"),
            ("Theme", "Application color theme", "Dark Theme"),
            ("Font Family", "Primary font family", "Funnel Display")
        ])
        
        scroll_area.setWidget(settings_widget)
        layout.addWidget(scroll_area)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        # Audio diagnostics button
        diagnostics_button = PushButton("Audio Diagnostics")
        diagnostics_button.clicked.connect(self.show_audio_diagnostics)
        diagnostics_button.setToolTip("Show detailed audio device information")
        
        close_button = PushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setFixedWidth(100)
        
        button_layout.addWidget(diagnostics_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def add_section(self, layout, title, items):
        """Add a settings section with title and items."""
        section_widget = QWidget()
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(0, 0, 0, 10)
        
        # Section title
        section_title = BodyLabel(title)
        section_title.setFont(get_font_manager().get_semibold_font(14))
        section_title.setStyleSheet("color: rgba(94, 129, 172, 1.0); font-weight: bold; margin-bottom: 10px;")
        section_layout.addWidget(section_title)
        
        # Items grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)
        
        for i, (key, description, value) in enumerate(items):
            self.add_info_row(grid_layout, i, key, value, description)
        
        section_layout.addLayout(grid_layout)
        layout.addWidget(section_widget)
    
    def add_info_row(self, grid_layout, row, key, value, tooltip=None):
        """Add an information row to the grid."""
        # Key label
        key_label = BodyLabel(f"{key}:")
        key_label.setFont(get_font_manager().get_medium_font(12))
        key_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-weight: bold;")
        if tooltip:
            key_label.setToolTip(tooltip)
        grid_layout.addWidget(key_label, row, 0, Qt.AlignmentFlag.AlignTop)
        
        # Value label
        value_label = BodyLabel(str(value))
        value_label.setFont(get_font_manager().get_font(12))
        value_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        value_label.setWordWrap(True)
        if tooltip:
            value_label.setToolTip(tooltip)
        grid_layout.addWidget(value_label, row, 1, Qt.AlignmentFlag.AlignTop)
        
        # Set column stretch
        grid_layout.setColumnStretch(0, 0)  # Key column - fixed width
        grid_layout.setColumnStretch(1, 1)  # Value column - stretch
    
    def reset_sample_cache(self):
        """Reset the sample cache after confirmation."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Reset Sample Cache")
        msg_box.setText("Reset the entire sample cache?")
        msg_box.setInformativeText(
            "This will clear all cached analysis data and force WAVFin to re-analyze samples. "
            "This can help if you're experiencing categorization issues with the improved analysis system."
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            try:
                # Clear the cache
                cache_count = len(self.parent_window.sample_manager.sample_cache)
                self.parent_window.sample_manager.clear_cache()
                
                # Notify user
                self.parent_window._add_notification(
                    "Cache Reset Complete",
                    f"Cleared {cache_count} cached analyses. Samples will be re-analyzed when accessed.",
                    "success"
                )
                
                # Refresh categories
                self.parent_window.populate_categories()
                
                # Close dialog
                self.accept()
                
            except Exception as e:
                self.parent_window._add_notification(
                    "Cache Reset Error",
                    f"Failed to reset cache: {str(e)}",
                    "error"
                )
    
    def cleanup_cache(self):
        """Clean up cache entries for missing files."""
        try:
            initial_count = len(self.parent_window.sample_manager.sample_cache)
            
            # Remove entries for files that don't exist
            missing_files = []
            for file_path in list(self.parent_window.sample_manager.sample_cache.keys()):
                if not Path(file_path).exists():
                    missing_files.append(file_path)
                    del self.parent_window.sample_manager.sample_cache[file_path]
            
            # Save the cleaned cache
            if missing_files:
                self.parent_window.sample_manager.save_cache()
                
                self.parent_window._add_notification(
                    "Cache Cleanup Complete",
                    f"Removed {len(missing_files)} entries for missing files",
                    "success"
                )
                
                # Refresh categories
                self.parent_window.populate_categories()
            else:
                self.parent_window._add_notification(
                    "Cache Cleanup",
                    "No missing files found in cache",
                    "info"
                )
            
        except Exception as e:
            self.parent_window._add_notification(
                "Cleanup Error",
                f"Failed to cleanup cache: {str(e)}",
                "error"
            )
    
    def show_audio_diagnostics(self):
        """Show audio diagnostics information."""
        try:
            device_info = self.parent_window.audio_player.get_audio_device_info()
            
            # Create diagnostics dialog
            diagnostics_dialog = QDialog(self)
            diagnostics_dialog.setWindowTitle("Audio Device Diagnostics")
            diagnostics_dialog.setMinimumSize(450, 500)
            
            layout = QVBoxLayout(diagnostics_dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # Title
            title = TitleLabel("Audio Device Diagnostics")
            title.setFont(get_font_manager().get_semibold_font(16))
            layout.addWidget(title)
            
            # Scroll area for diagnostics info
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setSpacing(12)
            
            # Display device information
            for key, value in device_info.items():
                if key == "error":
                    continue
                    
                info_widget = QWidget()
                info_layout = QVBoxLayout(info_widget)
                info_layout.setContentsMargins(10, 5, 10, 5)
                key_label = BodyLabel(f"{key.replace('_', ' ').title()}:")
                key_label.setFont(get_font_manager().get_medium_font(12))
                key_label.setStyleSheet("color: rgba(94, 129, 172, 1.0); font-weight: bold;")
                info_layout.addWidget(key_label)
                
                if isinstance(value, list):
                    value_text = ", ".join(map(str, value)) if value else "None available"
                else:
                    value_text = str(value)
                
                value_label = BodyLabel(value_text)
                value_label.setFont(get_font_manager().get_font(11))
                value_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
                value_label.setWordWrap(True)
                info_layout.addWidget(value_label)
                
                content_layout.addWidget(info_widget)
            
            scroll.setWidget(content_widget)
            layout.addWidget(scroll)
            
            # Close button
            close_button = PushButton("Close")
            close_button.clicked.connect(diagnostics_dialog.accept)
            close_button.setFixedWidth(100)
            
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            layout.addLayout(button_layout)
            
            diagnostics_dialog.exec()
            
        except Exception as e:
            self.parent_window._add_notification(
                "Diagnostics Error",
                f"Failed to show audio diagnostics: {str(e)}",
                "error"
            )

class MainWindow(SplitFluentWindow):
    def __init__(self):
        super().__init__()
        self.sample_manager = universal_sample_manager
        self.analyzer = universal_audio_analyzer
        
        # Cache system info during initialization to avoid expensive calls later
        self.cached_system_info = self.sample_manager.system_info.copy()
        
        # Cache expensive string operations
        self.cached_available_methods = ", ".join([k for k, v in self.cached_system_info['available_methods'].items() if v])
        
        # Initialize audio player
        self.audio_player = AudioPlayer()
        
        # Create notification window
        self.notification_window = NotificationWindow(self)
        
        # Settings - removed auto_create_subcategories as it's not needed in indexing approach
        
        # Set FluentWidgets theme
        setTheme(Theme.DARK)
        
        # Enable 120Hz display optimization
        self.setup_smooth_animations()
        
        self.init_ui()

    def setup_smooth_animations(self):
        """Setup smooth animations optimized for high refresh rate displays."""
        # Configure Qt for smooth animation performance
        self.animation_duration = 16  # ~60fps base, can go higher on 120Hz
        self.animation_easing = QEasingCurve.Type.OutCubic
        
        # Create high-performance timer for smooth updates
        self.smooth_update_timer = QTimer()
        self.smooth_update_timer.setInterval(8)  # 120Hz support
        self.smooth_update_timer.timeout.connect(self._smooth_ui_update)

    def _smooth_ui_update(self):
        """Smooth UI update for high refresh rate displays."""
        # Update any smooth animations or transitions
        pass

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("")
        self.setMinimumSize(1200, 800)
        
        # Load custom fonts
        get_font_manager().load_fonts()
        
        # Trigger cache migration if needed - reduced delay for faster startup
        QTimer.singleShot(50, self._perform_initial_setup)  # Reduced from 100 to 50ms
        
        # Check for invalid cache entries and clean them up
        QTimer.singleShot(300, self._cleanup_invalid_cache_entries)  # Reduced from 500 to 300ms
        
        # Create main content widget
        self.main_widget = QWidget()
        self.main_widget.setObjectName("main_widget")
        main_layout = QHBoxLayout(self.main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel (Categories)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Category header with info icon
        category_header_layout = QHBoxLayout()
        category_header = TitleLabel("Categories")
        category_header.setFont(get_font_manager().get_semibold_font(16))
        category_header.setStyleSheet("TitleLabel { text-decoration: none; }")
        category_header_layout.addWidget(category_header)
        
        # Add info icon for auto-creation feature with notification system
        self.info_button = ToolButton(self)
        self.info_button.setIcon(MaterialIcon('INFO', 20).icon())
        self.info_button.setFixedSize(24, 24)
        self.info_button.setToolTip("Open notification window")
        self.info_button.clicked.connect(self._show_notification_window)
        category_header_layout.addWidget(self.info_button)
        
        # Initialize notification system
        self.notification_timer = QTimer()
        self.notification_timer.timeout.connect(self._toggle_notification_flash)
        self.notification_flash_state = False
        self.has_notifications = False
        
        # Add settings button
        self.settings_button = ToolButton(self)
        self.settings_button.setIcon(MaterialIcon('SETTING', 20).icon())
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.setToolTip("Settings and database management")
        self.settings_button.clicked.connect(self._show_settings_dialog)
        category_header_layout.addWidget(self.settings_button)
        
        category_header_layout.addStretch()
        
        left_layout.addLayout(category_header_layout)

        # Category tree
        self.category_tree = TreeWidget()
        self.category_tree.setHeaderHidden(True)
        setFont(self.category_tree, 12, QFont.Weight.Bold)
        
        # Apply custom scrollbar styling
        self._apply_custom_scrollbar_style(self.category_tree)
        
        # Apply styling
        self.category_tree.setStyleSheet("""
            TreeWidget {
                border: none;
                border-radius: 8px;
                outline: none;
            }
            TreeWidget::item {
                padding: 8px;
                border: none;
                border-radius: 4px;
                margin: 2px;
                outline: none;
            }
            TreeWidget::item:selected {
                background-color: rgba(94, 129, 172, 0.6);
                color: white;
                outline: none;
            }
            TreeWidget::item:hover {
                background-color: rgba(94, 129, 172, 0.3);
                outline: none;
            }
        """)
        self.populate_categories()
        self.category_tree.itemClicked.connect(self.on_category_selected)
        left_layout.addWidget(self.category_tree)

        # Right panel (Sample list and details)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 0, 0, 0)
        right_layout.setSpacing(10)

        # Sample list header
        sample_header = TitleLabel("Samples")
        sample_header.setFont(get_font_manager().get_semibold_font(16))
        sample_header.setStyleSheet("TitleLabel { text-decoration: none; }")
        right_layout.addWidget(sample_header)
        
        right_layout.addSpacing(5)

        # Sample list with context menu
        self.sample_list = ListWidget()
        self.sample_list.itemClicked.connect(self.on_sample_selected)
        self.sample_list.itemDoubleClicked.connect(self.on_sample_double_clicked)
        
        # Enable right-click context menu
        self.sample_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sample_list.customContextMenuRequested.connect(self.show_sample_context_menu)
        
        # Apply custom scrollbar styling
        self._apply_custom_scrollbar_style(self.sample_list)
        
        # Remove outlines from sample list
        self.sample_list.setStyleSheet("""
            ListWidget {
                border: none;
                border-radius: 8px;
                outline: none;
            }
            ListWidget::item {
                padding: 8px;
                border: none;
                border-radius: 4px;
                margin: 2px;
                outline: none;
            }
            ListWidget::item:selected {
                background-color: rgba(94, 129, 172, 0.6);
                color: white;
                outline: none;
            }
            ListWidget::item:hover {
                background-color: rgba(94, 129, 172, 0.3);
                outline: none;
            }
        """)
        
        right_layout.addWidget(self.sample_list, 1)
        right_layout.addSpacing(10)

        # Add playback controls
        self.playback_controls = PlaybackControls(self, self.audio_player)
        right_layout.addWidget(self.playback_controls)
        right_layout.addSpacing(8)

        # Bottom row: Control buttons and WAVFin logo
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        
        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.add_button = self._create_styled_button(MaterialIcon('ADD', 20), "Import Directory")
        self.add_button.clicked.connect(self.add_sample)
        
        self.analyze_button = self._create_styled_button(MaterialIcon('SEARCH', 20), "Analyze Sample")
        self.analyze_button.clicked.connect(self.analyze_sample)
        self.analyze_button.setEnabled(False)
        
        self.remove_button = self._create_styled_button(MaterialIcon('DELETE', 20), "Remove Sample")
        self.remove_button.clicked.connect(self.remove_sample)
        self.remove_button.setEnabled(False)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.analyze_button)
        button_layout.addWidget(self.remove_button)
        
        bottom_layout.addLayout(button_layout)
        bottom_layout.addStretch()
        
        # Add WAVFin logo
        self.add_wavfin_logo_inline(bottom_layout)
        
        right_layout.addLayout(bottom_layout)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([360, 840])
        self.splitter = splitter
        splitter.splitterMoved.connect(self.on_splitter_moved)
        
        # Add main widget to the window
        self.addSubInterface(self.main_widget, MaterialIcon('MUSIC', 20).icon(), "Sample Manager")
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Add subtle startup animation
        self.animate_startup()

    def show_sample_context_menu(self, position):
        """Show context menu for sample list items."""
        item = self.sample_list.itemAt(position)
        if not item:
            return
        
        sample_data = item.data(Qt.ItemDataRole.UserRole)
        if not sample_data or sample_data.get("empty_state") or sample_data.get("help_message"):
            return
        
        # Create context menu
        context_menu = QMenu(self)
        
        # Manual category override action
        override_action = QAction("Manual Category & Key Override...", self)
        override_action.setIcon(MaterialIcon('EDIT', 16).icon())
        override_action.triggered.connect(lambda: self.show_manual_category_dialog(sample_data))
        context_menu.addAction(override_action)
        
        context_menu.addSeparator()
        
        # Analyze action
        analyze_action = QAction("Analyze Sample", self)
        analyze_action.setIcon(MaterialIcon('SEARCH', 16).icon())
        analyze_action.triggered.connect(self.analyze_sample)
        context_menu.addAction(analyze_action)
        
        # Play action
        play_action = QAction("Play Sample", self)
        play_action.setIcon(MaterialIcon('PLAY', 16).icon())
        play_action.triggered.connect(lambda: self.on_sample_double_clicked(item))
        context_menu.addAction(play_action)
        
        context_menu.addSeparator()
        
        # Remove action
        remove_action = QAction("Remove from Index", self)
        remove_action.setIcon(MaterialIcon('DELETE', 16).icon())
        remove_action.triggered.connect(self.remove_sample)
        context_menu.addAction(remove_action)
        
        # Show context menu
        context_menu.exec(self.sample_list.mapToGlobal(position))

    def show_manual_category_dialog(self, sample_data):
        """Show manual category override dialog."""
        try:
            current_category = sample_data.get("category", "Unknown").title()
            current_key = sample_data.get("key", "Unknown")
            
            # Get current subcategory
            if file_path := sample_data.get("file_path", ""):
                _, current_subcategory = self.sample_manager.get_current_category_subcategory(file_path)
            else:
                current_subcategory = "Unknown"
            
            dialog = ManualCategoryDialog(current_category, current_subcategory, current_key, self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                category, subcategory, key = dialog.get_selections()
                
                # Apply manual override
                self.apply_manual_category_override(sample_data, category, subcategory, key)
                
        except Exception as e:
            self._add_notification(
                "Dialog Error",
                f"Failed to show manual category dialog: {str(e)}",
                "error"
            )

    def apply_manual_category_override(self, sample_data, category, subcategory, key):
        """Apply manual category and key override to a sample."""
        try:
            file_path = sample_data.get("file_path", "")
            if not file_path:
                return
            
            # Update the sample data in cache
            file_key = str(Path(file_path).resolve())
            if file_key in self.sample_manager.sample_cache:
                # Update the cached analysis with manual overrides
                self.sample_manager.sample_cache[file_key].update({
                    "category": category.lower(),
                    "key": key,
                    "manual_override": True,
                    "manual_category": category,
                    "manual_subcategory": subcategory,
                    "manual_key": key
                })
                
                # Save the updated cache
                self.sample_manager.save_cache()
                
                self._add_notification(
                    "Manual Override Applied",
                    f"Set {Path(file_path).name} to {category} > {subcategory}, Key: {key}",
                    "success"
                )
                
                # Refresh the current view
                if (category_subcategory := self.get_current_category_subcategory()) != (None, None):
                    current_category, current_subcategory = category_subcategory
                    self.load_samples(current_category, current_subcategory)
                
                # Refresh categories in case new ones were added
                self.populate_categories()
                
            else:
                self._add_notification(
                    "Override Error",
                    "Sample not found in cache",
                    "error"
                )
                
        except Exception as e:
            self._add_notification(
                "Override Error",
                f"Failed to apply manual override: {str(e)}",
                "error"
            )

    def populate_categories(self):
        """Populate the category tree with data from sample manager."""
        try:
            self.category_tree.clear()
            categories = self.sample_manager.get_categories()
        except Exception as e:
            logger.error(f"Failed to populate categories: {e}")
            return
        
        # Create bold font for tree items
        bold_font = QFont()
        bold_font.setWeight(QFont.Weight.Bold)
        bold_font.setPointSizeF(9.0)
        
        for category, subcategories in categories.items():
            category_item = TreeWidgetItem([category])
            category_item.setIcon(0, MaterialIcon('FOLDER', 16).icon())
            category_item.setFont(0, bold_font)
            self.category_tree.addTopLevelItem(category_item)
            
            for subcategory in subcategories:
                subcategory_item = TreeWidgetItem([subcategory])
                subcategory_item.setIcon(0, MaterialIcon('FOLDER', 14).icon())
                subcategory_item.setFont(0, bold_font)
                category_item.addChild(subcategory_item)
        
        self.category_tree.expandAll()

    def on_category_selected(self, item, column):
        """Handle category selection."""
        if item.parent():  # This is a subcategory
            category = item.parent().text(0)
            subcategory = item.text(0)
            self.load_samples(category, subcategory)

    def load_samples(self, category, subcategory):
        """Load samples for the selected category/subcategory."""
        try:
            self.sample_list.clear()
            samples = self.sample_manager.get_samples(category, subcategory)
        except Exception as e:
            logger.error(f"Failed to load samples for {category}/{subcategory}: {e}")
            self._add_notification(
                "Loading Error",
                f"Failed to load samples: {str(e)}",
                "error"
            )
            return
        
        if not samples:
            self._add_empty_state_items(category, subcategory)
        else:
            self._populate_sample_list(samples)

    def _add_empty_state_items(self, category, subcategory):
        """Add empty state items."""
        empty_item = ListWidgetItem(f"No samples in {category} > {subcategory}")
        empty_item.setIcon(MaterialIcon('ADD', 16).icon())
        empty_item.setData(Qt.ItemDataRole.UserRole, {"empty_state": True})
        empty_item.setFlags(empty_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        empty_item.setForeground(QColor(150, 150, 150))
        self.sample_list.addItem(empty_item)

    def _populate_sample_list(self, samples):
        """Populate the sample list with sample items."""
        for sample in samples:
            item = self._create_sample_list_item(sample)
            self.sample_list.addItem(item)

    def _create_sample_list_item(self, sample):
        """Create a list widget item for a sample."""
        file_name = sample.get("file_name", "Unknown")
        display_text = file_name
        
        item = ListWidgetItem(display_text)
        item.setIcon(MaterialIcon('AUDIO_FILE', 16).icon())
        item.setData(Qt.ItemDataRole.UserRole, sample)
        
        return item

    def on_sample_selected(self, item):
        """Handle sample selection."""
        sample_data = item.data(Qt.ItemDataRole.UserRole)
        
        if sample_data and not sample_data.get("empty_state") and not sample_data.get("help_message"):
            self.analyze_button.setEnabled(True)
            self.remove_button.setEnabled(True)
            
            if "file_path" in sample_data:
                try:
                    file_path = sample_data["file_path"]
                    self.playback_controls.load_sample(file_path)
                except Exception as e:
                    self._add_notification(
                        "Playback Error",
                        f"Failed to load sample for playback: {str(e)}",
                        "error"
                    )
        else:
            self.analyze_button.setEnabled(False)
            self.remove_button.setEnabled(False)

    def on_sample_double_clicked(self, item):
        """Handle sample double-click to play the sample."""
        sample_data = item.data(Qt.ItemDataRole.UserRole)
        
        if sample_data and not sample_data.get("empty_state") and not sample_data.get("help_message") and "file_path" in sample_data:
            try:
                file_path = sample_data["file_path"]
                self.playback_controls.load_sample(file_path)
                QTimer.singleShot(100, self.playback_controls.toggle_playback)
                
                self._add_notification(
                    "Sample Playing", 
                    f"Playing: {sample_data.get('file_name', 'Unknown')}", 
                    "info"
                )
            except Exception as e:
                self._add_notification(
                    "Playback Error",
                    f"Failed to play sample: {str(e)}",
                    "error"
                )

    def get_current_category_subcategory(self):
        """Get the current category and subcategory from the tree widget."""
        if (category_item := self.category_tree.currentItem()) and (parent := category_item.parent()):
            category = parent.text(0)
            subcategory = category_item.text(0)
            return category, subcategory
        return None, None

    def add_sample(self):
        """Import samples by adding directories to the sample index for scanning."""
        directory_dialog = QFileDialog()
        directory_dialog.setFileMode(QFileDialog.FileMode.Directory)
        directory_dialog.setWindowTitle("Import Samples - Select Directory to Scan")
        directory_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        # Set a helpful dialog message
        directory_dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Import from Directory")
        
        if directory_dialog.exec() and (selected_directories := directory_dialog.selectedFiles()):
            self._scan_directories(selected_directories)

    def _scan_directories(self, directories):
        """Scan selected directories for audio samples."""
        total_new_files = 0
        
        for directory in directories:
            try:
                self._add_notification(
                    "Importing Samples",
                    f"Scanning {Path(directory).name} for audio files...",
                    "info"
                )
                
                new_files = self.sample_manager.add_directory_to_index(directory)
                total_new_files += new_files
                
                if new_files > 0:
                    self._add_notification(
                        "Import Success",
                        f"Imported {new_files} audio files from {Path(directory).name}",
                        "success"
                    )
                else:
                    self._add_notification(
                        "Directory Processed",
                        f"No new files found in {Path(directory).name} (may already be indexed)",
                        "info"
                    )
                
            except Exception as e:
                self._add_notification(
                    "Import Error",
                    f"Failed to import from {Path(directory).name}: {str(e)}",
                    "error"
                )
        
        if total_new_files > 0:
            self._add_notification(
                "Import Complete",
                f"Successfully imported {total_new_files} new audio files from {len(directories)} directories",
                "success"
            )
            self.populate_categories()
        else:
            self._add_notification(
                "Import Complete",
                "No new audio files were found. They may already be in your library.",
                "info"
            )

    def analyze_sample(self):
        """Analyze the selected sample."""
        if not (current_item := self.sample_list.currentItem()):
            return
            
        sample_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not sample_data or sample_data.get("empty_state") or sample_data.get("help_message"):
            return
            
        file_path = sample_data.get("file_path")
        if not file_path:
            return
            
        self._add_notification(
            "Analysis Started",
            f"Analyzing {sample_data.get('file_name', 'sample')}...",
            "info"
        )
        
        result = self.sample_manager.analyze_sample(file_path)
        
        try:
            dialog = AnalysisResultsDialog(result, self)
            dialog.exec()
        except Exception as e:
            self._add_notification(
                "Dialog Error",
                f"Failed to show analysis results: {str(e)}",
                "error"
            )
        
        if (category_subcategory := self.get_current_category_subcategory()) != (None, None):
            category, subcategory = category_subcategory
            self.load_samples(category, subcategory)

    def remove_sample(self):
        """Remove the selected sample from the index."""
        if not (current_item := self.sample_list.currentItem()):
            return
            
        sample_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not sample_data or sample_data.get("empty_state") or sample_data.get("help_message"):
            return
            
        file_path = sample_data.get("file_path")
        if not file_path:
            return
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Remove from Index")
        msg_box.setText(f"Remove {Path(file_path).name} from the sample index?")
        msg_box.setInformativeText(
            "This will remove the sample from WAVFin's index but will NOT delete the actual file from your disk."
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            try:
                self.sample_manager.remove_sample(file_path)
                
                self._add_notification(
                    "Sample Removed from Index",
                    f"Removed {Path(file_path).name} from index (file kept on disk)",
                    "success"
                )
                
                if (category_subcategory := self.get_current_category_subcategory()) != (None, None):
                    category, subcategory = category_subcategory
                    self.load_samples(category, subcategory)
                
            except Exception as e:
                self._add_notification(
                    "Remove Error", 
                    f"Failed to remove sample from index: {str(e)}",
                    "error"
                )

    # Add other essential methods
    def _create_styled_button(self, icon, tooltip, size=(48, 48)):
        """Create a styled ToolButton."""
        button = ToolButton(self)
        button.setIcon(icon.icon())
        button.setFixedSize(*size)
        button.setToolTip(tooltip)
        return button

    def add_wavfin_logo_inline(self, layout):
        """Add WAVFin logo inline."""
        logo_label = QLabel()
        logo_pixmap = QPixmap("Icons/WAVFinIcon.png")
        if not logo_pixmap.isNull():
            scaled_pixmap = logo_pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("WAVFin")
        layout.addWidget(logo_label)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts."""
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.activated.connect(self.toggle_playback)
        
        # Arrow keys for sample navigation
        self.up_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.up_shortcut.activated.connect(self.navigate_to_previous_sample)
        
        self.down_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.down_shortcut.activated.connect(self.navigate_to_next_sample)

    def toggle_playback(self):
        """Toggle playback when spacebar is pressed."""
        if hasattr(self, 'playback_controls') and self.playback_controls.current_sample_path:
            self.playback_controls.toggle_playback()
    
    def navigate_to_previous_sample(self):
        """Navigate to the previous sample in the list."""
        current_row = self.sample_list.currentRow()
        if current_row > 0:
            # Find the previous non-empty item
            for i in range(current_row - 1, -1, -1):
                item = self.sample_list.item(i)
                if item:
                    sample_data = item.data(Qt.ItemDataRole.UserRole)
                    if sample_data and not sample_data.get("empty_state") and not sample_data.get("help_message"):
                        self.sample_list.setCurrentItem(item)
                        self.on_sample_double_clicked(item)  # Auto-play the sample
                        break
    
    def navigate_to_next_sample(self):
        """Navigate to the next sample in the list."""
        current_row = self.sample_list.currentRow()
        if current_row < self.sample_list.count() - 1:
            # Find the next non-empty item
            for i in range(current_row + 1, self.sample_list.count()):
                item = self.sample_list.item(i)
                if item:
                    sample_data = item.data(Qt.ItemDataRole.UserRole)
                    if sample_data and not sample_data.get("empty_state") and not sample_data.get("help_message"):
                        self.sample_list.setCurrentItem(item)
                        self.on_sample_double_clicked(item)  # Auto-play the sample
                        break
    
    def on_splitter_moved(self, pos, index):
        """Handle splitter movement."""
        self.category_tree.updateGeometry()
        self.category_tree.update()

    def animate_startup(self):
        """Add startup animation."""
        pass

    def _apply_custom_scrollbar_style(self, widget):
        """Apply custom scrollbar styling."""
        scrollbar_style = """
            QScrollBar:vertical {
                background: rgba(46, 52, 64, 0.3);
                width: 12px;
                border-radius: 6px;
                margin: 0px;
                border: none;
                outline: none;
            }
            QScrollBar::handle:vertical {
                background: rgba(94, 129, 172, 0.8);
                border-radius: 6px;
                min-height: 30px;
                margin: 2px;
                border: none;
                outline: none;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(94, 129, 172, 1.0);
                outline: none;
            }
        """
        current_style = widget.styleSheet()
        widget.setStyleSheet(current_style + scrollbar_style)

    def _show_notification_window(self):
        """Show the notification window and stop flashing."""
        try:
            self._stop_notification_flash()
            self.notification_window.show_and_raise()
        except Exception as e:
            logger.error(f"Failed to show notification window: {e}")

    def _add_notification(self, title, content, notification_type="info"):
        """Add a notification to the window."""
        try:
            self.notification_window.add_notification(title, content, notification_type)
            
            # Start flashing for errors and warnings
            if notification_type in ["error", "warning"]:
                self._start_notification_flash()
        except Exception as e:
            logger.error(f"Failed to add notification: {e}")

    def _start_notification_flash(self):
        """Start flashing the notification icon for important messages."""
        try:
            self.has_notifications = True
            self.notification_flash_state = False
            if not self.notification_timer.isActive():
                self.notification_timer.start(500)  # Flash every 500ms
        except Exception as e:
            logger.error(f"Failed to start notification flash: {e}")
    
    def _stop_notification_flash(self):
        """Stop flashing the notification icon."""
        try:
            self.has_notifications = False
            if self.notification_timer.isActive():
                self.notification_timer.stop()
            # Reset icon to normal state
            self.info_button.setIcon(MaterialIcon('INFO', 20).icon())
            self.info_button.setStyleSheet("")
        except Exception as e:
            logger.error(f"Failed to stop notification flash: {e}")
    
    def _toggle_notification_flash(self):
        """Toggle the notification flash state for visual indicator."""
        try:
            if self.has_notifications:
                self.notification_flash_state = not self.notification_flash_state
                
                if self.notification_flash_state:
                    # Flash red for attention
                    self.info_button.setStyleSheet("""
                        ToolButton {
                            background-color: rgba(191, 97, 106, 0.8);
                            border-radius: 12px;
                            border: 2px solid rgba(191, 97, 106, 1.0);
                        }
                        ToolButton:hover {
                            background-color: rgba(191, 97, 106, 1.0);
                        }
                    """)
                else:
                    # Normal state
                    self.info_button.setStyleSheet("")
        except Exception as e:
            logger.error(f"Failed to toggle notification flash: {e}")

    def _cleanup_invalid_cache_entries(self):
        """Clean up invalid cache entries."""
        try:
            initial_count = len(self.sample_manager.sample_cache)
            categories = self.sample_manager.get_categories()
            for category, subcategories in categories.items():
                for subcategory in subcategories:
                    self.sample_manager.get_samples(category, subcategory)
            
            final_count = len(self.sample_manager.sample_cache)
            cleaned_count = initial_count - final_count
            
            if cleaned_count > 0:
                self._add_notification(
                    "Cache Cleanup",
                    f"Removed {cleaned_count} invalid cache entries with missing files.",
                    "info"
                )
                self.populate_categories()
        except Exception as e:
            self._add_notification(
                "Cleanup Error",
                f"Error during cache cleanup: {str(e)}",
                "error"
            )

    def _perform_initial_setup(self):
        """Perform initial setup including cache migration if needed."""
        try:
            # Check if cache migration is needed and perform it
            if hasattr(self.sample_manager, '_migration_pending') and self.sample_manager._migration_pending:
                self._add_notification(
                    "Cache Migration",
                    "Migrating sample cache to new format, this may take a moment...",
                    "info"
                )
                
                # Trigger cache migration
                self.sample_manager._ensure_cache_migrated()
                
                self._add_notification(
                    "Cache Migration Complete",
                    "Sample cache has been successfully migrated to the new format",
                    "success"
                )
                
                # Refresh the categories after migration
                QTimer.singleShot(100, self.populate_categories)  # Reduced from 200 to 100ms for faster response
                
        except Exception as e:
            self._add_notification(
                "Migration Error",
                f"Failed to migrate cache: {str(e)}",
                "error"
            )

    def _show_settings_dialog(self):
        """Show comprehensive settings dialog."""
        try:
            settings_dialog = SettingsDialog(self)
            settings_dialog.exec()
        except Exception as e:
            self._add_notification(
                "Settings Error",
                f"Failed to show settings dialog: {str(e)}",
                "error"
            )

def main():
    """Main application entry point."""
    print("WAVFin Sample Manager starting...")
    
    # Setup high refresh rate display optimization before creating app
    print("Setting up high refresh display...")
    setup_high_refresh_display()
    
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    
    # Set application properties for smooth rendering
    print("Setting application properties...")
    app.setApplicationName("WAVFin Sample Manager")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("WAVFin")
    
    print("Creating MainWindow...")
    try:
        window = MainWindow()
        print("MainWindow created successfully")
    except Exception as e:
        print(f"Error creating MainWindow: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("Showing window...")
    window.show()
    print("Window should now be visible")
    
    print("Starting event loop...")
    result = app.exec()
    print(f"Application exited with code: {result}")
    sys.exit(result)

if __name__ == "__main__":
    main()
