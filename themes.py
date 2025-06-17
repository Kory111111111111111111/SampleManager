# Nord color palette constants
NORD = {
    # Polar Night
    "nord0": "#2E3440",  # Background
    "nord1": "#3B4252",  # Lighter background
    "nord2": "#434C5E",  # Selection background
    "nord3": "#4C566A",  # Inactive text
    
    # Snow Storm
    "nord4": "#D8DEE9",  # Text color
    "nord5": "#E5E9F0",  # Light text
    "nord6": "#ECEFF4",  # Light background
    
    # Frost
    "nord7": "#8FBCBB",  # Declarations
    "nord8": "#88C0D0",  # Primary accent
    "nord9": "#81A1C1",  # Secondary accent
    "nord10": "#5E81AC", # Tertiary accent
    
    # Aurora
    "nord11": "#BF616A",  # Error
    "nord12": "#D08770",  # Warning
    "nord13": "#EBCB8B",  # Success
    "nord14": "#A3BE8C",  # Function calls
    "nord15": "#B48EAD"   # Keywords
}

def apply_nord_theme(app):
    """Apply Nord theme to the entire application."""
    stylesheet = f"""
        QWidget {{
            background-color: {NORD["nord0"]};
            color: {NORD["nord4"]};
            font-family: 'Gmarket Sans', 'Segoe UI', sans-serif;
        }}
        
        QPushButton {{
            background-color: {NORD["nord2"]};
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            color: {NORD["nord6"]};
            font-family: 'Gmarket Sans', 'Segoe UI', sans-serif;
            font-weight: 500;
        }}
        
        QPushButton:hover {{
            background-color: {NORD["nord3"]};
        }}
        
        QPushButton:pressed {{
            background-color: {NORD["nord1"]};
        }}
        
        QTreeWidget, QListWidget {{
            background-color: {NORD["nord1"]};
            border: 1px solid {NORD["nord3"]};
            border-radius: 4px;
            padding: 4px;
            font-family: 'Gmarket Sans', 'Segoe UI', sans-serif;
        }}
        
        QTreeWidget::item, QListWidget::item {{
            padding: 4px;
            border-radius: 2px;
        }}
        
        QTreeWidget::item:selected, QListWidget::item:selected {{
            background-color: {NORD["nord2"]};
            color: {NORD["nord6"]};
        }}
        
        QTreeWidget::item:hover, QListWidget::item:hover {{
            background-color: {NORD["nord3"]};
        }}
        
        QLabel {{
            color: {NORD["nord4"]};
            font-family: 'Gmarket Sans', 'Segoe UI', sans-serif;
        }}
        
        /* Header labels */
        QLabel[class="header"] {{
            font-weight: bold;
            font-size: 14px;
            color: {NORD["nord6"]};
        }}
        
        /* Body text labels */
        QLabel[class="body"] {{
            font-weight: normal;
            font-size: 10px;
        }}
        
        /* Light text labels */
        QLabel[class="light"] {{
            font-weight: 300;
            color: {NORD["nord3"]};
        }}
        
        QComboBox {{
            background-color: {NORD["nord1"]};
            border: 1px solid {NORD["nord3"]};
            border-radius: 4px;
            padding: 4px 8px;
            color: {NORD["nord4"]};
        }}
        
        QComboBox:hover {{
            border: 1px solid {NORD["nord8"]};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border: none;
        }}
        
        QLineEdit {{
            background-color: {NORD["nord1"]};
            border: 1px solid {NORD["nord3"]};
            border-radius: 4px;
            padding: 4px 8px;
            color: {NORD["nord4"]};
        }}
        
        QLineEdit:focus {{
            border: 1px solid {NORD["nord8"]};
        }}
        
        QProgressBar {{
            border: 1px solid {NORD["nord3"]};
            border-radius: 2px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {NORD["nord8"]};
        }}
    """
    app.setStyleSheet(stylesheet)
