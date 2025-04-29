import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

from models.models import db, User, UserProfile, UserPhoto, LunchPreference, UserAvailability, Restaurant, LunchMeeting, Notification
from config import config

# Load environment variables
load_dotenv()

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure upload directory exists
    uploads_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    # Register blueprints
    from controllers.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from controllers.profile import profile as profile_blueprint
    app.register_blueprint(profile_blueprint)
    
    from controllers.matching import matching as matching_blueprint
    app.register_blueprint(matching_blueprint)
    
    from controllers.messaging import messaging as messaging_blueprint
    app.register_blueprint(messaging_blueprint)
    
    from controllers.notifications import notifications as notifications_blueprint
    app.register_blueprint(notifications_blueprint)
    
    # Home route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('matching.matches_list'))
        return render_template('index.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    app.run(debug=True) 