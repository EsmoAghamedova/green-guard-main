import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from flask_login import current_user
from wtforms import BooleanField, DecimalField, IntegerField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, InputRequired, Length, NumberRange, Optional, ValidationError

from models import User


def validate_strong_password(value: str) -> None:
    if re.search(r"\s", value):
        raise ValidationError("Password must not contain spaces.")

    if not re.search(r"[A-Z]", value):
        raise ValidationError(
            "Password must include at least one uppercase letter.")

    if not re.search(r"[a-z]", value):
        raise ValidationError(
            "Password must include at least one lowercase letter.")

    if not re.search(r"\d", value):
        raise ValidationError("Password must include at least one number.")

    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValidationError(
            "Password must include at least one special character.")


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
                           InputRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[
                        InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[
                             InputRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[InputRequired(), EqualTo("password")]
    )
    submit = SubmitField("Create Account")

    def validate_username(self, username):
        if User.query.filter_by(username=username.data.strip()).first():
            raise ValidationError("Username is already taken.")

    def validate_email(self, email):
        if User.query.filter_by(email=email.data.strip().lower()).first():
            raise ValidationError("Email is already registered.")

    def validate_password(self, password):
        value = password.data or ""
        validate_strong_password(value)


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Login")


class PlantTreeForm(FlaskForm):
    species = StringField("Tree Species", validators=[
                          InputRequired(), Length(min=2, max=120)])
    quantity = IntegerField("Quantity", validators=[
                            InputRequired(), NumberRange(min=1, max=1000)])
    latitude = DecimalField("Latitude", validators=[
                            InputRequired(), NumberRange(min=-90, max=90)])
    longitude = DecimalField("Longitude", validators=[
                             InputRequired(), NumberRange(min=-180, max=180)])
    location_notes = StringField(
        "Location Notes", validators=[Length(max=255)])
    image = FileField("Image", validators=[FileAllowed(
        ["jpg", "jpeg", "png"], "Only JPG/JPEG/PNG files are allowed.")])
    privacy_confirm = BooleanField(
        "I confirm this image does not show identifiable faces, children, license plates, or private home details.",
        validators=[DataRequired(
            message="You must confirm the photo safety rules before submitting.")],
    )
    submit = SubmitField("Submit Tree Record")


class CuttingReportForm(FlaskForm):
    description = TextAreaField("Description", validators=[
                                InputRequired(), Length(min=10, max=1000)])
    latitude = DecimalField("Latitude", validators=[
                            InputRequired(), NumberRange(min=-90, max=90)])
    longitude = DecimalField("Longitude", validators=[
                             InputRequired(), NumberRange(min=-180, max=180)])
    location_text = StringField("Location", validators=[Length(max=255)])
    image = FileField("Image", validators=[FileAllowed(
        ["jpg", "jpeg", "png"], "Only JPG/JPEG/PNG files are allowed.")])
    privacy_confirm = BooleanField(
        "I confirm this image does not show identifiable faces, children, license plates, or private home details.",
        validators=[DataRequired(
            message="You must confirm the photo safety rules before submitting.")],
    )
    submit = SubmitField("Submit Cutting Report")


class TreeRecordEditForm(FlaskForm):
    species = StringField("Tree Species", validators=[
                          InputRequired(), Length(min=2, max=120)])
    quantity = IntegerField("Quantity", validators=[
                            InputRequired(), NumberRange(min=1, max=1000)])
    latitude = DecimalField("Latitude", validators=[
                            InputRequired(), NumberRange(min=-90, max=90)])
    longitude = DecimalField("Longitude", validators=[
                             InputRequired(), NumberRange(min=-180, max=180)])
    location_notes = StringField(
        "Location Notes", validators=[Length(max=255)])
    image = FileField("Replace Image", validators=[FileAllowed(
        ["jpg", "jpeg", "png"], "Only JPG/JPEG/PNG files are allowed.")])
    privacy_confirm = BooleanField(
        "If replacing image: I confirm it does not show identifiable faces, children, license plates, or private home details.")
    submit = SubmitField("Save Changes")

    def validate_privacy_confirm(self, privacy_confirm):
        if self.image.data and not privacy_confirm.data:
            raise ValidationError(
                "Confirm the photo safety rules when uploading a new image.")


class CuttingReportEditForm(FlaskForm):
    description = TextAreaField("Description", validators=[
                                InputRequired(), Length(min=10, max=1000)])
    latitude = DecimalField("Latitude", validators=[
                            InputRequired(), NumberRange(min=-90, max=90)])
    longitude = DecimalField("Longitude", validators=[
                             InputRequired(), NumberRange(min=-180, max=180)])
    location_text = StringField("Location", validators=[Length(max=255)])
    image = FileField("Replace Image", validators=[FileAllowed(
        ["jpg", "jpeg", "png"], "Only JPG/JPEG/PNG files are allowed.")])
    privacy_confirm = BooleanField(
        "If replacing image: I confirm it does not show identifiable faces, children, license plates, or private home details.")
    submit = SubmitField("Save Changes")

    def validate_privacy_confirm(self, privacy_confirm):
        if self.image.data and not privacy_confirm.data:
            raise ValidationError(
                "Confirm the photo safety rules when uploading a new image.")


class AccountSettingsForm(FlaskForm):
    username = StringField("Username", validators=[
                           InputRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[
                        InputRequired(), Email(), Length(max=120)])
    current_password = PasswordField(
        "Current Password", validators=[InputRequired()])
    new_password = PasswordField("New Password", validators=[
                                 Optional(), Length(min=8, max=128)])
    confirm_new_password = PasswordField(
        "Confirm New Password", validators=[Optional(), EqualTo("new_password", message="New passwords must match.")]
    )
    submit = SubmitField("Update Settings")

    def validate_username(self, username):
        existing = User.query.filter_by(username=username.data.strip()).first()
        if existing and existing.id != current_user.id:
            raise ValidationError("Username is already taken.")

    def validate_email(self, email):
        existing = User.query.filter_by(
            email=email.data.strip().lower()).first()
        if existing and existing.id != current_user.id:
            raise ValidationError("Email is already registered.")

    def validate_new_password(self, new_password):
        value = new_password.data or ""
        if value:
            validate_strong_password(value)


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")


class ContactForm(FlaskForm):
    full_name = StringField("Full Name", validators=[
                            InputRequired(), Length(min=2, max=120)])
    email = StringField("Email Address", validators=[
                        InputRequired(), Email(), Length(max=120)])
    message = TextAreaField("Message", validators=[
                            InputRequired(), Length(min=10, max=1000)])
    submit = SubmitField("Submit")
