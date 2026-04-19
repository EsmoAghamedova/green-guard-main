import os

from flask import Flask, flash, redirect, request, url_for
from flask_login import current_user
from werkzeug.security import generate_password_hash
from extensions import db, login_manager
from permissions import is_user_verified


def create_app() -> Flask:
    app = Flask(__name__)

    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "green-guard-dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(base_dir, 'green_guard.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"timeout": 30},
    }
    app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    app.config["GFW_DAILY_SYNC_TIME"] = os.getenv(
        "GFW_DAILY_SYNC_TIME", "06:00")
    app.config["GFW_MAX_COUNTRIES"] = int(
        os.getenv("GFW_MAX_COUNTRIES", "20"))
    app.config["GFW_GLOBAL_ZOOM"] = int(
        os.getenv("GFW_GLOBAL_ZOOM", "3"))
    app.config["GFW_MAX_GRID_POINTS"] = int(
        os.getenv("GFW_MAX_GRID_POINTS", "24"))
    app.config["GFW_HTTP_TIMEOUT"] = int(
        os.getenv("GFW_HTTP_TIMEOUT", "12"))
    app.config["GFW_HTTP_RETRIES"] = int(
        os.getenv("GFW_HTTP_RETRIES", "2"))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.main import main_bp, start_gfw_location_scheduler
    from routes.reports import reports_bp
    from routes.volunteer import volunteer_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(volunteer_bp)

    @app.before_request
    def restrict_admin_navigation():
        if not current_user.is_authenticated or not current_user.is_admin:
            if current_user.is_authenticated and not current_user.is_admin and not is_user_verified(current_user):
                endpoint = request.endpoint
                allowed_endpoints = {
                    "auth.logout",
                    "auth.settings",
                    "auth.verification_pending",
                    "static",
                }
                if endpoint not in allowed_endpoints:
                    return redirect(url_for("auth.verification_pending"))

            return None

        endpoint = request.endpoint
        if endpoint and endpoint.startswith("admin."):
            return None

        allowed_endpoints = {
            "main.profile",
            "auth.settings",
            "auth.logout",
            "static",
        }
        if endpoint in allowed_endpoints:
            return None

        if endpoint:
            flash(
                "Admin access is limited to Dashboard, Finance, Profile, and Settings.", "warning")
        return redirect(url_for("admin.dashboard"))

    @app.context_processor
    def inject_media_url_helper():
        def media_url(filename: str | None) -> str:
            if not filename:
                return ""

            normalized_filename = filename.replace("\\", "/")
            if normalized_filename.startswith(("images/", "uploads/")) or "/" in normalized_filename:
                return url_for("static", filename=normalized_filename)

            return url_for("static", filename=f"uploads/{normalized_filename}")

        return {"media_url": media_url}

    with app.app_context():
        from models import User

        db.create_all()
        ensure_user_schema_columns(app)
        ensure_gfw_schema_columns(app)
        ensure_support_donation_schema_columns(app)
        ensure_campaign_schema_columns(app)
        ensure_tree_record_schema_columns(app)
        ensure_cutting_report_schema_columns(app)
        ensure_admin_user(User)

    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_gfw_location_scheduler(app)

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
        verification_status="approved",
    )
    db.session.add(admin_user)
    db.session.commit()


def ensure_user_schema_columns(app: Flask) -> None:
    # Keep backward compatibility for existing SQLite databases without migrations.
    required_columns = {
        "role": "TEXT DEFAULT 'individual'",
        "verification_status": "TEXT DEFAULT 'approved'",
        "verified_at": "DATETIME",
        "verified_by_id": "INTEGER",
    }

    with db.engine.begin() as connection:
        existing_rows = connection.exec_driver_sql(
            "PRAGMA table_info(user)"
        ).fetchall()
        if not existing_rows:
            return

        existing_columns = {row[1] for row in existing_rows}
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue

            connection.exec_driver_sql(
                f"ALTER TABLE user ADD COLUMN {column_name} {column_type}"
            )
            app.logger.info(
                "Added missing user column: %s", column_name)

        connection.exec_driver_sql(
            "UPDATE user SET role = 'individual' WHERE role IS NULL OR role = ''"
        )
        connection.exec_driver_sql(
            "UPDATE user SET verification_status = 'approved' WHERE verification_status IS NULL OR verification_status = ''"
        )

        # Citizen role has been removed. Normalize existing accounts to volunteer.
        connection.exec_driver_sql(
            "UPDATE user SET role = 'volunteer' WHERE role = 'citizen'"
        )


