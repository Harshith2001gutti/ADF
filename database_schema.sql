-- Action Item Tracker Database Schema for Microsoft SQL Server
-- This script creates the database and tables required for the application

-- Create database (uncomment if you need to create the database)
-- CREATE DATABASE ActionItemDB;
-- GO

-- Use the database
USE ActionItemDB;
GO

-- Create Users table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
BEGIN
    CREATE TABLE users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(80) NOT NULL UNIQUE,
        email NVARCHAR(120) NOT NULL UNIQUE,
        password_hash NVARCHAR(128) NOT NULL,
        first_name NVARCHAR(50) NOT NULL,
        last_name NVARCHAR(50) NOT NULL,
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        is_active BIT DEFAULT 1
    );
    
    -- Create indexes for better performance
    CREATE INDEX IX_users_username ON users(username);
    CREATE INDEX IX_users_email ON users(email);
    CREATE INDEX IX_users_is_active ON users(is_active);
    
    PRINT 'Users table created successfully';
END
ELSE
BEGIN
    PRINT 'Users table already exists';
END
GO

-- Create Action Items table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='action_items' AND xtype='U')
BEGIN
    CREATE TABLE action_items (
        id INT IDENTITY(1,1) PRIMARY KEY,
        title NVARCHAR(200) NOT NULL,
        description NTEXT NULL,
        status NVARCHAR(20) DEFAULT 'Open' CHECK (status IN ('Open', 'In Progress', 'Completed', 'Cancelled')),
        priority NVARCHAR(10) DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
        assigned_to INT NULL,
        created_by INT NOT NULL,
        due_date DATE NULL,
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        updated_at DATETIME2 DEFAULT GETUTCDATE(),
        
        -- Foreign key constraints
        CONSTRAINT FK_action_items_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
        CONSTRAINT FK_action_items_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
    );
    
    -- Create indexes for better performance
    CREATE INDEX IX_action_items_status ON action_items(status);
    CREATE INDEX IX_action_items_priority ON action_items(priority);
    CREATE INDEX IX_action_items_assigned_to ON action_items(assigned_to);
    CREATE INDEX IX_action_items_created_by ON action_items(created_by);
    CREATE INDEX IX_action_items_due_date ON action_items(due_date);
    CREATE INDEX IX_action_items_created_at ON action_items(created_at);
    CREATE INDEX IX_action_items_updated_at ON action_items(updated_at);
    
    PRINT 'Action Items table created successfully';
END
ELSE
BEGIN
    PRINT 'Action Items table already exists';
END
GO

