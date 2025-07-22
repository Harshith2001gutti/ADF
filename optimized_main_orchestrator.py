"""
Optimized Main Orchestrator for ADF P2P MIS Automation

This module orchestrates the entire P2P MIS processing pipeline with
optimized performance, error handling, and monitoring.
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import time

# Import optimized modules
from optimized_config import config
from optimized_blob_uploader import OptimizedBlobUploader
from optimized_data_validator import DFColumnValidator
from optimized_file_processor import OptimizedFileProcessor, FileCopier
from optimized_email_service import OptimizedEmailService, EmailTemplates


@dataclass
class PipelineResult:
    """Result of the entire pipeline execution."""
    start_time: datetime
    end_time: datetime
    total_files_processed: int
    successful_operations: int
    failed_operations: int
    errors: List[str]
    performance_metrics: Dict[str, float]


class OptimizedP2PMISOrchestrator:
    """
    Main orchestrator for the P2P MIS automation pipeline.
    
    This class coordinates all the components for a complete
    end-to-end processing workflow.
    """
    
    def __init__(self, 
                 enable_email_notifications: bool = True,
                 enable_azure_upload: bool = True,
                 parallel_workers: int = 4):
        """
        Initialize the orchestrator.
        
        Args:
            enable_email_notifications: Whether to send email notifications
            enable_azure_upload: Whether to upload to Azure
            parallel_workers: Number of parallel workers
        """
        self.enable_email_notifications = enable_email_notifications
        self.enable_azure_upload = enable_azure_upload
        self.parallel_workers = parallel_workers
        
        # Initialize components
        self.file_processor = OptimizedFileProcessor(max_workers=parallel_workers)
        self.file_copier = FileCopier()
        self.validator = DFColumnValidator()
        
        if self.enable_azure_upload:
            self.blob_uploader = OptimizedBlobUploader("p2p-mis-data", max_workers=parallel_workers)
        
        if self.enable_email_notifications:
            try:
                self.email_service = OptimizedEmailService(max_workers=2)
            except ValueError as e:
                logging.warning(f"Email service not available: {e}")
                self.enable_email_notifications = False
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Performance metrics
        self.metrics = {}
    
    def _setup_logging(self):
        """Set up comprehensive logging."""
        logger = logging.getLogger(__name__)
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)
            
            # File handler
            log_file = config.OUTPUT_FOLDER / 'pipeline.log'
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
            logger.setLevel(logging.DEBUG)
        
        return logger
    
    def _record_metric(self, operation: str, duration: float):
        """Record performance metric."""
        self.metrics[operation] = duration
        self.logger.info(f"Performance metric - {operation}: {duration:.2f} seconds")
    
    def cleanup_folders(self, companies: List[str] = None) -> bool:
        """
        Clean up input and output folders.
        
        Args:
            companies: List of companies to clean (default: all)
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            if companies is None:
                companies = list(config.DF_COMPANY_PATHS.keys())
            
            self.logger.info(f"Cleaning folders for companies: {companies}")
            
            results = []
            for company in companies:
                # Clean input folder
                input_folder = config.INPUT_FOLDER / company
                result = self.file_processor.clean_folder(input_folder)
                results.append(result)
                
                # Clean output folder  
                output_folder = config.OUTPUT_FOLDER / company
                result = self.file_processor.clean_folder(output_folder)
                results.append(result)
            
            successful = sum(1 for r in results if r.success)
            self.logger.info(f"Folder cleanup: {successful}/{len(results)} operations successful")
            
            self._record_metric("cleanup_folders", time.time() - start_time)
            return successful == len(results)
            
        except Exception as e:
            self.logger.error(f"Error in folder cleanup: {e}")
            return False
    
    def copy_source_files(self, companies: List[str] = None) -> bool:
        """
        Copy source files from company directories.
        
        Args:
            companies: List of companies to process (default: all)
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            if companies is None:
                companies = list(config.DF_COMPANY_PATHS.keys())
            
            self.logger.info(f"Copying files for companies: {companies}")
            
            all_results = []
            for company in companies:
                # Define file patterns to copy
                patterns = ['*.xlsx', '*.xls', '*.csv']
                
                results = self.file_copier.copy_company_files(
                    company_name=company,
                    source_patterns=patterns,
                    destination_folder=config.INPUT_FOLDER
                )
                
                all_results.extend(results)
                
                successful = sum(1 for r in results if r.success)
                self.logger.info(f"Copied {successful} files for {company}")
            
            total_successful = sum(1 for r in all_results if r.success)
            self.logger.info(f"File copying: {total_successful}/{len(all_results)} files successful")
            
            self._record_metric("copy_source_files", time.time() - start_time)
            return total_successful > 0
            
        except Exception as e:
            self.logger.error(f"Error in file copying: {e}")
            return False
    
    def validate_data(self, companies: List[str] = None) -> Dict[str, Any]:
        """
        Validate data files for all companies.
        
        Args:
            companies: List of companies to validate (default: all)
            
        Returns:
            Dictionary with validation results
        """
        start_time = time.time()
        
        try:
            if companies is None:
                companies = list(config.DF_COMPANY_PATHS.keys())
            
            self.logger.info(f"Validating data for companies: {companies}")
            
            all_results = []
            
            for company in companies:
                input_folder = config.INPUT_FOLDER / company
                output_folder = config.OUTPUT_FOLDER / company
                
                if input_folder.exists():
                    results = self.validator.validate_all(input_folder, output_folder)
                    all_results.extend(results)
                else:
                    self.logger.warning(f"Input folder not found for {company}: {input_folder}")
            
            # Summary statistics
            total_files = len(all_results)
            valid_files = sum(1 for r in all_results if r.is_valid)
            total_errors = sum(len(r.errors) for r in all_results)
            total_warnings = sum(len(r.warnings) for r in all_results)
            
            validation_summary = {
                'total_files': total_files,
                'valid_files': valid_files,
                'invalid_files': total_files - valid_files,
                'total_errors': total_errors,
                'total_warnings': total_warnings,
                'results': all_results
            }
            
            self.logger.info(
                f"Data validation completed: {valid_files}/{total_files} files valid, "
                f"{total_errors} errors, {total_warnings} warnings"
            )
            
            self._record_metric("validate_data", time.time() - start_time)
            return validation_summary
            
        except Exception as e:
            self.logger.error(f"Error in data validation: {e}")
            return {'error': str(e)}
    
    def process_files(self, companies: List[str] = None) -> Dict[str, Any]:
        """
        Process files (merge, transform, etc.) for all companies.
        
        Args:
            companies: List of companies to process (default: all)
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        try:
            if companies is None:
                companies = list(config.DF_COMPANY_PATHS.keys())
            
            self.logger.info(f"Processing files for companies: {companies}")
            
            processing_results = []
            
            for company in companies:
                input_folder = config.INPUT_FOLDER / company
                output_folder = config.OUTPUT_FOLDER / company
                
                if not input_folder.exists():
                    self.logger.warning(f"Input folder not found for {company}")
                    continue
                
                # Merge CSV files
                csv_files = list(input_folder.glob("*.csv"))
                if csv_files:
                    merged_file = output_folder / f"{company}_merged_data.csv"
                    result = self.file_processor.merge_csv_files_streaming(
                        csv_files, merged_file, include_source_column=True
                    )
                    processing_results.append(result)
                
                # Copy Excel files to output
                excel_files = list(input_folder.glob("*.xlsx")) + list(input_folder.glob("*.xls"))
                if excel_files:
                    copy_mappings = [
                        (file_path, output_folder / file_path.name)
                        for file_path in excel_files
                    ]
                    copy_results = self.file_processor.copy_files_parallel(copy_mappings)
                    processing_results.extend(copy_results)
            
            successful = sum(1 for r in processing_results if r.success)
            
            processing_summary = {
                'total_operations': len(processing_results),
                'successful_operations': successful,
                'failed_operations': len(processing_results) - successful,
                'results': processing_results
            }
            
            self.logger.info(
                f"File processing completed: {successful}/{len(processing_results)} operations successful"
            )
            
            self._record_metric("process_files", time.time() - start_time)
            return processing_summary
            
        except Exception as e:
            self.logger.error(f"Error in file processing: {e}")
            return {'error': str(e)}
    
    def upload_to_azure(self, companies: List[str] = None) -> Dict[str, Any]:
        """
        Upload processed files to Azure Blob Storage.
        
        Args:
            companies: List of companies to upload (default: all)
            
        Returns:
            Dictionary with upload results
        """
        if not self.enable_azure_upload:
            self.logger.info("Azure upload disabled")
            return {'skipped': True}
        
        start_time = time.time()
        
        try:
            if companies is None:
                companies = list(config.DF_COMPANY_PATHS.keys())
            
            self.logger.info(f"Uploading files to Azure for companies: {companies}")
            
            # Create container if needed
            self.blob_uploader.create_container_if_not_exists()
            
            all_files = []
            for company in companies:
                output_folder = config.OUTPUT_FOLDER / company
                if output_folder.exists():
                    company_files = list(output_folder.rglob("*"))
                    company_files = [f for f in company_files if f.is_file()]
                    all_files.extend(company_files)
            
            if not all_files:
                self.logger.warning("No files found for upload")
                return {'no_files': True}
            
            # Upload files in parallel
            upload_results = self.blob_uploader.upload_files_parallel(all_files)
            
            successful = sum(1 for r in upload_results if r.success)
            total_size = sum(r.size_bytes or 0 for r in upload_results if r.success)
            
            upload_summary = {
                'total_files': len(upload_results),
                'successful_uploads': successful,
                'failed_uploads': len(upload_results) - successful,
                'total_size_mb': total_size / (1024 * 1024),
                'results': upload_results
            }
            
            self.logger.info(
                f"Azure upload completed: {successful}/{len(upload_results)} files uploaded, "
                f"{total_size / (1024 * 1024):.2f} MB"
            )
            
            self._record_metric("upload_to_azure", time.time() - start_time)
            return upload_summary
            
        except Exception as e:
            self.logger.error(f"Error in Azure upload: {e}")
            return {'error': str(e)}
    
    def send_notifications(self, 
                         pipeline_result: PipelineResult,
                         recipients: List[str]) -> bool:
        """
        Send email notifications about pipeline execution.
        
        Args:
            pipeline_result: Result of pipeline execution
            recipients: List of email recipients
            
        Returns:
            True if notifications sent successfully
        """
        if not self.enable_email_notifications:
            self.logger.info("Email notifications disabled")
            return True
        
        start_time = time.time()
        
        try:
            # Create email template
            template = self.email_service.create_processing_report_template(
                processing_results=[pipeline_result],
                report_date=pipeline_result.start_time.strftime('%Y-%m-%d')
            )
            
            # Send to all recipients
            email_results = []
            for recipient in recipients:
                result = self.email_service.send_template_email(recipient, template)
                email_results.append(result)
            
            successful = sum(1 for r in email_results if r.success)
            
            self.logger.info(f"Email notifications: {successful}/{len(recipients)} sent successfully")
            
            self._record_metric("send_notifications", time.time() - start_time)
            return successful == len(recipients)
            
        except Exception as e:
            self.logger.error(f"Error sending notifications: {e}")
            return False
    
    def run_full_pipeline(self, 
                         companies: List[str] = None,
                         email_recipients: List[str] = None) -> PipelineResult:
        """
        Run the complete P2P MIS processing pipeline.
        
        Args:
            companies: List of companies to process (default: all)
            email_recipients: List of email recipients for notifications
            
        Returns:
            PipelineResult with execution details
        """
        start_time = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info("Starting P2P MIS Processing Pipeline")
        self.logger.info("=" * 80)
        
        errors = []
        total_files = 0
        successful_ops = 0
        failed_ops = 0
        
        try:
            # Step 1: Cleanup folders
            self.logger.info("Step 1: Cleaning up folders...")
            if not self.cleanup_folders(companies):
                errors.append("Folder cleanup failed")
            
            # Step 2: Copy source files
            self.logger.info("Step 2: Copying source files...")
            if not self.copy_source_files(companies):
                errors.append("Source file copying failed")
            
            # Step 3: Validate data
            self.logger.info("Step 3: Validating data...")
            validation_result = self.validate_data(companies)
            if 'error' in validation_result:
                errors.append(f"Data validation failed: {validation_result['error']}")
            else:
                total_files += validation_result.get('total_files', 0)
                if validation_result.get('invalid_files', 0) > 0:
                    errors.append(f"{validation_result['invalid_files']} files failed validation")
            
            # Step 4: Process files
            self.logger.info("Step 4: Processing files...")
            processing_result = self.process_files(companies)
            if 'error' in processing_result:
                errors.append(f"File processing failed: {processing_result['error']}")
            else:
                successful_ops += processing_result.get('successful_operations', 0)
                failed_ops += processing_result.get('failed_operations', 0)
            
            # Step 5: Upload to Azure
            self.logger.info("Step 5: Uploading to Azure...")
            upload_result = self.upload_to_azure(companies)
            if 'error' in upload_result:
                errors.append(f"Azure upload failed: {upload_result['error']}")
            elif not upload_result.get('skipped', False) and not upload_result.get('no_files', False):
                successful_ops += upload_result.get('successful_uploads', 0)
                failed_ops += upload_result.get('failed_uploads', 0)
            
        except Exception as e:
            self.logger.error(f"Pipeline execution error: {e}")
            errors.append(f"Pipeline execution error: {str(e)}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Create pipeline result
        pipeline_result = PipelineResult(
            start_time=start_time,
            end_time=end_time,
            total_files_processed=total_files,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            errors=errors,
            performance_metrics=self.metrics
        )
        
        # Step 6: Send notifications
        if email_recipients:
            self.logger.info("Step 6: Sending notifications...")
            self.send_notifications(pipeline_result, email_recipients)
        
        # Log summary
        self.logger.info("=" * 80)
        self.logger.info("Pipeline Execution Summary")
        self.logger.info("=" * 80)
        self.logger.info(f"Duration: {duration:.2f} seconds")
        self.logger.info(f"Files Processed: {total_files}")
        self.logger.info(f"Successful Operations: {successful_ops}")
        self.logger.info(f"Failed Operations: {failed_ops}")
        self.logger.info(f"Errors: {len(errors)}")
        
        if errors:
            self.logger.error("Errors encountered:")
            for error in errors:
                self.logger.error(f"  - {error}")
        
        self.logger.info("Performance Metrics:")
        for operation, duration in self.metrics.items():
            self.logger.info(f"  - {operation}: {duration:.2f}s")
        
        return pipeline_result


def main():
    """Main entry point for the optimized P2P MIS pipeline."""
    # Configure logging for main execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize orchestrator
        orchestrator = OptimizedP2PMISOrchestrator(
            enable_email_notifications=True,
            enable_azure_upload=True,
            parallel_workers=4
        )
        
        # Define processing parameters
        companies_to_process = ['cocoblu']  # Add more companies as needed
        notification_recipients = [
            'admin@company.com',
            'operations@company.com'
        ]
        
        # Run the pipeline
        result = orchestrator.run_full_pipeline(
            companies=companies_to_process,
            email_recipients=notification_recipients
        )
        
        # Exit with appropriate code
        if result.errors:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Fatal error in main execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
