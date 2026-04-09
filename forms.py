import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from flask_login import current_user
from wtforms import BooleanField, DecimalField, HiddenField, IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, InputRequired, Length, NumberRange, Optional, ValidationError

from models import User

ROLE_CHOICES = [
    ("individual", "Individual Sponsor"),
    ("business", "Business / Company"),
    ("volunteer", "Volunteer"),
    ("citizen", "Citizen Reporter"),
]

DONATION_CATEGORY_CHOICES = [
    ("plants", "Plants and Seedlings"),
    ("tools", "Planting Tools and Equipment"),
    ("travel", "Volunteer Trip and Transport Money"),
]

DONATION_ITEM_CHOICES_BY_CATEGORY = {
    "plants": [
        ("oak_saplings", "Oak Saplings"),
        ("pine_seedlings", "Pine Seedlings"),
        ("maple_seedlings", "Maple Seedlings"),
        ("cedar_seedlings", "Cedar Seedlings"),
        ("mixed_native_pack", "Mixed Native Tree Pack"),
    ],
    "tools": [
        ("shovel_set", "Shovel Set"),
        ("watering_can", "Watering Can"),
        ("protective_gloves", "Protective Gloves"),
        ("soil_testing_kit", "Soil Testing Kit"),
        ("wheelbarrow", "Wheelbarrow"),
    ],
    "travel": [
        ("fuel_support", "Volunteer Fuel Support"),
        ("bus_transport", "Volunteer Bus Transport"),
        ("logistics_support", "Field Logistics Support"),
    ],
}

DONATION_ITEM_CHOICES = []
for category, choices in DONATION_ITEM_CHOICES_BY_CATEGORY.items():
    for value, label in choices:
        DONATION_ITEM_CHOICES.append((f"{category}:{value}", label))

TREE_SPECIES_CHOICES = [
    ("", "Select species"),
    ("oak_saplings", "Oak Saplings"),
    ("pine_seedlings", "Pine Seedlings"),
    ("maple_seedlings", "Maple Seedlings"),
    ("cedar_seedlings", "Cedar Seedlings"),
    ("mixed_native_pack", "Mixed Native Tree Pack"),
]

TREE_SPECIES_DEFAULT_PRICES = {
    "oak_saplings": 4.0,
    "pine_seedlings": 3.5,
    "maple_seedlings": 4.5,
    "cedar_seedlings": 5.0,
    "mixed_native_pack": 4.0,
}


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


def validate_location_coordinates(form, field):
    """Validate that latitude and longitude are both provided."""
    if not form.latitude.data or not form.longitude.data:
        raise ValidationError(
            "Please select a location using Search or GPS before submitting."
        )


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
                           InputRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[
                        InputRequired(), Email(), Length(max=120)])
    role = SelectField("I am joining as", choices=ROLE_CHOICES,
                       validators=[InputRequired()])
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

    def validate_role(self, role):
        allowed_values = {choice[0] for choice in ROLE_CHOICES}
        if role.data not in allowed_values:
            raise ValidationError("Please choose a valid account role.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Login")


class PlantTreeForm(FlaskForm):
    species = StringField("Tree Species", validators=[
                          InputRequired(), Length(min=2, max=120)])
    quantity = IntegerField("Quantity", validators=[
                            InputRequired(), NumberRange(min=1, max=1000)])
    location_search = StringField("Search Location (street, city, or landmark)", validators=[
                                  Length(max=255)])
    location_source = HiddenField()
    latitude = DecimalField("Latitude", validators=[
                            Optional(), NumberRange(min=-90, max=90), validate_location_coordinates])
    longitude = DecimalField("Longitude", validators=[
                             Optional(), NumberRange(min=-180, max=180)])
    location_notes = StringField(
        "Location Notes", validators=[Length(max=255)])
    image = FileField("Photo or Video Proof", validators=[FileAllowed(
        ["jpg", "jpeg", "png", "mp4", "mov", "webm"], "Only JPG/JPEG/PNG/MP4/MOV/WEBM files are allowed.")])
    privacy_confirm = BooleanField(
        "I confirm this image does not show identifiable faces, children, license plates, or private home details.",
        validators=[DataRequired(
            message="You must confirm the photo safety rules before submitting.")],
    )
    submit = SubmitField("Submit Tree Record")

    def validate_location_source(self, location_source):
        if location_source.data != "gps":
            raise ValidationError(
                "Please choose your planting location using GPS.")


class CampaignPlantTreeForm(FlaskForm):
    campaign_id = SelectField(
        "Joined Campaign", coerce=int, validators=[InputRequired()])
    species = StringField("Tree Species", validators=[
                          InputRequired(), Length(min=2, max=120)])
    quantity = IntegerField("Trees Planted", validators=[
                            InputRequired(), NumberRange(min=1, max=1000)])
    location_search = StringField("Search Location (street, city, or landmark)", validators=[
                                  Length(max=255)])
    location_source = HiddenField()
    latitude = DecimalField("Latitude", validators=[
                            Optional(), NumberRange(min=-90, max=90), validate_location_coordinates])
    longitude = DecimalField("Longitude", validators=[
                             Optional(), NumberRange(min=-180, max=180)])
    location_notes = StringField(
        "Location Notes", validators=[Length(max=255)])
    image = FileField("Planting Image Proof", validators=[
        FileRequired("Please upload a planting proof image."),
        FileAllowed(["jpg", "jpeg", "png"],
                    "Only JPG/JPEG/PNG files are allowed."),
    ])
    privacy_confirm = BooleanField(
        "I confirm this image does not show identifiable faces, children, license plates, or private home details.",
        validators=[DataRequired(
            message="You must confirm the photo safety rules before submitting.")],
    )
    submit = SubmitField("Submit Campaign Planting")

    def validate_location_source(self, location_source):
        if location_source.data != "gps":
            raise ValidationError(
                "Please choose your planting location using GPS.")


