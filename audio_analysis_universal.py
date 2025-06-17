import os
import platform
import logging
import numpy as np
from typing import Dict, Union, Tuple, List, Optional

# Set environment variables early for AMD compatibility
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['NUMBA_DISABLE_INTEL_SVML'] = '1'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CPUDetector:
    """Detect CPU type and capabilities for optimal audio analysis."""
    
    def __init__(self):
        self.cpu_info = self._detect_cpu()
        self.is_intel = self._is_intel_cpu()
        self.is_amd = self._is_amd_cpu()
        self.supports_svml = self._supports_svml()
        
    def _detect_cpu(self) -> Dict:
        """Detect CPU information."""
        try:
            # Try py-cpuinfo first
            import cpuinfo
            info = cpuinfo.get_cpu_info()
            return {
                'brand': info.get('brand_raw', 'Unknown'),
                'vendor': info.get('vendor_id_raw', 'Unknown'),
                'arch': info.get('arch', 'Unknown'),
                'flags': info.get('flags', [])
            }
        except ImportError:
            # Fallback to platform module
            processor = platform.processor()
            return {
                'brand': processor,
                'vendor': 'Intel' if 'intel' in processor.lower() else 'AMD' if 'amd' in processor.lower() else 'Unknown',
                'arch': platform.machine(),
                'flags': []
            }
        except Exception as e:
            logger.warning(f"Could not detect CPU info: {e}")
            return {
                'brand': platform.processor(),
                'vendor': 'Unknown',
                'arch': platform.machine(),
                'flags': []
            }
    
    def _is_intel_cpu(self) -> bool:
        """Check if CPU is Intel."""
        brand = self.cpu_info.get('brand', '').lower()
        vendor = self.cpu_info.get('vendor', '').lower()
        return 'intel' in brand or 'genuineintel' in vendor
    
    def _is_amd_cpu(self) -> bool:
        """Check if CPU is AMD."""
        brand = self.cpu_info.get('brand', '').lower()
        vendor = self.cpu_info.get('vendor', '').lower()
        return 'amd' in brand or 'authenticamd' in vendor
    
    def _supports_svml(self) -> bool:
        """Check if CPU supports Intel SVML functions."""
        return self.is_intel and 'avx' in self.cpu_info.get('flags', [])
    
    def get_recommended_config(self) -> Dict:
        """Get recommended configuration based on CPU."""
        config = {
            'cpu_type': 'Intel' if self.is_intel else 'AMD' if self.is_amd else 'Unknown',
            'use_librosa': True,
            'use_aubio': True,
            'use_tensorflow': True,
            'use_advanced_features': True,
            'environment_vars': {}
        }
        
        if self.is_amd or not self.supports_svml:
            # AMD or Intel without SVML support
            config['environment_vars'].update({
                'NUMBA_DISABLE_INTEL_SVML': '1',
                'NUMBA_DISABLE_JIT': '1',
                'MKL_NUM_THREADS': '1'
            })
            config['use_advanced_features'] = False
            logger.info(f"Detected {config['cpu_type']} CPU - using safe mode")
        else:
            # Intel with SVML support
            logger.info(f"Detected {config['cpu_type']} CPU - using advanced mode")
        
        return config

