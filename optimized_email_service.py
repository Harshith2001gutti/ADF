"""
Optimized Email Service for ADF P2P MIS Automation

This module provides efficient email operations with templates,
bulk sending, and comprehensive error handling.
"""
import smtplib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.mime.image import MIMEImage
import mimetypes
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from optimized_config import config


@dataclass
class EmailAttachment:
    """Email attachment configuration."""
    file_path: Path
    filename: Optional[str] = None
    content_type: Optional[str] = None
    
    def __post_init__(self):
        if self.filename is None:
            self.filename = self.file_path.name
        if self.content_type is None:
            self.content_type, _ = mimetypes.guess_type(str(self.file_path))


@dataclass
class EmailResult:
    """Result of an email sending operation."""
    recipient: str
    subject: str
    success: bool
    error: Optional[str] = None
    send_time_seconds: float = 0.0


@dataclass
class EmailTemplate:
    """Email template configuration."""
    subject: str
    body_text: str
    body_html: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)


class OptimizedEmailService:
    """
    Optimized email service with advanced features:
    - Template support with variable substitution
    - Bulk sending with connection reuse
    - Retry logic and error handling
    - Progress tracking
    - HTML and plain text support
    """
    
    def __init__(self, 
                 smtp_server: str = "smtp.gmail.com",
                 smtp_port: int = 587,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 use_tls: bool = True,
                 max_workers: int = 3,
                 max_retries: int = 3):
        """
        Initialize the email service.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            username: SMTP username (from env if not provided)
            password: SMTP password (from env if not provided)
            use_tls: Whether to use TLS encryption
            max_workers: Maximum number of parallel sending threads
            max_retries: Maximum number of retry attempts
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username or os.getenv('SMTP_USERNAME')
        self.password = password or os.getenv('SMTP_PASSWORD')
        self.use_tls = use_tls
        self.max_workers = max_workers
        self.max_retries = max_retries
        
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Validate configuration
        if not self.username or not self.password:
            raise ValueError("SMTP credentials not provided")
    
    def _setup_logging(self):
        """Configure logging for the email service."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection."""
        smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
        
        if self.use_tls:
            smtp.starttls()
        
        smtp.login(self.username, self.password)
        return smtp
    
    def _substitute_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in text using simple string replacement."""
        result = text
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def _create_message(self, 
                       recipient: str,
                       subject: str,
                       body_text: str,
                       body_html: Optional[str] = None,
                       attachments: Optional[List[EmailAttachment]] = None,
                       variables: Optional[Dict[str, Any]] = None) -> MIMEMultipart:
        """
        Create email message with attachments.
        
        Args:
            recipient: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            attachments: List of attachments (optional)
            variables: Variables for substitution (optional)
            
        Returns:
            Configured MIMEMultipart message
        """
        variables = variables or {}
        
        # Substitute variables
        subject = self._substitute_variables(subject, variables)
        body_text = self._substitute_variables(body_text, variables)
        if body_html:
            body_html = self._substitute_variables(body_html, variables)
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = self.username
        msg['To'] = recipient
        msg['Subject'] = subject
        
        # Add text part
        text_part = MIMEText(body_text, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # Add HTML part if provided
        if body_html:
            html_part = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(html_part)
        
        # Add attachments
        if attachments:
            for attachment in attachments:
                self._add_attachment(msg, attachment)
        
        return msg
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: EmailAttachment):
        """Add attachment to email message."""
        try:
            with open(attachment.file_path, 'rb') as file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file.read())
                encoders.encode_base64(part)
                
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment.filename}'
                )
                
                msg.attach(part)
                
        except Exception as e:
            self.logger.warning(f"Failed to attach {attachment.file_path}: {e}")
    
    def send_email(self, 
                   recipient: str,
                   subject: str,
                   body_text: str,
                   body_html: Optional[str] = None,
                   attachments: Optional[List[EmailAttachment]] = None,
                   variables: Optional[Dict[str, Any]] = None) -> EmailResult:
        """
        Send a single email with retry logic.
        
        Args:
            recipient: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            attachments: List of attachments (optional)
            variables: Variables for substitution (optional)
            
        Returns:
            EmailResult object
        """
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                # Create message
                msg = self._create_message(
                    recipient, subject, body_text, body_html, attachments, variables
                )
                
                # Send email
                with self._create_smtp_connection() as smtp:
                    smtp.send_message(msg)
                
                send_time = time.time() - start_time
                
                self.logger.info(f"Email sent successfully to {recipient} in {send_time:.2f}s")
                
                return EmailResult(
                    recipient=recipient,
                    subject=subject,
                    success=True,
                    send_time_seconds=send_time
                )
                
            except Exception as e:
                self.logger.warning(
                    f"Email send attempt {attempt + 1} failed for {recipient}: {e}"
                )
                
                if attempt == self.max_retries - 1:
                    send_time = time.time() - start_time
                    return EmailResult(
                        recipient=recipient,
                        subject=subject,
                        success=False,
                        error=str(e),
                        send_time_seconds=send_time
                    )
                
                # Exponential backoff
                time.sleep(2 ** attempt)
        
        return EmailResult(
            recipient=recipient,
            subject=subject,
            success=False,
            error="Max retries exceeded"
        )
    
    def send_template_email(self, 
                           recipient: str,
                           template: EmailTemplate) -> EmailResult:
        """
        Send email using a template.
        
        Args:
            recipient: Recipient email address
            template: Email template
            
        Returns:
            EmailResult object
        """
        return self.send_email(
            recipient=recipient,
            subject=template.subject,
            body_text=template.body_text,
            body_html=template.body_html,
            attachments=template.attachments,
            variables=template.variables
        )
    
    def send_bulk_emails(self, 
                        recipients: List[str],
                        subject: str,
                        body_text: str,
                        body_html: Optional[str] = None,
                        attachments: Optional[List[EmailAttachment]] = None,
                        variables_per_recipient: Optional[Dict[str, Dict[str, Any]]] = None) -> List[EmailResult]:
        """
        Send emails to multiple recipients in parallel.
        
        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            attachments: List of attachments (optional)
            variables_per_recipient: Variables per recipient (optional)
            
        Returns:
            List of EmailResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit email tasks
            future_to_recipient = {}
            
            for recipient in recipients:
                variables = variables_per_recipient.get(recipient, {}) if variables_per_recipient else {}
                
                future = executor.submit(
                    self.send_email,
                    recipient, subject, body_text, body_html, attachments, variables
                )
                future_to_recipient[future] = recipient
            
            # Collect results
            for future in as_completed(future_to_recipient):
                result = future.result()
                results.append(result)
        
        return results
    
    def send_bulk_template_emails(self, 
                                 recipient_templates: Dict[str, EmailTemplate]) -> List[EmailResult]:
        """
        Send template emails to multiple recipients in parallel.
        
        Args:
            recipient_templates: Dictionary mapping recipients to templates
            
        Returns:
            List of EmailResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit email tasks
            future_to_recipient = {
                executor.submit(self.send_template_email, recipient, template): recipient
                for recipient, template in recipient_templates.items()
            }
            
            # Collect results
            for future in as_completed(future_to_recipient):
                result = future.result()
                results.append(result)
        
        return results
    
    def create_processing_report_template(self, 
                                        processing_results: List[Any],
                                        report_date: str) -> EmailTemplate:
        """
        Create an email template for processing reports.
        
        Args:
            processing_results: List of processing results
            report_date: Date of the report
            
        Returns:
            EmailTemplate object
        """
        successful = sum(1 for r in processing_results if getattr(r, 'success', True))
        total = len(processing_results)
        
        subject = f"ADF P2P MIS Processing Report - {report_date}"
        
        body_text = f"""
