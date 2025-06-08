import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QSplitter, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QIcon, QFont

from themes import apply_nord_theme, NORD
from custom_scrollbar import DotScrollbar
from sample_manager import SampleManager
from audio_analysis import AudioAnalyzer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sample_manager = SampleManager()
        self.analyzer = AudioAnalyzer()
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Nord Sample Manager")
        self.setMinimumSize(1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel (Categories)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Category header
        category_header = QLabel("Categories")
        category_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        left_layout.addWidget(category_header)

        # Category tree
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setVerticalScrollBar(DotScrollbar(self.category_tree))
        self.populate_categories()
        self.category_tree.itemClicked.connect(self.on_category_selected)
        left_layout.addWidget(self.category_tree)

        # Right panel (Sample list and details)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # Sample list header
        sample_header = QLabel("Samples")
        sample_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        right_layout.addWidget(sample_header)

        # Sample list
        self.sample_list = QListWidget()
        self.sample_list.setVerticalScrollBar(DotScrollbar(self.sample_list))
        self.sample_list.itemClicked.connect(self.on_sample_selected)
        right_layout.addWidget(self.sample_list)

        # Control buttons
        button_layout = QHBoxLayout()
        
        self.add_button = self.create_button("Add Sample", self.add_sample)
        self.analyze_button = self.create_button("Analyze", self.analyze_sample)
        self.remove_button = self.create_button("Remove", self.remove_sample)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.analyze_button)
        button_layout.addWidget(self.remove_button)
        
        right_layout.addLayout(button_layout)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (30% left, 70% right)
        splitter.setSizes([int(self.width() * 0.3), int(self.width() * 0.7)])

        # Set up animations for buttons
        self.setup_button_animations()

    def create_button(self, text, callback):
        """Create a styled button with hover and click animations."""
        button = QPushButton(text)
        button.setFont(QFont("Segoe UI", 10))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(callback)
        return button

    def setup_button_animations(self):
        """Set up hover and click animations for buttons."""
        buttons = [self.add_button, self.analyze_button, self.remove_button]
        
        for button in buttons:
            # Store original style
            button.original_style = button.styleSheet()
            
            # Create hover animation
            button.hover_animation = QPropertyAnimation(button, b"size")
            button.hover_animation.setDuration(100)
            button.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # Create click animation
            button.click_animation = QPropertyAnimation(button, b"size")
            button.click_animation.setDuration(100)
            button.click_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # Connect events
            button.enterEvent = lambda e, b=button: self.button_hover_enter(e, b)
            button.leaveEvent = lambda e, b=button: self.button_hover_leave(e, b)
            button.mousePressEvent = lambda e, b=button: self.button_press(e, b)
            button.mouseReleaseEvent = lambda e, b=button: self.button_release(e, b)

    def button_hover_enter(self, event, button):
        """Handle button hover enter animation."""
        size = button.size()
        button.hover_animation.setStartValue(size)
        button.hover_animation.setEndValue(QSize(size.width() + 4, size.height() + 4))
        button.hover_animation.start()
        button.setStyleSheet(button.original_style + f"background-color: {NORD['nord3']};")

    def button_hover_leave(self, event, button):
        """Handle button hover leave animation."""
        size = button.size()
        button.hover_animation.setStartValue(size)
        button.hover_animation.setEndValue(QSize(size.width() - 4, size.height() - 4))
        button.hover_animation.start()
        button.setStyleSheet(button.original_style)

    def button_press(self, event, button):
        """Handle button press animation."""
        size = button.size()
        button.click_animation.setStartValue(size)
        button.click_animation.setEndValue(QSize(size.width() - 6, size.height() - 6))
        button.click_animation.start()
        button.setStyleSheet(button.original_style + f"background-color: {NORD['nord1']};")

    def button_release(self, event, button):
        """Handle button release animation."""
        size = button.size()
        button.click_animation.setStartValue(size)
        button.click_animation.setEndValue(QSize(size.width() + 6, size.height() + 6))
        button.click_animation.start()
        button.setStyleSheet(button.original_style + f"background-color: {NORD['nord3']};")
        button.clicked.emit()

    def populate_categories(self):
        """Populate the category tree with data from sample manager."""
        self.category_tree.clear()
        categories = self.sample_manager.get_categories()
        
        for category, subcategories in categories.items():
            category_item = QTreeWidgetItem([category])
            self.category_tree.addTopLevelItem(category_item)
            
            for subcategory in subcategories:
                subcategory_item = QTreeWidgetItem([subcategory])
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
        self.sample_list.clear()
        samples = self.sample_manager.get_samples(category, subcategory)
        
        for sample in samples:
            item = QListWidgetItem(sample["name"])
            item.setData(Qt.ItemDataRole.UserRole, sample)
            self.sample_list.addItem(item)

    def on_sample_selected(self, item):
        """Handle sample selection."""
        self.analyze_button.setEnabled(True)
        self.remove_button.setEnabled(True)

    def add_sample(self):
        """Add a new sample to the library."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.wav *.mp3 *.flac *.aiff *.ogg)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            
            # Get current category/subcategory
            current_item = self.category_tree.currentItem()
            if current_item and current_item.parent():
                category = current_item.parent().text(0)
                subcategory = current_item.text(0)
                
                for file_path in files:
                    success = self.sample_manager.add_sample(file_path, category, subcategory)
                    if success:
                        self.load_samples(category, subcategory)

    def analyze_sample(self):
        """Analyze the selected sample."""
        current_item = self.sample_list.currentItem()
        if not current_item:
            return
            
        sample_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not sample_data:
            return
            
        # Get the current category/subcategory
        category_item = self.category_tree.currentItem()
        if category_item and category_item.parent():
            category = category_item.parent().text(0)
            subcategory = category_item.text(0)
            
            # Perform analysis
            result = self.sample_manager.analyze_sample(
                category, subcategory, sample_data["name"]
            )
            
            # TODO: Display analysis results in a dialog
            print(result)  # Temporary, replace with proper dialog

    def remove_sample(self):
        """Remove the selected sample."""
        current_item = self.sample_list.currentItem()
        if not current_item:
            return
            
        sample_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not sample_data:
            return
            
        # Get the current category/subcategory
        category_item = self.category_tree.currentItem()
        if category_item and category_item.parent():
            category = category_item.parent().text(0)
            subcategory = category_item.text(0)
            
            # Remove the sample
            success = self.sample_manager.remove_sample(
                category, subcategory, sample_data["name"]
            )
            
            if success:
                self.load_samples(category, subcategory)

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    apply_nord_theme(app)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
