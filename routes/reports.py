import os
import uuid

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from forms import CampaignPlantTreeForm, CuttingReportEditForm, CuttingReportForm, DeleteForm, PlantTreeForm, TreeRecordEditForm
from models import Campaign, CuttingReport, TreeRecord, VolunteerCampaignSignup
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


def parse_form_coordinates(form) -> tuple[float | None, float | None]:
    latitude_value = form.latitude.data
    longitude_value = form.longitude.data

    if latitude_value is None or longitude_value is None:
        return None, None

    return float(latitude_value), float(longitude_value)


@reports_bp.route("/plant", methods=["GET", "POST"])
@login_required
def plant_tree():
    form = PlantTreeForm()
    if form.validate_on_submit():
        latitude, longitude = parse_form_coordinates(form)
        if latitude is None or longitude is None:
            flash("Please provide a valid location (latitude and longitude).", "warning")
            return render_template("plant_tree.html", form=form)

        image_filename = save_uploaded_image(form.image)

        record = TreeRecord(
            species=form.species.data.strip(),
            quantity=form.quantity.data,
            latitude=latitude,
            longitude=longitude,
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


@reports_bp.route("/plant/campaign", methods=["GET", "POST"])
@login_required
def plant_tree_campaign():
    form = CampaignPlantTreeForm()

    joined_signups = VolunteerCampaignSignup.query.filter_by(
        user_id=current_user.id
    ).all()
    joined_campaign_ids = [signup.campaign_id for signup in joined_signups]
    joined_campaigns = Campaign.query.filter(
        Campaign.id.in_(joined_campaign_ids)
    ).order_by(Campaign.event_date.asc()).all() if joined_campaign_ids else []

    form.campaign_id.choices = [
        (campaign.id,
         f"{campaign.title} ({campaign.event_date.strftime('%Y-%m-%d')})")
        for campaign in joined_campaigns
    ]

    requested_campaign_id = request.args.get("campaign_id", "").strip()
    if requested_campaign_id.isdigit():
        requested_campaign_id_int = int(requested_campaign_id)
        valid_campaign_ids = {choice[0] for choice in form.campaign_id.choices}
        if requested_campaign_id_int in valid_campaign_ids:
            form.campaign_id.data = requested_campaign_id_int

    if not form.campaign_id.choices:
        flash("Join a campaign first, then submit planted trees.", "warning")
        return redirect(url_for("main.explore", tab="campaigns"))

    if form.validate_on_submit():
        latitude, longitude = parse_form_coordinates(form)
        if latitude is None or longitude is None:
            flash("Please provide a valid location (latitude and longitude).", "warning")
            return render_template("plant_tree_campaign.html", form=form)

        image_filename = save_uploaded_image(form.image)

        record = TreeRecord(
            species=form.species.data.strip(),
            quantity=form.quantity.data,
            latitude=latitude,
            longitude=longitude,
            location_notes=form.location_notes.data.strip(
            ) if form.location_notes.data else None,
            image_filename=image_filename,
            user_id=current_user.id,
            campaign_id=form.campaign_id.data,
        )
        db.session.add(record)
        db.session.commit()
        flash("Campaign planting uploaded. It now appears on the map.", "success")
        return redirect(url_for("main.explore", tab="map"))

    return render_template("plant_tree_campaign.html", form=form)


@reports_bp.route("/report", methods=["GET", "POST"])
@login_required
def report_cutting():
    form = CuttingReportForm()
    if form.validate_on_submit():
        latitude, longitude = parse_form_coordinates(form)
        if latitude is None or longitude is None:
            flash("Please provide a valid location (latitude and longitude).", "warning")
            return render_template("report_cutting.html", form=form)

        image_filename = save_uploaded_image(form.image)

        report = CuttingReport(
            description=form.description.data.strip(),
            latitude=latitude,
            longitude=longitude,
            location_text=form.location_text.data.strip() if form.location_text.data else None,
            image_filename=image_filename,
            user_id=current_user.id,
        )
        db.session.add(report)
        db.session.commit()
        flash("Report submitted and queued for verification. It will appear on the map after review.", "success")
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
        latitude, longitude = parse_form_coordinates(form)
        if latitude is None or longitude is None:
            flash("Please provide a valid location (latitude and longitude).", "warning")
            return render_template("edit_cutting_report.html", form=form, report=report)

        old_image = report.image_filename
        new_image = save_uploaded_image(form.image)

        report.description = form.description.data.strip()
        report.latitude = latitude
        report.longitude = longitude
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
        latitude, longitude = parse_form_coordinates(form)
        if latitude is None or longitude is None:
            flash("Please provide a valid location (latitude and longitude).", "warning")
            return render_template("edit_tree_record.html", form=form, tree=tree)

        old_image = tree.image_filename
        new_image = save_uploaded_image(form.image)

        tree.species = form.species.data.strip()
        tree.quantity = form.quantity.data
        tree.latitude = latitude
        tree.longitude = longitude
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
