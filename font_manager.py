import os
from PyQt6.QtGui import QFontDatabase, QFont, QIcon
from PyQt6.QtCore import QStandardPaths
import logging

logger = logging.getLogger(__name__)

class FontManager:
    """Manages custom fonts for the WAVFin Sample Manager application."""
    
    def __init__(self):
        self.fonts_loaded = False
        self.funnel_family = "Funnel Display"
        self.material_symbols_family = "Material Symbols Rounded"
        self.material_symbols_loaded = False
        
    def load_fonts(self):
        """Load custom fonts from the Fonts directory."""
        if self.fonts_loaded:
            return True
            
        try:
            fonts_dir = os.path.join(os.path.dirname(__file__), "Fonts")
            
            # FunnelDisplay font files to load
            font_files = [
                "FunnelDisplay-Light.ttf",
                "FunnelDisplay-Regular.ttf",
                "FunnelDisplay-Medium.ttf",
                "FunnelDisplay-SemiBold.ttf",
                "FunnelDisplay-Bold.ttf",
                "FunnelDisplay-ExtraBold.ttf",
                "FunnelDisplay-VariableFont_wght.ttf"
            ]
            
            loaded_count = 0
            for font_file in font_files:
                font_path = os.path.join(fonts_dir, font_file)
                if os.path.exists(font_path):
                    font_id = QFontDatabase.addApplicationFont(font_path)
                    if font_id != -1:
                        loaded_count += 1
                        logger.info(f"Loaded font: {font_file}")
                    else:
                        logger.warning(f"Failed to load font: {font_file}")
                else:
                    logger.warning(f"Font file not found: {font_path}")
            
            # Load Material Symbols font
            material_symbols_path = os.path.join(os.path.dirname(__file__), "Icons", "Material_Symbols_Rounded", "MaterialSymbolsRounded-VariableFont_FILL,GRAD,opsz,wght.ttf")
            if os.path.exists(material_symbols_path):
                material_id = QFontDatabase.addApplicationFont(material_symbols_path)
                if material_id != -1:
                    self.material_symbols_loaded = True
                    logger.info("Loaded Material Symbols Rounded font")
                else:
                    logger.warning("Failed to load Material Symbols font")
            else:
                logger.warning(f"Material Symbols font not found: {material_symbols_path}")
            
            if loaded_count > 0:
                self.fonts_loaded = True
                logger.info(f"Successfully loaded {loaded_count} Funnel Display fonts")
                return True
            else:
                logger.error("No fonts were loaded successfully")
                return False
                
        except Exception as e:
            logger.error(f"Error loading fonts: {str(e)}")
            return False
    
    def get_font(self, size=10, weight=QFont.Weight.Normal):
        """
        Get a Funnel Display font with specified size and weight.
        
        Args:
            size: Font size in points
            weight: Font weight (QFont.Weight.Light, Normal, Medium, Bold)
            
        Returns:
            QFont object
        """
        if not self.fonts_loaded:
            self.load_fonts()
        
        font = QFont()
        
        if self.fonts_loaded and self.funnel_family in QFontDatabase.families():
            font.setFamily(self.funnel_family)
        else:
            # Fallback to system fonts
            font.setFamily("Segoe UI")  # Windows
            if not font.exactMatch():
                font.setFamily("SF Pro Display")  # macOS
            if not font.exactMatch():
                font.setFamily("Ubuntu")  # Linux
        
        font.setPointSize(size)
        font.setWeight(weight)
        
        return font
    
    def get_header_font(self, size=14):
        """Get a bold font for headers."""
        return self.get_font(size, QFont.Weight.Bold)
    
    def get_body_font(self, size=10):
        """Get a normal weight font for body text."""
        return self.get_font(size, QFont.Weight.Normal)
    
    def get_light_font(self, size=10):
        """Get a light weight font."""
        return self.get_font(size, QFont.Weight.Light)
    
    def get_medium_font(self, size=10):
        """Get a medium weight font."""
        return self.get_font(size, QFont.Weight.Medium)
    
    def get_semibold_font(self, size=10):
        """Get a semibold weight font."""
        return self.get_font(size, QFont.Weight.DemiBold)
    
    def get_extrabold_font(self, size=10):
        """Get an extra bold weight font."""
        return self.get_font(size, QFont.Weight.ExtraBold)
    
    def is_font_available(self):
        """Check if Funnel Display fonts are available."""
        return self.fonts_loaded and self.funnel_family in QFontDatabase.families()

class MaterialSymbolsIcon:
    """Material Symbols icon manager using the loaded font."""
    
    # Material Symbols Unicode mappings
    SYMBOLS = {
        'ADD': '\ue145',
        'SEARCH': '\ue8b6',
        'DELETE': '\ue872',
        'MUSIC': '\ue405',
        'MICROPHONE': '\ue3c9',
        'SETTING': '\ue8b8',
        'FOLDER': '\ue2c7',
        'INFO': '\ue88e',
        'PLAY': '\ue037',
        'PAUSE': '\ue034',
        'VOLUME': '\ue050',
        'VOLUME_MUTE': '\ue04f',
        'DOCUMENT': '\ue873',
        'AUDIO_FILE': '\ue3b7',
        'LIBRARY_MUSIC': '\ue217',
        'EQUALIZER': '\ue01d',
        'WAVEFORM': '\uf8e1',
        'DRUMS': '\ue40e',
        'PIANO': '\ue3af',
        'VOCALS': '\ue3c9',
        'EFFECTS': '\ue3ba',
        'EDIT': '\ue3c9'
    }
    
    def __init__(self, symbol_name, size=24):
        self.symbol_name = symbol_name
        self.size = size
        self.font_manager = get_font_manager()
    
    def icon(self):
        """Create a QIcon from the Material Symbol."""
        if not self.font_manager.material_symbols_loaded:
            # Fallback to a simple text-based icon
            return QIcon()
        
        from PyQt6.QtGui import QPixmap, QPainter, QColor
        from PyQt6.QtCore import Qt
        
        # Create a pixmap
        pixmap = QPixmap(self.size, self.size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Create painter
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up font
        font = QFont(self.font_manager.material_symbols_family)
        font.setPixelSize(self.size)
        painter.setFont(font)
        
        # Set color (white for dark theme)
        painter.setPen(QColor(255, 255, 255))
        
        # Draw the symbol
        symbol_char = self.SYMBOLS.get(self.symbol_name, '\ue88e')  # Default to info icon
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, symbol_char)
        
        painter.end()
        
        return QIcon(pixmap)

# Icon creation functions to replace FluentIcon usage
def MaterialIcon(symbol_name, size=24):
    """Create a Material Symbols icon."""
    return MaterialSymbolsIcon(symbol_name, size)

# Global font manager instance - will be initialized when first accessed
font_manager = None

def get_font_manager():
    """Get the global font manager instance, creating it if necessary."""
    global font_manager
    if font_manager is None:
        font_manager = FontManager()
    return font_manager 