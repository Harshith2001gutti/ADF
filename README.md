# Action Item Tracker

A comprehensive web-based action item tracking application built with Flask and Microsoft SQL Server. This application provides a modern, responsive interface for managing tasks, tracking progress, and collaborating with team members.

## Features

### 🔐 User Management
- User registration and authentication
- Secure password hashing
- Session management
- User profiles with first name, last name, email, and username

### 📋 Action Item Management
- Create, read, update, and delete action items
- Rich text descriptions
- Priority levels (Low, Medium, High, Critical)
- Status tracking (Open, In Progress, Completed, Cancelled)
- Due date management with overdue indicators
- Assignment to team members

### 📊 Dashboard & Analytics
- Personal dashboard with key statistics
- Items assigned to you
- Items created by you
- Recent activity overview
- Progress tracking

### 🔍 Advanced Features
- Real-time filtering and search
- Sortable table columns
- Responsive design for mobile and desktop
- Export functionality
- Modern UI with Bootstrap 5
- Keyboard shortcuts

## Technology Stack

- **Backend**: Python Flask
- **Database**: Microsoft SQL Server
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Authentication**: Flask-Login
- **ORM**: SQLAlchemy
- **Database Driver**: pyodbc

## Prerequisites

Before running the application, ensure you have:

1. **Python 3.8+** installed
2. **Microsoft SQL Server** (Local, Remote, or SQL Server Express)
3. **ODBC Driver 17 for SQL Server** installed
4. **Git** for cloning the repository

### Installing ODBC Driver

#### Windows
Download and install from Microsoft's official site:
- [ODBC Driver 17 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

#### Linux (Ubuntu/Debian)
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

#### macOS
```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
HOMEBREW_NO_ENV_FILTERING=1 ACCEPT_EULA=Y brew install msodbcsql17 mssql-tools
```

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd action-item-tracker
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### Create Database
1. Connect to your SQL Server instance
2. Create a new database:
```sql
CREATE DATABASE ActionItemDB;
```

#### Run Schema Script
Execute the provided SQL schema script:
```bash
sqlcmd -S your_server -d ActionItemDB -i database_schema.sql
```

Or manually execute the `database_schema.sql` file in your SQL Server Management Studio.

### 5. Environment Configuration

Create a `.env` file in the project root and configure your database connection:

```env
# Application Settings
SECRET_KEY=your-super-secret-key-change-this-in-production

# MSSQL Database Configuration
DB_SERVER=localhost
DB_NAME=ActionItemDB
DB_USERNAME=your_username
DB_PASSWORD=your_password

# Application Configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

**Security Note**: In production, use a strong, random secret key and secure database credentials.

### 6. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Database Schema

### Users Table
- `id` (Primary Key)
- `username` (Unique)
- `email` (Unique)
- `password_hash`
- `first_name`
- `last_name`
- `created_at`
- `is_active`

### Action Items Table
- `id` (Primary Key)
- `title`
- `description`
- `status` (Open, In Progress, Completed, Cancelled)
- `priority` (Low, Medium, High, Critical)
- `assigned_to` (Foreign Key to Users)
- `created_by` (Foreign Key to Users)
- `due_date`
- `created_at`
- `updated_at`

### Additional Database Objects
- **Views**: `VW_ActionItemsWithUsers` for joined data
- **Stored Procedures**: For common operations
- **Functions**: For statistics and calculations
- **Triggers**: Automatic timestamp updates

## Usage Guide

### First Time Setup
1. Navigate to `http://localhost:5000`
2. Click "Register" to create your first user account
3. Fill in your details and create an account
4. Log in with your credentials

### Creating Action Items
1. Click "Create New Item" from the dashboard or navigation
2. Fill in the required fields:
   - **Title**: Brief description of the task
   - **Description**: Detailed information (optional)
   - **Priority**: Choose importance level
   - **Assign To**: Select team member (optional)
   - **Due Date**: Set deadline (optional)
3. Click "Create Action Item"

### Managing Action Items
- **View All**: Navigate to "Action Items" to see all items
- **Filter**: Use the filter controls to narrow down results
- **Search**: Use the search box to find specific items
- **Edit**: Click the edit icon to modify an item
- **Delete**: Click the delete icon and confirm removal

### Dashboard Features
- **Statistics Cards**: Quick overview of item counts
- **My Items**: Items assigned to you
- **Created Items**: Items you've created
- **Recent Activity**: Latest updates across all items

## API Endpoints

The application also provides REST API endpoints:

- `GET /api/action-items` - Retrieve all action items (JSON)

Additional API endpoints can be easily added following the existing pattern.

## Customization

### Styling
- Modify `static/css/style.css` for custom styling
- The application uses Bootstrap 5 for responsive design
- Custom CSS classes are available for specific components

### Functionality
- Add new fields to the database schema
- Extend the models in `app.py`
- Create new templates in the `templates/` directory
- Add JavaScript enhancements in `static/js/main.js`

## Security Features

- Password hashing using Werkzeug's security utilities
- CSRF protection with Flask-WTF
- SQL injection prevention through SQLAlchemy ORM
- Session management with Flask-Login
- Input validation and sanitization

## Performance Optimization

- Database indexes on frequently queried columns
- Efficient SQL queries with proper joins
- Pagination can be added for large datasets
- Static file caching
- Minified CSS and JavaScript in production

## Deployment

### Production Considerations
1. **Database**: Use a production SQL Server instance
2. **Security**: 
   - Change the secret key
   - Use HTTPS
   - Implement proper authentication
   - Set up database user with minimal privileges
3. **Performance**:
   - Use a WSGI server like Gunicorn
   - Set up reverse proxy with Nginx
   - Enable gzip compression
   - Use CDN for static files

### Example Production Deployment
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
- Verify SQL Server is running
- Check connection string parameters
- Ensure ODBC driver is installed
- Verify database permissions

#### Python Package Issues
- Make sure virtual environment is activated
- Update pip: `pip install --upgrade pip`
- Install packages individually if batch install fails

#### Application Not Starting
- Check Python version compatibility
- Verify all environment variables are set
- Review error logs for specific issues

### Debug Mode
Set `FLASK_DEBUG=True` in your `.env` file for detailed error messages during development.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the database schema documentation
3. Check application logs for error details
4. Create an issue in the repository

## Changelog

### Version 1.0.0
- Initial release
- User authentication system
- Action item CRUD operations
- Dashboard with statistics
- Responsive web interface
- MSSQL database integration
- Modern UI with Bootstrap 5

---

**Built with ❤️ using Flask and Microsoft SQL Server**