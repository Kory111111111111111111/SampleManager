from PyQt6.QtWidgets import QScrollBar
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from themes import NORD

class DotScrollbar(QScrollBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOrientation(Qt.Orientation.Vertical)
        
        # Apply the Nord-themed styling
        self.setStyleSheet(f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            
            QScrollBar::handle:vertical {{
                background: {NORD["nord8"]};
                min-height: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: {NORD["nord9"]};
            }}
            
            QScrollBar::handle:vertical:pressed {{
                background: {NORD["nord10"]};
            }}
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                background: none;
                border: none;
            }}
            
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: {NORD["nord1"]};
                border-radius: 4px;
            }}
        """)
        
        # Initialize animation properties
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setDuration(300)

    def mousePressEvent(self, event):
        """Override mouse press to add smooth scrolling animation."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate the new scroll position
            click_position = event.pos().y()
            viewport_height = self.height()
            value_range = self.maximum() - self.minimum()
            
            # Calculate target value based on click position
            target_value = (click_position / viewport_height) * value_range
            
            # Set up and start the animation
            self._animation.setStartValue(self.value())
            self._animation.setEndValue(target_value)
            self._animation.start()
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event):
        """Override wheel event to add smooth scrolling animation."""
        # Calculate the target value
        delta = event.angleDelta().y()
        target_value = max(min(self.value() - delta, self.maximum()), self.minimum())
        
        # Set up and start the animation
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(target_value)
        self._animation.start()
