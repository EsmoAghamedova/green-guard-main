from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import CuttingReport, TreeRecord, User

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
    return render_template(
        "admin/dashboard.html",
        users=users,
        tree_records=tree_records,
        reports=reports,
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
