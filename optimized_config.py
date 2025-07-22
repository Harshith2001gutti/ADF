"""
Optimized Configuration Module for ADF P2P MIS Automation

This module provides centralized configuration with environment variable support,
type hints, and validation.
"""
import os
from typing import Dict, List, Set
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration class with type hints and validation."""
    
    # Company paths configuration
    DF_COMPANY_PATHS: Dict[str, str] = None
    
    # Expected DataFrame columns
    EXPECTED_DF_DAILY_COLUMNS: Set[str] = None
    EXPECTED_DF_OPEN_COLUMNS: Set[str] = None
    
    # Scanning configuration
    MONTHS_TO_SCAN: List[str] = None
    DATES_TO_SCAN: List[str] = None
    
    # Azure configuration
    AZURE_CONN_STR: str = None
    TENANT_ID: str = None
    CLIENT_ID: str = None
    CLIENT_SECRET: str = None
    
    # File paths
    BASE_PATH: Path = None
    INPUT_FOLDER: Path = None
    OUTPUT_FOLDER: Path = None
    TEMP_FOLDER: Path = None
    
    def __post_init__(self):
        """Initialize configuration with environment variables and defaults."""
        self._load_from_environment()
        self._set_defaults()
        self._validate_config()
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        self.AZURE_CONN_STR = os.getenv('AZURE_CONN_STR', '')
        self.TENANT_ID = os.getenv('TENANT_ID', '')
        self.CLIENT_ID = os.getenv('CLIENT_ID', '')
        self.CLIENT_SECRET = os.getenv('CLIENT_SECRET', '')
        
        base_path = os.getenv('BASE_PATH', 'T:/')
        self.BASE_PATH = Path(base_path)
    
    def _set_defaults(self):
        """Set default values for configuration."""
        if self.DF_COMPANY_PATHS is None:
            self.DF_COMPANY_PATHS = {
                'cocoblu': 'T:/',
                # Add other company paths as needed
            }
        
        if self.EXPECTED_DF_DAILY_COLUMNS is None:
            self.EXPECTED_DF_DAILY_COLUMNS = {
                'Date', 'Company', 'Amount', 'Status', 'Reference'
                # Add more columns as needed
            }
        
        if self.EXPECTED_DF_OPEN_COLUMNS is None:
            self.EXPECTED_DF_OPEN_COLUMNS = {
                'OpenDate', 'Company', 'PendingAmount', 'DueDate'
                # Add more columns as needed
            }
        
        if self.MONTHS_TO_SCAN is None:
            self.MONTHS_TO_SCAN = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
        
        if self.DATES_TO_SCAN is None:
            self.DATES_TO_SCAN = [f"{i:02d}" for i in range(1, 32)]
        
        # Set path defaults
        if self.INPUT_FOLDER is None:
            self.INPUT_FOLDER = self.BASE_PATH / 'input'
        if self.OUTPUT_FOLDER is None:
            self.OUTPUT_FOLDER = self.BASE_PATH / 'output'
        if self.TEMP_FOLDER is None:
            self.TEMP_FOLDER = self.BASE_PATH / 'temp'
    
    def _validate_config(self):
        """Validate configuration values."""
        if not self.BASE_PATH.exists():
            raise ValueError(f"Base path does not exist: {self.BASE_PATH}")
        
        # Create necessary directories
        for folder in [self.INPUT_FOLDER, self.OUTPUT_FOLDER, self.TEMP_FOLDER]:
            folder.mkdir(parents=True, exist_ok=True)
    
    @property
    def azure_credentials_configured(self) -> bool:
        """Check if Azure credentials are properly configured."""
        return all([
            self.AZURE_CONN_STR,
            self.TENANT_ID,
            self.CLIENT_ID,
            self.CLIENT_SECRET
        ])


# Global configuration instance
config = Config()

# Backward compatibility exports
DF_COMPANY_PATHS = config.DF_COMPANY_PATHS
EXPECTED_DF_DAILY_COLUMNS = config.EXPECTED_DF_DAILY_COLUMNS
EXPECTED_DF_OPEN_COLUMNS = config.EXPECTED_DF_OPEN_COLUMNS
MONTHS_TO_SCAN = config.MONTHS_TO_SCAN
DATES_TO_SCAN = config.DATES_TO_SCAN
