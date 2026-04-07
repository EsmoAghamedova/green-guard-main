from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Campaign, CuttingReport, SupportDonation, TreeRecord, User

admin_bp = Blueprint("admin", __name__)


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


@admin_bp.route("/admin")
@login_required
@admin_required
def dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    tree_records = TreeRecord.query.order_by(
        TreeRecord.created_at.desc()).all()
    reports = CuttingReport.query.order_by(
        CuttingReport.created_at.desc()).all()
    campaigns = Campaign.query.order_by(Campaign.event_date.desc()).all()
    sponsor_donations = SupportDonation.query.order_by(
        SupportDonation.created_at.desc()).all()

    sponsor_totals = (
        db.session.query(User, db.func.sum(
            SupportDonation.amount).label("total_amount"))
        .join(SupportDonation, SupportDonation.user_id == User.id)
        .filter(User.role.in_(["business", "individual"]))
        .group_by(User.id)
        .order_by(db.func.sum(SupportDonation.amount).desc())
        .all()
    )
    donation_volume = sum(float(item.amount) for item in sponsor_donations)

    campaign_rows = [
        {
            "id": campaign.id,
            "title": campaign.title,
            "creator_name": campaign.creator.username if campaign.creator else "Green Guard",
            "event_date_text": campaign.event_date.strftime("%Y-%m-%d"),
            "status": campaign.status,
        }
        for campaign in campaigns
    ]
    return render_template(
        "admin/dashboard.html",
        users=users,
        tree_records=tree_records,
        reports=reports,
        campaigns=campaigns,
        campaign_rows=campaign_rows,
        sponsor_donations=sponsor_donations,
        sponsor_totals=sponsor_totals,
        donation_volume=donation_volume,
    )


@admin_bp.route("/admin/users")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/admin/report/<int:report_id>/status", methods=["POST"])
@login_required
@admin_required
def update_report_status(report_id):
    report = CuttingReport.query.get_or_404(report_id)
    new_status = request.form.get("status", "pending").strip().lower()
    valid_statuses = {"pending", "reviewed", "resolved", "rejected"}

    if new_status not in valid_statuses:
        flash("Invalid status value.", "danger")
        return redirect(url_for("admin.dashboard"))

    report.status = new_status
    db.session.commit()
    flash("Report status updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/campaign/<int:campaign_id>/status", methods=["POST"])
@login_required
@admin_required
def update_campaign_status(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    new_status = request.form.get("status", "open").strip().lower()
    valid_statuses = {"open", "ongoing", "closed"}

    if new_status not in valid_statuses:
        flash("Invalid campaign status value.", "danger")
        return redirect(url_for("admin.dashboard"))

    campaign.status = new_status
    db.session.commit()
    flash("Campaign status updated.", "success")
    return redirect(url_for("admin.dashboard"))
