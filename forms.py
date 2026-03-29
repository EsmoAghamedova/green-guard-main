from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DecimalField, IntegerField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import Email, EqualTo, InputRequired, Length, NumberRange, ValidationError

from models import User


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
                           InputRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[
                        InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[
                             InputRequired(), Length(min=6)])
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
    submit = SubmitField("Submit Cutting Report")
