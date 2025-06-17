import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFrame, QFileDialog, QDialog, QGridLayout, QScrollArea,
    QMessageBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QPixmap, QShortcut, QKeySequence, QColor
from PyQt6.QtWidgets import QLabel

# FluentWidgets imports
from qfluentwidgets import (
    TreeWidget, ListWidget, ToolButton,
    PushButton, BodyLabel, TitleLabel, SplitFluentWindow,
    setTheme, Theme, NavigationItemPosition,
    FluentBackgroundTheme, setFont, setCustomStyleSheet,
    MessageBox, InfoBar, InfoBarPosition,
    ScrollArea
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
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
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
        
        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)
        
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
        title_label.setFont(get_font_manager().get_header_font(12))
        title_label.setStyleSheet(f"color: {type_text_colors.get(notification_type, type_text_colors['info'])}; font-weight: bold;")
        notification_layout.addWidget(title_label)
        
        # Message
        message_label = BodyLabel(message)
        message_label.setFont(get_font_manager().get_body_font(10))
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        notification_layout.addWidget(message_label)
        
        # Timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = BodyLabel(timestamp)
        time_label.setFont(get_font_manager().get_body_font(9))
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
        
        # Auto-scroll to top
        QTimer.singleShot(100, lambda: self.scroll.verticalScrollBar().setValue(0))
    
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
        title.setFont(get_font_manager().get_header_font(18))
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
        section_title.setFont(get_font_manager().get_header_font(14))
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
            key_label.setFont(get_font_manager().get_body_font(10))
            key_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-weight: bold;")
            grid_layout.addWidget(key_label, row, 0, Qt.AlignmentFlag.AlignTop)
            
            # Value label
            value_label = BodyLabel(str(value))
            value_label.setFont(get_font_manager().get_body_font(10))
            value_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
            value_label.setWordWrap(True)
            grid_layout.addWidget(value_label, row, 1, Qt.AlignmentFlag.AlignTop)
        
        # Set column stretch
        grid_layout.setColumnStretch(0, 0)  # Key column - fixed width
        grid_layout.setColumnStretch(1, 1)  # Value column - stretch
        
        layout.addWidget(grid_widget)

