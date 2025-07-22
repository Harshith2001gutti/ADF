"""
Optimized File Processing Module for ADF P2P MIS Automation

This module provides efficient file operations with parallel processing,
memory optimization, and progress tracking.
"""
import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional, Generator, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time

import pandas as pd
from tqdm import tqdm

from optimized_config import config


@dataclass
class ProcessingResult:
    """Result of a file processing operation."""
    file_path: str
    operation: str
    success: bool
    error: Optional[str] = None
    processing_time_seconds: float = 0.0
    output_path: Optional[str] = None


class OptimizedFileProcessor:
    """
    Optimized file processor with parallel operations and memory efficiency.
    
    Features:
    - Parallel file operations
    - Memory-efficient streaming for large files
    - Progress tracking
    - Robust error handling
    - Automatic cleanup
    """
    
    def __init__(self, max_workers: int = 4, chunk_size: int = 10000):
        """
        Initialize the file processor.
        
        Args:
            max_workers: Maximum number of parallel workers
            chunk_size: Chunk size for processing large files
        """
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the processor."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def copy_file_safe(self, source: Path, destination: Path) -> ProcessingResult:
        """
        Safely copy a file with error handling and verification.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            ProcessingResult object
        """
        start_time = time.time()
        
        try:
            # Create destination directory if it doesn't exist
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source, destination)
            
            # Verify copy
            if not destination.exists():
                raise FileNotFoundError(f"Copy verification failed: {destination}")
            
            # Verify size
            if source.stat().st_size != destination.stat().st_size:
                raise ValueError(f"File size mismatch after copy")
            
            processing_time = time.time() - start_time
            
            self.logger.debug(f"Successfully copied {source.name} in {processing_time:.2f}s")
            
            return ProcessingResult(
                file_path=str(source),
                operation="copy",
                success=True,
                processing_time_seconds=processing_time,
                output_path=str(destination)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Failed to copy {source}: {e}")
            
            return ProcessingResult(
                file_path=str(source),
                operation="copy",
                success=False,
                error=str(e),
                processing_time_seconds=processing_time
            )
    
    def copy_files_parallel(self, 
                           file_mappings: List[Tuple[Path, Path]]) -> List[ProcessingResult]:
        """
        Copy multiple files in parallel.
        
        Args:
            file_mappings: List of (source, destination) tuples
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit copy tasks
            future_to_mapping = {
                executor.submit(self.copy_file_safe, source, dest): (source, dest)
                for source, dest in file_mappings
            }
            
            # Collect results with progress bar
            with tqdm(total=len(file_mappings), desc="Copying files") as pbar:
                for future in as_completed(future_to_mapping):
                    result = future.result()
                    results.append(result)
                    pbar.update(1)
        
        return results
    
    def merge_csv_files_streaming(self, 
                                 input_files: List[Path], 
                                 output_file: Path,
                                 include_source_column: bool = True) -> ProcessingResult:
        """
        Merge CSV files using streaming for memory efficiency.
        
        Args:
            input_files: List of CSV files to merge
            output_file: Output merged CSV file
            include_source_column: Whether to add a source filename column
            
        Returns:
            ProcessingResult object
        """
        start_time = time.time()
        
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            first_file = True
            total_rows = 0
            
            with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
                for input_file in input_files:
                    try:
                        # Read in chunks for memory efficiency
                        for chunk_num, chunk in enumerate(pd.read_csv(input_file, chunksize=self.chunk_size)):
                            if include_source_column:
                                chunk['source_file'] = input_file.name
                            
                            # Write header only for first chunk of first file
                            write_header = first_file and chunk_num == 0
                            
                            chunk.to_csv(
                                outfile, 
                                mode='a' if not write_header else 'w',
                                header=write_header,
                                index=False
                            )
                            
                            total_rows += len(chunk)
                            first_file = False
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing {input_file}: {e}")
                        continue
            
            processing_time = time.time() - start_time
            
            self.logger.info(
                f"Merged {len(input_files)} files into {output_file.name} "
                f"({total_rows} total rows) in {processing_time:.2f}s"
            )
            
            return ProcessingResult(
                file_path=str(output_file),
                operation="merge",
                success=True,
                processing_time_seconds=processing_time,
                output_path=str(output_file)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Failed to merge CSV files: {e}")
            
            return ProcessingResult(
                file_path="<multiple>",
                operation="merge",
                success=False,
                error=str(e),
                processing_time_seconds=processing_time
            )
    
    def clean_folder(self, folder_path: Path, 
                    patterns: Optional[List[str]] = None,
                    preserve_structure: bool = True) -> ProcessingResult:
        """
        Clean a folder by removing files matching patterns.
        
        Args:
            folder_path: Path to the folder to clean
            patterns: List of glob patterns to match (default: all files)
            preserve_structure: Whether to keep empty directories
            
        Returns:
            ProcessingResult object
        """
        start_time = time.time()
        
        try:
            if not folder_path.exists():
                return ProcessingResult(
                    file_path=str(folder_path),
                    operation="clean",
                    success=True,
                    processing_time_seconds=0.0
                )
            
            files_removed = 0
            
            if patterns is None:
                patterns = ['*']
            
            for pattern in patterns:
                for file_path in folder_path.rglob(pattern):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            files_removed += 1
                        except Exception as e:
                            self.logger.warning(f"Could not remove {file_path}: {e}")
            
            # Remove empty directories if not preserving structure
            if not preserve_structure:
                for dir_path in sorted(folder_path.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                    if dir_path.is_dir() and not any(dir_path.iterdir()):
                        try:
                            dir_path.rmdir()
                        except Exception as e:
                            self.logger.warning(f"Could not remove directory {dir_path}: {e}")
            
            processing_time = time.time() - start_time
            
            self.logger.info(
                f"Cleaned {folder_path}: removed {files_removed} files "
                f"in {processing_time:.2f}s"
            )
            
            return ProcessingResult(
                file_path=str(folder_path),
                operation="clean",
                success=True,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Failed to clean {folder_path}: {e}")
            
            return ProcessingResult(
                file_path=str(folder_path),
                operation="clean",
                success=False,
                error=str(e),
                processing_time_seconds=processing_time
            )
    
    def organize_files_by_date(self, 
                              source_folder: Path, 
                              destination_folder: Path,
                              date_format: str = "%Y-%m-%d") -> List[ProcessingResult]:
        """
        Organize files into date-based folder structure.
        
        Args:
            source_folder: Source folder containing files
            destination_folder: Destination folder for organized files
            date_format: Date format for folder names
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        
        try:
            files_to_move = []
            
            for file_path in source_folder.rglob('*'):
                if file_path.is_file():
                    # Use file modification time for organization
                    file_date = time.strftime(date_format, time.localtime(file_path.stat().st_mtime))
                    dest_dir = destination_folder / file_date
                    dest_file = dest_dir / file_path.name
                    
                    files_to_move.append((file_path, dest_file))
            
            # Move files in parallel
            results = self.copy_files_parallel(files_to_move)
            
            # Remove original files if copy was successful
            for result in results:
                if result.success:
                    try:
                        Path(result.file_path).unlink()
                    except Exception as e:
                        self.logger.warning(f"Could not remove original file {result.file_path}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to organize files: {e}")
            results.append(ProcessingResult(
                file_path=str(source_folder),
                operation="organize",
                success=False,
                error=str(e)
            ))
        
        return results
    
    def compress_folder(self, 
                       folder_path: Path, 
                       output_path: Path,
                       compression_format: str = 'zip') -> ProcessingResult:
        """
        Compress a folder into an archive.
        
        Args:
            folder_path: Path to the folder to compress
            output_path: Path for the output archive
            compression_format: Format for compression (zip, tar, gztar)
            
        Returns:
            ProcessingResult object
        """
        start_time = time.time()
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove extension from output path for shutil.make_archive
            archive_path = str(output_path.with_suffix(''))
            
            shutil.make_archive(
                archive_path,
                compression_format,
                root_dir=folder_path.parent,
                base_dir=folder_path.name
            )
            
            processing_time = time.time() - start_time
            
            self.logger.info(
                f"Compressed {folder_path} to {output_path} in {processing_time:.2f}s"
            )
            
            return ProcessingResult(
                file_path=str(folder_path),
                operation="compress",
                success=True,
                processing_time_seconds=processing_time,
                output_path=str(output_path)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Failed to compress {folder_path}: {e}")
            
            return ProcessingResult(
                file_path=str(folder_path),
                operation="compress",
                success=False,
                error=str(e),
                processing_time_seconds=processing_time
            )


class FileCopier(OptimizedFileProcessor):
    """Specialized file copier for P2P MIS automation."""
    
    def __init__(self):
        super().__init__(max_workers=6)  # Increased workers for file operations
    
    def copy_company_files(self, 
                          company_name: str, 
                          source_patterns: List[str],
                          destination_folder: Path) -> List[ProcessingResult]:
        """
        Copy files for a specific company based on patterns.
        
        Args:
            company_name: Name of the company
            source_patterns: List of glob patterns to match files
            destination_folder: Destination folder
            
        Returns:
            List of ProcessingResult objects
        """
        if company_name not in config.DF_COMPANY_PATHS:
            return [ProcessingResult(
                file_path=company_name,
                operation="copy_company",
                success=False,
                error=f"Company path not configured: {company_name}"
            )]
        
        source_path = Path(config.DF_COMPANY_PATHS[company_name])
        files_to_copy = []
        
        # Find files matching patterns
        for pattern in source_patterns:
            matching_files = source_path.rglob(pattern)
            for file_path in matching_files:
                if file_path.is_file():
                    # Preserve relative structure
                    relative_path = file_path.relative_to(source_path)
                    dest_path = destination_folder / company_name / relative_path
                    files_to_copy.append((file_path, dest_path))
        
        if not files_to_copy:
            self.logger.warning(f"No files found for company {company_name}")
            return []
        
        return self.copy_files_parallel(files_to_copy)


def merge_csv_from_folder(folder_path: str, output_file: str = None) -> ProcessingResult:
    """
    Merge all CSV files from a folder using optimized processing.
    
    Args:
        folder_path: Path to folder containing CSV files
        output_file: Output file path (optional)
        
    Returns:
        ProcessingResult object
    """
    processor = OptimizedFileProcessor()
    folder = Path(folder_path)
    
    if output_file is None:
        output_file = folder / "merged_data.csv"
    else:
        output_file = Path(output_file)
    
    # Find all CSV files
    csv_files = list(folder.glob("*.csv"))
    
    if not csv_files:
        return ProcessingResult(
            file_path=str(folder),
            operation="merge",
            success=False,
            error="No CSV files found"
        )
    
    return processor.merge_csv_files_streaming(csv_files, output_file)


def clean_company_folders(company_names: Optional[List[str]] = None):
    """
    Clean input/output folders for specified companies.
    
    Args:
        company_names: List of company names to clean (default: all)
    """
    processor = OptimizedFileProcessor()
    
    if company_names is None:
        company_names = list(config.DF_COMPANY_PATHS.keys())
    
    results = []
    
    for company in company_names:
        # Clean input folder
        input_folder = config.INPUT_FOLDER / company
        result = processor.clean_folder(input_folder)
        results.append(result)
        
        # Clean output folder
        output_folder = config.OUTPUT_FOLDER / company
        result = processor.clean_folder(output_folder)
        results.append(result)
    
    # Log summary
    successful = sum(1 for r in results if r.success)
    logging.info(f"Folder cleaning completed: {successful}/{len(results)} operations successful")
    
    return results


if __name__ == "__main__":
    # Example usage
    processor = OptimizedFileProcessor()
    
    # Test file copying
    test_source = Path("test_source.txt")
    test_dest = Path("test_destination.txt")
    
    # Create test file
    test_source.write_text("This is a test file")
    
    # Copy file
    result = processor.copy_file_safe(test_source, test_dest)
    print(f"Copy result: {result}")
    
    # Clean up
    if test_source.exists():
        test_source.unlink()
    if test_dest.exists():
        test_dest.unlink()
