from datetime import datetime
from functools import wraps
from collections import defaultdict

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Campaign, CuttingReport, SupportDonation, TreeRecord, User, VolunteerCampaignSignup

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
    pending_verifications = (
        User.query.filter(
            User.is_admin.is_(False),
            User.role.in_(["business", "volunteer"]),
            User.verification_status != "approved",
        )
        .order_by(User.created_at.desc())
        .all()
    )
    tree_records = TreeRecord.query.order_by(
        TreeRecord.created_at.desc()).all()
    reports = CuttingReport.query.order_by(
        CuttingReport.created_at.desc()).all()
    campaigns = Campaign.query.order_by(Campaign.event_date.desc()).all()
    pending_signups = (
        VolunteerCampaignSignup.query.filter_by(status="pending")
        .order_by(VolunteerCampaignSignup.created_at.desc())
        .all()
    )
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
        pending_verifications=pending_verifications,
        tree_records=tree_records,
        reports=reports,
        campaigns=campaigns,
        pending_signups=pending_signups,
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


@admin_bp.route("/admin/user/<int:user_id>/verification", methods=["POST"])
@login_required
@admin_required
def update_user_verification(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("Admin accounts are always verified.", "warning")
        return redirect(url_for("admin.users"))

    new_status = request.form.get(
        "verification_status", "pending").strip().lower()
    valid_statuses = {"approved", "pending", "rejected"}

    if new_status not in valid_statuses:
        flash("Invalid verification status.", "danger")
        return redirect(url_for("admin.users"))

    user.verification_status = new_status
    if new_status == "approved":
        user.verified_at = datetime.utcnow()
        user.verified_by_id = current_user.id
    else:
        user.verified_at = None
        user.verified_by_id = None

    db.session.commit()
    flash(f"{user.username}'s verification status updated.", "success")
    return redirect(url_for("admin.users"))


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


@admin_bp.route("/admin/campaign-signup/<int:signup_id>/status", methods=["POST"])
@login_required
@admin_required
def update_campaign_signup_status(signup_id):
    signup = VolunteerCampaignSignup.query.get_or_404(signup_id)
    new_status = request.form.get("status", "pending").strip().lower()
    valid_statuses = {"pending", "approved", "rejected"}

    if new_status not in valid_statuses:
        flash("Invalid volunteer verification status.", "danger")
        return redirect(url_for("admin.dashboard"))

    signup.status = new_status
    db.session.commit()
    flash("Volunteer campaign verification updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/money")
@login_required
@admin_required
def money():
    sponsor_donations = SupportDonation.query.order_by(
        SupportDonation.created_at.desc()).all()

    total_donation_volume = 0.0
    total_commission_earned = 0.0
    total_project_allocation = 0.0
    rows = []
    commission_by_rate = defaultdict(float)
    commission_by_sponsor = defaultdict(float)

    for donation in sponsor_donations:
        amount = float(donation.amount)
        if amount < 1000:
            commission_rate = 0.05
        elif amount < 5000:
            commission_rate = 0.10
        else:
            commission_rate = 0.15

        commission_amount = amount * commission_rate
        project_allocation = amount - commission_amount

        total_donation_volume += amount
        total_commission_earned += commission_amount
        total_project_allocation += project_allocation

        commission_rate_label = f"{int(commission_rate * 100)}%"
        commission_by_rate[commission_rate_label] += commission_amount
        commission_by_sponsor[donation.user.username] += commission_amount

        rows.append(
            {
                "id": donation.id,
                "sponsor_name": donation.user.username,
                "category": donation.category,
                "amount": amount,
                "rate_label": commission_rate_label,
                "commission_amount": commission_amount,
                "project_allocation": project_allocation,
                "created_at_text": donation.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )

    top_sponsor_commissions = sorted(
        commission_by_sponsor.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:10]

    rate_breakdown_rows = [
        {
            "rate": rate,
            "commission_total": total,
        }
        for rate, total in sorted(
            commission_by_rate.items(),
            key=lambda item: int(item[0].replace("%", "")),
        )
    ]

    return render_template(
        "admin/money.html",
        total_donation_volume=total_donation_volume,
        total_commission_earned=total_commission_earned,
        total_project_allocation=total_project_allocation,
        rows=rows,
        rate_breakdown_rows=rate_breakdown_rows,
        top_sponsor_commissions=top_sponsor_commissions,
    )
