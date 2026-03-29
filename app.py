import os

from flask import Flask
from werkzeug.security import generate_password_hash
from extensions import db, login_manager


def create_app() -> Flask:
    app = Flask(__name__)

    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "green-guard-dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(base_dir, 'green_guard.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.reports import reports_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        from models import User

        db.create_all()
        ensure_admin_user(User)

    return app


def ensure_admin_user(user_model) -> None:
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@greenguard.local")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    admin_user = user_model.query.filter_by(username=admin_username).first()
    if admin_user:
        return

    admin_user = user_model(
        username=admin_username,
        email=admin_email,
        password_hash=generate_password_hash(admin_password),
        is_admin=True,
    )
    db.session.add(admin_user)
    db.session.commit()


@login_manager.user_loader
def load_user(user_id: str):
    from models import User

    return User.query.get(int(user_id))


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
