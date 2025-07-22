"""
Environment Setup Script for Optimized ADF P2P MIS Automation

This script helps set up the environment variables and configuration
needed for the optimized automation system.
"""
import os
import sys
from pathlib import Path


def create_env_template():
    """Create a template .env file with required environment variables."""
    env_template = """
# Azure Configuration
AZURE_CONN_STR=your_azure_storage_connection_string_here
TENANT_ID=your_azure_tenant_id_here
CLIENT_ID=your_azure_client_id_here
CLIENT_SECRET=your_azure_client_secret_here
AZURE_SUBSCRIPTION_ID=your_azure_subscription_id_here

# Email Configuration
SMTP_USERNAME=your_email@company.com
SMTP_PASSWORD=your_email_password_here

# File System Configuration
BASE_PATH=T:/
# or for Linux/Mac: BASE_PATH=/mnt/shared/

# Optional: Custom paths
# INPUT_FOLDER=/custom/input/path
# OUTPUT_FOLDER=/custom/output/path
# TEMP_FOLDER=/custom/temp/path
    """.strip()
    
    env_file = Path('.env')
    if not env_file.exists():
        env_file.write_text(env_template)
        print(f"Created environment template: {env_file}")
        print("Please edit .env file with your actual configuration values")
    else:
        print(f"Environment file already exists: {env_file}")


def check_dependencies():
    """Check if required Python packages are installed."""
    required_packages = [
        'pandas',
        'numpy', 
        'openpyxl',
        'azure.storage.blob',
        'azure.identity',
        'azure.mgmt.datafactory',
        'tqdm'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_').replace('.', '.'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall missing packages with:")
        print("pip install -r requirements.txt")
        return False
    else:
        print("All required packages are installed ✓")
        return True


def create_directory_structure():
    """Create the required directory structure."""
    from optimized_config import config
    
    directories = [
        config.INPUT_FOLDER,
        config.OUTPUT_FOLDER, 
        config.TEMP_FOLDER
    ]
    
    # Add company-specific directories
    for company in config.DF_COMPANY_PATHS.keys():
        directories.extend([
            config.INPUT_FOLDER / company,
            config.OUTPUT_FOLDER / company,
            config.TEMP_FOLDER / company
        ])
    
    created_dirs = []
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs.append(directory)
        except Exception as e:
            print(f"Warning: Could not create directory {directory}: {e}")
    
    print(f"Created/verified {len(created_dirs)} directories")


def test_configuration():
    """Test the configuration and connectivity."""
    try:
        from optimized_config import config
        print("Configuration loaded successfully ✓")
        
        # Test Azure connectivity
        if config.azure_credentials_configured:
            try:
                from optimized_blob_uploader import OptimizedBlobUploader
                uploader = OptimizedBlobUploader("test-container")
                print("Azure configuration appears valid ✓")
            except Exception as e:
                print(f"Azure configuration issue: {e}")
        else:
            print("Azure credentials not configured (check .env file)")
        
        # Test email configuration
        try:
            from optimized_email_service import OptimizedEmailService
            email_service = OptimizedEmailService()
            print("Email configuration appears valid ✓")
        except Exception as e:
            print(f"Email configuration issue: {e}")
        
        return True
        
    except Exception as e:
        print(f"Configuration test failed: {e}")
        return False


def run_setup():
    """Run the complete setup process."""
    print("=" * 60)
    print("ADF P2P MIS Optimization Setup")
    print("=" * 60)
    
    # Step 1: Create environment template
    print("\n1. Setting up environment configuration...")
    create_env_template()
    
    # Step 2: Check dependencies
    print("\n2. Checking dependencies...")
    if not check_dependencies():
        print("Please install missing dependencies before continuing")
        return False
    
    # Step 3: Create directories
    print("\n3. Creating directory structure...")
    try:
        create_directory_structure()
    except Exception as e:
        print(f"Error creating directories: {e}")
        print("You may need to configure BASE_PATH in your .env file")
    
    # Step 4: Test configuration
    print("\n4. Testing configuration...")
    if test_configuration():
        print("\n✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit .env file with your actual configuration values")
        print("2. Test the optimized pipeline with: python optimized_main_orchestrator.py")
        print("3. Review optimization_recommendations.md for migration guidance")
        return True
    else:
        print("\n⚠ Setup completed with warnings")
        print("Please review the configuration issues above")
        return False


if __name__ == "__main__":
    success = run_setup()
    sys.exit(0 if success else 1)