class UniversalAudioAnalyzer:
    """
    Universal audio analyzer that adapts to different CPU types and capabilities.
    Provides the best possible analysis regardless of hardware.
    """
    
    def __init__(self):
        # Detect CPU and configure accordingly
        self.cpu_detector = CPUDetector()
        self.config = self.cpu_detector.get_recommended_config()
        
        # Set environment variables based on CPU
        for key, value in self.config['environment_vars'].items():
            os.environ[key] = value
        
        # Initialize based on capabilities
        self._initialize_analyzers()
        
        # Analysis parameters
        self.sr = 22050
        self.hop_length = 512
        
        # Category classification mappings
        self.category_keywords = {
            'Bass': ['bass', '808', 'sub', 'low'],
            'Drums': ['kick', 'snare', 'hat', 'cymbal', 'perc', 'drum', 'clap'],
            'FX': ['fx', 'effect', 'sweep', 'riser', 'impact', 'ambient', 'foley'],
            'Melodic': ['lead', 'melody', 'synth', 'key', 'pad', 'pluck', 'chord'],
            'Vocals': ['vocal', 'voice', 'chop', 'phrase', 'word']
        }
        
        # Improved drum type detection
        self.drum_type_keywords = {
            'kick': ['kick', 'bd', 'bassdrum'],
            'snare': ['snare', 'sd'],
            'clap': ['clap', 'handclap'],
            'hihat': ['hat', 'hh', 'hihat', 'hi-hat'],
            'cymbal': ['cymbal', 'crash', 'ride'],
            'percussion': ['perc', 'shaker', 'tambourine', 'conga']
        }
        
        # Key profiles for key detection
        self.key_profiles = self._initialize_key_profiles()
        
        logger.info(f"UniversalAudioAnalyzer initialized for {self.config['cpu_type']} CPU")
    
    def _initialize_analyzers(self):
        """Initialize available analyzers based on CPU capabilities."""
        self.available_methods = {
            'librosa': False,
            'aubio': False,
            'tensorflow': False,
            'safe_fallback': True
        }
        
        # Try to import libraries based on CPU capabilities
        if self.config['use_librosa']:
            try:
                import librosa
                self.available_methods['librosa'] = True
                logger.info("✓ librosa available")
            except Exception as e:
                logger.warning(f"librosa not available: {e}")
        
        if self.config['use_aubio']:
            try:
                import aubio
                self.available_methods['aubio'] = True
                logger.info("✓ aubio available")
            except Exception as e:
                logger.warning(f"aubio not available: {e}")
        
        if self.config['use_tensorflow']:
            try:
                import tensorflow as tf
                tf.get_logger().setLevel('ERROR')
                self.available_methods['tensorflow'] = True
                logger.info("✓ tensorflow available")
            except Exception as e:
                logger.warning(f"tensorflow not available: {e}")
        
        # Always have safe fallback
        import numpy as np
        import soundfile as sf
        logger.info("✓ safe fallback methods available")
    
    def _initialize_key_profiles(self) -> Dict:
        """Initialize key profiles for key detection."""
        import numpy as np
        
        # Krumhansl-Schmuckler key profiles
        major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
        
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        profiles = {}
        for i, key in enumerate(keys):
            # Rotate profiles for each key
            profiles[f"{key} Major"] = major_profile[i:] + major_profile[:i]
            profiles[f"{key} Minor"] = minor_profile[i:] + minor_profile[:i]
        
        return profiles
    
    def analyze_sample(self, file_path: str) -> Dict[str, Union[str, float, Dict, List]]:
        """
        Universal audio analysis that adapts to available libraries and CPU type.
        """
        try:
            logger.info(f"Starting universal analysis of: {file_path}")
            
            # Load audio using the best available method
            y, sr = self._load_audio_universal(file_path)
            
            # Get basic properties
            duration = len(y) / sr
            
            # Perform analysis using available methods
            result = {
                "file_path": file_path,
                "duration": duration,
                "sample_rate": sr,
                "cpu_type": self.config['cpu_type'],
                "analysis_methods": [k for k, v in self.available_methods.items() if v],
                
                # Universal analysis
                "sample_type": self._determine_sample_type_universal(y, sr),
                "category": self._classify_category_universal(file_path, y, sr),
                "bpm": self._detect_bpm_universal(y, sr),
                "key": self._detect_key_universal(y, sr),
                "characteristics": self._analyze_characteristics_universal(y, sr),
                
                "confidence_scores": {},
                "error": None
            }
            
            # Calculate overall confidence
            result["overall_confidence"] = self._calculate_confidence_universal(result)
            
            logger.info(f"Universal analysis complete for: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return {
                "file_path": file_path,
                "duration": 0,
                "sample_type": "unknown",
                "category": "unknown",
                "bpm": 0,
                "key": "unknown",
                "characteristics": {},
                "confidence_scores": {},
                "overall_confidence": 0.0,
                "error": str(e)
            }
    
    def _load_audio_universal(self, file_path: str) -> Tuple[np.ndarray, int]:
        """Load audio using the best available method."""
        import numpy as np
        import soundfile as sf
        
        # Try librosa first if available and safe
        if self.available_methods['librosa'] and self.config['use_advanced_features']:
            try:
                import librosa
                y, sr = librosa.load(file_path, sr=self.sr)
                return y, sr
            except Exception as e:
                logger.warning(f"librosa load failed, falling back to soundfile: {e}")
        
        # Fallback to soundfile
        y, sr_original = sf.read(file_path)
        
        # Convert to mono if stereo
        if len(y.shape) > 1:
            y = np.mean(y, axis=1)
        
        # Simple resampling if needed
        if sr_original != self.sr:
            y = self._simple_resample(y, sr_original, self.sr)
        
        return y, self.sr
    
    def _simple_resample(self, y: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple resampling using linear interpolation."""
        import numpy as np
        
        if orig_sr == target_sr:
            return y
        
        ratio = target_sr / orig_sr
        old_indices = np.arange(len(y))
        new_length = int(len(y) * ratio)
        new_indices = np.linspace(0, len(y) - 1, new_length)
        
        return np.interp(new_indices, old_indices, y)
    
    def _determine_sample_type_universal(self, y: np.ndarray, sr: int) -> str:
        """Universal sample type detection using multiple methods."""
        methods_results = []
        
        # Method 1: Safe energy analysis (always available)
        energy_result = self._sample_type_energy_safe(y)
        methods_results.append(energy_result)
        
        # Method 2: Safe onset detection (always available)
        onset_result = self._sample_type_onset_safe(y)
        methods_results.append(onset_result)
        
        # Method 3: librosa-based (if available and safe)
        if self.available_methods['librosa'] and self.config['use_advanced_features']:
            try:
                librosa_result = self._sample_type_librosa_safe(y, sr)
                methods_results.append(librosa_result)
            except Exception as e:
                logger.warning(f"librosa sample type detection failed: {e}")
        
        # Method 4: aubio-based (if available)
        if self.available_methods['aubio']:
            try:
                aubio_result = self._sample_type_aubio_safe(y, sr)
                methods_results.append(aubio_result)
            except Exception as e:
                logger.warning(f"aubio sample type detection failed: {e}")
        
        # Voting system
        oneshot_votes = sum(1 for result in methods_results if result == "one-shot")
        loop_votes = sum(1 for result in methods_results if result == "loop")
        
        if oneshot_votes > loop_votes:
            return "one-shot"
        elif loop_votes > oneshot_votes:
            return "loop"
        else:
            # Tie-breaker: use duration
            duration = len(y) / sr
            return "one-shot" if duration < 2.0 else "loop"
    
    def _sample_type_energy_safe(self, y: np.ndarray) -> str:
        """Safe energy-based sample type detection."""
        import numpy as np
        
        window_size = self.hop_length
        rms_values = []
        
        for i in range(0, len(y) - window_size, window_size):
            window = y[i:i + window_size]
            rms = np.sqrt(np.mean(window**2))
            rms_values.append(rms)
        
        if len(rms_values) < 2:
            return "one-shot"
        
        rms_values = np.array(rms_values)
        
        # Check for fade-out
        end_portion = rms_values[-int(len(rms_values) * 0.3):]
        start_portion = rms_values[:int(len(rms_values) * 0.3)]
        
        if len(end_portion) == 0 or len(start_portion) == 0:
            return "one-shot"
        
        end_energy = np.mean(end_portion)
        start_energy = np.mean(start_portion)
        
        return "one-shot" if end_energy < start_energy * 0.4 else "loop"
    
    def _sample_type_onset_safe(self, y: np.ndarray) -> str:
        """Safe onset-based sample type detection."""
        import numpy as np
        
        window_size = self.hop_length
        energy_diff = []
        prev_energy = 0
        
        for i in range(0, len(y) - window_size, window_size):
            window = y[i:i + window_size]
            energy = np.sum(window**2)
            
            if i > 0:
                diff = max(0, energy - prev_energy)
                energy_diff.append(diff)
            
            prev_energy = energy
        
        if len(energy_diff) == 0:
            return "one-shot"
        
        energy_diff = np.array(energy_diff)
        threshold = np.mean(energy_diff) + 2 * np.std(energy_diff)
        onsets = np.where(energy_diff > threshold)[0]
        
        return "one-shot" if len(onsets) <= 2 else "loop"
    
    def _sample_type_librosa_safe(self, y: np.ndarray, sr: int) -> str:
        """Safe librosa-based sample type detection."""
        try:
            import librosa
            
            # Use only safe librosa functions
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
            
            return "one-shot" if len(onsets) <= 2 else "loop"
            
        except Exception as e:
            logger.warning(f"Safe librosa analysis failed: {e}")
            return "one-shot"
    
    def _sample_type_aubio_safe(self, y: np.ndarray, sr: int) -> str:
        """Safe aubio-based sample type detection."""
        try:
            import aubio
            import numpy as np
            
            y_aubio = y.astype(np.float32)
            buffer_size = min(1024, len(y_aubio))
            
            if buffer_size < 512:
                return "one-shot"
            
            onset_detector = aubio.onset("default", buffer_size, self.hop_length, sr)
            onsets = 0
            
            for i in range(0, len(y_aubio) - buffer_size, self.hop_length):
                chunk = y_aubio[i:i+buffer_size]
                if len(chunk) == buffer_size:
                    try:
                        if onset_detector(chunk):
                            onsets += 1
                    except:
                        continue
            
            return "one-shot" if onsets <= 2 else "loop"
            
        except Exception as e:
            logger.warning(f"Safe aubio analysis failed: {e}")
            return "one-shot"
    
    def _classify_category_universal(self, file_path: str, y: np.ndarray, sr: int) -> str:
        """Universal category classification with improved drum detection."""
        methods_results = []
        
        # Method 1: Enhanced filename analysis
        filename_result = self._classify_by_filename_enhanced(file_path)
        methods_results.append(filename_result)
        
        # Method 2: Safe frequency analysis
        frequency_result = self._classify_by_frequency_safe(y, sr)
        methods_results.append(frequency_result)
        
        # Method 3: Enhanced spectral analysis
        if self.available_methods['librosa'] and self.config['use_advanced_features']:
            try:
                spectral_result = self._classify_by_spectral_features_enhanced(y, sr)
                methods_results.append(spectral_result)
            except Exception as e:
                logger.warning(f"Enhanced spectral analysis failed: {e}")
        
        # Voting system with better logic
        category_votes = {}
        for result in methods_results:
            if result and result != "unknown":
                category_votes[result] = category_votes.get(result, 0) + 1
        
        if category_votes:
            return max(category_votes, key=category_votes.get)
        
        # Fallback: if no clear category, try to infer from audio characteristics
        return self._fallback_classification(y, sr)

    def _classify_by_filename_enhanced(self, file_path: str) -> str:
        """Enhanced filename classification with better drum detection."""
        path_lower = file_path.lower()
        
        # First check for specific drum types
        for drum_type, keywords in self.drum_type_keywords.items():
            if any(keyword in path_lower for keyword in keywords):
                return "Drums"
        
        # Then check general categories
        for category, keywords in self.category_keywords.items():
            if any(keyword in path_lower for keyword in keywords):
                return category
        
        return "unknown"

    def _classify_by_frequency_safe(self, y: np.ndarray, sr: int) -> str:
        """Safe frequency content analysis."""
        import numpy as np
        
        try:
            fft = np.fft.fft(y)
            magnitude = np.abs(fft)
            freqs = np.fft.fftfreq(len(y), 1/sr)
            
            positive_freqs = freqs[:len(freqs)//2]
            positive_magnitude = magnitude[:len(magnitude)//2]
            
            # Calculate energy in frequency bands
            bass_mask = positive_freqs < 250
            mid_mask = (positive_freqs >= 250) & (positive_freqs < 4000)
            high_mask = positive_freqs >= 4000
            
            bass_energy = np.sum(positive_magnitude[bass_mask])
            mid_energy = np.sum(positive_magnitude[mid_mask])
            high_energy = np.sum(positive_magnitude[high_mask])
            
            total_energy = bass_energy + mid_energy + high_energy
            
            if total_energy == 0:
                return "unknown"
            
            bass_ratio = bass_energy / total_energy
            high_ratio = high_energy / total_energy
            
            if bass_ratio > 0.6:
                return "Bass"
            elif high_ratio > 0.4:
                return "FX"
            else:
                return "Melodic"
                
        except Exception as e:
            logger.warning(f"Frequency analysis failed: {e}")
            return "unknown"
    
    def _classify_by_spectral_features_enhanced(self, y: np.ndarray, sr: int) -> str:
        """Enhanced spectral features analysis."""
        try:
            import librosa
            import numpy as np
            
            # Calculate multiple features
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
            zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(y))
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))
            
            # Calculate additional features for better classification
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfccs, axis=1)
            
            # Calculate onset strength for percussive detection
            onset_strength = np.mean(librosa.onset.onset_strength(y=y, sr=sr))
            
            # More sophisticated classification with improved logic
            if spectral_centroid < 600:  # Very low frequency content
                return "Bass"
            elif onset_strength > 0.5 and zero_crossing_rate > 0.05:  # Strong onsets = drums
                return "Drums"
            elif spectral_rolloff > 8000 and zero_crossing_rate > 0.1:  # High frequency with noise = FX
                return "FX"
            elif 1000 <= spectral_centroid <= 3000 and onset_strength < 0.3:  # Mid-range tonal content
                return "Melodic"
            elif spectral_centroid > 3000 and zero_crossing_rate < 0.08:  # High but smooth = vocals
                return "Vocals"
            elif spectral_centroid < 1000 and onset_strength > 0.3:  # Low with onsets = drums
                return "Drums"
            else:
                return "Melodic"  # Default for tonal content
                
        except Exception as e:
            logger.warning(f"Enhanced spectral features analysis failed: {e}")
            return "unknown"

    def _fallback_classification(self, y: np.ndarray, sr: int) -> str:
        """Fallback classification based on basic audio characteristics."""
        import numpy as np
        
        try:
            # Calculate basic energy distribution
            fft = np.fft.fft(y)
            magnitude = np.abs(fft)
            freqs = np.fft.fftfreq(len(y), 1/sr)
            
            positive_freqs = freqs[:len(freqs)//2]
            positive_magnitude = magnitude[:len(magnitude)//2]
            
            # Energy in different bands
            sub_bass = np.sum(positive_magnitude[positive_freqs < 100])
            bass = np.sum(positive_magnitude[(positive_freqs >= 100) & (positive_freqs < 300)])
            low_mid = np.sum(positive_magnitude[(positive_freqs >= 300) & (positive_freqs < 1000)])
            mid = np.sum(positive_magnitude[(positive_freqs >= 1000) & (positive_freqs < 4000)])
            high = np.sum(positive_magnitude[positive_freqs >= 4000])
            
            total_energy = sub_bass + bass + low_mid + mid + high
            
            if total_energy == 0:
                return "Melodic"  # Safe default
            
            # Calculate ratios
            bass_ratio = (sub_bass + bass) / total_energy
            mid_ratio = (low_mid + mid) / total_energy
            high_ratio = high / total_energy
            
            # Classification based on energy distribution
            if bass_ratio > 0.6:
                return "Bass"
            elif high_ratio > 0.4:
                return "FX"
            elif mid_ratio > 0.5:
                return "Melodic"
            else:
                return "Drums"  # Likely percussive if energy is spread
                
        except Exception as e:
            logger.warning(f"Fallback classification failed: {e}")
            return "Melodic"  # Ultimate fallback
    
    def _detect_bpm_universal(self, y: np.ndarray, sr: int) -> float:
        """Universal BPM detection using multiple methods."""
        import numpy as np
        
        bpm_results = []
        
        # Method 1: Safe autocorrelation (always available)
        try:
            bpm_safe = self._detect_bpm_safe(y, sr)
            if bpm_safe > 0:
                bpm_results.append(bpm_safe)
        except Exception as e:
            logger.warning(f"Safe BPM detection failed: {e}")
        
        # Method 2: librosa (if available and safe)
        if self.available_methods['librosa'] and self.config['use_advanced_features']:
            try:
                import librosa
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                if tempo > 0:
                    bpm_results.append(tempo)
            except Exception as e:
                logger.warning(f"librosa BPM detection failed: {e}")
        
        # Method 3: aubio (if available)
        if self.available_methods['aubio']:
            try:
                bpm_aubio = self._detect_bpm_aubio_safe(y, sr)
                if bpm_aubio > 0:
                    bpm_results.append(bpm_aubio)
            except Exception as e:
                logger.warning(f"aubio BPM detection failed: {e}")
        
        return float(np.median(bpm_results)) if bpm_results else 0.0
    
    def _detect_bpm_safe(self, y: np.ndarray, sr: int) -> float:
        """Safe BPM detection using autocorrelation."""
        import numpy as np
        
        try:
            window_size = self.hop_length
            onset_strength = []
            
            for i in range(0, len(y) - window_size, window_size):
                window = y[i:i + window_size]
                energy = np.sum(window**2)
                onset_strength.append(energy)
            
            if len(onset_strength) < 4:
                return 0.0
            
            onset_strength = np.array(onset_strength)
            autocorr = np.correlate(onset_strength, onset_strength, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            min_period = int(60 / 200 * sr / window_size)  # 200 BPM max
            max_period = int(60 / 60 * sr / window_size)   # 60 BPM min
            
            if max_period >= len(autocorr):
                return 0.0
            
            search_range = autocorr[min_period:max_period]
            if len(search_range) == 0:
                return 0.0
            
            peak_idx = np.argmax(search_range) + min_period
            period_samples = peak_idx * window_size
            period_seconds = period_samples / sr
            bpm = 60.0 / period_seconds
            
            return float(bpm) if 60 <= bpm <= 200 else 0.0
            
        except Exception as e:
            logger.warning(f"Safe BPM detection failed: {e}")
            return 0.0
    
    def _detect_bpm_aubio_safe(self, y: np.ndarray, sr: int) -> float:
        """Safe aubio BPM detection."""
        try:
            import aubio
            import numpy as np
            
            y_aubio = y.astype(np.float32)
            buffer_size = min(1024, len(y_aubio))
            
            if buffer_size < 512:
                return 0.0
            
            tempo_detector = aubio.tempo("default", buffer_size, self.hop_length, sr)
            tempo_values = []
            
            for i in range(0, len(y_aubio) - buffer_size, self.hop_length):
                chunk = y_aubio[i:i+buffer_size]
                if len(chunk) == buffer_size:
                    try:
                        tempo = tempo_detector(chunk)
                        if tempo > 0:
                            tempo_values.append(tempo)
                    except:
                        continue
            
            return np.median(tempo_values) if tempo_values else 0.0
            
        except Exception as e:
            logger.warning(f"Safe aubio BPM detection failed: {e}")
            return 0.0
    
    def _detect_key_universal(self, y: np.ndarray, sr: int) -> str:
        """Universal key detection."""
        key_results = []
        
        # Method 1: Safe pitch analysis (always available)
        try:
            key_safe = self._detect_key_safe(y, sr)
            if key_safe != "unknown":
                key_results.append(key_safe)
        except Exception as e:
            logger.warning(f"Safe key detection failed: {e}")
        
        # Method 2: librosa chroma (if available and safe)
        if self.available_methods['librosa'] and self.config['use_advanced_features']:
            try:
                key_chroma = self._detect_key_chroma_safe(y, sr)
                if key_chroma != "unknown":
                    key_results.append(key_chroma)
            except Exception as e:
                logger.warning(f"librosa key detection failed: {e}")
        
        if not key_results:
            return "unknown"
        
        # Return most common result
        from collections import Counter
        key_counts = Counter(key_results)
        return key_counts.most_common(1)[0][0]
    
    def _detect_key_safe(self, y: np.ndarray, sr: int) -> str:
        """Safe key detection using basic pitch analysis."""
        import numpy as np
        
        try:
            fft = np.fft.fft(y)
            magnitude = np.abs(fft)
            freqs = np.fft.fftfreq(len(y), 1/sr)
            
            positive_freqs = freqs[:len(freqs)//2]
            positive_magnitude = magnitude[:len(magnitude)//2]
            
            if len(positive_magnitude) == 0:
                return "unknown"
            
            peak_idx = np.argmax(positive_magnitude)
            dominant_freq = positive_freqs[peak_idx]
            
            if dominant_freq <= 0:
                return "unknown"
            
            # Convert to note
            a4_freq = 440.0
            semitones_from_a4 = 12 * np.log2(dominant_freq / a4_freq)
            
            note_names = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
            note_idx = int(round(semitones_from_a4)) % 12
            note = note_names[note_idx]
            
            return f"{note} Major"
            
        except Exception as e:
            logger.warning(f"Safe key detection failed: {e}")
            return "unknown"
    
    def _detect_key_chroma_safe(self, y: np.ndarray, sr: int) -> str:
        """Safe chroma-based key detection using librosa."""
        try:
            import librosa
            import numpy as np
            
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            chroma_mean = chroma_mean / np.sum(chroma_mean)
            
            best_correlation = -1
            best_key = "unknown"
            
            for key_name, profile in self.key_profiles.items():
                profile_norm = np.array(profile) / np.sum(profile)
                correlation = np.corrcoef(chroma_mean, profile_norm)[0, 1]
                
                if correlation > best_correlation:
                    best_correlation = correlation
                    best_key = key_name
            
            return best_key if best_correlation > 0.6 else "unknown"
            
        except Exception as e:
            logger.warning(f"Chroma key detection failed: {e}")
            return "unknown"
    
    def _analyze_characteristics_universal(self, y: np.ndarray, sr: int) -> Dict:
        """Universal characteristic analysis."""
        import numpy as np
        
        characteristics = {}
        
        try:
            # Basic characteristics (always available)
            characteristics["duration"] = len(y) / sr
            characteristics["sample_rate"] = sr
            characteristics["cpu_type"] = self.config['cpu_type']
            
            # Safe characteristics
            rms = np.sqrt(np.mean(y**2))
            characteristics["rms_mean"] = float(rms)
            
            zero_crossings = np.where(np.diff(np.signbit(y)))[0]
            zcr = len(zero_crossings) / len(y)
            characteristics["zero_crossing_rate"] = float(zcr)
            
            # Safe spectral analysis
            fft = np.fft.fft(y)
            magnitude = np.abs(fft)
            freqs = np.fft.fftfreq(len(y), 1/sr)
            
            positive_freqs = freqs[:len(freqs)//2]
            positive_magnitude = magnitude[:len(magnitude)//2]
            
            if np.sum(positive_magnitude) > 0:
                spectral_centroid = np.sum(positive_freqs * positive_magnitude) / np.sum(positive_magnitude)
                characteristics["spectral_centroid"] = float(spectral_centroid)
            else:
                characteristics["spectral_centroid"] = 0.0
            
            # Advanced characteristics (if available)
            if self.available_methods['librosa'] and self.config['use_advanced_features']:
                try:
                    import librosa
                    
                    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
                    characteristics["spectral_rolloff_mean"] = float(np.mean(spectral_rolloff))
                    
                    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
                    characteristics["spectral_bandwidth_mean"] = float(np.mean(spectral_bandwidth))
                    
                except Exception as e:
                    logger.warning(f"Advanced librosa characteristics failed: {e}")
            
        except Exception as e:
            logger.warning(f"Error extracting characteristics: {e}")
        
        return characteristics
    
    def _calculate_confidence_universal(self, result: Dict) -> float:
        """Calculate confidence score based on available methods."""
        import numpy as np
        
        confidence_factors = []
        
        # Base confidence factors
        if result["sample_type"] != "unknown":
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.3)
        
        if result["category"] != "unknown":
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.4)
        
        # Bonus for advanced methods
        if self.config['use_advanced_features']:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.7)
        
        # Duration factor
        duration = result.get("duration", 0)
        if duration > 0.5:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        return float(np.mean(confidence_factors)) if confidence_factors else 0.0
    
    def get_waveform_data(self, y: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
        """Get waveform data for visualization."""
        import numpy as np
        times = np.arange(len(y)) / sr
        return times, y
    
    def get_system_info(self) -> Dict:
        """Get information about the analysis system."""
        return {
            "cpu_type": self.config['cpu_type'],
            "cpu_brand": self.cpu_detector.cpu_info.get('brand', 'Unknown'),
            "available_methods": self.available_methods,
            "use_advanced_features": self.config['use_advanced_features'],
            "environment_vars": self.config['environment_vars']
        }

# Create a global instance for easy access
universal_audio_analyzer = UniversalAudioAnalyzer() 