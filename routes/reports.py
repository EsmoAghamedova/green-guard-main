import os
import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from forms import CuttingReportForm, PlantTreeForm
from models import CuttingReport, TreeRecord

reports_bp = Blueprint("reports", __name__)


def save_uploaded_image(image_field):
    if not image_field.data:
        return None

    filename = secure_filename(image_field.data.filename)
    if not filename:
        return None

    ext = filename.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"], unique_name)
    image_field.data.save(upload_path)
    return unique_name


@reports_bp.route("/plant", methods=["GET", "POST"])
@login_required
def plant_tree():
    form = PlantTreeForm()
    if form.validate_on_submit():
        image_filename = save_uploaded_image(form.image)

        record = TreeRecord(
            species=form.species.data.strip(),
            quantity=form.quantity.data,
            latitude=float(form.latitude.data),
            longitude=float(form.longitude.data),
            location_notes=form.location_notes.data.strip(
            ) if form.location_notes.data else None,
            image_filename=image_filename,
            user_id=current_user.id,
        )
        db.session.add(record)
        db.session.commit()
        flash("Tree planting record submitted successfully.", "success")
        return redirect(url_for("main.index"))

    return render_template("plant_tree.html", form=form)


@reports_bp.route("/report", methods=["GET", "POST"])
@login_required
def report_cutting():
    form = CuttingReportForm()
    if form.validate_on_submit():
        image_filename = save_uploaded_image(form.image)

        report = CuttingReport(
            description=form.description.data.strip(),
            latitude=float(form.latitude.data),
            longitude=float(form.longitude.data),
            location_text=form.location_text.data.strip() if form.location_text.data else None,
            image_filename=image_filename,
            user_id=current_user.id,
        )
        db.session.add(report)
        db.session.commit()
        flash("Cutting report submitted. Thank you for helping protect nature.", "success")
        return redirect(url_for("reports.view_reports"))

    return render_template("report_cutting.html", form=form)


@reports_bp.route("/reports")
def view_reports():
    reports = CuttingReport.query.order_by(
        CuttingReport.created_at.desc()).all()
    trees = TreeRecord.query.order_by(TreeRecord.created_at.desc()).all()
    return render_template("reports.html", reports=reports, trees=trees)
