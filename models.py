from datetime import datetime

from flask_login import UserMixin

from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)

    tree_records = db.relationship(
        "TreeRecord", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    cutting_reports = db.relationship(
        "CuttingReport", backref="user", lazy=True, cascade="all, delete-orphan"
    )


class TreeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    species = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_notes = db.Column(db.String(255))
    image_filename = db.Column(db.String(255))
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class CuttingReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_text = db.Column(db.String(255))
    image_filename = db.Column(db.String(255))
    status = db.Column(db.String(30), default="pending", nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
