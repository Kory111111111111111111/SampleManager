import os
import json
import shutil
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from audio_analysis import AudioAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SampleManager:
    def __init__(self, base_dir: str = "samples"):
        """
        Initialize the Sample Manager.
        
        Args:
            base_dir: Base directory for sample storage
        """
        self.base_dir = Path(base_dir)
        self.analyzer = AudioAnalyzer()
        self.supported_formats = {'.wav', '.mp3', '.flac', '.aiff', '.ogg'}
        
        # Default category structure
        self.default_categories = {
            "Drums": [
                "Kicks",
                "Snares",
                "Hi-Hats",
                "Cymbals",
                "Percussion",
                "Full Loops"
            ],
            "Bass": [
                "Electric Bass",
                "Synth Bass",
                "808",
                "Bass Loops"
            ],
            "Melodic": [
                "Keys",
                "Synth Leads",
                "Pads",
                "Plucks",
                "Melodic Loops"
            ],
            "FX": [
                "Impacts",
                "Risers",
                "Downlifters",
                "Ambient",
                "Foley"
            ],
            "Vocals": [
                "One-Shots",
                "Phrases",
                "Vocal Loops",
                "Chops"
            ]
        }
        
        # Initialize directory structure
        self._initialize_directory_structure()

    def _initialize_directory_structure(self):
        """Create the initial directory structure if it doesn't exist."""
        try:
            self.base_dir.mkdir(exist_ok=True)
            
            # Create category and subcategory directories
            for category, subcategories in self.default_categories.items():
                category_dir = self.base_dir / category
                category_dir.mkdir(exist_ok=True)
                
                for subcategory in subcategories:
                    subcategory_dir = category_dir / subcategory
                    subcategory_dir.mkdir(exist_ok=True)
            
            logger.info(f"Directory structure initialized at {self.base_dir}")
        except Exception as e:
            logger.error(f"Error initializing directory structure: {str(e)}")
            raise

    def get_categories(self) -> Dict[str, List[str]]:
        """Get all categories and their subcategories."""
        return self.default_categories

    def get_samples(self, category: str, subcategory: str) -> List[Dict[str, str]]:
        """
        Get all samples in a specific category/subcategory.
        
        Returns:
            List of dictionaries containing sample information
        """
        try:
            directory = self.base_dir / category / subcategory
            if not directory.exists():
                logger.warning(f"Directory does not exist: {directory}")
                return []
            
            samples = []
            for file in directory.iterdir():
                if file.suffix.lower() in self.supported_formats:
                    sample_info = {
                        "name": file.name,
                        "path": str(file),
                        "type": self._get_cached_sample_type(file)
                    }
                    samples.append(sample_info)
            
            return samples
        except Exception as e:
            logger.error(f"Error getting samples: {str(e)}")
            return []

    def _get_cached_sample_type(self, file_path: Path) -> str:
        """Get the sample type from cache or analyze if not cached."""
        cache_file = file_path.with_suffix('.cache')
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                return cache_data.get('type', 'unknown')
            except:
                pass
        
        # Analyze the sample if not cached
        result = self.analyzer.analyze_sample(str(file_path))
        
        # Cache the result
        try:
            with open(cache_file, 'w') as f:
                json.dump({'type': result['type']}, f)
        except:
            pass
        
        return result['type']

    def add_sample(self, file_path: str, category: str, subcategory: str) -> bool:
        """
        Add a sample to the library.
        
        Args:
            file_path: Path to the sample file
            category: Target category
            subcategory: Target subcategory
            
        Returns:
            bool: Success status
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                logger.error(f"Source file does not exist: {file_path}")
                return False
            
            if source_path.suffix.lower() not in self.supported_formats:
                logger.error(f"Unsupported file format: {source_path.suffix}")
                return False
            
            target_dir = self.base_dir / category / subcategory
            if not target_dir.exists():
                logger.error(f"Target directory does not exist: {target_dir}")
                return False
            
            # Copy the file
            target_path = target_dir / source_path.name
            shutil.copy2(source_path, target_path)
            
            # Analyze and cache the sample type
            result = self.analyzer.analyze_sample(str(target_path))
            cache_file = target_path.with_suffix('.cache')
            
            with open(cache_file, 'w') as f:
                json.dump({'type': result['type']}, f)
            
            logger.info(f"Sample added successfully: {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding sample: {str(e)}")
            return False

    def remove_sample(self, category: str, subcategory: str, sample_name: str) -> bool:
        """
        Remove a sample from the library.
        
        Returns:
            bool: Success status
        """
        try:
            sample_path = self.base_dir / category / subcategory / sample_name
            cache_path = sample_path.with_suffix('.cache')
            
            if sample_path.exists():
                sample_path.unlink()
                if cache_path.exists():
                    cache_path.unlink()
                logger.info(f"Sample removed successfully: {sample_path}")
                return True
            else:
                logger.warning(f"Sample does not exist: {sample_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing sample: {str(e)}")
            return False

    def move_sample(self, sample_name: str, 
                   source_category: str, source_subcategory: str,
                   target_category: str, target_subcategory: str) -> bool:
        """
        Move a sample to a different category/subcategory.
        
        Returns:
            bool: Success status
        """
        try:
            source_path = self.base_dir / source_category / source_subcategory / sample_name
            target_path = self.base_dir / target_category / target_subcategory / sample_name
            
            if not source_path.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return False
            
            # Move the file
            shutil.move(str(source_path), str(target_path))
            
            # Move the cache file if it exists
            source_cache = source_path.with_suffix('.cache')
            target_cache = target_path.with_suffix('.cache')
            
            if source_cache.exists():
                shutil.move(str(source_cache), str(target_cache))
            
            logger.info(f"Sample moved successfully: {source_path} -> {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving sample: {str(e)}")
            return False

    def analyze_sample(self, category: str, subcategory: str, sample_name: str) -> Dict:
        """
        Analyze a specific sample.
        
        Returns:
            Dict containing analysis results
        """
        try:
            sample_path = self.base_dir / category / subcategory / sample_name
            if not sample_path.exists():
                return {"error": "Sample not found"}
            
            return self.analyzer.analyze_sample(str(sample_path))
            
        except Exception as e:
            logger.error(f"Error analyzing sample: {str(e)}")
            return {"error": str(e)}

    def search_samples(self, query: str) -> List[Dict[str, str]]:
        """
        Search for samples across all categories.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching samples with their details
        """
        results = []
        query = query.lower()
        
        try:
            for category, subcategories in self.default_categories.items():
                for subcategory in subcategories:
                    directory = self.base_dir / category / subcategory
                    if not directory.exists():
                        continue
                    
                    for file in directory.iterdir():
                        if (file.suffix.lower() in self.supported_formats and 
                            query in file.name.lower()):
                            results.append({
                                "name": file.name,
                                "category": category,
                                "subcategory": subcategory,
                                "path": str(file),
                                "type": self._get_cached_sample_type(file)
                            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching samples: {str(e)}")
            return []
