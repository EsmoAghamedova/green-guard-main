from flask import Blueprint, flash, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import ContactForm, DeleteForm
from models import CuttingReport, TreeRecord, User

main_bp = Blueprint("main", __name__)


def build_map_payload() -> dict:
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

    return {"trees": trees_json, "reports": reports_json}


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
    payload = build_map_payload()

    return render_template(
        "map.html",
        trees_json=payload["trees"],
        reports_json=payload["reports"],
    )


@main_bp.route("/api/map-data")
def map_data():
    return jsonify(build_map_payload())


@main_bp.route("/leaderboard")
def leaderboard():
    tree_totals = dict(
        db.session.query(TreeRecord.user_id, db.func.sum(TreeRecord.quantity))
        .group_by(TreeRecord.user_id)
        .all()
    )
    report_counts = dict(
        db.session.query(CuttingReport.user_id,
                         db.func.count(CuttingReport.id))
        .group_by(CuttingReport.user_id)
        .all()
    )

    rows = []
    for user in User.query.filter_by(is_admin=False).all():
        trees_planted = int(tree_totals.get(user.id, 0) or 0)
        reports_submitted = int(report_counts.get(user.id, 0) or 0)
        score = trees_planted * 2 + reports_submitted
        rows.append(
            {
                "user": user,
                "trees_planted": trees_planted,
                "reports_submitted": reports_submitted,
                "score": score,
            }
        )

    rows.sort(
        key=lambda item: (
            item["score"],
            item["trees_planted"],
            item["reports_submitted"],
            item["user"].username.lower(),
        ),
        reverse=True,
    )

    for index, item in enumerate(rows, start=1):
        item["rank"] = index

    return render_template("leaderboard.html", leaderboard=rows)


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()

    if form.validate_on_submit():
        flash("Thank you for contacting Green Guard. We received your message.", "success")
        return redirect(url_for("main.contact"))

    return render_template("contact.html", form=form)


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
    delete_form = DeleteForm()
    return render_template("profile.html", user_trees=user_trees, user_reports=user_reports, delete_form=delete_form)