def ensure_gfw_schema_columns(app: Flask) -> None:
    # Keep backward compatibility for existing SQLite databases without migrations.
    required_columns = {
        "country_code": "TEXT",
        "country_name": "TEXT",
        "reforestation_type": "TEXT",
    }

    with db.engine.begin() as connection:
        existing_rows = connection.exec_driver_sql(
            "PRAGMA table_info(gfw_location)"
        ).fetchall()
        if not existing_rows:
            return

        existing_columns = {row[1] for row in existing_rows}
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue

            connection.exec_driver_sql(
                f"ALTER TABLE gfw_location ADD COLUMN {column_name} {column_type}"
            )
            app.logger.info(
                "Added missing gfw_location column: %s", column_name)


def ensure_support_donation_schema_columns(app: Flask) -> None:
    # Keep backward compatibility for existing SQLite databases without migrations.
    required_columns = {
        "donation_item": "TEXT DEFAULT 'plants:oak_saplings'",
        "quantity": "INTEGER DEFAULT 1",
        "points": "INTEGER DEFAULT 0",
    }

    with db.engine.begin() as connection:
        existing_rows = connection.exec_driver_sql(
            "PRAGMA table_info(support_donation)"
        ).fetchall()
        if not existing_rows:
            return

        existing_columns = {row[1] for row in existing_rows}
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue

            connection.exec_driver_sql(
                f"ALTER TABLE support_donation ADD COLUMN {column_name} {column_type}"
            )
            app.logger.info(
                "Added missing support_donation column: %s", column_name)


def ensure_campaign_schema_columns(app: Flask) -> None:
    # Keep backward compatibility for existing SQLite databases without migrations.
    required_columns = {
        "creator_user_id": "INTEGER",
        "target_trees": "INTEGER DEFAULT 100",
    }

    with db.engine.begin() as connection:
        existing_rows = connection.exec_driver_sql(
            "PRAGMA table_info(campaign)"
        ).fetchall()
        if not existing_rows:
            return

        existing_columns = {row[1] for row in existing_rows}
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue

            connection.exec_driver_sql(
                f"ALTER TABLE campaign ADD COLUMN {column_name} {column_type}"
            )
            app.logger.info(
                "Added missing campaign column: %s", column_name)


def ensure_tree_record_schema_columns(app: Flask) -> None:
    required_columns = {
        "campaign_id": "INTEGER",
    }

    with db.engine.begin() as connection:
        existing_rows = connection.exec_driver_sql(
            "PRAGMA table_info(tree_record)"
        ).fetchall()
        if not existing_rows:
            return

        existing_columns = {row[1] for row in existing_rows}
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue

            connection.exec_driver_sql(
                f"ALTER TABLE tree_record ADD COLUMN {column_name} {column_type}"
            )
            app.logger.info(
                "Added missing tree_record column: %s", column_name)


def ensure_cutting_report_schema_columns(app: Flask) -> None:
    required_columns = {
        "is_anonymous": "INTEGER DEFAULT 0",
    }

    with db.engine.begin() as connection:
        existing_rows = connection.exec_driver_sql(
            "PRAGMA table_info(cutting_report)"
        ).fetchall()
        if not existing_rows:
            return

        existing_columns = {row[1] for row in existing_rows}
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue

            connection.exec_driver_sql(
                f"ALTER TABLE cutting_report ADD COLUMN {column_name} {column_type}"
            )
            connection.exec_driver_sql(
                "UPDATE cutting_report SET is_anonymous = 0 WHERE is_anonymous IS NULL"
            )
            app.logger.info(
                "Added missing cutting_report column: %s", column_name)


@login_manager.user_loader
def load_user(user_id: str):
    from models import User

    return User.query.get(int(user_id))


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
