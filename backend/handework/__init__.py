import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from .config import Config
from .extensions import db, jwt, limiter, migrate, socketio


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=app.config["WEB_ORIGINS"])
    CORS(app, origins=app.config["WEB_ORIGINS"], supports_credentials=False, allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])

    from .routes.auth import bp as auth_bp
    from .routes.marketplace import bp as marketplace_bp
    from .routes.bookings import bp as bookings_bp
    from .routes.payments import bp as payments_bp
    from .routes.platform import bp as platform_bp
    from .routes.admin import bp as admin_bp
    from .routes.workproof import bp as workproof_bp
    from .routes.shop import bp as shop_bp
    for blueprint in (auth_bp, marketplace_bp, bookings_bp, payments_bp, platform_bp, admin_bp, workproof_bp, shop_bp):
        app.register_blueprint(blueprint, url_prefix="/v1")

    if os.getenv("FLASK_ENV") == "development" or os.getenv("STORAGE_MODE") == "local":
        @app.get("/v1/local-uploads/<path:filename>")
        def local_upload(filename):
            root = os.getenv("LOCAL_UPLOAD_DIR") or os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
            return send_from_directory(root, filename)

    @app.get("/v1/health")
    def health():
        database = "ok"
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception:
            database = "unavailable"
        status = 200 if database == "ok" else 503
        return jsonify({"status": "ok" if status == 200 else "degraded", "database": database, "service": "handework-api"}), status

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"message": "File is larger than the configured upload limit", "code": "upload_too_large"}), 413

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"message": "Route not found", "code": "not_found"}), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return jsonify({"message": "The request could not be completed", "code": "server_error"}), 500

    if os.getenv("FLASK_ENV") == "development":
        admin_email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD") or ""
        admin_phone = (os.getenv("ADMIN_PHONE") or "").strip()
        if admin_email and admin_password:
            from .models import Role, User
            with app.app_context():
                user = User.query.filter_by(email=admin_email).first()
                if not user and admin_phone:
                    user = User(
                        email=admin_email,
                        phone=admin_phone,
                        first_name=os.getenv("ADMIN_FIRST_NAME", "ALLMORROW"),
                        last_name=os.getenv("ADMIN_LAST_NAME", "Admin"),
                        role=Role.ADMIN,
                    )
                    db.session.add(user)
                if user:
                    user.role = Role.ADMIN
                    user.set_password(admin_password)
                    db.session.commit()

        @app.cli.command("init-db")
        def init_db():
            """Development-only table creation. Production uses Flask-Migrate."""
            db.create_all()
            print("Development database initialized")
    return app
