#!/usr/bin/env python3
"""
Action Item Tracker - Startup Script
This script provides better error handling and setup guidance for running the application.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required.")
        print(f"   Current version: {sys.version}")
        print("   Please upgrade Python and try again.")
        return False
    return True

def check_virtual_environment():
    """Check if virtual environment is activated."""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected.")
        print("   It's recommended to use a virtual environment.")
        response = input("   Continue anyway? (y/N): ").lower()
        return response in ['y', 'yes']
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'flask',
        'flask-sqlalchemy',
        'flask-login',
        'pyodbc',
        'python-dotenv',
        'werkzeug'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print("   pip install -r requirements.txt")
        return False
    return True

def check_env_file():
    """Check if .env file exists and has required variables."""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ Error: .env file not found.")
        print("\n💡 Create a .env file with the following variables:")
        print("""
SECRET_KEY=your-super-secret-key-change-this-in-production
DB_SERVER=localhost
DB_NAME=ActionItemDB
DB_USERNAME=your_username
DB_PASSWORD=your_password
FLASK_ENV=development
FLASK_DEBUG=True
""")
        return False
    
    # Check for required variables
    required_vars = ['SECRET_KEY', 'DB_SERVER', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD']
    env_content = env_file.read_text()
    missing_vars = []
    
    for var in required_vars:
        if f'{var}=' not in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables in .env:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    return True

def test_database_connection():
    """Test database connection."""
    try:
        from dotenv import load_dotenv
        import pyodbc
        
        load_dotenv()
        
        server = os.getenv('DB_SERVER')
        database = os.getenv('DB_NAME')
        username = os.getenv('DB_USERNAME')
        password = os.getenv('DB_PASSWORD')
        
        driver = 'ODBC Driver 17 for SQL Server'
        conn_string = f'DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        
        print("🔍 Testing database connection...")
        conn = pyodbc.connect(conn_string, timeout=5)
        conn.close()
        print("✅ Database connection successful!")
        return True
        
    except pyodbc.Error as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Common solutions:")
        print("   1. Ensure SQL Server is running")
        print("   2. Check database credentials in .env file")
        print("   3. Verify ODBC Driver 17 for SQL Server is installed")
        print("   4. Check network connectivity to the database server")
        return False
    except Exception as e:
        print(f"❌ Error testing database connection: {e}")
        return False

def create_database_tables():
    """Create database tables if they don't exist."""
    try:
        print("🔍 Checking database schema...")
        from app import app, db
        
        with app.app_context():
            db.create_all()
        
        print("✅ Database schema is ready!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        print("\n💡 You may need to run the database_schema.sql script manually.")
        return False

def run_application():
    """Start the Flask application."""
    try:
        print("🚀 Starting Action Item Tracker...")
        print("📍 Application will be available at: http://localhost:5000")
        print("🛑 Press Ctrl+C to stop the application\n")
        
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user.")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return False

def main():
    """Main function to run all checks and start the application."""
    print("🔧 Action Item Tracker - Startup Checks")
    print("=" * 50)
    
    # Run all checks
    checks = [
        ("Python version", check_python_version),
        ("Virtual environment", check_virtual_environment),
        ("Dependencies", check_dependencies),
        ("Environment file", check_env_file),
        ("Database connection", test_database_connection),
        ("Database schema", create_database_tables),
    ]
    
    for check_name, check_func in checks:
        print(f"\n🔍 Checking {check_name}...")
        if not check_func():
            print(f"\n❌ Setup failed at: {check_name}")
            print("Please fix the issues above and try again.")
            sys.exit(1)
    
    print("\n✅ All checks passed! Starting application...")
    print("=" * 50)
    
    # Start the application
    run_application()

if __name__ == "__main__":
    main()