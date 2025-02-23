from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid  # For generating unique filenames
from datetime import datetime

app = Flask(__name__)

# Configuration (replace with your actual database credentials)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:myuser:mypassword@localhost:5432/mydatabase'  # Example for PostgreSQL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Directory to store uploaded files
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) # Create uploads directory if it doesn't exist

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    capsules = db.relationship('Capsule', backref='user', lazy=True)  # Add relationship to capsules

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Capsule Model
class Capsule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    opening_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Foreign key to link with the User
    files = db.relationship('File', backref='capsule', lazy=True)

# File Model (for storing file metadata)
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)  # Path to the file in storage
    capsule_id = db.Column(db.Integer, db.ForeignKey('capsule.id'), nullable=False)


# Create database tables (run this once)
with app.app_context():
    db.create_all()


# Routes
@app.route('/api/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already exists'}), 400

    new_user = User(name=name, email=email)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'success': True}), 201  # 201 Created
    except Exception as e:
        db.session.rollback()  # Important: Rollback on error
        print(f"Error during signup: {e}")  # Log the error
        return jsonify({'success': False, 'message': 'An error occurred during signup'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401  # 401 Unauthorized

    # In a real application, you would generate a JWT here
    # For this example, we'll just return a success message
    return jsonify({'success': True, 'token': 'your_jwt_token'}), 200  # Replace with actual JWT


@app.route('/api/capsules', methods=['POST'])
def create_capsule():
    title = request.form.get('title')
    description = request.form.get('description')
    opening_date_str = request.form.get('openingDate')  # Get the date as a string

    if not title or not opening_date_str:
        return jsonify({'success': False, 'message': 'Title and opening date are required'}), 400

    try:
        opening_date = datetime.strptime(opening_date_str, '%Y-%m-%d').date()  # Convert to date object
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400

    # ... (Get the user ID from the token - you'll need to implement JWT handling)
    user_id = 1  # Placeholder - replace with actual user ID from token

    new_capsule = Capsule(title=title, description=description, opening_date=opening_date, user_id=user_id)

    try:
        db.session.add(new_capsule)
        db.session.commit()

        # Handle file uploads
        if 'images' in request.files:
            for file in request.files.getlist('images'):
                filename = str(uuid.uuid4()) + "." + file.filename.rsplit('.', 1)[1]  # Generate unique filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                new_file = File(filename=filename, path=filepath, capsule_id=new_capsule.id)
                db.session.add(new_file)

        if 'videos' in request.files: # Similar handling for videos
            for file in request.files.getlist('videos'):
                filename = str(uuid.uuid4()) + "." + file.filename.rsplit('.', 1)[1]
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                new_file = File(filename=filename, path=filepath, capsule_id=new_capsule.id)
                db.session.add(new_file)

        if 'documents' in request.files: # And similar for documents
            for file in request.files.getlist('documents'):
                filename = str(uuid.uuid4()) + "." + file.filename.rsplit('.', 1)[1]
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                new_file = File(filename=filename, path=filepath, capsule_id=new_capsule.id)
                db.session.add(new_file)

        db.session.commit()
        return jsonify({'success': True}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating capsule: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

# Serve static files from the uploads folder (for accessing uploaded files)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == 'main':
    app.run(debug=True)  # Set debug=False in production