ADF P2P MIS Processing Report

Date: {report_date}
Total Operations: {total}
Successful: {successful}
Failed: {total - successful}
Success Rate: {(successful/total*100):.1f}%

Summary:
{self._format_results_summary(processing_results)}

This is an automated report from the ADF P2P MIS system.
        """.strip()
        
        body_html = f"""
<html>
<body>
<h2>ADF P2P MIS Processing Report</h2>

<table border="1" style="border-collapse: collapse;">
<tr><td><strong>Date:</strong></td><td>{report_date}</td></tr>
<tr><td><strong>Total Operations:</strong></td><td>{total}</td></tr>
<tr><td><strong>Successful:</strong></td><td style="color: green;">{successful}</td></tr>
<tr><td><strong>Failed:</strong></td><td style="color: red;">{total - successful}</td></tr>
<tr><td><strong>Success Rate:</strong></td><td>{(successful/total*100):.1f}%</td></tr>
</table>

<h3>Summary:</h3>
<pre>{self._format_results_summary(processing_results)}</pre>

<p><em>This is an automated report from the ADF P2P MIS system.</em></p>
</body>
</html>
        """.strip()
        
        return EmailTemplate(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            variables={'date': report_date}
        )
    
    def _format_results_summary(self, results: List[Any]) -> str:
        """Format processing results for email summary."""
        summary_lines = []
        
        for i, result in enumerate(results[:10], 1):  # Show first 10 results
            status = "SUCCESS" if getattr(result, 'success', True) else "FAILED"
            file_path = getattr(result, 'file_path', f'Operation {i}')
            summary_lines.append(f"{status}: {Path(file_path).name}")
        
        if len(results) > 10:
            summary_lines.append(f"... and {len(results) - 10} more operations")
        
        return '\n'.join(summary_lines)


# Pre-defined email templates
class EmailTemplates:
    """Collection of pre-defined email templates."""
    
    @staticmethod
    def validation_report(validation_results: List[Any], date: str) -> EmailTemplate:
        """Template for validation reports."""
        valid_files = sum(1 for r in validation_results if r.is_valid)
        total_files = len(validation_results)
        
        return EmailTemplate(
            subject=f"Data Validation Report - {date}",
            body_text=f"""
