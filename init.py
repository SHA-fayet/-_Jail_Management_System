# app/__init__.py
import os  # <-- ADDING THIS LINE TO FIX THE 'os is not defined' ERROR SOMETIMES THAT ERROR OCCUR
from flask import Flask
from flask_mysqldb import MySQL
from flask_cors import CORS
from .config import Config
from app.routes.alerts import start_scheduler

mysql = MySQL()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
  
    
    CORS(app, supports_credentials=True) 

    mysql.init_app(app)

    # Register blueprints AFTER initializing MySQL to prevent import issues
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.inmates import inmates_bp
    from .routes.visitors import visitors_bp
    from .routes.visit_request import visit_request_bp
  
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inmates_bp)
    app.register_blueprint(visitors_bp)
    app.register_blueprint(visit_request_bp)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_scheduler()

    return app