-- Create trigger to update the updated_at column
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'TR_action_items_update_timestamp')
BEGIN
    EXEC('
    CREATE TRIGGER TR_action_items_update_timestamp
    ON action_items
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE action_items 
        SET updated_at = GETUTCDATE()
        WHERE id IN (SELECT DISTINCT id FROM inserted);
    END
    ');
    
    PRINT 'Update timestamp trigger created successfully';
END
ELSE
BEGIN
    PRINT 'Update timestamp trigger already exists';
END
GO

-- Insert sample data (optional - for testing)
-- Uncomment the following section if you want to populate with sample data

/*
-- Insert sample users
IF NOT EXISTS (SELECT * FROM users WHERE username = 'admin')
BEGIN
    INSERT INTO users (username, email, password_hash, first_name, last_name)
    VALUES 
        ('admin', 'admin@example.com', 'pbkdf2:sha256:260000$salt$hash', 'System', 'Administrator'),
        ('john.doe', 'john.doe@example.com', 'pbkdf2:sha256:260000$salt$hash', 'John', 'Doe'),
        ('jane.smith', 'jane.smith@example.com', 'pbkdf2:sha256:260000$salt$hash', 'Jane', 'Smith');
    
    PRINT 'Sample users inserted';
END

-- Insert sample action items
IF NOT EXISTS (SELECT * FROM action_items WHERE title = 'Setup Development Environment')
BEGIN
    DECLARE @admin_id INT = (SELECT id FROM users WHERE username = 'admin');
    DECLARE @john_id INT = (SELECT id FROM users WHERE username = 'john.doe');
    DECLARE @jane_id INT = (SELECT id FROM users WHERE username = 'jane.smith');
    
    INSERT INTO action_items (title, description, status, priority, assigned_to, created_by, due_date)
    VALUES 
        ('Setup Development Environment', 'Configure development environment for new team members', 'Open', 'High', @john_id, @admin_id, DATEADD(day, 7, GETDATE())),
        ('Review Code Standards', 'Review and update coding standards documentation', 'In Progress', 'Medium', @jane_id, @admin_id, DATEADD(day, 14, GETDATE())),
        ('Database Backup Strategy', 'Implement automated database backup strategy', 'Open', 'Critical', @admin_id, @admin_id, DATEADD(day, 3, GETDATE())),
        ('User Training Session', 'Conduct training session for new application features', 'Completed', 'Low', @jane_id, @john_id, DATEADD(day, -2, GETDATE()));
    
    PRINT 'Sample action items inserted';
END
*/

-- Create views for reporting
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'VW_ActionItemsWithUsers')
BEGIN
    EXEC('
    CREATE VIEW VW_ActionItemsWithUsers AS
    SELECT 
        ai.id,
        ai.title,
        ai.description,
        ai.status,
        ai.priority,
        ai.due_date,
        ai.created_at,
        ai.updated_at,
        creator.username AS created_by_username,
        creator.first_name + '' '' + creator.last_name AS created_by_name,
        assignee.username AS assigned_to_username,
        assignee.first_name + '' '' + assignee.last_name AS assigned_to_name,
        CASE 
            WHEN ai.due_date IS NOT NULL AND ai.due_date < CAST(GETDATE() AS DATE) AND ai.status NOT IN (''Completed'', ''Cancelled'')
            THEN 1 
            ELSE 0 
        END AS is_overdue,
        CASE 
            WHEN ai.due_date IS NOT NULL 
            THEN DATEDIFF(day, CAST(GETDATE() AS DATE), ai.due_date)
            ELSE NULL 
        END AS days_until_due
    FROM action_items ai
    INNER JOIN users creator ON ai.created_by = creator.id
    LEFT JOIN users assignee ON ai.assigned_to = assignee.id
    ');
    
    PRINT 'ActionItems view created successfully';
END
ELSE
BEGIN
    PRINT 'ActionItems view already exists';
END
GO

-- Create stored procedures for common operations
IF NOT EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_GetActionItemsByUser')
BEGIN
    EXEC('
    CREATE PROCEDURE SP_GetActionItemsByUser
        @UserId INT,
        @IncludeCreated BIT = 1,
        @IncludeAssigned BIT = 1
    AS
    BEGIN
        SET NOCOUNT ON;
        
        SELECT * FROM VW_ActionItemsWithUsers
        WHERE (@IncludeCreated = 1 AND created_by = (SELECT username FROM users WHERE id = @UserId))
           OR (@IncludeAssigned = 1 AND assigned_to_username = (SELECT username FROM users WHERE id = @UserId))
        ORDER BY created_at DESC;
    END
    ');
    
    PRINT 'GetActionItemsByUser stored procedure created successfully';
END
ELSE
BEGIN
    PRINT 'GetActionItemsByUser stored procedure already exists';
END
GO

IF NOT EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_GetOverdueActionItems')
BEGIN
    EXEC('
    CREATE PROCEDURE SP_GetOverdueActionItems
    AS
    BEGIN
        SET NOCOUNT ON;
        
        SELECT * FROM VW_ActionItemsWithUsers
        WHERE is_overdue = 1
        ORDER BY due_date ASC;
    END
    ');
    
    PRINT 'GetOverdueActionItems stored procedure created successfully';
END
ELSE
BEGIN
    PRINT 'GetOverdueActionItems stored procedure already exists';
END
GO

-- Create function for action item statistics
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = 'FN_GetActionItemStats' AND type = 'FN')
BEGIN
    EXEC('
    CREATE FUNCTION FN_GetActionItemStats(@UserId INT = NULL)
    RETURNS TABLE
    AS
    RETURN
    (
        SELECT 
            COUNT(*) AS total_items,
            SUM(CASE WHEN status = ''Open'' THEN 1 ELSE 0 END) AS open_items,
            SUM(CASE WHEN status = ''In Progress'' THEN 1 ELSE 0 END) AS in_progress_items,
            SUM(CASE WHEN status = ''Completed'' THEN 1 ELSE 0 END) AS completed_items,
            SUM(CASE WHEN status = ''Cancelled'' THEN 1 ELSE 0 END) AS cancelled_items,
            SUM(CASE WHEN due_date IS NOT NULL AND due_date < CAST(GETDATE() AS DATE) AND status NOT IN (''Completed'', ''Cancelled'') THEN 1 ELSE 0 END) AS overdue_items
        FROM action_items
        WHERE @UserId IS NULL OR assigned_to = @UserId OR created_by = @UserId
    )
    ');
    
    PRINT 'GetActionItemStats function created successfully';
END
ELSE
BEGIN
    PRINT 'GetActionItemStats function already exists';
END
GO

-- Grant permissions (adjust as needed for your environment)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON users TO [your_app_user];
-- GRANT SELECT, INSERT, UPDATE, DELETE ON action_items TO [your_app_user];
-- GRANT SELECT ON VW_ActionItemsWithUsers TO [your_app_user];
-- GRANT EXECUTE ON SP_GetActionItemsByUser TO [your_app_user];
-- GRANT EXECUTE ON SP_GetOverdueActionItems TO [your_app_user];
-- GRANT SELECT ON FN_GetActionItemStats TO [your_app_user];

PRINT 'Database schema setup completed successfully!';
PRINT 'You can now run your Flask application and it will connect to this database.';
GO