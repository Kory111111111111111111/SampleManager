import librosa
import numpy as np
from typing import Dict, Union, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioAnalyzer:
    def __init__(self):
        # Analysis parameters
        self.sr = 22050  # Sample rate
        self.hop_length = 512
        self.onset_threshold = 0.5
        self.minimum_silence = 0.1  # seconds

    def analyze_sample(self, file_path: str) -> Dict[str, Union[str, float, Dict]]:
        """
        Analyze an audio sample to determine if it's a one-shot or loop,
        and extract relevant characteristics.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Load the audio file
            y, sr = librosa.load(file_path, sr=self.sr)
            
            # Get basic properties
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Analyze the sample
            result = {
                "duration": duration,
                "type": self._determine_sample_type(y, sr),
                "characteristics": self._analyze_characteristics(y, sr),
                "error": None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return {
                "duration": 0,
                "type": "unknown",
                "characteristics": {},
                "error": str(e)
            }

    def _determine_sample_type(self, y: np.ndarray, sr: int) -> str:
        """
        Determine if the sample is a one-shot or loop based on its characteristics.
        """
        # Get onset strength
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Detect onsets
        onsets = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=sr,
            threshold=self.onset_threshold
        )
        
        # Analyze RMS energy
        rms = librosa.feature.rms(y=y)[0]
        
        # Check for silence at the end
        end_silence = self._check_end_silence(rms)
        
        # Decision logic
        if len(onsets) == 1 and end_silence:
            return "one-shot"
        elif self._check_loop_compatibility(y, sr):
            return "loop"
        else:
            return "one-shot"

    def _check_end_silence(self, rms: np.ndarray) -> bool:
        """
        Check if the sample ends in silence.
        """
        # Consider the last 10% of the sample
        end_section = rms[-int(len(rms) * 0.1):]
        threshold = np.mean(rms) * 0.1
        
        return np.mean(end_section) < threshold

    def _check_loop_compatibility(self, y: np.ndarray, sr: int) -> bool:
        """
        Check if the sample is suitable for looping.
        """
        # Analyze start and end segments
        start_segment = y[:sr//4]  # First 0.25 seconds
        end_segment = y[-sr//4:]   # Last 0.25 seconds
        
        # Compare waveform similarity
        correlation = np.correlate(start_segment, end_segment)
        
        # Check tempo consistency
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo_stability = self._check_tempo_stability(y, sr)
        
        return (correlation.max() > 0.7) and tempo_stability

    def _check_tempo_stability(self, y: np.ndarray, sr: int) -> bool:
        """
        Check if the tempo is stable throughout the sample.
        """
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)
        
        # Split sample into segments and check tempo consistency
        n_segments = 4
        segment_length = len(y) // n_segments
        tempo_variations = []
        
        for i in range(n_segments):
            start = i * segment_length
            end = start + segment_length
            segment = y[start:end]
            onset_env_segment = librosa.onset.onset_strength(y=segment, sr=sr)
            tempo_segment = librosa.beat.tempo(onset_envelope=onset_env_segment, sr=sr)
            tempo_variations.append(tempo_segment)
        
        # Check if tempo variations are within 5% of the main tempo
        tempo_stability = all(
            abs(t - tempo) / tempo < 0.05 
            for t in tempo_variations
        )
        
        return tempo_stability

    def _analyze_characteristics(self, y: np.ndarray, sr: int) -> Dict:
        """
        Extract additional characteristics of the sample.
        """
        characteristics = {}
        
        # Spectral characteristics
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        characteristics["spectral_centroid"] = float(np.mean(spectral_centroid))
        
        # Temporal characteristics
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        characteristics["tempo"] = float(tempo)
        
        # Energy characteristics
        rms = librosa.feature.rms(y=y)[0]
        characteristics["rms_mean"] = float(np.mean(rms))
        characteristics["rms_std"] = float(np.std(rms))
        
        # Pitch characteristics
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        characteristics["pitch_mean"] = float(np.mean(pitches[magnitudes > 0]))
        
        return characteristics

    def get_waveform_data(self, y: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get waveform data for visualization.
        """
        times = librosa.times_like(y)
        return times, y