Data Validation Report for {date}

Files Processed: {total_files}
Valid Files: {valid_files}
Invalid Files: {total_files - valid_files}

Please review the attached validation report for details.
            """.strip(),
            variables={'date': date, 'valid_files': valid_files, 'total_files': total_files}
        )
    
    @staticmethod
    def processing_complete(company: str, files_processed: int) -> EmailTemplate:
        """Template for processing completion notifications."""
        return EmailTemplate(
            subject=f"Processing Complete - {company}",
            body_text=f"""
Processing has been completed for {company}.

Files Processed: {files_processed}
Status: Complete

The processed files are now available in the output directory.
            """.strip(),
            variables={'company': company, 'files_processed': files_processed}
        )
    
    @staticmethod
    def error_notification(error_message: str, operation: str) -> EmailTemplate:
        """Template for error notifications."""
        return EmailTemplate(
            subject=f"ADF P2P MIS Error - {operation}",
            body_text=f"""
An error occurred during {operation} operation:

Error: {error_message}

Please investigate and take appropriate action.
            """.strip(),
            variables={'error_message': error_message, 'operation': operation}
        )


# Example usage functions
def send_daily_report(results: List[Any], recipients: List[str]):
    """Send daily processing report to recipients."""
    email_service = OptimizedEmailService()
    
    from datetime import datetime
    report_date = datetime.now().strftime('%Y-%m-%d')
    
    template = email_service.create_processing_report_template(results, report_date)
    
    # Send to all recipients
    email_results = []
    for recipient in recipients:
        result = email_service.send_template_email(recipient, template)
        email_results.append(result)
    
    # Log summary
    successful_emails = sum(1 for r in email_results if r.success)
    logging.info(f"Daily report sent: {successful_emails}/{len(recipients)} successful")
    
    return email_results


if __name__ == "__main__":
    import os
    
    # Example usage (requires SMTP credentials in environment)
    if os.getenv('SMTP_USERNAME') and os.getenv('SMTP_PASSWORD'):
        email_service = OptimizedEmailService()
        
        # Test email
        result = email_service.send_email(
            recipient="test@example.com",
            subject="Test Email from ADF Automation",
            body_text="This is a test email from the optimized ADF automation system.",
            variables={'system_name': 'ADF P2P MIS'}
        )
        
        print(f"Email result: {result}")
    else:
        print("SMTP credentials not configured - skipping email test")
