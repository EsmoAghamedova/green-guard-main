from datetime import datetime

from flask_login import UserMixin

from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="individual", nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)

    tree_records = db.relationship(
        "TreeRecord", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    cutting_reports = db.relationship(
        "CuttingReport", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    volunteer_signups = db.relationship(
        "VolunteerCampaignSignup", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    support_donations = db.relationship(
        "SupportDonation", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    created_campaigns = db.relationship(
        "Campaign", backref="creator", lazy=True, foreign_keys="Campaign.creator_user_id"
    )
    merch_purchases = db.relationship(
        "MerchPurchase", backref="user", lazy=True, cascade="all, delete-orphan"
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
    campaign_id = db.Column(
        db.Integer, db.ForeignKey("campaign.id"), nullable=True)


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


class GFWLocationSyncState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    last_synced_at = db.Column(db.DateTime)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class GFWLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_key = db.Column(db.String(160), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    region_label = db.Column(db.String(120), nullable=False)
    country_code = db.Column(db.String(3))
    country_name = db.Column(db.String(120))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    alert_date = db.Column(db.String(20), nullable=False)
    alert_time_utc = db.Column(db.String(20))
    confidence = db.Column(db.String(12))
    frp_mw = db.Column(db.Float)
    reforestation_type = db.Column(db.String(120))
    description = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(80), nullable=False,
                       default="nasa_viirs_fire_alerts")
    last_seen_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    location = db.Column(db.String(140), nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    target_trees = db.Column(db.Integer, default=100, nullable=False)
    status = db.Column(db.String(30), default="open", nullable=False)
    creator_user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)

    volunteer_signups = db.relationship(
        "VolunteerCampaignSignup", backref="campaign", lazy=True, cascade="all, delete-orphan"
    )
    tree_records = db.relationship(
        "TreeRecord", backref="campaign", lazy=True
    )


class VolunteerCampaignSignup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    motivation = db.Column(db.String(500))
    status = db.Column(db.String(30), default="pending", nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey(
        "campaign.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "campaign_id",
                            name="uq_volunteer_campaign_signup"),
    )


class SupportDonation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(40), nullable=False)
    donation_item = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)
    note = db.Column(db.String(500))
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class MerchPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    merch_key = db.Column(db.String(80), nullable=False)
    merch_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    payment_mode = db.Column(db.String(20), nullable=False, default="money")
    amount_usd = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    points_spent = db.Column(db.Integer, default=0, nullable=False)
    trees_supported = db.Column(db.Integer, default=0, nullable=False)
    note = db.Column(db.String(500))
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
