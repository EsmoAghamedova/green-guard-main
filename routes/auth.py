import time

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import OperationalError
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from forms import AccountSettingsForm, LoginForm, RegisterForm
from models import User
from permissions import redirect_for_role

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect_for_role(current_user.role)

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data,
            is_admin=False,
        )
        db.session.add(user)
        for attempt in range(2):
            try:
                db.session.commit()
                break
            except OperationalError as error:
                db.session.rollback()
                is_locked = "database is locked" in str(error).lower()
                if is_locked and attempt == 0:
                    # Brief retry handles transient SQLite writer contention.
                    time.sleep(0.35)
                    db.session.add(user)
                    continue

                current_app.logger.warning(
                    "Register failed due to database operation error: %s", error)
                flash(
                    "The system is busy right now. Please try registration again in a moment.", "warning")
                return render_template("auth/register.html", form=form)

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect_for_role(current_user.role)

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            email=form.email.data.strip().lower()).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash("Welcome back!", "success")

            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect_for_role(user.role)

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = AccountSettingsForm(obj=current_user)

    if form.validate_on_submit():
        if not check_password_hash(current_user.password_hash, form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return render_template("auth/settings.html", form=form)

        current_user.username = form.username.data.strip()
        current_user.email = form.email.data.strip().lower()
        current_user.role = form.role.data

        if form.new_password.data:
            current_user.password_hash = generate_password_hash(
                form.new_password.data)

        db.session.commit()
        flash("Settings updated successfully.", "success")
        return redirect(url_for("main.profile"))

    return render_template("auth/settings.html", form=form)