class CuttingReportForm(FlaskForm):
    description = TextAreaField("Description", validators=[
                                InputRequired(), Length(min=10, max=1000)])
    location_search = StringField("Search Location (street, city, or landmark)", validators=[
                                  Length(max=255)])
    latitude = DecimalField("Latitude", validators=[
                            Optional(), NumberRange(min=-90, max=90), validate_location_coordinates])
    longitude = DecimalField("Longitude", validators=[
                             Optional(), NumberRange(min=-180, max=180)])
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
    location_search = StringField("Search Location (street, city, or landmark)", validators=[
                                  Length(max=255)])
    latitude = DecimalField("Latitude", validators=[
                            Optional(), NumberRange(min=-90, max=90), validate_location_coordinates])
    longitude = DecimalField("Longitude", validators=[
                             Optional(), NumberRange(min=-180, max=180)])
    location_notes = StringField(
        "Location Notes", validators=[Length(max=255)])
    image = FileField("Replace Photo or Video", validators=[FileAllowed(
        ["jpg", "jpeg", "png", "mp4", "mov", "webm"], "Only JPG/JPEG/PNG/MP4/MOV/WEBM files are allowed.")])
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
    location_search = StringField("Search Location (street, city, or landmark)", validators=[
                                  Length(max=255)])
    latitude = DecimalField("Latitude", validators=[
                            Optional(), NumberRange(min=-90, max=90), validate_location_coordinates])
    longitude = DecimalField("Longitude", validators=[
                             Optional(), NumberRange(min=-180, max=180)])
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
    role = SelectField("Account Role", choices=ROLE_CHOICES,
                       validators=[InputRequired()])
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

    def validate_role(self, role):
        allowed_values = {choice[0] for choice in ROLE_CHOICES}
        if role.data not in allowed_values:
            raise ValidationError("Please choose a valid account role.")


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


class VolunteerCampaignJoinForm(FlaskForm):
    campaign_id = HiddenField(validators=[InputRequired()])
    motivation = TextAreaField("Why do you want to join this campaign?", validators=[
                               Optional(), Length(max=500)])
    submit = SubmitField("Join Campaign")


class VolunteerCampaignCreateForm(FlaskForm):
    title = StringField("Campaign Title", validators=[
                        InputRequired(), Length(min=5, max=140)])
    location = StringField("Location", validators=[
                           InputRequired(), Length(min=3, max=140)])
    event_date = StringField("Event Date (YYYY-MM-DD)", validators=[
                             InputRequired(), Length(min=10, max=10)])
    target_trees = IntegerField("Target Trees", validators=[
        InputRequired(), NumberRange(min=1, max=100000)])
    description = TextAreaField("Campaign Description", validators=[
                                InputRequired(), Length(min=20, max=1000)])
    submit = SubmitField("Create Campaign")


class SupportDonationForm(FlaskForm):
    category = SelectField("Donation Category", choices=DONATION_CATEGORY_CHOICES,
                           validators=[InputRequired()])
    donation_item = SelectField("Item to Donate", choices=DONATION_ITEM_CHOICES,
                                validators=[InputRequired()])
    tree_species = SelectField(
        "Tree Species",
        choices=TREE_SPECIES_CHOICES,
        validators=[Optional()],
    )
    price_per_tree = DecimalField(
        "Price Per Tree (USD)",
        validators=[Optional(), NumberRange(min=0.5, max=10000)],
    )
    quantity = IntegerField("Number of Trees", validators=[
                            Optional(), NumberRange(min=1, max=100000)])
    amount = DecimalField("Amount (USD)", validators=[
                          Optional(), NumberRange(min=1, max=1000000)])
    campaign_id = SelectField(
        "Fund Campaign (Optional)", coerce=int, validators=[Optional()], choices=[(0, "Any Campaign")]
    )
    note = TextAreaField("Optional Note", validators=[
                         Optional(), Length(max=500)])
    submit = SubmitField("Continue to Payment")

    def validate_category(self, category):
        allowed_values = {choice[0] for choice in DONATION_CATEGORY_CHOICES}
        if category.data not in allowed_values:
            raise ValidationError("Please select a valid donation category.")

    def validate_donation_item(self, donation_item):
        if self.category.data == "plants" and self.tree_species.data:
            return

        raw_value = donation_item.data or ""
        if ":" not in raw_value:
            raise ValidationError("Please select a valid donation item.")

        selected_category, _ = raw_value.split(":", 1)
        if self.category.data != selected_category:
            raise ValidationError(
                "Donation item must match the selected donation category.")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        has_quantity = self.quantity.data is not None
        has_amount = self.amount.data is not None

        if self.category.data == "plants":
            allowed_species = {choice[0]
                               for choice in TREE_SPECIES_CHOICES if choice[0]}
            if not self.tree_species.data or self.tree_species.data not in allowed_species:
                self.tree_species.errors.append(
                    "Please choose a valid tree species.")
                return False

            if self.price_per_tree.data is None:
                self.price_per_tree.errors.append(
                    "Enter price per tree for tree funding.")
                return False

            if not has_quantity:
                self.quantity.errors.append(
                    "Enter number of trees for tree funding.")
                return False

            return True

        if not has_quantity and not has_amount:
            error_message = "Enter donation amount, number of trees, or both."
            self.quantity.errors.append(error_message)
            self.amount.errors.append(error_message)
            return False

        return True
