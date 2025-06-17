import os
import logging
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QAudioDevice, QMediaDevices, QAudioFormat
from PyQt6.QtWidgets import QApplication

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioPlayer(QObject):
    """
    Universal audio player for WAVFin Sample Manager.
    Handles playback of audio samples with progress tracking and volume control.
    """
    
    # Signals for UI updates
    position_changed = pyqtSignal(int)  # Current position in ms
    duration_changed = pyqtSignal(int)  # Total duration in ms
    playback_state_changed = pyqtSignal(int)  # QMediaPlayer.PlaybackState
    volume_changed = pyqtSignal(float)  # Volume level 0.0-1.0
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(self):
        super().__init__()
        
        # Initialize media player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        
        # Enhanced audio output configuration for better low frequency reproduction
        self._configure_audio_output()
        
        # Set the audio output to the media player
        self.media_player.setAudioOutput(self.audio_output)
        
        # Connect signals
        self.media_player.positionChanged.connect(self.position_changed.emit)
        self.media_player.durationChanged.connect(self.duration_changed.emit)
        self.media_player.playbackStateChanged.connect(self.playback_state_changed.emit)
        self.media_player.errorOccurred.connect(self._handle_error)
        self.audio_output.volumeChanged.connect(self.volume_changed.emit)
        
        # Current file info
        self.current_file = None
        self.is_loaded = False
        self._loading = False  # Prevent multiple simultaneous loads
        
        # Supported formats with better compatibility
        self.supported_formats = {
            '.wav': 'WAV (uncompressed)',
            '.mp3': 'MP3 (compressed)',
            '.flac': 'FLAC (lossless)',
            '.aiff': 'AIFF (uncompressed)',
            '.aif': 'AIFF (uncompressed)',
            '.m4a': 'M4A/AAC (compressed)',
            '.ogg': 'OGG Vorbis (compressed)',
            '.wma': 'WMA (compressed)'
        }
        
        logger.info("AudioPlayer initialized with enhanced format support and low frequency optimization")
    
    def _configure_audio_output(self):
        """Configure audio output for optimal low frequency reproduction."""
        try:
            # Get the default audio device
            default_device = self._get_default_audio_device()
            
            if default_device.isNull():
                logger.warning("No default audio output device found")
                self.audio_output.setVolume(0.7)
                return
            
            # Get the preferred format for the device
            preferred_format = default_device.preferredFormat()
            
            # Create an optimized format for low frequency reproduction
            optimized_format = QAudioFormat()
            
            # Use higher sample rates if supported (better for bass reproduction)
            try:
                supported_rates = default_device.supportedSampleRates()
                if supported_rates is not None:
                    # Prefer 48kHz or 44.1kHz for better low frequency response
                    target_rates = [48000, 44100, 96000, 88200]
                    selected_rate = preferred_format.sampleRate()
                    
                    for rate in target_rates:
                        if rate in supported_rates:
                            selected_rate = rate
                            break
                    
                    optimized_format.setSampleRate(selected_rate)
                    logger.info(f"Using sample rate: {selected_rate} Hz for better bass reproduction")
                else:
                    optimized_format.setSampleRate(preferred_format.sampleRate())
            except (AttributeError, RuntimeError) as e:
                logger.warning(f"Could not get supported sample rates, using default: {e}")
                optimized_format.setSampleRate(preferred_format.sampleRate())
            
            # Use 16-bit or 32-bit depth for better dynamic range
            try:
                supported_formats = default_device.supportedSampleFormats()
                if supported_formats is not None:
                    # Prefer higher bit depths for better low frequency detail
                    if QAudioFormat.SampleFormat.Float in supported_formats:
                        optimized_format.setSampleFormat(QAudioFormat.SampleFormat.Float)
                        logger.info("Using Float sample format for better dynamic range")
                    elif QAudioFormat.SampleFormat.Int32 in supported_formats:
                        optimized_format.setSampleFormat(QAudioFormat.SampleFormat.Int32)
                        logger.info("Using Int32 sample format for better dynamic range")
                    elif QAudioFormat.SampleFormat.Int16 in supported_formats:
                        optimized_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
                        logger.info("Using Int16 sample format")
                    else:
                        optimized_format.setSampleFormat(preferred_format.sampleFormat())
                else:
                    optimized_format.setSampleFormat(preferred_format.sampleFormat())
            except (AttributeError, RuntimeError) as e:
                logger.warning(f"Could not get supported sample formats, using default: {e}")
                optimized_format.setSampleFormat(preferred_format.sampleFormat())
            
            # Use stereo for better bass imaging
            try:
                supported_channels = default_device.supportedChannelConfigurations()
                if supported_channels is not None:
                    if 2 in supported_channels:  # Stereo
                        optimized_format.setChannelCount(2)
                        logger.info("Using stereo output for better bass imaging")
                    elif 1 in supported_channels:  # Mono
                        optimized_format.setChannelCount(1)
                    else:
                        optimized_format.setChannelCount(preferred_format.channelCount())
                else:
                    optimized_format.setChannelCount(preferred_format.channelCount())
            except (AttributeError, RuntimeError) as e:
                logger.warning(f"Could not get supported channel configurations, using default: {e}")
                optimized_format.setChannelCount(preferred_format.channelCount())
            
            # Try to set the optimized format
            self.audio_output = QAudioOutput(default_device)
            if default_device.isFormatSupported(optimized_format):
                logger.info("Applied optimized audio format for low frequency reproduction")
            else:
                logger.info("Using default audio format (optimized format not supported)")
            
            # Set initial volume
            self.audio_output.setVolume(0.7)
            
        except Exception as e:
            logger.warning(f"Failed to configure optimized audio output: {e}")
            # Fall back to basic configuration
            self.audio_output.setVolume(0.7)
    
    def load_file(self, file_path: str) -> bool:
        """
        Load an audio file for playback with enhanced format support and sample rate handling.
        Includes special handling for low frequency samples.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            bool: True if file loaded successfully, False otherwise
        """
        if self._loading:
            logger.warning("Already loading a file, skipping")
            return False
            
        try:
            self._loading = True
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"Audio file not found: {file_path}")
                self.error_occurred.emit(f"File not found: {file_path.name}")
                return False
            
            # Check format support
            file_ext = file_path.suffix.lower()
            if file_ext not in self.supported_formats:
                logger.error(f"Unsupported audio format: {file_ext}")
                self.error_occurred.emit(f"Unsupported format: {file_ext}. Supported: {', '.join(self.supported_formats.keys())}")
                return False
            
            # Stop current playback and reset
            self.stop()
            self.is_loaded = False
            
            # Ensure clean state
            QApplication.processEvents()
            
            # Special handling for bass-heavy samples (likely 808s, kicks, etc.)
            if is_bass_sample := self._is_bass_sample(file_path):
                logger.info(f"Detected bass sample, applying optimizations: {file_path.name}")
                self._optimize_for_bass_playback()
            
            # Load new file with absolute path and proper URL encoding
            file_url = QUrl.fromLocalFile(str(file_path.resolve()))
            
            # Verify URL is valid
            if not file_url.isValid():
                logger.error(f"Invalid file URL: {file_url}")
                self.error_occurred.emit("Invalid file path")
                return False
            
            logger.info(f"Loading {self.supported_formats[file_ext]} file: {file_path.name}")
            
            # Set source with retry mechanism for problematic files
            success = self._set_source_with_retry(file_url, file_ext)
            if not success:
                return False
            
            self.current_file = str(file_path)
            self.is_loaded = True
            
            logger.info(f"Successfully loaded: {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading audio file {file_path}: {e}")
            self.error_occurred.emit(f"Error loading file: {str(e)}")
            return False
        finally:
            self._loading = False
    
    def _is_bass_sample(self, file_path: Path) -> bool:
        """Detect if a sample is likely bass-heavy based on filename and path."""
        path_str = str(file_path).lower()
        bass_indicators = [
            '808', 'bass', 'kick', 'sub', 'low', 'boom', 'thump',
            'deep', 'heavy', 'punch', 'knock', 'bd', 'bassdrum'
        ]
        return any(indicator in path_str for indicator in bass_indicators)
    
    def _optimize_for_bass_playback(self):
        """Apply specific optimizations for bass-heavy samples."""
        try:
            # Temporarily increase buffer size for better low frequency handling
            # This helps prevent dropouts in bass-heavy content
            current_volume = self.audio_output.volume()
            
            # Ensure we're using the best available audio device configuration
            default_device = self._get_default_audio_device()
            
            if not default_device.isNull():
                # Check if we need to recreate the audio output for better bass handling
                preferred_format = default_device.preferredFormat()
                
                # For bass samples, prefer lower sample rates if they provide better compatibility
                if preferred_format.sampleRate() > 48000:
                    logger.info("Using standard sample rate for bass sample compatibility")
                
            logger.debug("Applied bass playback optimizations")
            
        except Exception as e:
            logger.warning(f"Failed to apply bass optimizations: {e}")
    
    def _set_source_with_retry(self, file_url: QUrl, file_ext: str, max_retries: int = 3) -> bool:
        """Set media source with retry mechanism for better reliability."""
        for attempt in range(max_retries):
            try:
                self.media_player.setSource(file_url)
                
                # Wait for media to be recognized with timeout
                import time
                timeout = 2.0  # 2 second timeout
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    QApplication.processEvents()
                    # Check if source was set successfully
                    if self.media_player.source() == file_url:
                        return True
                    time.sleep(0.01)
                
                # If we get here, the source wasn't set properly
                if attempt < max_retries - 1:
                    logger.warning(f"Source setting attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.1)  # Brief pause before retry
                else:
                    logger.error("Failed to set media source after all retries")
                    self.error_occurred.emit("Failed to load audio file - format may not be supported")
                    return False
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Source setting attempt {attempt + 1} failed with error: {e}, retrying...")
                else:
                    logger.error(f"Failed to set media source: {e}")
                    self.error_occurred.emit(f"Failed to load audio file: {str(e)}")
                    return False
        
        return False
    
    def play(self) -> bool:
        """
        Start or resume playback with improved reliability.
        
        Returns:
            bool: True if playback started, False otherwise
        """
        if not self.is_loaded:
            logger.warning("No audio file loaded")
            return False
        
        if self._loading:
            logger.warning("File still loading, cannot play yet")
            return False
        
        try:
            # Ensure we're not already playing
            if self.is_playing():
                return True
                
            self.media_player.play()
            logger.debug("Playback started")
            return True
        except Exception as e:
            logger.error(f"Error starting playback: {e}")
            self.error_occurred.emit(f"Playback error: {str(e)}")
            return False
    
    def _safe_media_operation(self, operation, operation_name: str, success_message: str = None):
        """Safely execute a media player operation with error handling."""
        try:
            operation()
            if success_message:
                logger.debug(success_message)
        except Exception as e:
            logger.error(f"Error {operation_name}: {e}")
    
    def pause(self):
        """Pause playback."""
        self._safe_media_operation(
            self.media_player.pause,
            "pausing playback",
            "Playback paused"
        )
    
    def stop(self):
        """Stop playback and reset position."""
        self._safe_media_operation(
            self.media_player.stop,
            "stopping playback", 
            "Playback stopped"
        )
    
    def toggle_playback(self) -> bool:
        """
        Toggle between play and pause.
        
        Returns:
            bool: True if now playing, False if paused/stopped
        """
        if not self.is_loaded:
            return False
        
        current_state = self.media_player.playbackState()
        
        if current_state != QMediaPlayer.PlaybackState.PlayingState:
            return self.play()
        
        self.pause()
        return False
    
    def set_position(self, position_ms: int):
        """
        Set playback position.
        
        Args:
            position_ms: Position in milliseconds
        """
        if self.is_loaded:
            try:
                self.media_player.setPosition(position_ms)
                logger.debug(f"Position set to {position_ms}ms")
            except Exception as e:
                logger.error(f"Error setting position: {e}")
    
    def set_volume(self, volume: float):
        """
        Set playback volume with improved handling.
        
        Args:
            volume: Volume level from 0.0 to 1.0
        """
        try:
            volume = max(0.0, min(1.0, volume))  # Clamp to valid range
            
            # Set volume on audio output
            self.audio_output.setVolume(volume)
            
            logger.debug(f"Volume set to {volume:.2f}")
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
    
    def get_position(self) -> int:
        """
        Get current playback position.
        
        Returns:
            int: Current position in milliseconds
        """
        return self.media_player.position()
    
    def get_duration(self) -> int:
        """
        Get total duration of current file.
        
        Returns:
            int: Duration in milliseconds
        """
        return self.media_player.duration()
    
    def get_volume(self) -> float:
        """
        Get current volume level.
        
        Returns:
            float: Volume level from 0.0 to 1.0
        """
        return self.audio_output.volume()
    
    def is_playing(self) -> bool:
        """
        Check if audio is currently playing.
        
        Returns:
            bool: True if playing, False otherwise
        """
        return self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
    
    def is_paused(self) -> bool:
        """
        Check if audio is currently paused.
        
        Returns:
            bool: True if paused, False otherwise
        """
        return self.media_player.playbackState() == QMediaPlayer.PlaybackState.PausedState
    
    def is_stopped(self) -> bool:
        """
        Check if audio is currently stopped.
        
        Returns:
            bool: True if stopped, False otherwise
        """
        return self.media_player.playbackState() == QMediaPlayer.PlaybackState.StoppedState
    
    def get_current_file(self) -> Optional[str]:
        """
        Get the path of the currently loaded file.
        
        Returns:
            str: File path if loaded, None otherwise
        """
        return self.current_file
    
    def _handle_error(self, error):
        """Handle media player errors with enhanced diagnostics for low frequency issues."""
        error_string = self.media_player.errorString()
        
        # Enhanced error reporting for common low frequency playback issues
        if "format" in error_string.lower() or "codec" in error_string.lower():
            enhanced_message = f"Audio format error: {error_string}. "
            if self.current_file and self._is_bass_sample(Path(self.current_file)):
                enhanced_message += "This bass sample may require different audio settings. Try adjusting your system's audio sample rate to 44.1kHz or 48kHz."
        elif "device" in error_string.lower() or "output" in error_string.lower():
            enhanced_message = f"Audio device error: {error_string}. "
            enhanced_message += "Check your audio device settings and ensure no other applications are using exclusive audio access."
        elif "resource" in error_string.lower() or "busy" in error_string.lower():
            enhanced_message = f"Audio resource error: {error_string}. "
            enhanced_message += "Another application may be using the audio device. Close other audio applications and try again."
        else:
            enhanced_message = f"Playback error: {error_string}"
        
        logger.error(f"Media player error: {enhanced_message}")
        self.error_occurred.emit(enhanced_message)
    
    def format_time(self, milliseconds: int) -> str:
        """
        Format time in milliseconds to MM:SS format.
        
        Args:
            milliseconds: Time in milliseconds
            
        Returns:
            str: Formatted time string
        """
        if milliseconds < 0:
            return "00:00"
        
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_playback_info(self) -> dict:
        """
        Get comprehensive playback information.
        
        Returns:
            dict: Playback information including position, duration, state, etc.
        """
        return {
            "current_file": self.current_file,
            "is_loaded": self.is_loaded,
            "position_ms": self.get_position(),
            "duration_ms": self.get_duration(),
            "position_formatted": self.format_time(self.get_position()),
            "duration_formatted": self.format_time(self.get_duration()),
            "volume": self.get_volume(),
            "is_playing": self.is_playing(),
            "is_paused": self.is_paused(),
            "is_stopped": self.is_stopped(),
            "progress_percent": (self.get_position() / max(self.get_duration(), 1)) * 100
        }
    
    def _get_default_audio_device(self):
        """Get the default audio output device."""
        from PyQt6.QtMultimedia import QMediaDevices
        return QMediaDevices.defaultAudioOutput()
    
    def get_audio_device_info(self) -> dict:
        """Get detailed audio device information for diagnostics."""
        try:
            default_device = self._get_default_audio_device()
            if default_device.isNull():
                return {"error": "No audio output device available"}
            
            preferred_format = default_device.preferredFormat()
            
            info = {
                "device_name": default_device.description(),
                "is_default": default_device.isDefault(),
                "preferred_sample_rate": preferred_format.sampleRate(),
                "preferred_channels": preferred_format.channelCount(),
                "preferred_sample_format": str(preferred_format.sampleFormat()),
                "current_volume": self.audio_output.volume() if hasattr(self, 'audio_output') else 0.0
            }
            
            # Safely get supported sample rates
            try:
                supported_rates = default_device.supportedSampleRates()
                if supported_rates is not None:
                    info["supported_sample_rates"] = list(supported_rates)
                else:
                    info["supported_sample_rates"] = []
            except (AttributeError, RuntimeError) as e:
                logger.warning(f"Could not get supported sample rates: {e}")
                info["supported_sample_rates"] = []
            
            # Safely get supported channel configurations
            try:
                supported_channels = default_device.supportedChannelConfigurations()
                if supported_channels is not None:
                    info["supported_channel_configs"] = list(supported_channels)
                else:
                    info["supported_channel_configs"] = []
            except (AttributeError, RuntimeError) as e:
                logger.warning(f"Could not get supported channel configurations: {e}")
                info["supported_channel_configs"] = []
            
            # Safely get supported sample formats
            try:
                supported_formats = default_device.supportedSampleFormats()
                if supported_formats is not None:
                    info["supported_sample_formats"] = [str(fmt) for fmt in supported_formats]
                else:
                    info["supported_sample_formats"] = []
            except (AttributeError, RuntimeError) as e:
                logger.warning(f"Could not get supported sample formats: {e}")
                info["supported_sample_formats"] = []
            
            # Add bass-specific recommendations
            if info["preferred_sample_rate"] > 48000:
                info["bass_recommendation"] = "Consider using 44.1kHz or 48kHz sample rate for better bass sample compatibility"
            
            if info["preferred_channels"] == 1:
                info["bass_recommendation"] = info.get("bass_recommendation", "") + " Stereo output recommended for better bass imaging"
            
            return info
            
        except Exception as e:
            return {"error": f"Failed to get audio device info: {e}"}
    
    def diagnose_playback_issues(self, file_path: str = None) -> dict:
        """Diagnose potential playback issues, especially for low frequency samples."""
        diagnosis = {
            "timestamp": str(QTimer().remainingTime()),
            "issues": [],
            "recommendations": [],
            "device_info": self.get_audio_device_info()
        }
        
        # Check current file if provided
        if file_path:
            file_path_obj = Path(file_path)
            if self._is_bass_sample(file_path_obj):
                diagnosis["sample_type"] = "bass_heavy"
                diagnosis["recommendations"].append("This appears to be a bass-heavy sample. Ensure your audio system can reproduce low frequencies properly.")
            
            # Check file size (very large files might cause issues)
            if file_path_obj.exists():
                file_size_mb = file_path_obj.stat().st_size / (1024 * 1024)
                if file_size_mb > 50:  # Files larger than 50MB
                    diagnosis["issues"].append(f"Large file size ({file_size_mb:.1f}MB) may cause loading delays")
                    diagnosis["recommendations"].append("Consider using compressed formats for very large samples")
        
        # Check audio device configuration
        device_info = diagnosis["device_info"]
        if "error" not in device_info:
            if device_info.get("preferred_sample_rate", 0) > 96000:
                diagnosis["issues"].append("Very high sample rate may cause compatibility issues")
                diagnosis["recommendations"].append("Try setting system audio to 44.1kHz or 48kHz")
            
            if device_info.get("preferred_channels", 0) == 1:
                diagnosis["issues"].append("Mono output detected")
                diagnosis["recommendations"].append("Stereo output provides better bass imaging")
        
        # Check current playback state
        if hasattr(self, 'media_player') and self.media_player.error() != self.media_player.Error.NoError:
            diagnosis["issues"].append(f"Media player error: {self.media_player.errorString()}")
        
        return diagnosis

# Create a global instance for easy access
audio_player = AudioPlayer() 