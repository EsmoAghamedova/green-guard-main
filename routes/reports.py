import os
import uuid

from flask import Blueprint, abort, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from forms import CuttingReportEditForm, CuttingReportForm, DeleteForm, PlantTreeForm, TreeRecordEditForm
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


def remove_uploaded_image(filename: str | None) -> None:
    if not filename:
        return

    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path):
        os.remove(file_path)


def ensure_owner_or_admin(owner_user_id: int) -> None:
    if current_user.id != owner_user_id and not current_user.is_admin:
        abort(403)


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
        return redirect(url_for("reports.cutting_gallery"))

    return render_template("report_cutting.html", form=form)


@reports_bp.route("/reports")
def view_reports():
    report_count = CuttingReport.query.count()
    tree_count = TreeRecord.query.count()
    return render_template("reports.html", report_count=report_count, tree_count=tree_count)


@reports_bp.route("/reports/cutting")
def cutting_gallery():
    reports = CuttingReport.query.order_by(
        CuttingReport.created_at.desc()).all()
    return render_template("cutting_gallery.html", reports=reports)


@reports_bp.route("/reports/cutting/<int:report_id>")
def cutting_detail(report_id):
    report = CuttingReport.query.get_or_404(report_id)
    delete_form = DeleteForm()
    return render_template("cutting_detail.html", report=report, delete_form=delete_form)


@reports_bp.route("/reports/trees")
def trees_gallery():
    trees = TreeRecord.query.order_by(TreeRecord.created_at.desc()).all()
    return render_template("trees_gallery.html", trees=trees)


@reports_bp.route("/reports/trees/<int:tree_id>")
def tree_detail(tree_id):
    tree = TreeRecord.query.get_or_404(tree_id)
    delete_form = DeleteForm()
    return render_template("tree_detail.html", tree=tree, delete_form=delete_form)


@reports_bp.route("/reports/cutting/<int:report_id>/edit", methods=["GET", "POST"])
@login_required
def edit_cutting_report(report_id):
    report = CuttingReport.query.get_or_404(report_id)
    ensure_owner_or_admin(report.user_id)

    form = CuttingReportEditForm(obj=report)
    if form.validate_on_submit():
        old_image = report.image_filename
        new_image = save_uploaded_image(form.image)

        report.description = form.description.data.strip()
        report.latitude = float(form.latitude.data)
        report.longitude = float(form.longitude.data)
        report.location_text = form.location_text.data.strip(
        ) if form.location_text.data else None

        if new_image:
            report.image_filename = new_image
            remove_uploaded_image(old_image)

        db.session.commit()
        flash("Cutting report updated.", "success")
        return redirect(url_for("reports.cutting_detail", report_id=report.id))

    return render_template("edit_cutting_report.html", form=form, report=report)


@reports_bp.route("/reports/cutting/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_cutting_report(report_id):
    report = CuttingReport.query.get_or_404(report_id)
    ensure_owner_or_admin(report.user_id)

    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Invalid delete request.", "danger")
        return redirect(url_for("reports.cutting_detail", report_id=report.id))

    remove_uploaded_image(report.image_filename)
    db.session.delete(report)
    db.session.commit()
    flash("Cutting report deleted.", "info")
    return redirect(url_for("main.profile"))


@reports_bp.route("/reports/trees/<int:tree_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tree_record(tree_id):
    tree = TreeRecord.query.get_or_404(tree_id)
    ensure_owner_or_admin(tree.user_id)

    form = TreeRecordEditForm(obj=tree)
    if form.validate_on_submit():
        old_image = tree.image_filename
        new_image = save_uploaded_image(form.image)

        tree.species = form.species.data.strip()
        tree.quantity = form.quantity.data
        tree.latitude = float(form.latitude.data)
        tree.longitude = float(form.longitude.data)
        tree.location_notes = form.location_notes.data.strip(
        ) if form.location_notes.data else None

        if new_image:
            tree.image_filename = new_image
            remove_uploaded_image(old_image)

        db.session.commit()
        flash("Tree record updated.", "success")
        return redirect(url_for("reports.tree_detail", tree_id=tree.id))

    return render_template("edit_tree_record.html", form=form, tree=tree)


@reports_bp.route("/reports/trees/<int:tree_id>/delete", methods=["POST"])
@login_required
def delete_tree_record(tree_id):
    tree = TreeRecord.query.get_or_404(tree_id)
    ensure_owner_or_admin(tree.user_id)

    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Invalid delete request.", "danger")
        return redirect(url_for("reports.tree_detail", tree_id=tree.id))

    remove_uploaded_image(tree.image_filename)
    db.session.delete(tree)
    db.session.commit()
    flash("Tree record deleted.", "info")
    return redirect(url_for("main.profile"))
