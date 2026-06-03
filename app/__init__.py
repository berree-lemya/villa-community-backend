from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()


def create_app(config_name="development"):
    app = Flask(__name__)

    if config_name == "development":
        app.config.from_object("app.config.DevelopmentConfig")
    elif config_name == "production":
        app.config.from_object("app.config.ProductionConfig")
    else:
        app.config.from_object("app.config.TestingConfig")

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.bookings import bookings_bp
    from app.routes.maintenance import maintenance_bp
    from app.routes.gate_access import gate_bp
    from app.routes.admin import admin_bp
    from app.routes.villas import villas_bp
    from app.routes.bills import bills_bp
    from app.routes.announcements import announcements_bp
    from app.routes.parking import parking_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(maintenance_bp, url_prefix="/api/maintenance")
    app.register_blueprint(gate_bp, url_prefix="/api/gate")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(villas_bp, url_prefix="/api/villas")
    app.register_blueprint(bills_bp, url_prefix="/api/bills")
    app.register_blueprint(announcements_bp, url_prefix="/api/announcements")
    app.register_blueprint(parking_bp, url_prefix="/api/parking")

    return app