class MainWindow(SplitFluentWindow):
    def __init__(self):
        super().__init__()
        self.sample_manager = universal_sample_manager
        self.analyzer = universal_audio_analyzer
        
        # Initialize audio player
        self.audio_player = AudioPlayer()
        
        # Create notification window
        self.notification_window = NotificationWindow(self)
        
        # Settings - use persistent variables instead of widget references
        self.auto_create_subcategories = True  # Default setting
        
        # Set FluentWidgets theme
        setTheme(Theme.DARK)
        
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("")
        self.setMinimumSize(1200, 800)
        
        # Load custom fonts
        get_font_manager().load_fonts()
        
        # Auto-create missing subcategories on startup
        if created_subcategories := self._auto_create_missing_subcategories():
            # Delay the notification so it shows after the UI is ready
            QTimer.singleShot(1000, lambda: self._show_auto_created_subcategories_notification(created_subcategories))
        
        # Check for invalid cache entries and clean them up
        QTimer.singleShot(500, self._cleanup_invalid_cache_entries)
        
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
        category_header.setFont(get_font_manager().get_header_font(16))
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
        # Use QFluentWidgets font system for proper bold text
        setFont(self.category_tree, 12, QFont.Weight.Bold)
        
        # Apply custom scrollbar styling
        self._apply_custom_scrollbar_style(self.category_tree)
        
        # Apply Nord10 color styling only to dropdown items
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
            TreeWidget::item:focus {
                outline: none;
                border: none;
            }
        """)
        self.populate_categories()
        self.category_tree.itemClicked.connect(self.on_category_selected)
        left_layout.addWidget(self.category_tree)

        # Right panel (Sample list and details)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 0, 0, 0)  # Add left margin to move content right
        right_layout.setSpacing(10)  # Reduced from 15 to 10

        # Sample list header
        sample_header = TitleLabel("Samples")
        sample_header.setFont(get_font_manager().get_header_font(16))
        # Remove underline styling
        sample_header.setStyleSheet("TitleLabel { text-decoration: none; }")
        right_layout.addWidget(sample_header)
        
        # Reduced padding between Samples label and list
        right_layout.addSpacing(5)  # Reduced from 10 to 5

        # Sample list - give it more space
        self.sample_list = ListWidget()
        self.sample_list.itemClicked.connect(self.on_sample_selected)
        self.sample_list.itemDoubleClicked.connect(self.on_sample_double_clicked)
        
        # Apply custom scrollbar styling and remove outlines
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
            ListWidget::item:focus {
                outline: none;
                border: none;
            }
        """)
        
        right_layout.addWidget(self.sample_list, 1)  # Added stretch factor of 1

        # Reduced stretch to push playback controls closer
        right_layout.addSpacing(10)  # Small fixed spacing instead of stretch

        # Add playback controls
        self.playback_controls = PlaybackControls(self, self.audio_player)
        right_layout.addWidget(self.playback_controls)

        # Minimal spacing between playback controls and buttons
        right_layout.addSpacing(8)

        # Bottom row: Control buttons and WAVFin logo on same level
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        
        # Control buttons on the left
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Use ToolButton for icon-only buttons (better for FluentWidgets)
        
        self.add_button = self._create_styled_button(MaterialIcon('ADD', 20), "Add Sample")
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
        
        # Add buttons to bottom layout
        bottom_layout.addLayout(button_layout)
        bottom_layout.addStretch()  # Push logo to the right
        
        # Add WAVFin logo on the right
        self.add_wavfin_logo_inline(bottom_layout)
        
        right_layout.addLayout(bottom_layout)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (30% left, 70% right)
        splitter.setSizes([360, 840])
        
        # Make splitter responsive - store reference for resizing
        self.splitter = splitter
        splitter.splitterMoved.connect(self.on_splitter_moved)
        
        # Add main widget to the window
        self.addSubInterface(self.main_widget, MaterialIcon('MUSIC', 20).icon(), "Sample Manager")
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Add subtle startup animation
        self.animate_startup()

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
            # Set icons based on category using custom icons from Icons directory
            icon_path = None
            if category == "Drums":
                icon_path = "Icons/DrumSamplesIcon.svg"
            elif category == "Bass":
                icon_path = "Icons/MusicKeyIcon.svg"
            elif category == "Melodic":
                icon_path = "Icons/NonDrumSamples.svg"
            elif category == "FX":
                icon_path = "Icons/WaveformIcon.svg"
            elif category == "Vocals":
                icon_path = "Icons/VocalSamplesIcon.svg"
            
            # Use custom icon if available, otherwise fallback to FluentIcon
            if icon_path and os.path.exists(icon_path):
                icon = QIcon(icon_path)
            else:
                # Fallback to MaterialIcon
                category_icons = {
                    "Drums": MaterialIcon('DRUMS', 16),
                    "Bass": MaterialIcon('MUSIC', 16),
                    "Melodic": MaterialIcon('PIANO', 16),
                    "FX": MaterialIcon('EFFECTS', 16),
                    "Vocals": MaterialIcon('VOCALS', 16)
                }
                icon = category_icons.get(category, MaterialIcon('FOLDER', 16)).icon()
                
            category_item = TreeWidgetItem([category])
            category_item.setIcon(0, icon)
            # Apply bold font to category item
            category_item.setFont(0, bold_font)
            self.category_tree.addTopLevelItem(category_item)
            
            for subcategory in subcategories:
                subcategory_item = TreeWidgetItem([subcategory])
                subcategory_item.setIcon(0, MaterialIcon('FOLDER', 14).icon())
                # Apply bold font to subcategory item
                subcategory_item.setFont(0, bold_font)
                category_item.addChild(subcategory_item)
        
        self.category_tree.expandAll()

    def _create_styled_button(self, icon, tooltip, size=(48, 48)):
        """Create a styled ToolButton with consistent styling."""
        button = ToolButton(self)
        button.setIcon(icon.icon())
        button.setFixedSize(*size)
        button.setToolTip(tooltip)
        self.setup_button_animations(button)
        return button

    def setup_button_animations(self, button):
        """Setup hover animations and styling for buttons."""
        # Set icon size for proper centering
        button.setIconSize(QSize(20, 20))
        
        # Use QFluentWidgets setCustomStyleSheet for proper styling
        qss = """
            ToolButton {
                border-radius: 16px;
                border: 2px solid transparent;
                background-color: rgba(94, 129, 172, 0.8);
                color: white;
                outline: none;
            }
            ToolButton:hover {
                background-color: rgba(94, 129, 172, 1.0);
                border: 2px solid rgba(94, 129, 172, 0.3);
                outline: none;
            }
            ToolButton:pressed {
                background-color: rgba(94, 129, 172, 0.6);
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
        setCustomStyleSheet(button, qss, qss)  # Same style for light and dark themes
        
        # Create property animations for push effect
        self.setup_push_animation(button)

    def _setup_animation_duration(self, animation, duration=25):
        """Setup animation duration and easing curve."""
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.OutQuad)

    def setup_push_animation(self, button):
        """Setup push animation for button using Qt property animations."""
        # Create animation for button press effect
        button.press_animation = QPropertyAnimation(button, b"geometry")
        self._setup_animation_duration(button.press_animation)
        
        button.release_animation = QPropertyAnimation(button, b"geometry")
        self._setup_animation_duration(button.release_animation)
        
        # Store original geometry
        button.original_geometry = None
        
        # Connect press and release events
        button.pressed.connect(lambda: self.animate_button_press(button))
        button.released.connect(lambda: self.animate_button_release(button))

    def animate_button_press(self, button):
        """Animate button press with slight scale down effect."""
        if button.original_geometry is None:
            button.original_geometry = button.geometry()
        
        # Create slightly smaller geometry for press effect
        pressed_geometry = button.original_geometry.adjusted(2, 2, -2, -2)
        
        button.press_animation.setStartValue(button.geometry())
        button.press_animation.setEndValue(pressed_geometry)
        button.press_animation.start()

    def animate_button_release(self, button):
        """Animate button release back to original size."""
        if button.original_geometry is not None:
            button.release_animation.setStartValue(button.geometry())
            button.release_animation.setEndValue(button.original_geometry)
            button.release_animation.start()

    def _create_logo_label(self, size, alignment):
        """Create a logo label with specified size and alignment."""
        logo_label = QLabel()
        logo_pixmap = QPixmap("Icons/WAVFinIcon.png")
        
        # Scale the logo to the specified size
        if not logo_pixmap.isNull():
            scaled_pixmap = logo_pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("WAVFin")  # Fallback text
        
        logo_label.setAlignment(alignment)
        
        # Add subtle styling for logo
        logo_label.setStyleSheet("""
            QLabel {
                background: transparent;
            }
        """)
        
        return logo_label

    def add_wavfin_logo(self, layout):
        """Add WAVFin logo to the bottom right corner."""
        # Create a container for the logo
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add stretch to push logo to the right
        logo_layout.addStretch()
        
        # Create logo label
        self.logo_label = self._create_logo_label(64, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        
        # Add hover effect using Qt animation
        self.setup_logo_hover_effect()
        
        logo_layout.addWidget(self.logo_label)
        layout.addWidget(logo_container)

    def add_wavfin_logo_inline(self, layout):
        """Add WAVFin logo inline to a horizontal layout."""
        # Create logo label
        self.logo_label = self._create_logo_label(48, Qt.AlignmentFlag.AlignCenter)
        
        # Add hover effect using Qt animation
        self.setup_logo_hover_effect()
        
        layout.addWidget(self.logo_label)

    def setup_logo_hover_effect(self):
        """Setup hover effect for logo using Qt events."""
        # Create opacity effect
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self.logo_opacity_effect = QGraphicsOpacityEffect()
        self.logo_opacity_effect.setOpacity(0.7)
        self.logo_label.setGraphicsEffect(self.logo_opacity_effect)
        
        # Create animation for opacity
        self.logo_fade_animation = QPropertyAnimation(self.logo_opacity_effect, b"opacity")
        self.logo_fade_animation.setDuration(150)
        
        # Install event filter for hover detection
        self.logo_label.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Handle hover events for logo."""
        if hasattr(self, 'logo_label') and obj == self.logo_label:
            if event.type() == event.Type.Enter:
                # Mouse entered - fade to full opacity
                self._setup_logo_fade_animation(0.7, 1.0)
            elif event.type() == event.Type.Leave:
                # Mouse left - fade back to 70%
                self._setup_logo_fade_animation(1.0, 0.7)
        
        return super().eventFilter(obj, event)

    def _setup_logo_fade_animation(self, start_value, end_value):
        """Setup and start logo fade animation."""
        self.logo_fade_animation.setStartValue(start_value)
        self.logo_fade_animation.setEndValue(end_value)
        self.logo_fade_animation.start()

    def animate_startup(self):
        """Add subtle startup animation using a simple fade approach."""
        # Instead of QGraphicsOpacityEffect which causes QPainter conflicts,
        # use a simple timer-based approach or skip animation entirely
        # to avoid rendering issues
        
        # Simple approach: just show the widget normally
        # The fade effect was causing too many QPainter conflicts
        pass

    def start_fade_in(self):
        """Start the fade-in animation."""
        # Animation removed to prevent QPainter conflicts
        pass

    def on_splitter_moved(self, pos, index):
        """Handle splitter movement to make dropdowns responsive."""
        # Force update of tree widget layout when splitter moves
        self.category_tree.updateGeometry()
        self.category_tree.update()

    def on_category_selected(self, item, column):
        """Handle category selection."""
        if item.parent():  # This is a subcategory
            category = item.parent().text(0)
            subcategory = item.text(0)
            self.load_samples(category, subcategory)

    def _create_empty_state_item(self, text, icon, item_type, tooltip_text):
        """Create a styled empty state or help item that is unselectable and visually distinct."""
        item = ListWidgetItem(text)
        item.setIcon(icon.icon())
        item.setData(Qt.ItemDataRole.UserRole, {item_type: True})
        
        # Make item unselectable and visually distinct
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        
        # Set different colors for different item types
        if item_type == "empty_state":
            item.setForeground(QColor(150, 150, 150))  # Gray text
        elif item_type == "help_message":
            item.setForeground(QColor(120, 120, 120))  # Darker gray text
        
        item.setToolTip(tooltip_text)
        return item

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
        """Add empty state and help items to the sample list."""
        empty_item = self._create_empty_state_item(
            f"No samples in {category} > {subcategory}",
            MaterialIcon('ADD', 16),
            "empty_state",
            "Click the + button below to add samples to this category"
        )
        self.sample_list.addItem(empty_item)
        
        help_item = self._create_empty_state_item(
            "Click the + button to add audio files",
            MaterialIcon('INFO', 16),
            "help_message",
            "Supported formats: WAV, MP3, FLAC, AIFF, OGG"
        )
        self.sample_list.addItem(help_item)

    def _populate_sample_list(self, samples):
        """Populate the sample list with sample items."""
        for sample in samples:
            item = self._create_sample_list_item(sample)
            self.sample_list.addItem(item)

    def _create_sample_list_item(self, sample):
        """Create a list widget item for a sample."""
        # Extract and normalize sample metadata
        file_name = self._get_sample_filename(sample)
        bpm = self._normalize_numeric_value(sample.get("bpm", 0))
        key = self._normalize_key_value(sample.get("key", "Unknown"))
        duration = self._normalize_numeric_value(sample.get("duration", 0))
        sample_type = sample.get("sample_type", "unknown")
        detected_category = sample.get("category", "unknown")
        
        # Create display text and item
        display_text = self._create_sample_display_text(file_name, bpm, key, duration, sample_type)
        item = ListWidgetItem(display_text)
        
        # Set icon and data
        item.setIcon(self._get_sample_icon(detected_category, sample_type))
        item.setData(Qt.ItemDataRole.UserRole, sample)
        
        # Set tooltip
        tooltip = self._create_sample_tooltip(file_name, detected_category, sample_type, duration, bpm, key)
        item.setToolTip(tooltip)
        
        return item

    def _get_sample_filename(self, sample):
        """Extract filename from sample data with fallback."""
        file_name = sample.get("file_name", "Unknown")
        if file_name == "Unknown" and "file_path" in sample:
            file_name = Path(sample["file_path"]).name
        return file_name

    def _normalize_numeric_value(self, value):
        """Normalize numeric values with proper type conversion."""
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0
        return value or 0

    def _normalize_key_value(self, key):
        """Normalize key value."""
        return "Unknown" if not key or key == "unknown" else key

    def _create_sample_display_text(self, file_name, bpm, key, duration, sample_type):
        """Create display text for sample list item."""
        display_parts = [file_name]
        
        if bpm > 0:
            display_parts.append(f"{bpm:.0f} BPM")
        
        if key != "Unknown":
            display_parts.append(key)
        
        if duration > 0:
            display_parts.append(f"{duration:.1f}s")
        
        if sample_type != "unknown":
            display_parts.append(f"({sample_type})")
        
        return " • ".join(display_parts)

    def _get_sample_icon(self, detected_category, sample_type):
        """Get appropriate icon for sample based on category and type."""
        category_lower = detected_category.lower()
        
        if category_lower == "drums" or sample_type == "drums":
            return MaterialIcon('DRUMS', 16).icon()
        elif category_lower == "bass" or sample_type == "bass":
            return MaterialIcon('MUSIC', 16).icon()
        elif category_lower == "melodic" or sample_type == "melodic":
            return MaterialIcon('PIANO', 16).icon()
        elif category_lower == "fx" or sample_type == "fx":
            return MaterialIcon('EFFECTS', 16).icon()
        elif category_lower == "vocals" or sample_type == "vocals":
            return MaterialIcon('VOCALS', 16).icon()
        else:
            return MaterialIcon('AUDIO_FILE', 16).icon()

    def _create_sample_tooltip(self, file_name, detected_category, sample_type, duration, bpm, key):
        """Create detailed tooltip for sample."""
        tooltip_parts = [
            f"File: {file_name}",
            f"Category: {detected_category.title() if detected_category != 'unknown' else 'Unknown'}",
            f"Type: {sample_type.title() if sample_type != 'unknown' else 'Unknown'}",
            f"Duration: {duration:.1f}s" if duration > 0 else "Duration: Unknown",
        ]
        
        if bpm > 0:
            tooltip_parts.append(f"BPM: {bpm:.1f}")
        
        if key != "Unknown":
            tooltip_parts.append(f"Key: {key}")
        
        return "\n".join(tooltip_parts)

    def on_sample_selected(self, item):
        """Handle sample selection."""
        sample_data = item.data(Qt.ItemDataRole.UserRole)
        
        # Check if this is an empty state or help message (should not happen due to unselectable flags)
        if sample_data and (sample_data.get("empty_state") or sample_data.get("help_message")):
            # Don't enable buttons for empty state items
            self.analyze_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            # Clear selection to prevent confusion
            self.sample_list.clearSelection()
            return
        
        # Enable buttons for real samples
        self.analyze_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        
        # Load sample for audio preview
        if sample_data and "file_path" in sample_data:
            try:
                file_path = sample_data["file_path"]
                self.playback_controls.load_sample(file_path)
                
                # Check for potential low frequency playback issues
                self._check_low_frequency_playback_issues(file_path, sample_data)
                
            except Exception as e:
                self._add_notification(
                    "Playback Error",
                    f"Failed to load sample for playback: {str(e)}",
                    "error"
                )

    def _check_low_frequency_playback_issues(self, file_path, sample_data):
        """Check for potential low frequency playback issues and provide recommendations."""
        try:
            # Get audio diagnostics
            diagnosis = self.audio_player.diagnose_playback_issues(file_path)
            
            # Check if this is a bass sample
            if diagnosis.get("sample_type") == "bass_heavy":
                # Check for common issues with bass samples
                issues = diagnosis.get("issues", [])
                recommendations = diagnosis.get("recommendations", [])
                
                if issues or recommendations:
                    # Create a helpful notification for bass samples
                    message_parts = []
                    
                    if issues:
                        message_parts.append("Potential issues detected:")
                        message_parts.extend([f"• {issue}" for issue in issues[:3]])
                    
                    if recommendations:
                        if message_parts:
                            message_parts.append("")
                        message_parts.append("Recommendations:")
                        message_parts.extend([f"• {rec}" for rec in recommendations[:3]])
                    
                    if message_parts:
                        self._add_notification(
                            "Bass Sample Detected",
                            "\n".join(message_parts),
                            "info"
                        )
            
            # Check for device-specific issues
            device_info = diagnosis.get("device_info", {})
            if "error" in device_info:
                self._add_notification(
                    "Audio Device Issue",
                    f"Audio device problem detected: {device_info['error']}",
                    "warning"
                )
            elif device_info.get("bass_recommendation"):
                self._add_notification(
                    "Audio Setup Tip",
                    device_info["bass_recommendation"],
                    "info"
                )
                
        except Exception as e:
            logger.warning(f"Failed to check low frequency playback issues: {e}")
    
    def _show_audio_diagnostics(self):
        """Show detailed audio diagnostics dialog."""
        try:
            # Get current sample if any
            current_file = None
            if current_item := self.sample_list.currentItem():
                sample_data = current_item.data(Qt.ItemDataRole.UserRole)
                if sample_data and "file_path" in sample_data:
                    current_file = sample_data["file_path"]
            
            # Get diagnostics
            diagnosis = self.audio_player.diagnose_playback_issues(current_file)
            device_info = self.audio_player.get_audio_device_info()
            
            # Create diagnostic dialog
            dialog = AudioDiagnosticsDialog(diagnosis, device_info, self)
            dialog.exec()
            
        except Exception as e:
            self._add_notification(
                "Diagnostics Error",
                f"Failed to show audio diagnostics: {str(e)}",
                "error"
            )

    def on_sample_double_clicked(self, item):
        """Handle sample double-click to play the sample."""
        sample_data = item.data(Qt.ItemDataRole.UserRole)
        
        # Check if this is an empty state or help message
        if not sample_data or sample_data.get("empty_state") or sample_data.get("help_message"):
            return
        
        # Load and play sample
        if "file_path" in sample_data:
            try:
                file_path = sample_data["file_path"]
                self.playback_controls.load_sample(file_path)
                # Automatically start playing after loading
                QTimer.singleShot(100, self.playback_controls.toggle_playback)
                
                # Add notification
                self._add_notification(
                    "Sample Playing", 
                    f"Playing: {sample_data.get('file_name', 'Unknown')}", 
                    "info"
                )
            except Exception as e:
                self._add_notification(
                    "Playback Error",
                    f"Failed to play {sample_data.get('file_name', 'sample')}: {str(e)}",
                    "error"
                )

    def get_current_category_subcategory(self):
        """Get the current category and subcategory from the tree widget.
        
        Returns:
            tuple: (category, subcategory) if valid selection, (None, None) otherwise
        """
        if (category_item := self.category_tree.currentItem()) and category_item.parent():
            category = category_item.parent().text(0)
            subcategory = category_item.text(0)
            return category, subcategory
        return None, None

    def add_sample(self):
        """Add a new sample to the library."""
        auto_organize = self._get_organization_choice()
        if auto_organize is None:  # User cancelled
            return
        
        if not auto_organize:
            manual_category, manual_subcategory = self._get_manual_category_selection()
            if not manual_category:  # User needs to select category
                return
        else:
            manual_category = manual_subcategory = None
        
        files = self._get_files_to_add(auto_organize, manual_category, manual_subcategory)
        if not files:
            return
        
        self._process_selected_files(files, auto_organize, manual_category, manual_subcategory)
    
    def _get_organization_choice(self):
        """Ask user if they want automatic organization. Returns True/False/None(cancelled)."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Add Samples")
        msg_box.setText("Would you like to auto-organize the samples?")
        msg_box.setInformativeText(
            "• Auto-organize: Analyzes files and places them automatically based on content\n"
            "• Manual: You manually choose the category/subcategory"
        )
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No | 
            QMessageBox.StandardButton.Cancel
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        # Set button text
        msg_box.button(QMessageBox.StandardButton.Yes).setText("Auto-organize")
        msg_box.button(QMessageBox.StandardButton.No).setText("Manual")
        msg_box.button(QMessageBox.StandardButton.Cancel).setText("Cancel")
        
        reply = msg_box.exec()
        return None if reply == QMessageBox.StandardButton.Cancel else reply == QMessageBox.StandardButton.Yes
    
    def _get_manual_category_selection(self):
        """Get manual category selection. Returns (category, subcategory) or (None, None)."""
        if not (current_item := self.category_tree.currentItem()):
            self._add_notification(
                "No Category Selected",
                "Please select a category/subcategory first",
                "warning"
            )
            return None, None
        
        # Determine category and subcategory
        if current_item.parent():
            # Subcategory selected
            return current_item.parent().text(0), current_item.text(0)
        
        # Only category selected, ask user to select subcategory
        self._add_notification(
            "Select Subcategory",
            "Please select a specific subcategory to add samples to",
            "warning"
        )
        return None, None
    
    def _get_files_to_add(self, auto_organize, manual_category, manual_subcategory):
        """Show file dialog and return selected files."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.wav *.mp3 *.flac *.aiff *.m4a *.ogg)")
        
        title = "Add Samples (Auto-organize)" if auto_organize else f"Add Samples to {manual_category} > {manual_subcategory}"
        file_dialog.setWindowTitle(title)
        
        return file_dialog.selectedFiles() if file_dialog.exec() else []
    
    def _process_selected_files(self, files, auto_organize, manual_category, manual_subcategory):
        """Process the selected files and add them to the library."""
        import shutil
        from pathlib import Path
        
        successful_adds = 0
        organized_samples = {}  # Track where samples were organized
        
        for i, file_path in enumerate(files):
            try:
                source_path = Path(file_path)
                
                if auto_organize:
                    category, subcategory, analysis_result = self._auto_organize_sample(source_path, i, len(files))
                    if category:
                        org_key = f"{category} > {subcategory}"
                        organized_samples.setdefault(org_key, []).append(source_path.name)
                else:
                    category, subcategory = manual_category, manual_subcategory
                    analysis_result = None
                
                if category and self._copy_and_analyze_sample(source_path, category, subcategory, analysis_result, auto_organize, i, len(files)):
                    successful_adds += 1
                    
            except Exception as e:
                # Start flashing for errors
                self._start_notification_flash()
                self._add_notification(
                    "Import Error",
                    f"Failed to add {Path(file_path).name}: {str(e)}",
                    "error"
                )
        
        self._show_completion_message(successful_adds, auto_organize, organized_samples, manual_category, manual_subcategory)
        self._refresh_ui(auto_organize, manual_category, manual_subcategory)
    
    def _auto_organize_sample(self, source_path, current_index, total_files):
        """Auto-organize a sample by analyzing it. Returns (category, subcategory, analysis_result)."""
        self._add_notification(
            "Auto-organizing",
            f"Analyzing {source_path.name} for auto-organization ({current_index+1}/{total_files})",
            "info"
        )
        
        # Analyze the sample to determine its category
        try:
            analysis_result = self.analyzer.analyze_sample(str(source_path))
        except Exception as e:
            # Start flashing for analysis errors
            self._start_notification_flash()
            self._add_notification(
                "Analysis Error",
                f"Failed to analyze {source_path.name}: {str(e)}",
                "error"
            )
            # Use default values if analysis fails
            analysis_result = {
                "category": "Unknown",
                "sample_type": "unknown",
                "bpm": 0,
                "key": "Unknown",
                "duration": 0,
                "file_name": source_path.name,
                "file_path": str(source_path)
            }
        
        return self._determine_category_from_analysis(analysis_result) + (analysis_result,)
    
    def _determine_category_from_analysis(self, analysis_result):
        """Determine category and subcategory from analysis result with improved logic."""
        detected_category = analysis_result.get("category", "Unknown").title()
        sample_type = analysis_result.get("sample_type", "unknown")
        file_name = analysis_result.get("file_name", "").lower()
        file_path = analysis_result.get("file_path", "").lower()
        duration = analysis_result.get("duration", 0)
        bpm = analysis_result.get("bpm", 0)
        
        # Get characteristics for better classification
        characteristics = analysis_result.get("characteristics", {})
        spectral_centroid = characteristics.get("spectral_centroid", 0)
        zero_crossing_rate = characteristics.get("zero_crossing_rate", 0)
        
        # Priority 1: Check for explicit filename keywords
        if category_result := self._classify_by_keywords(file_path):
            return category_result
        
        # Priority 2: Use detected category from analysis
        if category_result := self._classify_by_detected_category(detected_category, spectral_centroid, zero_crossing_rate, duration, bpm):
            return category_result
        
        # Priority 3: Fallback based on audio characteristics
        if duration > 0:
            return self._classify_by_audio_characteristics(duration, spectral_centroid, bpm)
        
        # Ultimate fallback
        return "Melodic", "Melodic Loops"

    def _classify_by_keywords(self, file_path):
        """Classify sample based on filename keywords."""
        # Enhanced drum type detection with more keywords
        drum_keywords = {
            'kick': ['kick', 'bd', 'bassdrum', 'bass drum'],
            'snare': ['snare', 'sd', 'snr'],
            'clap': ['clap', 'handclap', 'hand clap'],
            'hihat': ['hat', 'hh', 'hihat', 'hi-hat', 'hi hat'],
            'cymbal': ['cymbal', 'crash', 'ride', 'splash'],
            'percussion': ['perc', 'shaker', 'tambourine', 'conga', 'bongo', 'cowbell']
        }
        
        for drum_type, keywords in drum_keywords.items():
            if any(keyword in file_path for keyword in keywords):
                subcategory_map = {
                    'kick': 'Kicks',
                    'snare': 'Snares', 
                    'clap': 'Claps',
                    'hihat': 'Hi-Hats',
                    'cymbal': 'Cymbals',
                    'percussion': 'Percussion'
                }
                return "Drums", subcategory_map[drum_type]
        
        # Check for melodic loops specifically
        if any(keyword in file_path for keyword in ['melodic loop', 'melody loop', 'melodic', 'hook', 'verse', 'bridge']):
            if any(keyword in file_path for keyword in ['piano', 'key', 'keys']):
                return "Melodic", "Keys"
            elif any(keyword in file_path for keyword in ['synth', 'lead']):
                return "Melodic", "Synth Leads"
            elif any(keyword in file_path for keyword in ['pad', 'string']):
                return "Melodic", "Pads"
            else:
                return "Melodic", "Melodic Loops"
        
        # Enhanced bass detection
        if any(keyword in file_path for keyword in ['bass', '808', 'sub', 'low end']):
            if '808' in file_path or 'eight' in file_path:
                return "Bass", "808"
            elif any(keyword in file_path for keyword in ['synth bass', 'synthbass']):
                return "Bass", "Synth Bass"
            elif any(keyword in file_path for keyword in ['electric bass', 'e-bass']):
                return "Bass", "Electric Bass"
            elif any(keyword in file_path for keyword in ['bass loop', 'bassloop']):
                return "Bass", "Bass Loops"
            else:
                return "Bass", "Bass Loops"
        
        # Enhanced vocal detection
        if any(keyword in file_path for keyword in ['vocal', 'voice', 'chop', 'vox']):
            if any(keyword in file_path for keyword in ['chop', 'cut', 'vocal chop']):
                return "Vocals", "Chops"
            elif any(keyword in file_path for keyword in ['phrase', 'word', 'lyric']):
                return "Vocals", "Phrases"
            elif any(keyword in file_path for keyword in ['one shot', 'oneshot', 'hit']):
                return "Vocals", "One-Shots"
            else:
                return "Vocals", "Vocal Loops"
        
        # Enhanced FX detection
        if any(keyword in file_path for keyword in ['fx', 'effect', 'sweep', 'riser', 'impact', 'ambient', 'foley']):
            if any(keyword in file_path for keyword in ['riser', 'sweep', 'uplifter']):
                return "FX", "Risers"
            elif any(keyword in file_path for keyword in ['impact', 'hit', 'stab']):
                return "FX", "Impacts"
            elif any(keyword in file_path for keyword in ['ambient', 'atmosphere', 'texture']):
                return "FX", "Ambient"
            elif any(keyword in file_path for keyword in ['foley', 'sound effect']):
                return "FX", "Foley"
            elif any(keyword in file_path for keyword in ['downlifter', 'down']):
                return "FX", "Downlifters"
            else:
                return "FX", "Impacts"
        
        return None

    def _classify_by_detected_category(self, detected_category, spectral_centroid, zero_crossing_rate, duration, bpm):
        """Classify sample based on detected category from analysis."""
        if detected_category == "Drums":
            # Use spectral analysis to determine drum type
            if spectral_centroid < 800:
                return "Drums", "Kicks"
            elif spectral_centroid > 4000:
                return "Drums", "Hi-Hats"
            elif zero_crossing_rate > 0.1:
                return "Drums", "Snares"
            else:
                return "Drums", "Full Loops"
        elif detected_category == "Bass":
            return "Bass", "Bass Loops"
        elif detected_category == "Melodic":
            # Use duration and BPM to classify melodic content
            if duration > 8.0:
                return "Melodic", "Melodic Loops"
            elif spectral_centroid < 1500:
                return "Melodic", "Keys"
            elif spectral_centroid > 3000:
                return "Melodic", "Synth Leads"
            else:
                return "Melodic", "Melodic Loops"
        elif detected_category == "FX":
            return "FX", "Impacts"
        elif detected_category == "Vocals":
            return "Vocals", "Vocal Loops"
        
        return None

    def _classify_by_audio_characteristics(self, duration, spectral_centroid, bpm):
        """Classify sample based on audio characteristics."""
        if duration < 1.0:  # Very short samples
            if spectral_centroid < 800:
                return "Drums", "Kicks"
            elif spectral_centroid > 4000:
                return "FX", "Impacts"
            else:
                return "Drums", "Snares"
        elif duration > 8.0:  # Long samples are likely loops
            if spectral_centroid < 1000:
                return "Bass", "Bass Loops"
            elif bpm > 0:
                return "Melodic", "Melodic Loops"
            else:
                return "FX", "Ambient"
        else:  # Medium length samples
            if bpm > 0 and spectral_centroid > 1000:
                return "Melodic", "Melodic Loops"
            elif spectral_centroid < 800:
                return "Bass", "Bass Loops"
            else:
                return "Melodic", "Melodic Loops"

    def _copy_and_analyze_sample(self, source_path, category, subcategory, analysis_result, auto_organize, current_index, total_files):
        """Copy sample to target directory and analyze if needed. Returns True if successful."""
        import shutil
        from pathlib import Path
        
        # Auto-create subcategory if enabled and doesn't exist
        if self.auto_create_subcategories:
            target_dir = Path("samples") / category / subcategory
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                self._add_notification(
                    "Created Subcategory",
                    f"Auto-created: {category} > {subcategory}",
                    "info"
                )
        
        target_dir = Path("samples") / category / subcategory
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / source_path.name
        
        # Check if file already exists (case-insensitive)
        existing_files = [f for f in target_dir.iterdir() if f.is_file()]
        lower_target_name = source_path.name.lower()
        for f in existing_files:
            if f.name.lower() == lower_target_name:
                self._add_notification(
                    "File Exists",
                    f"{source_path.name} already exists in {category} > {subcategory} (case-insensitive match: {f.name}), skipping",
                    "warning"
                )
                return False
        
        # Copy file
        try:
            shutil.copy2(source_path, target_path)
        except Exception as e:
            self._add_notification(
                "Copy Failed",
                f"Failed to copy {source_path.name} to {category} > {subcategory}: {e}",
                "error"
            )
            return False
        # Analyze the sample (or use existing analysis for auto-organize)
        if auto_organize and analysis_result:
            # Save the analysis result we already have
            try:
                relative_path = str(target_path.relative_to(Path("samples")))
                self.sample_manager.sample_cache[relative_path] = analysis_result
                self.sample_manager.save_cache()
            except Exception as e:
                logger.warning(f"Failed to save analysis cache: {e}")
        else:
            self._add_notification(
                "Processing",
                f"Analyzing {source_path.name} ({current_index+1}/{total_files})",
                "info"
            )
            self.sample_manager.analyze_sample(str(target_path))
        
        return True
    
    def _show_completion_message(self, successful_adds, auto_organize, organized_samples, manual_category, manual_subcategory):
        """Show completion message based on operation type."""
        if successful_adds <= 0:
            return
        
        if auto_organize:
            if organized_samples:
                org_summary = [f"{location}: {len(files)} sample(s)" for location, files in organized_samples.items()]
                summary_text = f"Successfully organized {successful_adds} sample(s):\n" + "\n".join(org_summary[:3])
                if len(org_summary) > 3:
                    summary_text += f"\n... and {len(org_summary) - 3} more"
            else:
                summary_text = f"Successfully organized {successful_adds} sample(s)"
            
            self._add_notification(
                "Auto-organization Complete",
                summary_text,
                "success"
            )
        else:
            self._add_notification(
                "Samples Added",
                f"Successfully added {successful_adds} sample(s) to {manual_category} > {manual_subcategory}",
                "success"
            )
    
    def _refresh_ui(self, auto_organize, manual_category, manual_subcategory):
        """Refresh the UI after adding samples."""
        self.populate_categories()
        if not auto_organize and manual_category and manual_subcategory:
            self.load_samples(manual_category, manual_subcategory)

    def analyze_sample(self):
        """Analyze the selected sample."""
        if not (current_item := self.sample_list.currentItem()):
            return
            
        sample_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not sample_data or sample_data.get("empty_state") or sample_data.get("help_message"):
            return
            
        # Get the file path for analysis
        file_path = sample_data.get("file_path")
        if not file_path:
            return
            
        # Show info that analysis is starting
        self._add_notification(
            "Analysis Started",
            f"Analyzing {sample_data.get('file_name', 'sample')}...",
            "info"
        )
        
        # Perform analysis using universal analyzer
        result = self.sample_manager.analyze_sample(file_path)
        
        # Show analysis results in dialog
        try:
            dialog = AnalysisResultsDialog(result, self)
            dialog.exec()
        except Exception as e:
            self._add_notification(
                "Dialog Error",
                f"Failed to show analysis results: {str(e)}",
                "error"
            )
        
        # Refresh the sample list to show updated metadata
        if (category_subcategory := self.get_current_category_subcategory()) != (None, None):
            category, subcategory = category_subcategory
            self.load_samples(category, subcategory)

    def remove_sample(self):
        """Remove the selected sample."""
        if not (current_item := self.sample_list.currentItem()):
            return
            
        sample_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not sample_data or sample_data.get("empty_state") or sample_data.get("help_message"):
            return
            
        # Get the file path for removal
        file_path = sample_data.get("file_path")
        if not file_path:
            return
        
        # Check if this is a file in our samples directory
        try:
            samples_path = Path("samples")
            file_path_obj = Path(file_path)
            
            # Try to get relative path to samples directory
            if samples_path.exists() and file_path_obj.exists():
                try:
                    relative_path = file_path_obj.relative_to(samples_path.resolve())
                    # This is a file in our samples directory - we can remove it
                    self.sample_manager.remove_sample(file_path)
                    
                    # Also delete the actual file
                    if file_path_obj.exists():
                        file_path_obj.unlink()
                        self._add_notification(
                            "Sample Removed",
                            f"Removed {file_path_obj.name} from library and disk",
                            "success"
                        )
                    
                except ValueError:
                    # File is not in samples directory - just remove from cache
                    self._add_notification(
                        "External File",
                        f"Cannot remove external file {file_path_obj.name}. Only files in the samples directory can be removed.",
                        "warning"
                    )
                    return
            else:
                self._add_notification(
                    "File Not Found",
                    f"Could not locate file {file_path}",
                    "error"
                )
                return
                
        except Exception as e:
            self._add_notification(
                "Remove Error", 
                f"Failed to remove sample: {str(e)}",
                "error"
            )
            return
        
        # Reload the current category
        if (category_subcategory := self.get_current_category_subcategory()) != (None, None):
            category, subcategory = category_subcategory
            self.load_samples(category, subcategory)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for spacebar play/pause and arrow key navigation."""
        # Spacebar for play/pause
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.activated.connect(self.toggle_playback)
        
        # Arrow keys for sample navigation
        self.up_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.up_shortcut.activated.connect(self.navigate_sample_up)
        
        self.down_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.down_shortcut.activated.connect(self.navigate_sample_down)

    def toggle_playback(self):
        """Toggle playback when spacebar is pressed."""
        if hasattr(self, 'playback_controls') and self.playback_controls.current_sample_path:
            self.playback_controls.toggle_playback()
    
    def navigate_sample_up(self):
        """Navigate to the previous sample and preview it."""
        current_row = self.sample_list.currentRow()
        if current_row > 0:
            self.sample_list.setCurrentRow(current_row - 1)
            self._preview_current_sample()
    
    def navigate_sample_down(self):
        """Navigate to the next sample and preview it."""
        current_row = self.sample_list.currentRow()
        if current_row < self.sample_list.count() - 1:
            self.sample_list.setCurrentRow(current_row + 1)
            self._preview_current_sample()
    
    def _preview_current_sample(self):
        """Preview the currently selected sample."""
        current_item = self.sample_list.currentItem()
        if not current_item:
            return
            
        sample_data = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Check if this is an empty state or help message
        if not sample_data or sample_data.get("empty_state") or sample_data.get("help_message"):
            return
        
        # Load and play sample
        if "file_path" in sample_data:
            try:
                file_path = sample_data["file_path"]
                self.playback_controls.load_sample(file_path)
                # Automatically start playing after loading
                QTimer.singleShot(100, self.playback_controls.toggle_playback)
                
                # Add notification
                self._add_notification(
                    "Sample Preview", 
                    f"Previewing: {sample_data.get('file_name', 'Unknown')}", 
                    "info"
                )
            except Exception as e:
                self._add_notification(
                    "Preview Error",
                    f"Failed to preview {sample_data.get('file_name', 'sample')}: {str(e)}",
                    "error"
                )

    def _auto_create_missing_subcategories(self):
        """Auto-create missing subcategories based on common sample types."""
        # Define the complete category structure
        complete_structure = {
            "Bass": ["808", "Bass Loops", "Electric Bass", "Synth Bass"],
            "Drums": ["Cymbals", "Full Loops", "Hi-Hats", "Kicks", "Percussion", "Snares", "Claps"],
            "FX": ["Ambient", "Downlifters", "Foley", "Impacts", "Risers"],
            "Melodic": ["Keys", "Melodic Loops", "Pads", "Plucks", "Synth Leads"],
            "Vocals": ["Chops", "One-Shots", "Phrases", "Vocal Loops"]
        }
        
        created_subcategories = []
        
        for category, subcategories in complete_structure.items():
            category_path = Path("samples") / category
            category_path.mkdir(parents=True, exist_ok=True)
            
            for subcategory in subcategories:
                subcategory_path = category_path / subcategory
                if not subcategory_path.exists():
                    subcategory_path.mkdir(parents=True, exist_ok=True)
                    created_subcategories.append(f"{category} > {subcategory}")
        
        return created_subcategories

    def _show_auto_created_subcategories_notification(self, created_subcategories):
        """Show notification about auto-created subcategories."""
        if created_subcategories:
            subcategory_list = "\n".join(f"• {sub}" for sub in created_subcategories[:5])
            if len(created_subcategories) > 5:
                subcategory_list += f"\n... and {len(created_subcategories) - 5} more"
            
            # Add to notification window instead of info bar
            self._add_notification(
                "Auto-Created Categories",
                f"Created {len(created_subcategories)} missing subcategories:\n{subcategory_list}",
                "success"
            )

    def _create_section_label(self, text, margin_top=10):
        """Create a styled section label for settings dialog."""
        section_label = BodyLabel(text)
        section_label.setFont(get_font_manager().get_header_font(14))
        section_label.setStyleSheet(f"color: rgba(94, 129, 172, 1.0); font-weight: bold; margin-top: {margin_top}px;")
        return section_label

    def _show_settings_dialog(self):
        """Show settings dialog with database management options."""
        from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QCheckBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumSize(400, 300)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = TitleLabel("WAVFin Settings")
        title.setFont(get_font_manager().get_header_font(16))
        layout.addWidget(title)
        
        # Database Management Section
        layout.addWidget(self._create_section_label("Database Management"))
        
        # Reset database button
        reset_button = PushButton("Reset Sample Database")
        reset_button.setToolTip("Clear all cached sample analysis data and force re-analysis with improved categorization")
        reset_button.clicked.connect(lambda: self._reset_sample_database(dialog))
        layout.addWidget(reset_button)
        
        # Info about reset
        reset_info = BodyLabel(
            "This will clear all cached sample analysis data, allowing you to re-import "
            "samples with the latest categorization improvements. Your sample files will "
            "not be deleted, only the analysis cache."
        )
        reset_info.setWordWrap(True)
        reset_info.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 10px;")
        layout.addWidget(reset_info)
        
        # Auto-categorization Section
        layout.addWidget(self._create_section_label("Auto-Categorization", 15))
        
        # Auto-create subcategories checkbox
        auto_create_checkbox = QCheckBox("Auto-create missing subcategories")
        auto_create_checkbox.setChecked(self.auto_create_subcategories)
        auto_create_checkbox.setToolTip("Automatically create missing subcategories like 'Claps' when adding samples")
        
        # Connect to update the persistent setting
        auto_create_checkbox.toggled.connect(lambda checked: setattr(self, 'auto_create_subcategories', checked))
        
        layout.addWidget(auto_create_checkbox)
        
        # Create missing subcategories now button
        create_now_button = PushButton("Create Missing Subcategories Now")
        create_now_button.setToolTip("Manually create any missing standard subcategories")
        create_now_button.clicked.connect(self._create_missing_subcategories_now)
        layout.addWidget(create_now_button)
        
        # Audio System Section
        layout.addWidget(self._create_section_label("Audio System", 15))
        
        # Audio diagnostics button
        diagnostics_button = PushButton("Audio Diagnostics")
        diagnostics_button.setToolTip("Check audio system configuration and troubleshoot playback issues")
        diagnostics_button.clicked.connect(self._show_audio_diagnostics)
        layout.addWidget(diagnostics_button)
        
        # Info about audio diagnostics
        diagnostics_info = BodyLabel(
            "Use this to troubleshoot audio playback issues, especially with low frequency "
            "samples like 808s and kicks. The diagnostics will check your audio device "
            "configuration and provide recommendations for optimal bass reproduction."
        )
        diagnostics_info.setWordWrap(True)
        diagnostics_info.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 10px;")
        layout.addWidget(diagnostics_info)
        
        layout.addStretch()
        
        # Close button
        close_button = PushButton("Close")
        close_button.clicked.connect(dialog.accept)
        close_button.setFixedWidth(100)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        dialog.exec()

    def _reset_sample_database(self, parent_dialog):
        """Reset the sample database by clearing the cache."""
        if not self._confirm_database_reset(parent_dialog):
            return
        
        try:
            self._perform_database_reset()
            self._show_reset_success(parent_dialog)
        except Exception as e:
            self._show_reset_error(e)

    def _confirm_database_reset(self, parent_dialog):
        """Confirm the database reset action."""
        msg_box = QMessageBox(parent_dialog)
        msg_box.setWindowTitle("Reset Sample Database")
        msg_box.setText("Are you sure you want to reset the sample database?")
        msg_box.setInformativeText(
            "This will:\n"
            "• Clear all cached sample analysis data\n"
            "• Force re-analysis of all samples when accessed\n"
            "• Apply the latest categorization improvements\n"
            "• NOT delete your actual sample files\n\n"
            "This action cannot be undone."
        )
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        return msg_box.exec() == QMessageBox.StandardButton.Yes

    def _perform_database_reset(self):
        """Perform the actual database reset."""
        self.sample_manager.sample_cache.clear()
        self.sample_manager.save_cache()
        self.sample_list.clear()

    def _show_reset_success(self, parent_dialog):
        """Show success message and close dialog."""
        self._add_notification(
            "Database Reset",
            "Sample database has been reset. Re-import samples to see improved categorization.",
            "success"
        )
        parent_dialog.accept()
        logger.info("Sample database reset successfully")

    def _show_reset_error(self, error):
        """Show error message for reset failure."""
        logger.error(f"Error resetting database: {error}")
        self._add_notification(
            "Reset Failed",
            f"Failed to reset database: {str(error)}",
            "error"
        )

    def _create_missing_subcategories_now(self):
        """Manually create missing subcategories."""
        if created_subcategories := self._auto_create_missing_subcategories():
            self._show_auto_created_subcategories_notification(created_subcategories)
            # Refresh the category tree to show new subcategories
            self.populate_categories()
        else:
            self._add_notification(
                "No Missing Categories",
                "All standard subcategories already exist.",
                "info"
            )

    def _apply_custom_scrollbar_style(self, widget):
        """Apply custom Nord blue scrollbar styling to a widget."""
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
                background: rgba(94, 129, 172, 1.0);
                outline: none;
            }
            
            QScrollBar::handle:vertical:pressed {
                background: rgba(81, 92, 109, 1.0);
                outline: none;
            }
            
            QScrollBar::handle:vertical:focus {
                outline: none;
            }
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
                border: none;
                outline: none;
            }
            
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
                outline: none;
            }
            
            QScrollBar:horizontal {
                background: rgba(46, 52, 64, 0.3);
                height: 12px;
                border-radius: 6px;
                margin: 0px;
                border: none;
                outline: none;
            }
            
            QScrollBar::handle:horizontal {
                background: rgba(94, 129, 172, 0.8);
                border-radius: 6px;
                min-width: 30px;
                margin: 2px;
                border: none;
                outline: none;
            }
            
            QScrollBar::handle:horizontal:hover {
                background: rgba(94, 129, 172, 1.0);
                outline: none;
            }
            
            QScrollBar::handle:horizontal:pressed {
                background: rgba(81, 92, 109, 1.0);
                outline: none;
            }
            
            QScrollBar::handle:horizontal:focus {
                outline: none;
            }
            
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
                border: none;
                outline: none;
            }
            
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
                border: none;
                outline: none;
            }
        """
        
        # Apply the style to the widget
        current_style = widget.styleSheet()
        widget.setStyleSheet(current_style + scrollbar_style)

    def _start_notification_flash(self):
        """Start flashing the notification icon red."""
        self.has_notifications = True
        self.notification_flash_state = False
        self.notification_timer.start(500)  # Flash every 500ms
    
    def _stop_notification_flash(self):
        """Stop flashing the notification icon."""
        self.has_notifications = False
        self.notification_timer.stop()
        # Reset to normal blue color
        self._set_info_button_style(False)
    
    def _toggle_notification_flash(self):
        """Toggle the notification flash state."""
        if self.has_notifications:
            self.notification_flash_state = not self.notification_flash_state
            self._set_info_button_style(self.notification_flash_state)
    
    def _set_info_button_style(self, is_red):
        """Set the info button style - red for notifications, blue for normal."""
        if is_red:
            # Nord red color for notifications
            style = """
                ToolButton {
                    border-radius: 12px;
                    border: 2px solid transparent;
                    background-color: rgba(191, 97, 106, 0.8);
                    color: white;
                    outline: none;
                }
                ToolButton:hover {
                    background-color: rgba(191, 97, 106, 1.0);
                    border: 2px solid rgba(191, 97, 106, 0.3);
                    outline: none;
                }
                ToolButton:pressed {
                    background-color: rgba(191, 97, 106, 0.6);
                    outline: none;
                }
                ToolButton:focus {
                    outline: none;
                }
            """
        else:
            # Normal Nord blue color
            style = """
                ToolButton {
                    border-radius: 12px;
                    border: 2px solid transparent;
                    background-color: rgba(94, 129, 172, 0.8);
                    color: white;
                    outline: none;
                }
                ToolButton:hover {
                    background-color: rgba(94, 129, 172, 1.0);
                    border: 2px solid rgba(94, 129, 172, 0.3);
                    outline: none;
                }
                ToolButton:pressed {
                    background-color: rgba(94, 129, 172, 0.6);
                    outline: none;
                }
                ToolButton:focus {
                    outline: none;
                }
            """
        
        setCustomStyleSheet(self.info_button, style, style)

    def _show_notification_window(self):
        """Show the notification window and stop flashing."""
        self._stop_notification_flash()
        self.notification_window.show_and_raise()

    def _add_notification(self, title, content, notification_type="info"):
        """Add a notification to the notification window and flash the icon if needed."""
        self.notification_window.add_notification(title, content, notification_type)
        
        # Flash icon for important notifications
        if notification_type in ["error", "warning"]:
            self._start_notification_flash()

    def _cleanup_invalid_cache_entries(self):
        """Clean up invalid cache entries and notify user."""
        try:
            initial_count = len(self.sample_manager.sample_cache)
            
            # Force a sample check by loading each category - this will trigger cleanup
            categories = self.sample_manager.get_categories()
            for category, subcategories in categories.items():
                for subcategory in subcategories:
                    # This will trigger the cleanup in get_samples
                    self.sample_manager.get_samples(category, subcategory)
            
            final_count = len(self.sample_manager.sample_cache)
            cleaned_count = initial_count - final_count
            
            if cleaned_count > 0:
                self._add_notification(
                    "Cache Cleanup",
                    f"Removed {cleaned_count} invalid cache entries with missing files.",
                    "info"
                )
                # Refresh the UI to show current state
                self.populate_categories()
        except Exception as e:
            self._add_notification(
                "Cleanup Error",
                f"Error during cache cleanup: {str(e)}",
                "error"
            )

