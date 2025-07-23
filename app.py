from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# MSSQL Database Configuration
server = os.getenv('DB_SERVER', 'localhost')
database = os.getenv('DB_NAME', 'ActionItemDB')
username = os.getenv('DB_USERNAME', 'sa')
password = os.getenv('DB_PASSWORD', 'YourPassword123')
driver = 'ODBC Driver 17 for SQL Server'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mssql+pyodbc://{username}:{password}@{server}/{database}?driver={driver}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# User Model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship with action items
    action_items = db.relationship('ActionItem', backref='assigned_user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Action Item Model
class ActionItem(db.Model):
    __tablename__ = 'action_items'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Open')  # Open, In Progress, Completed, Cancelled
    priority = db.Column(db.String(10), default='Medium')  # Low, Medium, High, Critical
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with user who created the item
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_items')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get action items assigned to current user
    my_items = ActionItem.query.filter_by(assigned_to=current_user.id).all()
    
    # Get action items created by current user
    created_items = ActionItem.query.filter_by(created_by=current_user.id).all()
    
    # Get all action items for overview (if user needs to see all)
    all_items = ActionItem.query.all()
    
    return render_template('dashboard.html', 
                         my_items=my_items, 
                         created_items=created_items, 
                         all_items=all_items)

@app.route('/action-items')
@login_required
def action_items():
    items = ActionItem.query.all()
    users = User.query.all()
    return render_template('action_items.html', items=items, users=users)

@app.route('/create-action-item', methods=['GET', 'POST'])
@login_required
def create_action_item():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        priority = request.form['priority']
        assigned_to = request.form.get('assigned_to')
        due_date = request.form.get('due_date')
        
        # Convert due_date string to date object if provided
        due_date_obj = None
        if due_date:
            try:
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format', 'error')
                return render_template('create_action_item.html', users=User.query.all())
        
        action_item = ActionItem(
            title=title,
            description=description,
            priority=priority,
            assigned_to=int(assigned_to) if assigned_to else None,
            created_by=current_user.id,
            due_date=due_date_obj
        )
        
        db.session.add(action_item)
        db.session.commit()
        
        flash('Action item created successfully!', 'success')
        return redirect(url_for('action_items'))
    
    users = User.query.all()
    return render_template('create_action_item.html', users=users)

@app.route('/edit-action-item/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_action_item(id):
    item = ActionItem.query.get_or_404(id)
    
    if request.method == 'POST':
        item.title = request.form['title']
        item.description = request.form['description']
        item.status = request.form['status']
        item.priority = request.form['priority']
        assigned_to = request.form.get('assigned_to')
        item.assigned_to = int(assigned_to) if assigned_to else None
        
        due_date = request.form.get('due_date')
        if due_date:
            try:
                item.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format', 'error')
                return render_template('edit_action_item.html', item=item, users=User.query.all())
        else:
            item.due_date = None
        
        item.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Action item updated successfully!', 'success')
        return redirect(url_for('action_items'))
    
    users = User.query.all()
    return render_template('edit_action_item.html', item=item, users=users)

@app.route('/delete-action-item/<int:id>', methods=['POST'])
@login_required
def delete_action_item(id):
    item = ActionItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Action item deleted successfully!', 'success')
    return redirect(url_for('action_items'))

@app.route('/api/action-items')
@login_required
def api_action_items():
    items = ActionItem.query.all()
    return jsonify([{
        'id': item.id,
        'title': item.title,
        'description': item.description,
        'status': item.status,
        'priority': item.priority,
        'assigned_to': item.assigned_user.username if item.assigned_user else None,
        'created_by': item.creator.username,
        'due_date': item.due_date.isoformat() if item.due_date else None,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat()
    } for item in items])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)