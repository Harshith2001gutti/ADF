"""
Optimized Azure Blob Storage Uploader for ADF Integration

This module provides efficient blob storage operations with connection pooling,
retry logic, and parallel uploads.
"""
import os
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.storage.blob._shared.response_handlers import process_storage_error
from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.core.exceptions import AzureError, ResourceExistsError

from optimized_config import config


@dataclass
class UploadResult:
    """Result of a blob upload operation."""
    file_path: str
    blob_name: str
    success: bool
    error: Optional[str] = None
    size_bytes: Optional[int] = None
    upload_time_seconds: Optional[float] = None


class OptimizedBlobUploader:
    """
    Optimized Azure Blob Storage uploader with advanced features:
    - Connection pooling
    - Parallel uploads
    - Retry logic
    - Progress tracking
    - Error handling
    """
    
    def __init__(self, 
                 container_name: str,
                 max_workers: int = 5,
                 chunk_size: int = 4 * 1024 * 1024,  # 4MB chunks
                 max_retries: int = 3):
        """
        Initialize the blob uploader.
        
        Args:
            container_name: Name of the Azure storage container
            max_workers: Maximum number of parallel upload threads
            chunk_size: Size of upload chunks in bytes
            max_retries: Maximum number of retry attempts
        """
        self.container_name = container_name
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Initialize Azure clients
        self._blob_service_client = None
        self._df_client = None
        self._initialize_clients()
    
    def _setup_logging(self):
        """Configure logging for the uploader."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _initialize_clients(self):
        """Initialize Azure service clients with proper authentication."""
        try:
            if config.azure_credentials_configured:
                # Use service principal authentication
                credential = ClientSecretCredential(
                    tenant_id=config.TENANT_ID,
                    client_id=config.CLIENT_ID,
                    client_secret=config.CLIENT_SECRET
                )
                
                # Extract account name from connection string
                account_name = self._extract_account_name(config.AZURE_CONN_STR)
                account_url = f"https://{account_name}.blob.core.windows.net"
                
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                
                # Initialize Data Factory client
                subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
                if subscription_id:
                    self._df_client = DataFactoryManagementClient(
                        credential=credential,
                        subscription_id=subscription_id
                    )
            else:
                # Fallback to connection string
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    config.AZURE_CONN_STR
                )
            
            self.logger.info("Azure clients initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure clients: {e}")
            raise
    
    def _extract_account_name(self, connection_string: str) -> str:
        """Extract storage account name from connection string."""
        for part in connection_string.split(';'):
            if part.startswith('AccountName='):
                return part.split('=', 1)[1]
        raise ValueError("Account name not found in connection string")
    
    def upload_file(self, file_path: Path, blob_name: Optional[str] = None) -> UploadResult:
        """
        Upload a single file to blob storage with retry logic.
        
        Args:
            file_path: Path to the file to upload
            blob_name: Name for the blob (defaults to filename)
            
        Returns:
            UploadResult with operation details
        """
        if blob_name is None:
            blob_name = file_path.name
        
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                blob_client = self._blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=blob_name
                )
                
                file_size = file_path.stat().st_size
                
                with open(file_path, 'rb') as data:
                    blob_client.upload_blob(
                        data,
                        overwrite=True,
                        max_concurrency=self.max_workers
                    )
                
                upload_time = time.time() - start_time
                
                self.logger.info(
                    f"Successfully uploaded {file_path.name} "
                    f"({file_size} bytes) in {upload_time:.2f}s"
                )
                
                return UploadResult(
                    file_path=str(file_path),
                    blob_name=blob_name,
                    success=True,
                    size_bytes=file_size,
                    upload_time_seconds=upload_time
                )
                
            except AzureError as e:
                self.logger.warning(
                    f"Upload attempt {attempt + 1} failed for {file_path.name}: {e}"
                )
                if attempt == self.max_retries - 1:
                    return UploadResult(
                        file_path=str(file_path),
                        blob_name=blob_name,
                        success=False,
                        error=str(e)
                    )
                
                # Exponential backoff
                time.sleep(2 ** attempt)
        
        return UploadResult(
            file_path=str(file_path),
            blob_name=blob_name,
            success=False,
            error="Max retries exceeded"
        )
    
    def upload_files_parallel(self, file_paths: List[Path]) -> List[UploadResult]:
        """
        Upload multiple files in parallel.
        
        Args:
            file_paths: List of file paths to upload
            
        Returns:
            List of UploadResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all upload tasks
            future_to_file = {
                executor.submit(self.upload_file, file_path): file_path
                for file_path in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Unexpected error uploading {file_path}: {e}")
                    results.append(UploadResult(
                        file_path=str(file_path),
                        blob_name=file_path.name,
                        success=False,
                        error=str(e)
                    ))
        
        return results
    
    def upload_dataframe_as_csv(self, 
                               df: pd.DataFrame, 
                               blob_name: str,
                               index: bool = False) -> UploadResult:
        """
        Upload a DataFrame as CSV directly to blob storage.
        
        Args:
            df: Pandas DataFrame to upload
            blob_name: Name for the blob
            index: Whether to include the DataFrame index
            
        Returns:
            UploadResult with operation details
        """
        start_time = time.time()
        
        try:
            # Convert DataFrame to CSV string
            csv_data = df.to_csv(index=index)
            csv_bytes = csv_data.encode('utf-8')
            
            blob_client = self._blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(
                csv_bytes,
                overwrite=True
            )
            
            upload_time = time.time() - start_time
            
            self.logger.info(
                f"Successfully uploaded DataFrame as {blob_name} "
                f"({len(csv_bytes)} bytes) in {upload_time:.2f}s"
            )
            
            return UploadResult(
                file_path="<DataFrame>",
                blob_name=blob_name,
                success=True,
                size_bytes=len(csv_bytes),
                upload_time_seconds=upload_time
            )
            
        except Exception as e:
            self.logger.error(f"Failed to upload DataFrame as {blob_name}: {e}")
            return UploadResult(
                file_path="<DataFrame>",
                blob_name=blob_name,
                success=False,
                error=str(e)
            )
    
    def trigger_adf_pipeline(self, 
                           factory_name: str, 
                           resource_group: str,
                           pipeline_name: str,
                           parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Trigger an Azure Data Factory pipeline.
        
        Args:
            factory_name: Name of the ADF factory
            resource_group: Azure resource group name
            pipeline_name: Name of the pipeline to trigger
            parameters: Optional pipeline parameters
            
        Returns:
            True if pipeline was triggered successfully
        """
        if not self._df_client:
            self.logger.error("Data Factory client not initialized")
            return False
        
        try:
            run_response = self._df_client.pipelines.create_run(
                resource_group_name=resource_group,
                factory_name=factory_name,
                pipeline_name=pipeline_name,
                parameters=parameters or {}
            )
            
            self.logger.info(
                f"Pipeline {pipeline_name} triggered successfully. "
                f"Run ID: {run_response.run_id}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to trigger pipeline {pipeline_name}: {e}")
            return False
    
    def create_container_if_not_exists(self) -> bool:
        """Create the container if it doesn't exist."""
        try:
            container_client = self._blob_service_client.get_container_client(
                self.container_name
            )
            container_client.create_container()
            self.logger.info(f"Created container: {self.container_name}")
            return True
        except ResourceExistsError:
            self.logger.info(f"Container {self.container_name} already exists")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create container {self.container_name}: {e}")
            return False


# Example usage functions
def upload_processed_files(file_paths: List[str], container_name: str = "processed-data"):
    """Upload processed files to Azure Blob Storage."""
    uploader = OptimizedBlobUploader(container_name)
    uploader.create_container_if_not_exists()
    
    paths = [Path(fp) for fp in file_paths]
    results = uploader.upload_files_parallel(paths)
    
    # Log summary
    successful = sum(1 for r in results if r.success)
    total_size = sum(r.size_bytes or 0 for r in results if r.success)
    
    logging.info(f"Upload completed: {successful}/{len(results)} files successful")
    logging.info(f"Total size uploaded: {total_size / (1024*1024):.2f} MB")
    
    return results


if __name__ == "__main__":
    import time
    
    # Example usage
    uploader = OptimizedBlobUploader("test-container")
    
    # Test DataFrame upload
    test_df = pd.DataFrame({
        'Column1': range(100),
        'Column2': [f'Value_{i}' for i in range(100)]
    })
    
    result = uploader.upload_dataframe_as_csv(test_df, "test_data.csv")
    print(f"Upload result: {result}")