class AudioDiagnosticsDialog(QDialog):
    """Dialog to show audio diagnostics and troubleshooting information."""
    
    def __init__(self, diagnosis, device_info, parent=None):
        super().__init__(parent)
        self.diagnosis = diagnosis
        self.device_info = device_info
        self.init_ui()
    
    def init_ui(self):
        """Initialize the diagnostics dialog UI."""
        self.setWindowTitle("Audio Diagnostics")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = TitleLabel("Audio System Diagnostics")
        title.setFont(get_font_manager().get_header_font(16))
        layout.addWidget(title)
        
        # Scroll area for content
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # Device Information Section
        self._add_section(content_layout, "Audio Device Information", self._create_device_info())
        
        # Issues Section
        if self.diagnosis.get("issues"):
            self._add_section(content_layout, "Detected Issues", self._create_issues_list())
        
        # Recommendations Section
        if self.diagnosis.get("recommendations"):
            self._add_section(content_layout, "Recommendations", self._create_recommendations_list())
        
        # Sample-specific information
        if self.diagnosis.get("sample_type") == "bass_heavy":
            self._add_section(content_layout, "Bass Sample Information", self._create_bass_info())
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        close_button = PushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setFixedWidth(100)
        
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def _add_section(self, layout, title, content):
        """Add a section with title and content."""
        section_title = BodyLabel(title)
        section_title.setFont(get_font_manager().get_header_font(14))
        section_title.setStyleSheet("color: rgba(94, 129, 172, 1.0); font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(section_title)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(46, 52, 64, 0.3);
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(content)
        
        layout.addWidget(content_widget)
    
    def _create_device_info(self):
        """Create device information widget."""
        info_text = []
        
        if "error" in self.device_info:
            info_text.append(f"❌ Error: {self.device_info['error']}")
        else:
            info_text.append(f"🎵 Device: {self.device_info.get('device_name', 'Unknown')}")
            info_text.append(f"📊 Sample Rate: {self.device_info.get('preferred_sample_rate', 'Unknown')} Hz")
            info_text.append(f"🔊 Channels: {self.device_info.get('preferred_channels', 'Unknown')}")
            info_text.append(f"🎛️ Format: {self.device_info.get('preferred_sample_format', 'Unknown')}")
            info_text.append(f"🔉 Current Volume: {self.device_info.get('current_volume', 0):.1%}")
            
            if supported_rates := self.device_info.get('supported_sample_rates'):
                rates_str = ", ".join(map(str, sorted(supported_rates)[:5]))
                if len(supported_rates) > 5:
                    rates_str += "..."
                info_text.append(f"📈 Supported Rates: {rates_str} Hz")
        
        label = BodyLabel("\n".join(info_text))
        label.setWordWrap(True)
        label.setStyleSheet("color: rgba(255, 255, 255, 0.9); line-height: 1.4;")
        return label
    
    def _create_issues_list(self):
        """Create issues list widget."""
        issues_text = []
        for issue in self.diagnosis["issues"]:
            issues_text.append(f"⚠️ {issue}")
        
        label = BodyLabel("\n".join(issues_text))
        label.setWordWrap(True)
        label.setStyleSheet("color: rgba(235, 203, 139, 1.0); line-height: 1.4;")
        return label
    
    def _create_recommendations_list(self):
        """Create recommendations list widget."""
        rec_text = []
        for rec in self.diagnosis["recommendations"]:
            rec_text.append(f"💡 {rec}")
        
        label = BodyLabel("\n".join(rec_text))
        label.setWordWrap(True)
        label.setStyleSheet("color: rgba(163, 190, 140, 1.0); line-height: 1.4;")
        return label
    
    def _create_bass_info(self):
        """Create bass-specific information widget."""
        bass_info = [
            "🎵 This appears to be a bass-heavy sample (808, kick, sub-bass, etc.)",
            "",
            "For optimal bass playback:",
            "• Ensure your audio system can reproduce low frequencies (20-250 Hz)",
            "• Use quality headphones or speakers with good bass response",
            "• Check that your audio interface supports the sample's bit depth and sample rate",
            "• Avoid using built-in laptop speakers for bass-heavy content",
            "• Consider using a dedicated audio interface or external DAC"
        ]
        
        label = BodyLabel("\n".join(bass_info))
        label.setWordWrap(True)
        label.setStyleSheet("color: rgba(255, 255, 255, 0.9); line-height: 1.4;")
        return label

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # High DPI support is enabled by default in PyQt6
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
