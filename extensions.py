from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

# Shared Flask extensions are defined here to avoid circular imports.
db = SQLAlchemy()
login_manager = LoginManager()
