import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Set
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QApplication
from contextlib import suppress

# Import the universal audio analyzer
from audio_analysis_universal import universal_audio_analyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalSampleManager(QObject):
    """
    Universal Sample Manager that indexes samples from their original locations.
    Works as a library indexer rather than importing/copying files.
    Uses the Universal Audio Analyzer for comprehensive audio analysis.
    """
    
    # Signals for UI updates
    sample_analyzed = pyqtSignal(str, dict)  # file_path, analysis_result
    analysis_progress = pyqtSignal(int, int)  # current, total
    analysis_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    directory_scanned = pyqtSignal(str, int)  # directory_path, files_found
    
    def __init__(self):
        super().__init__()
        
        self.cache_file = Path("sample_cache_universal.json")
        
        # Sample cache with comprehensive analysis results (indexed by absolute file path)
        self.sample_cache = {}
        
        # Set of directories being tracked for samples
        self.tracked_directories = set()
        
        # Load existing cache and tracked directories
        self.load_cache()
        
        # Check if cache needs migration
        if self._needs_cache_migration():
            logger.info("Cache migration needed - will be performed on first use")
            self._migration_pending = True
        else:
            self._migration_pending = False
        
        # Get system information
        self.system_info = universal_audio_analyzer.get_system_info()
        logger.info(f"UniversalSampleManager initialized for {self.system_info['cpu_type']} CPU")
        
        # Analysis statistics
        self.analysis_stats = {
            "total_analyzed": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "cpu_type": self.system_info['cpu_type'],
            "available_methods": [k for k, v in self.system_info['available_methods'].items() if v],
            "tracked_directories": len(self.tracked_directories)
        }
    
    def load_cache(self):
        """Load sample analysis cache and tracked directories from file."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                
                # Handle both old format (just cache) and new format (cache + directories)
                if isinstance(data, dict) and "sample_cache" in data:
                    self.sample_cache = data["sample_cache"]
                    self.tracked_directories = set(data.get("tracked_directories", []))
                else:
                    # Old format - just the cache
                    self.sample_cache = data
                    self.tracked_directories = set()
                
                logger.info(f"Loaded {len(self.sample_cache)} cached analyses from {len(self.tracked_directories)} tracked directories")
            else:
                self.sample_cache = {}
                self.tracked_directories = set()
                logger.info("No existing cache found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.sample_cache = {}
            self.tracked_directories = set()
    
    def save_cache(self):
        """Save sample analysis cache and tracked directories to file."""
        try:
            data = {
                "sample_cache": self.sample_cache,
                "tracked_directories": list(self.tracked_directories)
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.sample_cache)} analyses and {len(self.tracked_directories)} tracked directories to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def add_directory_to_index(self, directory_path: Union[str, Path], auto_analyze: bool = True) -> int:
        """
        Add a directory to the sample index. Scans for audio files and optionally analyzes them.
        
        Args:
            directory_path: Path to directory to scan for samples
            auto_analyze: Whether to automatically analyze samples for better categorization
            
        Returns:
            Number of new audio files found and indexed
        """
        directory_path = Path(directory_path).resolve()
        
        if not self._is_valid_directory(directory_path):
            return 0
        
        # Add to tracked directories
        self.tracked_directories.add(str(directory_path))
        
        # Scan for audio files
        audio_files = self._get_audio_files_in_directory(directory_path)
        stats = self._process_audio_files(audio_files, auto_analyze)
        
        # Save updated cache
        self.save_cache()
        
        # Emit directory scanned signal
        self.directory_scanned.emit(str(directory_path), stats["new_files"])
        
        self._log_indexing_results(directory_path, stats, auto_analyze)
        
        return stats["new_files"]
    
    def _is_valid_directory(self, directory_path: Path) -> bool:
        """Check if directory path is valid."""
        if not directory_path.exists() or not directory_path.is_dir():
            logger.warning(f"Directory {directory_path} does not exist or is not a directory")
            return False
        return True
    
    def _process_audio_files(self, audio_files: List[Path], auto_analyze: bool) -> Dict[str, int]:
        """Process a list of audio files for indexing."""
        stats = {"new_files": 0, "analyzed_files": 0}
        
        logger.info(f"Processing {len(audio_files)} audio files")
        
        for i, file_path in enumerate(audio_files):
            file_key = str(file_path)
            
            if self._handle_existing_file(file_key, file_path, auto_analyze, stats):
                continue
            
            # Add new file to index
            if self._index_new_file(file_path, auto_analyze, stats):
                stats["new_files"] += 1
            
            # Emit progress signal
            if i % 10 == 0 or i == len(audio_files) - 1:
                self.analysis_progress.emit(i + 1, len(audio_files))
        
        return stats
    
    def _handle_existing_file(self, file_key: str, file_path: Path, auto_analyze: bool, stats: Dict[str, int]) -> bool:
        """Handle files that are already in cache. Returns True if file was handled and should be skipped."""
        if file_key not in self.sample_cache:
            return False
            
        if file_path.exists():
            # File exists, check if it needs analysis
            if auto_analyze and not self.sample_cache[file_key].get("analyzed", False):
                try:
                    result = self.analyze_sample(file_path)
                    if not result.get("error"):
                        stats["analyzed_files"] += 1
                except Exception as e:
                    logger.warning(f"Failed to analyze existing file {file_path}: {e}")
            return True  # Already indexed
        else:
            # File no longer exists, remove from cache
            del self.sample_cache[file_key]
            return False
    
    def _index_new_file(self, file_path: Path, auto_analyze: bool, stats: Dict[str, int]) -> bool:
        """Index a new audio file. Returns True if successful."""
        try:
            file_key = str(file_path)
            
            if auto_analyze:
                return self._analyze_and_index_file(file_path, file_key, stats)
            else:
                # Basic indexing without analysis
                basic_info = self._create_basic_file_info(file_path)
                self.sample_cache[file_key] = basic_info
                return True
                
        except Exception as e:
            logger.warning(f"Error indexing file {file_path}: {e}")
            return False
    
    def _analyze_and_index_file(self, file_path: Path, file_key: str, stats: Dict[str, int]) -> bool:
        """Analyze and index a single file."""
        try:
            analysis_result = universal_audio_analyzer.analyze_sample(str(file_path))
            
            # Add file metadata using extracted method
            self._add_file_metadata_to_analysis(analysis_result, file_path)
            
            self.sample_cache[file_key] = analysis_result
            stats["analyzed_files"] += 1
            logger.debug(f"Analyzed and indexed: {file_path.name}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
            # Fall back to basic indexing
            basic_info = self._create_basic_file_info(file_path)
            self.sample_cache[file_key] = basic_info
            return True
    
    def _add_file_metadata_to_analysis(self, analysis_result: Dict, file_path: Path):
        """Add file metadata to analysis result."""
        analysis_result.update({
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "directory": str(file_path.parent),
            "analysis_timestamp": QTimer().remainingTime(),
            "analyzer_version": "universal_1.0",
            "analyzed": True
        })
    
    def _log_indexing_results(self, directory_path: Path, stats: Dict[str, int], auto_analyze: bool):
        """Log the results of directory indexing."""
        if auto_analyze and stats["analyzed_files"] > 0:
            logger.info(f"Indexed {stats['new_files']} new files and analyzed {stats['analyzed_files']} files from {directory_path}")
        else:
            logger.info(f"Indexed {stats['new_files']} new files from {directory_path}")
    
    def _create_basic_file_info(self, file_path: Path) -> Dict:
        """Create basic file info for indexing without analysis."""
        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "directory": str(file_path.parent),
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
    
    def remove_directory_from_index(self, directory_path: Union[str, Path]):
        """
        Remove a directory from the index and clean up its samples from cache.
        
        Args:
            directory_path: Path to directory to remove from index
        """
        directory_path = str(Path(directory_path).resolve())
        
        if directory_path in self.tracked_directories:
            self.tracked_directories.remove(directory_path)
            
            # Remove all samples from this directory from cache
            files_to_remove = [
                file_path for file_path in self.sample_cache.keys()
                if file_path.startswith(directory_path)
            ]
            
            for file_path in files_to_remove:
                del self.sample_cache[file_path]
            
            self.save_cache()
            logger.info(f"Removed directory {directory_path} and {len(files_to_remove)} samples from index")
    
    def refresh_index(self) -> Dict[str, int]:
        """
        Refresh the entire index by rescanning all tracked directories.
        
        Returns:
            Dictionary with statistics about the refresh operation
        """
        # Clean up non-existent files first
        files_to_remove = [file_path for file_path in self.sample_cache.keys() 
                          if not Path(file_path).exists()]
        
        for file_path in files_to_remove:
            del self.sample_cache[file_path]

        stats = {
            "directories_scanned": 0,
            "new_files": 0,
            "removed_files": len(files_to_remove),
            "updated_files": 0
        }
        
        # Rescan all tracked directories
        tracked_dirs = list(self.tracked_directories)  # Copy to avoid modification during iteration
        for directory in tracked_dirs:
            directory_path = Path(directory)
            if directory_path.exists():
                new_files = self.add_directory_to_index(directory_path)
                stats["new_files"] += new_files
                stats["directories_scanned"] += 1
            else:
                # Directory no longer exists, remove it
                self.remove_directory_from_index(directory)
        
        logger.info(f"Index refresh complete: {stats}")
        return stats
    
    def _get_audio_files_in_directory(self, directory_path: Path) -> List[Path]:
        """Get all audio files in a directory recursively."""
        audio_extensions = {'.wav', '.mp3', '.flac', '.aiff', '.aif', '.m4a', '.ogg', '.wma'}
        
        try:
            return [file_path for file_path in directory_path.rglob('*')
                   if file_path.is_file() and file_path.suffix.lower() in audio_extensions]
        except Exception as e:
            logger.warning(f"Error scanning directory {directory_path}: {e}")
            return []
    
    def get_audio_files(self) -> List[Path]:
        """Get all audio files currently in the index."""
        return [Path(file_path) for file_path in self.sample_cache.keys() if Path(file_path).exists()]
    
    def get_tracked_directories(self) -> List[str]:
        """Get list of currently tracked directories."""
        return list(self.tracked_directories)
    
    def analyze_sample(self, file_path: Union[str, Path]) -> Dict:
        """
        Analyze a single sample using the universal analyzer.
        """
        file_path = Path(file_path).resolve()
        file_key = str(file_path)
        
        # Check cache first
        if self._should_use_cached_analysis(file_key):
            logger.info(f"Using cached analysis for {file_path.name}")
            return self.sample_cache[file_key]
        
        # Perform new analysis
        try:
            logger.info(f"Analyzing {file_path.name} with universal analyzer...")
            result = universal_audio_analyzer.analyze_sample(str(file_path))
            
            # Add additional metadata using extracted method
            self._add_file_metadata_to_analysis(result, file_path)
            
            # Cache the result
            self.sample_cache[file_key] = result
            
            # Update statistics
            self._update_analysis_statistics(result)
            
            # Emit signal for UI update
            self.sample_analyzed.emit(str(file_path), result)
            
            logger.info(f"Analysis complete for {file_path.name}: {result['sample_type']}, {result['category']}")
            return result
            
        except Exception as e:
            return self._create_error_result(file_path, e)
    
    def _should_use_cached_analysis(self, file_key: str) -> bool:
        """Check if cached analysis should be used."""
        if file_key not in self.sample_cache:
            return False
            
        cached_result = self.sample_cache[file_key]
        # Check if cache is from same CPU type and has all required fields
        return (cached_result.get('cpu_type') == self.system_info['cpu_type'] and
                all(key in cached_result for key in ['sample_type', 'category', 'bpm', 'key']) and
                cached_result.get('analyzed', False))
    
    def _update_analysis_statistics(self, result: Dict):
        """Update analysis statistics based on result."""
        self.analysis_stats["total_analyzed"] += 1
        if result.get("error"):
            self.analysis_stats["failed_analyses"] += 1
        else:
            self.analysis_stats["successful_analyses"] += 1
    
    def _create_error_result(self, file_path: Path, error: Exception) -> Dict:
        """Create an error result for failed analysis."""
        error_msg = f"Error analyzing {file_path.name}: {str(error)}"
        logger.error(error_msg)
        
        # Create error result
        error_result = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "directory": str(file_path.parent),
            "duration": 0,
            "sample_type": "unknown",
            "category": "unknown",
            "bpm": 0,
            "key": "unknown",
            "characteristics": {},
            "confidence_scores": {},
            "overall_confidence": 0.0,
            "error": str(error),
            "cpu_type": self.system_info['cpu_type'],
            "analyzed": True
        }
        
        # Cache the error result to avoid repeated failures
        file_key = str(file_path)
        self.sample_cache[file_key] = error_result
        
        self.analysis_stats["total_analyzed"] += 1
        self.analysis_stats["failed_analyses"] += 1
        
        self.error_occurred.emit(error_msg)
        return error_result
    
    def analyze_all_samples(self):
        """Analyze all samples in the index."""
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
        # Ensure cache is migrated
        self._ensure_cache_migrated()
        
        samples = []
        invalid_keys = []
        
        for file_key, analysis in self.sample_cache.items():
            # Check if the file actually exists
            if not self._validate_file_existence(file_key, analysis, invalid_keys):
                continue
            
            # Apply filters
            if not self._passes_category_filter(analysis, category):
                continue
                
            if not self._passes_subcategory_filter(analysis, subcategory):
                continue
            
            samples.append(analysis)
        
        # Clean up invalid entries
        self._cleanup_invalid_entries(invalid_keys)
        
        # Sort by file name for consistent display
        samples.sort(key=lambda x: x.get('file_name', '').lower())
        
        return samples
    
    def _validate_file_existence(self, file_key: str, analysis: Dict, invalid_keys: List[str]) -> bool:
        """Validate if file exists and update analysis if needed."""
        try:
            file_path = Path(file_key).resolve()
            
            # If file doesn't exist, mark for removal
            if not file_path.exists():
                invalid_keys.append(file_key)
                return False
            
            # Update file_path in analysis if needed
            analysis['file_path'] = str(file_path)
            return True
            
        except Exception:
            invalid_keys.append(file_key)
            return False
    
    def _passes_category_filter(self, analysis: Dict, category: Optional[str]) -> bool:
        """Check if analysis passes category filter."""
        if not category:
            return True
            
        if analysis.get('manual_override'):
            analysis_category = analysis.get('manual_category', '').lower()
        else:
            analysis_category = analysis.get('category', '').lower()
        
        return analysis_category == category.lower()
    
    def _passes_subcategory_filter(self, analysis: Dict, subcategory: Optional[str]) -> bool:
        """Check if analysis passes subcategory filter."""
        if not subcategory:
            return True
            
        return self._matches_subcategory(analysis, subcategory.lower())
    
    def _cleanup_invalid_entries(self, invalid_keys: List[str]):
        """Clean up invalid cache entries."""
        for key in invalid_keys:
            logger.info(f"Removing invalid cache entry: {key}")
            del self.sample_cache[key]
        
        if invalid_keys:
            self.save_cache()
    
    def _matches_subcategory(self, analysis: Dict, subcategory: str) -> bool:
        """Check if an analysis matches a given subcategory."""
        # Check for manual overrides first
        if analysis.get('manual_override'):
            manual_subcategory = analysis.get('manual_subcategory', '').lower()
            return manual_subcategory == subcategory.lower()
        
        # Get analysis data
        sample_type = analysis.get('sample_type', '').lower()
        file_name = analysis.get('file_name', '').lower()
        file_path = analysis.get('file_path', '').lower()
        category = analysis.get('category', '').lower()
        
        # Get keywords for this subcategory
        keywords = self._get_subcategory_keywords().get(subcategory.lower(), [subcategory.lower()])
        
        # Check if any keywords match
        if self._keyword_matches_file(keywords, file_name, file_path):
            return True
        
        # Enhanced matching based on analysis results
        return self._enhanced_subcategory_matching(category, subcategory.lower(), sample_type, file_name, keywords)
    
    def _get_subcategory_keywords(self) -> Dict[str, List[str]]:
        """Get the mapping of subcategories to their keywords."""
        return {
            'kicks': ['kick', 'bd', 'bassdrum', 'bass drum'],
            'snares': ['snare', 'sd', 'snr'],
            'claps': ['clap', 'handclap', 'hand clap'],
            'closed hi-hats': ['closed hat', 'closehat', 'closed_hat', 'chh', 'cl hat', 'clhat', 'close hat'],
            'open hi-hats': ['open hat', 'openhat', 'open_hat', 'ohh', 'op hat', 'ophat'],
            'hi-hats': ['hat', 'hh', 'hihat', 'hi-hat', 'hi hat'],  # Fallback for generic hi-hats
            'cymbals': ['cymbal', 'crash', 'ride', 'splash'],
            'percussion': ['perc', 'shaker', 'tambourine', 'conga', 'bongo', 'cowbell'],
            '808': ['808', 'eight', 'sub bass'],
            'bass loops': ['bass loop', 'bassloop', 'bass'],
            'electric bass': ['electric bass', 'e-bass'],
            'synth bass': ['synth bass', 'synthbass'],
            'melodic loops': ['melodic loop', 'melody loop', 'melodic', 'hook', 'verse', 'bridge'],
            'keys': ['piano', 'key', 'keys'],
            'synth leads': ['synth', 'lead'],
            'pads': ['pad', 'string'],
            'plucks': ['pluck'],
            'vocal loops': ['vocal loop', 'vox loop'],
            'chops': ['chop', 'vocal chop'],
            'one-shots': ['one shot', 'oneshot', 'hit'],
            'phrases': ['phrase', 'word', 'lyric'],
            'risers': ['riser', 'sweep', 'uplifter'],
            'impacts': ['impact', 'hit', 'stab'],
            'ambient': ['ambient', 'atmosphere', 'texture'],
            'foley': ['foley', 'sound effect'],
            'downlifters': ['downlifter', 'down'],
            'full loops': ['drum loop', 'drumloop', 'loop']
        }
    
    def _keyword_matches_file(self, keywords: List[str], file_name: str, file_path: str) -> bool:
        """Check if any keywords match the file name or path."""
        return any(keyword in file_name or keyword in file_path for keyword in keywords)
    
    def _enhanced_subcategory_matching(self, category: str, subcategory: str, sample_type: str, file_name: str, keywords: List[str]) -> bool:
        """Enhanced matching based on analysis results and category."""
        if category == 'bass':
            return self._match_bass_subcategory(subcategory, file_name, sample_type)
        elif category == 'drums':
            return self._match_drums_subcategory(subcategory, sample_type, file_name, keywords)
        elif category == 'melodic':
            return self._match_melodic_subcategory(subcategory, sample_type, file_name, keywords)
        elif category == 'fx':
            return self._match_fx_subcategory(subcategory, sample_type, file_name, keywords)
        elif category == 'vocals':
            return self._match_vocals_subcategory(subcategory, sample_type, file_name, keywords)
        
        return False
    
    def _match_bass_subcategory(self, subcategory: str, file_name: str, sample_type: str) -> bool:
        """Match bass subcategories."""
        if subcategory == '808' and ('808' in file_name or sample_type == 'bass'):
            return True
        elif subcategory in {'bass loops', 'electric bass', 'synth bass'} and sample_type == 'bass':
            return True
        return False
    
    def _match_drums_subcategory(self, subcategory: str, sample_type: str, file_name: str, keywords: List[str]) -> bool:
        """Match drums subcategories."""
        if subcategory in {'kicks', 'snares', 'claps', 'closed hi-hats', 'open hi-hats', 'hi-hats', 'cymbals', 'percussion', 'full loops'}:
            return sample_type == 'drums' or any(kw in file_name for kw in keywords)
        return False
    
    def _match_melodic_subcategory(self, subcategory: str, sample_type: str, file_name: str, keywords: List[str]) -> bool:
        """Match melodic subcategories."""
        if subcategory in {'melodic loops', 'keys', 'synth leads', 'pads', 'plucks'}:
            return sample_type == 'melodic' or any(kw in file_name for kw in keywords)
        return False
    
    def _match_fx_subcategory(self, subcategory: str, sample_type: str, file_name: str, keywords: List[str]) -> bool:
        """Match FX subcategories."""
        if subcategory in {'risers', 'impacts', 'ambient', 'foley', 'downlifters'}:
            return sample_type == 'fx' or any(kw in file_name for kw in keywords)
        return False
    
    def _match_vocals_subcategory(self, subcategory: str, sample_type: str, file_name: str, keywords: List[str]) -> bool:
        """Match vocals subcategories."""
        if subcategory in {'chops', 'one-shots', 'phrases', 'vocal loops'}:
            return sample_type == 'vocals' or any(kw in file_name for kw in keywords)
        return False
    
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
        """Get all categories and their subcategories from indexed samples."""
        categories = {
            "Bass": ["808", "Bass Loops", "Electric Bass", "Synth Bass"],
            "Drums": ["Claps", "Closed Hi-Hats", "Cymbals", "Full Loops", "Kicks", "Open Hi-Hats", "Percussion", "Snares"],
            "FX": ["Ambient", "Downlifters", "Foley", "Impacts", "Risers"],
            "Melodic": ["Keys", "Melodic Loops", "Pads", "Plucks", "Synth Leads"],
            "Vocals": ["Chops", "One-Shots", "Phrases", "Vocal Loops"]
        }
        
        # Also dynamically add categories based on cached samples (merged nested if condition)
        for analysis in self.sample_cache.values():
            category = analysis.get('category', '').title()
            if category and category != "Unknown" and category not in categories:
                categories[category] = []
        
        return categories
    
    def get_current_category_subcategory(self, file_path: str) -> Tuple[str, str]:
        """Extract category and subcategory from sample analysis."""
        try:
            file_key = str(Path(file_path).resolve())
            
            if file_key in self.sample_cache and (analysis := self.sample_cache[file_key]):
                category = analysis.get('category', 'Unknown').title()
                subcategory = self._determine_subcategory_from_analysis(analysis, category)
                return category, subcategory
            
            return "Unknown", "Unknown"
                
        except Exception as e:
            logger.warning(f"Error extracting category/subcategory from {file_path}: {e}")
            return "Unknown", "Unknown"
    
    def _determine_subcategory_from_analysis(self, analysis: Dict, category: str) -> str:
        """Determine subcategory based on analysis data."""
        file_name = analysis.get('file_name', '').lower()
        category_lower = category.lower()
        
        if category_lower == 'drums':
            # Check if audio analysis provided hi-hat subcategory
            if 'hihat_subcategory' in analysis:
                return analysis['hihat_subcategory']
            return self._get_drums_subcategory(file_name)
        elif category_lower == 'bass':
            return self._get_bass_subcategory(file_name)
        elif category_lower == 'melodic':
            return self._get_melodic_subcategory(file_name)
        elif category_lower == 'fx':
            return self._get_fx_subcategory(file_name)
        elif category_lower == 'vocals':
            return self._get_vocals_subcategory(file_name)
        
        return "Unknown"
    
    def _get_drums_subcategory(self, file_name: str) -> str:
        """Get drums subcategory based on file name."""
        if any(kw in file_name for kw in ['kick', 'bd', 'bassdrum']):
            return "Kicks"
        elif any(kw in file_name for kw in ['snare', 'sd', 'snr']):
            return "Snares"
        elif any(kw in file_name for kw in ['clap', 'handclap']):
            return "Claps"
        elif any(kw in file_name for kw in ['closed hat', 'closehat', 'closed_hat', 'chh', 'cl hat', 'clhat', 'close hat']):
            return "Closed Hi-Hats"
        elif any(kw in file_name for kw in ['open hat', 'openhat', 'open_hat', 'ohh', 'op hat', 'ophat']):
            return "Open Hi-Hats"
        elif any(kw in file_name for kw in ['hat', 'hh', 'hihat', 'hi-hat', 'hi hat']):
            return "Closed Hi-Hats"  # Default generic hi-hats to closed (more common)
        elif any(kw in file_name for kw in ['cymbal', 'crash', 'ride', 'splash']):
            return "Cymbals"
        elif any(kw in file_name for kw in ['perc', 'shaker', 'tambourine']):
            return "Percussion"
        else:
            return "Full Loops"
    
    def _get_bass_subcategory(self, file_name: str) -> str:
        """Get bass subcategory based on file name."""
        if '808' in file_name or 'eight' in file_name:
            return "808"
        elif any(kw in file_name for kw in ['electric bass', 'e-bass']):
            return "Electric Bass"
        elif any(kw in file_name for kw in ['synth bass', 'synthbass']):
            return "Synth Bass"
        else:
            return "Bass Loops"
    
    def _get_melodic_subcategory(self, file_name: str) -> str:
        """Get melodic subcategory based on file name."""
        if any(kw in file_name for kw in ['piano', 'key', 'keys']):
            return "Keys"
        elif any(kw in file_name for kw in ['synth', 'lead']):
            return "Synth Leads"
        elif any(kw in file_name for kw in ['pad', 'string']):
            return "Pads"
        elif 'pluck' in file_name:
            return "Plucks"
        else:
            return "Melodic Loops"
    
    def _get_fx_subcategory(self, file_name: str) -> str:
        """Get FX subcategory based on file name."""
        if any(kw in file_name for kw in ['riser', 'sweep']):
            return "Risers"
        elif any(kw in file_name for kw in ['impact', 'hit', 'stab']):
            return "Impacts"
        elif any(kw in file_name for kw in ['ambient', 'atmosphere']):
            return "Ambient"
        elif any(kw in file_name for kw in ['foley', 'sound effect']):
            return "Foley"
        elif any(kw in file_name for kw in ['downlifter', 'down']):
            return "Downlifters"
        else:
            return "Impacts"
    
    def _get_vocals_subcategory(self, file_name: str) -> str:
        """Get vocals subcategory based on file name."""
        if any(kw in file_name for kw in ['chop', 'vocal chop']):
            return "Chops"
        elif any(kw in file_name for kw in ['phrase', 'word', 'lyric']):
            return "Phrases"
        elif any(kw in file_name for kw in ['one shot', 'oneshot', 'hit']):
            return "One-Shots"
        else:
            return "Vocal Loops"
    
    def remove_sample(self, file_path: str):
        """Remove a sample from cache."""
        try:
            file_key = str(Path(file_path).resolve())
            
            # Remove from cache
            if file_key in self.sample_cache:
                del self.sample_cache[file_key]
                logger.info(f"Removed {file_path} from cache")
                
                # Save updated cache
                self.save_cache()
            else:
                logger.warning(f"Sample {file_path} not found in cache")
            
        except Exception as e:
            logger.error(f"Error removing sample {file_path}: {e}")
    
    def get_analysis_stats(self) -> Dict:
        """Get analysis statistics."""
        stats = self.analysis_stats.copy()
        stats.update({
            "cached_samples": len(self.sample_cache),
            "tracked_directories": len(self.tracked_directories),
            "success_rate": (stats["successful_analyses"] / max(stats["total_analyzed"], 1)) * 100,
            "system_info": self.system_info
        })
        return stats
    
    def clear_cache(self):
        """Clear the analysis cache and tracked directories."""
        self.sample_cache = {}
        self.tracked_directories = set()
        
        # Save empty cache
        self.save_cache()
        
        logger.info("Cache and tracked directories cleared")
    
    def export_analysis_results(self, output_file: str):
        """Export analysis results to JSON file."""
        try:
            export_data = {
                "system_info": self.system_info,
                "analysis_stats": self.get_analysis_stats(),
                "tracked_directories": list(self.tracked_directories),
                "samples": self.sample_cache
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Analysis results exported to {output_file}")
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
    
    def migrate_cache_to_absolute_paths(self):
        """Migrate cache from relative paths to absolute paths and fix categorization issues."""
        try:
            logger.info("Starting cache migration to absolute paths...")
            
            migration_stats = {"migrated_count": 0, "fixed_paths": 0, "analyzed_count": 0}
            migrated_cache = {}
            
            for file_key, analysis in list(self.sample_cache.items()):
                if self._process_migration_entry(file_key, analysis, migrated_cache, migration_stats):
                    migration_stats["migrated_count"] += 1
            
            # Replace cache with migrated version
            self.sample_cache = migrated_cache
            
            # Save migrated cache
            self.save_cache()
            
            logger.info(f"Cache migration complete: {migration_stats['migrated_count']} entries migrated, "
                       f"{migration_stats['fixed_paths']} paths fixed, {migration_stats['analyzed_count']} samples re-analyzed")
            
            return migration_stats
            
        except Exception as e:
            logger.error(f"Error during cache migration: {e}")
            return {"error": str(e)}
    
    def _process_migration_entry(self, file_key: str, analysis: Dict, migrated_cache: Dict, stats: Dict) -> bool:
        """Process a single cache entry for migration."""
        try:
            abs_path = self._resolve_file_path(file_key)
            if abs_path is None:
                return False
            
            # Check if file exists
            if not abs_path.exists():
                logger.warning(f"File no longer exists: {abs_path}")
                return False
            
            abs_key = str(abs_path)
            
            # Update analysis with correct path
            analysis["file_path"] = abs_key
            
            # Re-analyze if needed
            if self._should_reanalyze_entry(analysis):
                analysis = self._reanalyze_migration_entry(abs_path, analysis, stats)
            else:
                # Already analyzed, just update path
                analysis["file_path"] = abs_key
                analysis["file_name"] = abs_path.name
                analysis["directory"] = str(abs_path.parent)
            
            migrated_cache[abs_key] = analysis
            
            if abs_key != file_key:
                stats["fixed_paths"] += 1
            
            return True
            
        except Exception as e:
            logger.warning(f"Error migrating cache entry {file_key}: {e}")
            return False
    
    def _resolve_file_path(self, file_key: str) -> Optional[Path]:
        """Resolve file path from cache key."""
        if Path(file_key).is_absolute():
            return Path(file_key).resolve()
        
        # Try different base directories for relative paths
        potential_paths = [
            Path.cwd() / file_key,
            Path.cwd() / "samples" / file_key,
            Path(file_key)
        ]
        
        for path in potential_paths:
            if path.exists():
                return path.resolve()
        
        logger.warning(f"Could not resolve path for {file_key}")
        return None
    
    def _should_reanalyze_entry(self, analysis: Dict) -> bool:
        """Check if cache entry should be re-analyzed."""
        return not analysis.get("analyzed", False) or analysis.get("category") == "unknown"
    
    def _reanalyze_migration_entry(self, abs_path: Path, analysis: Dict, stats: Dict) -> Dict:
        """Re-analyze a cache entry during migration."""
        try:
            fresh_analysis = universal_audio_analyzer.analyze_sample(str(abs_path))
            
            # Preserve manual overrides if they exist
            if analysis.get("manual_override"):
                fresh_analysis.update({
                    "manual_override": analysis.get("manual_override"),
                    "manual_category": analysis.get("manual_category"),
                    "manual_subcategory": analysis.get("manual_subcategory"),
                    "manual_key": analysis.get("manual_key")
                })
            
            # Add file metadata
            self._add_file_metadata_to_analysis(fresh_analysis, abs_path)
            
            stats["analyzed_count"] += 1
            return fresh_analysis
            
        except Exception as e:
            logger.warning(f"Failed to re-analyze {abs_path}: {e}")
            # Keep the old analysis but fix the path
            analysis["file_path"] = str(abs_path)
            analysis["file_name"] = abs_path.name
            analysis["directory"] = str(abs_path.parent)
            return analysis
    
    def _needs_cache_migration(self) -> bool:
        """Check if the cache needs migration from relative to absolute paths."""
        for file_key, analysis in self.sample_cache.items():
            # Check if path is relative or if category is unknown
            if not Path(file_key).is_absolute():
                return True
            if analysis.get("category") == "unknown" and not analysis.get("analyzed", False):
                return True
        return False
    
    def _ensure_cache_migrated(self):
        """Ensure cache is migrated before performing operations."""
        if not self._migration_pending:
            return
            
        logger.info("Performing pending cache migration...")
        migration_result = self.migrate_cache_to_absolute_paths()
        self._migration_pending = False
        
        # Emit signal about migration if there's a listener
        with suppress(Exception):
            migration_count = migration_result.get("migrated_count", 0)
            analyzed_count = migration_result.get("analyzed_count", 0)
            if migration_count > 0:
                self.directory_scanned.emit("Cache Migration", analyzed_count)

# Create a global instance
universal_sample_manager = UniversalSampleManager() 
