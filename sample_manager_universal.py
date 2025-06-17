import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QApplication

# Import the universal audio analyzer
from audio_analysis_universal import universal_audio_analyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalSampleManager(QObject):
    """
    Universal Sample Manager that works with any CPU type.
    Uses the Universal Audio Analyzer for comprehensive audio analysis.
    """
    
    # Signals for UI updates
    sample_analyzed = pyqtSignal(str, dict)  # file_path, analysis_result
    analysis_progress = pyqtSignal(int, int)  # current, total
    analysis_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, samples_directory: str = "samples"):
        super().__init__()
        
        self.samples_directory = Path(samples_directory)
        self.cache_file = Path("sample_cache_universal.json")
        
        # Sample cache with comprehensive analysis results
        self.sample_cache = {}
        
        # Load existing cache
        self.load_cache()
        
        # Get system information
        self.system_info = universal_audio_analyzer.get_system_info()
        logger.info(f"UniversalSampleManager initialized for {self.system_info['cpu_type']} CPU")
        
        # Auto-scan for files if cache is empty
        if not self.sample_cache:
            self._auto_scan_samples()
        
        # Analysis statistics
        self.analysis_stats = {
            "total_analyzed": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "cpu_type": self.system_info['cpu_type'],
            "available_methods": [k for k, v in self.system_info['available_methods'].items() if v]
        }
    
    def load_cache(self):
        """Load sample analysis cache from file."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.sample_cache = json.load(f)
                logger.info(f"Loaded {len(self.sample_cache)} cached analyses")
            else:
                self.sample_cache = {}
                logger.info("No existing cache found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.sample_cache = {}
    
    def save_cache(self):
        """Save sample analysis cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.sample_cache, f, indent=2)
            logger.info(f"Saved {len(self.sample_cache)} analyses to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get_audio_files(self) -> List[Path]:
        """Get all audio files in the samples directory."""
        audio_extensions = {'.wav', '.mp3', '.flac', '.aiff', '.m4a', '.ogg'}
        audio_files = []
        
        if not self.samples_directory.exists():
            logger.warning(f"Samples directory {self.samples_directory} does not exist")
            return audio_files
        
        for file_path in self.samples_directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                audio_files.append(file_path)
        
        logger.info(f"Found {len(audio_files)} audio files")
        return audio_files
    
    def _auto_scan_samples(self):
        """Auto-scan for existing samples and populate basic structure."""
        logger.info("Auto-scanning for existing samples...")
        
        if not self.samples_directory.exists():
            logger.info("Samples directory doesn't exist, creating basic structure...")
            # Create basic category structure
            basic_categories = {
                "Bass": ["808", "Bass Loops", "Electric Bass", "Synth Bass"],
                "Drums": ["Cymbals", "Full Loops", "Hi-Hats", "Kicks", "Percussion", "Snares"],
                "FX": ["Ambient", "Downlifters", "Foley", "Impacts", "Risers"],
                "Melodic": ["Keys", "Melodic Loops", "Pads", "Plucks", "Synth Leads"],
                "Vocals": ["Chops", "One-Shots", "Phrases", "Vocal Loops"]
            }
            
            for category, subcategories in basic_categories.items():
                for subcategory in subcategories:
                    category_path = self.samples_directory / category / subcategory
                    category_path.mkdir(parents=True, exist_ok=True)
            
            logger.info("Created basic sample directory structure")
            return
        
        # Scan existing files and add them to cache with basic info
        audio_files = self.get_audio_files()
        for file_path in audio_files:
            try:
                file_key = str(file_path.relative_to(self.samples_directory))
                if file_key not in self.sample_cache:
                    # Add basic file info without full analysis
                    basic_info = {
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_size": file_path.stat().st_size,
                        "relative_path": file_key,
                        "duration": 0,
                        "sample_type": "unknown",
                        "category": "unknown",
                        "bpm": 0,
                        "key": "unknown",
                        "characteristics": {},
                        "confidence_scores": {},
                        "overall_confidence": 0.0,
                        "error": None,
                        "cpu_type": self.system_info['cpu_type'],
                        "analyzed": False  # Mark as not fully analyzed
                    }
                    self.sample_cache[file_key] = basic_info
            except Exception as e:
                logger.warning(f"Error scanning file {file_path}: {e}")
        
        if audio_files:
            logger.info(f"Auto-scanned {len(audio_files)} existing audio files")
            self.save_cache()
    
    def analyze_sample(self, file_path: Union[str, Path]) -> Dict:
        """
        Analyze a single sample using the universal analyzer.
        """
        file_path = Path(file_path)
        file_key = str(file_path.relative_to(self.samples_directory))
        
        # Check cache first
        if file_key in self.sample_cache:
            cached_result = self.sample_cache[file_key]
            # Check if cache is from same CPU type and has all required fields
            if (cached_result.get('cpu_type') == self.system_info['cpu_type'] and
                all(key in cached_result for key in ['sample_type', 'category', 'bpm', 'key'])):
                logger.info(f"Using cached analysis for {file_path.name}")
                return cached_result
        
        # Perform new analysis
        try:
            logger.info(f"Analyzing {file_path.name} with universal analyzer...")
            result = universal_audio_analyzer.analyze_sample(str(file_path))
            
            # Add additional metadata
            result.update({
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "relative_path": file_key,
                "analysis_timestamp": QTimer().remainingTime(),  # Simple timestamp
                "analyzer_version": "universal_1.0"
            })
            
            # Cache the result
            self.sample_cache[file_key] = result
            
            # Update statistics
            self.analysis_stats["total_analyzed"] += 1
            if result.get("error"):
                self.analysis_stats["failed_analyses"] += 1
            else:
                self.analysis_stats["successful_analyses"] += 1
            
            # Emit signal for UI update
            self.sample_analyzed.emit(str(file_path), result)
            
            logger.info(f"Analysis complete for {file_path.name}: {result['sample_type']}, {result['category']}")
            return result
            
        except Exception as e:
            error_msg = f"Error analyzing {file_path.name}: {str(e)}"
            logger.error(error_msg)
            
            # Create error result
            error_result = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "relative_path": file_key,
                "duration": 0,
                "sample_type": "unknown",
                "category": "unknown",
                "bpm": 0,
                "key": "unknown",
                "characteristics": {},
                "confidence_scores": {},
                "overall_confidence": 0.0,
                "error": str(e),
                "cpu_type": self.system_info['cpu_type']
            }
            
            self.analysis_stats["total_analyzed"] += 1
            self.analysis_stats["failed_analyses"] += 1
            
            self.error_occurred.emit(error_msg)
            return error_result
    
    def analyze_all_samples(self):
        """Analyze all samples in the directory."""
        audio_files = self.get_audio_files()
        
        if not audio_files:
            logger.warning("No audio files found to analyze")
            self.analysis_complete.emit()
            return
        
        logger.info(f"Starting analysis of {len(audio_files)} files...")
        
        for i, file_path in enumerate(audio_files):
            self.analysis_progress.emit(i + 1, len(audio_files))
            self.analyze_sample(file_path)
            
            # Process events to keep UI responsive
            QApplication.processEvents()
        
        # Save cache after analysis
        self.save_cache()
        
        logger.info("Analysis of all samples complete")
        self.analysis_complete.emit()
    
    def get_samples(self, category: Optional[str] = None, 
                   subcategory: Optional[str] = None) -> List[Dict]:
        """Get samples with optional filtering and file existence checking."""
        samples = []
        invalid_keys = []
        
        for file_key, analysis in self.sample_cache.items():
            # Check if the file actually exists
            expected_path = self.samples_directory / file_key
            actual_file_path = analysis.get('file_path', '')
            
            # If file doesn't exist at expected location, mark for removal
            if not expected_path.exists() and not Path(actual_file_path).exists():
                invalid_keys.append(file_key)
                continue
            
            # Update file_path to point to correct location if needed
            if expected_path.exists():
                analysis['file_path'] = str(expected_path)
            
            # Apply category filter
            if category:
                # Check both analysis category and file path structure
                analysis_category = analysis.get('category', '').lower()
                path_category = Path(file_key).parts[0].lower() if Path(file_key).parts else ''
                
                if (analysis_category != category.lower() and 
                    path_category != category.lower()):
                    continue
            
            # Apply subcategory filter
            if subcategory:
                # Check if subcategory is in the file path structure
                path_parts = Path(file_key).parts
                if len(path_parts) < 2 or path_parts[1].lower() != subcategory.lower():
                    continue
            
            samples.append(analysis)
        
        # Clean up invalid entries
        if invalid_keys:
            for key in invalid_keys:
                del self.sample_cache[key]
            self.save_cache()
            logger.info(f"Removed {len(invalid_keys)} invalid cache entries")
        
        return samples
    
    def get_sample_suggestions(self, 
                             sample_type: Optional[str] = None,
                             category: Optional[str] = None,
                             bpm_range: Optional[Tuple[float, float]] = None,
                             key: Optional[str] = None,
                             min_confidence: float = 0.0) -> List[Dict]:
        """Get sample suggestions based on criteria."""
        suggestions = []
        
        for analysis in self.sample_cache.values():
            # Check criteria
            if sample_type and analysis.get('sample_type') != sample_type:
                continue
            
            if category and analysis.get('category') != category:
                continue
            
            if bpm_range:
                bpm = analysis.get('bpm', 0)
                if not (bpm_range[0] <= bpm <= bpm_range[1]):
                    continue
            
            if key and analysis.get('key') != key:
                continue
            
            if analysis.get('overall_confidence', 0) < min_confidence:
                continue
            
            suggestions.append(analysis)
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x.get('overall_confidence', 0), reverse=True)
        return suggestions
    
    def search_samples(self, query: str) -> List[Dict]:
        """Search samples by filename, category, or characteristics."""
        query_lower = query.lower()
        results = []
        
        for analysis in self.sample_cache.values():
            # Search in filename
            if query_lower in analysis.get('file_name', '').lower():
                results.append(analysis)
                continue
            
            # Search in category
            if query_lower in analysis.get('category', '').lower():
                results.append(analysis)
                continue
            
            # Search in sample type
            if query_lower in analysis.get('sample_type', '').lower():
                results.append(analysis)
                continue
            
            # Search in key
            if query_lower in analysis.get('key', '').lower():
                results.append(analysis)
                continue
        
        return results
    
    def get_categories(self) -> Dict[str, List[str]]:
        """Get all categories and their subcategories."""
        categories = {}
        
        # First, scan the directory structure directly
        if self.samples_directory.exists():
            for category_dir in self.samples_directory.iterdir():
                if category_dir.is_dir():
                    category_name = category_dir.name
                    categories[category_name] = []
                    
                    for subcategory_dir in category_dir.iterdir():
                        if subcategory_dir.is_dir():
                            subcategory_name = subcategory_dir.name
                            if subcategory_name not in categories[category_name]:
                                categories[category_name].append(subcategory_name)
        
        # Also add categories from cached files (in case of files not in standard structure)
        for file_key, analysis in self.sample_cache.items():
            path_parts = Path(file_key).parts
            if len(path_parts) >= 2:
                category = path_parts[0]
                subcategory = path_parts[1]
                
                if category not in categories:
                    categories[category] = []
                
                if subcategory not in categories[category]:
                    categories[category].append(subcategory)
        
        return categories
    
    def get_current_category_subcategory(self, file_path: str) -> Tuple[str, str]:
        """Extract category and subcategory from file path."""
        try:
            path = Path(file_path)
            relative_path = path.relative_to(self.samples_directory)
            parts = relative_path.parts
            
            if len(parts) >= 2:
                category = parts[0]
                subcategory = parts[1]
                return category, subcategory
            elif len(parts) == 1:
                return "Unknown", "Unknown"
            else:
                return "Unknown", "Unknown"
                
        except Exception:
            return "Unknown", "Unknown"
    
    def remove_sample(self, file_path: str):
        """Remove a sample from cache and optionally delete file."""
        try:
            path = Path(file_path)
            file_key = str(path.relative_to(self.samples_directory))
            
            # Remove from cache
            if file_key in self.sample_cache:
                del self.sample_cache[file_key]
                logger.info(f"Removed {file_path} from cache")
            
            # Save updated cache
            self.save_cache()
            
        except Exception as e:
            logger.error(f"Error removing sample {file_path}: {e}")
    
    def get_analysis_stats(self) -> Dict:
        """Get analysis statistics."""
        stats = self.analysis_stats.copy()
        stats.update({
            "cached_samples": len(self.sample_cache),
            "success_rate": (stats["successful_analyses"] / max(stats["total_analyzed"], 1)) * 100,
            "system_info": self.system_info
        })
        return stats
    
    def clear_cache(self):
        """Clear the analysis cache."""
        self.sample_cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cache cleared")
    
    def export_analysis_results(self, output_file: str):
        """Export analysis results to JSON file."""
        try:
            export_data = {
                "system_info": self.system_info,
                "analysis_stats": self.get_analysis_stats(),
                "samples": self.sample_cache
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Analysis results exported to {output_file}")
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")

# Create a global instance
universal_sample_manager = UniversalSampleManager() 