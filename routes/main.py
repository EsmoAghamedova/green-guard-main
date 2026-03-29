import json

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from markupsafe import Markup

from models import CuttingReport, TreeRecord, User

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    total_trees = TreeRecord.query.with_entities(TreeRecord.quantity).all()
    total_tree_count = sum(item.quantity for item in total_trees)
    total_reports = CuttingReport.query.count()
    total_users = User.query.count()

    co2_kg = total_tree_count * 21
    co2_display = f"{co2_kg} kg"
    if co2_kg >= 1000:
        co2_display = f"{co2_kg / 1000:.2f} tonnes"

    return render_template(
        "home.html",
        total_trees=total_tree_count,
        total_reports=total_reports,
        total_users=total_users,
        co2_display=co2_display,
    )


@main_bp.route("/map")
def map_view():
    trees = TreeRecord.query.all()
    reports = CuttingReport.query.all()

    trees_json = [
        {
            "id": tree.id,
            "species": tree.species,
            "quantity": tree.quantity,
            "latitude": tree.latitude,
            "longitude": tree.longitude,
            "username": tree.user.username,
        }
        for tree in trees
    ]
    reports_json = [
        {
            "id": report.id,
            "description": report.description,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "status": report.status,
            "username": report.user.username,
        }
        for report in reports
    ]

    return render_template(
        "map.html",
        trees_json=Markup(json.dumps(trees_json)),
        reports_json=Markup(json.dumps(reports_json)),
    )


@main_bp.route("/profile")
@login_required
def profile():
    user_trees = (
        TreeRecord.query.filter_by(user_id=current_user.id)
        .order_by(TreeRecord.created_at.desc())
        .all()
    )
    user_reports = (
        CuttingReport.query.filter_by(user_id=current_user.id)
        .order_by(CuttingReport.created_at.desc())
        .all()
    )
    return render_template("profile.html", user_trees=user_trees, user_reports=user_reports)
