"""
Optimized Data Validation Module for ADF P2P MIS Automation

This module provides efficient data validation with vectorized operations,
parallel processing, and comprehensive error reporting.
"""
import re
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from optimized_config import config


@dataclass
class ValidationResult:
    """Result of data validation operation."""
    file_path: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    processing_time_seconds: float = 0.0


class OptimizedDataValidator:
    """
    Optimized data validator with vectorized operations and parallel processing.
    
    Features:
    - Vectorized pandas operations for speed
    - Parallel validation of multiple files
    - Comprehensive error reporting
    - Memory-efficient processing
    - Configurable validation rules
    """
    
    # Optimized regex patterns (compiled once)
    SPECIAL_CHARACTERS_PATTERN = re.compile(r'[^\w\s.-]')
    DATE_PATTERNS = {
        'YYYY-MM-DD': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        'DD/MM/YYYY': re.compile(r'^\d{2}/\d{2}/\d{4}$'),
        'MM-DD-YYYY': re.compile(r'^\d{2}-\d{2}-\d{4}$'),
    }
    
    def __init__(self, 
                 special_chars_to_remove: str = r'[^\w\s.-]',
                 date_columns: Optional[List[str]] = None,
                 numeric_columns: Optional[List[str]] = None,
                 required_columns: Optional[List[str]] = None):
        """
        Initialize the data validator.
        
        Args:
            special_chars_to_remove: Regex pattern for special characters
            date_columns: List of columns that should contain dates
            numeric_columns: List of columns that should be numeric
            required_columns: List of required columns
        """
        self.special_chars_pattern = re.compile(special_chars_to_remove)
        self.date_columns = date_columns or []
        self.numeric_columns = numeric_columns or []
        self.required_columns = required_columns or []
        
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the validator."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize column names using vectorized operations.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with normalized column names
        """
        # Create a copy to avoid modifying original
        df_normalized = df.copy()
        
        # Normalize column names
        normalized_columns = {}
        for col in df.columns:
            normalized = col.strip().replace(' ', '_').lower()
            normalized = re.sub(r'[^\w]', '_', normalized)
            normalized = re.sub(r'_+', '_', normalized)
            normalized = normalized.strip('_')
            normalized_columns[col] = normalized
        
        df_normalized.rename(columns=normalized_columns, inplace=True)
        
        return df_normalized
    
    def clean_special_characters(self, 
                                df: pd.DataFrame, 
                                columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Clean special characters from specified columns using vectorized operations.
        
        Args:
            df: Input DataFrame
            columns: List of columns to clean (default: all string columns)
            
        Returns:
            DataFrame with cleaned data
        """
        df_cleaned = df.copy()
        
        if columns is None:
            # Auto-detect string columns
            columns = df_cleaned.select_dtypes(include=['object']).columns.tolist()
        
        # Vectorized string cleaning
        for col in columns:
            if col in df_cleaned.columns:
                # Use vectorized string operations
                df_cleaned[col] = (
                    df_cleaned[col]
                    .astype(str)
                    .str.replace(self.special_chars_pattern, '', regex=True)
                    .str.strip()
                )
        
        return df_cleaned
    
    def validate_data_types(self, df: pd.DataFrame) -> List[str]:
        """
        Validate data types using vectorized operations.
        
        Args:
            df: Input DataFrame
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate numeric columns
        for col in self.numeric_columns:
            if col in df.columns:
                # Try to convert to numeric and check for errors
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                null_count = numeric_series.isna().sum()
                original_null_count = df[col].isna().sum()
                
                if null_count > original_null_count:
                    invalid_count = null_count - original_null_count
                    errors.append(
                        f"Column '{col}': {invalid_count} non-numeric values found"
                    )
        
        # Validate date columns
        for col in self.date_columns:
            if col in df.columns:
                # Try to parse dates
                date_series = pd.to_datetime(df[col], errors='coerce')
                null_count = date_series.isna().sum()
                original_null_count = df[col].isna().sum()
                
                if null_count > original_null_count:
                    invalid_count = null_count - original_null_count
                    errors.append(
                        f"Column '{col}': {invalid_count} invalid date values found"
                    )
        
        return errors
    
    def validate_required_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Validate that all required columns are present.
        
        Args:
            df: Input DataFrame
            
        Returns:
            List of validation errors
        """
        errors = []
        missing_columns = set(self.required_columns) - set(df.columns)
        
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        return errors
    
    def validate_data_quality(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """
        Perform comprehensive data quality validation.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check for completely empty rows
        empty_rows = df.isnull().all(axis=1).sum()
        if empty_rows > 0:
            warnings.append(f"Found {empty_rows} completely empty rows")
        
        # Check for duplicate rows
        duplicate_rows = df.duplicated().sum()
        if duplicate_rows > 0:
            warnings.append(f"Found {duplicate_rows} duplicate rows")
        
        # Check for high null percentages
        null_percentages = df.isnull().sum() / len(df) * 100
        high_null_columns = null_percentages[null_percentages > 50].index.tolist()
        
        if high_null_columns:
            warnings.append(
                f"Columns with >50% null values: {', '.join(high_null_columns)}"
            )
        
        # Check for suspicious patterns
        for col in df.select_dtypes(include=['object']).columns:
            # Check for potential encoding issues
            if df[col].astype(str).str.contains(r'[^\x00-\x7F]').any():
                warnings.append(f"Column '{col}' contains non-ASCII characters")
        
        return errors, warnings
    
    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate a single file with comprehensive checks.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            ValidationResult object
        """
        import time
        start_time = time.time()
        
        try:
            # Read file based on extension
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                return ValidationResult(
                    file_path=str(file_path),
                    is_valid=False,
                    errors=[f"Unsupported file format: {file_path.suffix}"]
                )
            
            all_errors = []
            all_warnings = []
            
            # Validate required columns
            all_errors.extend(self.validate_required_columns(df))
            
            # Validate data types
            all_errors.extend(self.validate_data_types(df))
            
            # Validate data quality
            quality_errors, quality_warnings = self.validate_data_quality(df)
            all_errors.extend(quality_errors)
            all_warnings.extend(quality_warnings)
            
            processing_time = time.time() - start_time
            
            result = ValidationResult(
                file_path=str(file_path),
                is_valid=len(all_errors) == 0,
                errors=all_errors,
                warnings=all_warnings,
                row_count=len(df),
                column_count=len(df.columns),
                processing_time_seconds=processing_time
            )
            
            self.logger.info(
                f"Validated {file_path.name}: "
                f"{'PASS' if result.is_valid else 'FAIL'} "
                f"({result.row_count} rows, {processing_time:.2f}s)"
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error validating {file_path}: {e}")
            
            return ValidationResult(
                file_path=str(file_path),
                is_valid=False,
                errors=[f"File processing error: {str(e)}"],
                processing_time_seconds=processing_time
            )
    
    def validate_files_parallel(self, 
                               file_paths: List[Path], 
                               max_workers: int = 4) -> List[ValidationResult]:
        """
        Validate multiple files in parallel.
        
        Args:
            file_paths: List of file paths to validate
            max_workers: Maximum number of parallel workers
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit validation tasks
            future_to_file = {
                executor.submit(self.validate_file, file_path): file_path
                for file_path in file_paths
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Unexpected error validating {file_path}: {e}")
                    results.append(ValidationResult(
                        file_path=str(file_path),
                        is_valid=False,
                        errors=[f"Processing error: {str(e)}"]
                    ))
        
        return results
    
    def generate_validation_report(self, 
                                 results: List[ValidationResult], 
                                 output_path: Path) -> None:
        """
        Generate a comprehensive validation report in Excel format.
        
        Args:
            results: List of validation results
            output_path: Path for the output report
        """
        wb = Workbook()
        
        # Summary sheet
        ws_summary = wb.active
        ws_summary.title = "Summary"
        
        # Headers
        headers = ['File', 'Status', 'Rows', 'Columns', 'Errors', 'Warnings', 'Processing Time (s)']
        for col, header in enumerate(headers, 1):
            cell = ws_summary.cell(row=1, column=col, value=header)
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        for row, result in enumerate(results, 2):
            ws_summary.cell(row=row, column=1, value=Path(result.file_path).name)
            ws_summary.cell(row=row, column=2, value='PASS' if result.is_valid else 'FAIL')
            ws_summary.cell(row=row, column=3, value=result.row_count)
            ws_summary.cell(row=row, column=4, value=result.column_count)
            ws_summary.cell(row=row, column=5, value=len(result.errors))
            ws_summary.cell(row=row, column=6, value=len(result.warnings))
            ws_summary.cell(row=row, column=7, value=round(result.processing_time_seconds, 2))
        
        # Details sheet
        ws_details = wb.create_sheet("Details")
        detail_headers = ['File', 'Type', 'Message']
        for col, header in enumerate(detail_headers, 1):
            cell = ws_details.cell(row=1, column=col, value=header)
            cell.alignment = Alignment(horizontal='center')
        
        detail_row = 2
        for result in results:
            filename = Path(result.file_path).name
            
            for error in result.errors:
                ws_details.cell(row=detail_row, column=1, value=filename)
                ws_details.cell(row=detail_row, column=2, value='ERROR')
                ws_details.cell(row=detail_row, column=3, value=error)
                detail_row += 1
            
            for warning in result.warnings:
                ws_details.cell(row=detail_row, column=1, value=filename)
                ws_details.cell(row=detail_row, column=2, value='WARNING')
                ws_details.cell(row=detail_row, column=3, value=warning)
                detail_row += 1
        
        # Auto-adjust column widths
        for ws in [ws_summary, ws_details]:
            for column in ws.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
        
        wb.save(output_path)
        self.logger.info(f"Validation report saved to {output_path}")


class DFColumnValidator(OptimizedDataValidator):
    """
    Specialized validator for DataFrame columns with P2P MIS specific rules.
    """
    
    def __init__(self):
        super().__init__(
            special_chars_to_remove=r'[^\w\s.-]',
            date_columns=['Date', 'DueDate', 'ProcessedDate'],
            numeric_columns=['Amount', 'PendingAmount', 'ProcessedAmount'],
            required_columns=list(config.EXPECTED_DF_DAILY_COLUMNS)
        )
    
    def validate_all(self, input_folder: Path, output_folder: Path) -> List[ValidationResult]:
        """
        Validate all files in a folder and generate a comprehensive report.
        
        Args:
            input_folder: Folder containing files to validate
            output_folder: Folder for output reports
            
        Returns:
            List of validation results
        """
        # Find all relevant files
        file_patterns = ['*.xlsx', '*.xls', '*.csv']
        file_paths = []
        
        for pattern in file_patterns:
            file_paths.extend(input_folder.glob(pattern))
        
        if not file_paths:
            self.logger.warning(f"No files found in {input_folder}")
            return []
        
        # Validate files in parallel
        results = self.validate_files_parallel(file_paths)
        
        # Generate report
        report_path = output_folder / f"validation_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.generate_validation_report(results, report_path)
        
        # Log summary
        total_files = len(results)
        valid_files = sum(1 for r in results if r.is_valid)
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        
        self.logger.info(f"Validation completed: {valid_files}/{total_files} files valid")
        self.logger.info(f"Total errors: {total_errors}, Total warnings: {total_warnings}")
        
        return results


# Example usage functions
def validate_p2p_files(input_folder: str, output_folder: str = None):
    """Validate P2P MIS files with optimized processing."""
    if output_folder is None:
        output_folder = str(config.OUTPUT_FOLDER)
    
    validator = DFColumnValidator()
    results = validator.validate_all(Path(input_folder), Path(output_folder))
    
    return results


if __name__ == "__main__":
    # Example usage
    validator = DFColumnValidator()
    
    # Test with sample data
    test_df = pd.DataFrame({
        'Date': ['2023-01-01', '2023-01-02', 'invalid_date'],
        'Amount': [100.0, 200.0, 'invalid_amount'],
        'Company': ['CompanyA', 'CompanyB', 'CompanyC']
    })
    
    # Save test file
    test_file = Path('test_data.csv')
    test_df.to_csv(test_file, index=False)
    
    # Validate
    result = validator.validate_file(test_file)
    print(f"Validation result: {result}")
    
    # Clean up
    test_file.unlink()
