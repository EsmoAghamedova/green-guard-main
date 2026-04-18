from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


ROLE_HOME = {
    "individual": "main.sponsorship_donations",
    "business": "main.business_dashboard",
    "volunteer": "main.volunteer_dashboard",
}

CAMPAIGN_CREATOR_ROLES = {"business"}
VERIFICATION_REQUIRED_ROLES = {"business", "volunteer"}


def redirect_for_role(role: str):
    endpoint = ROLE_HOME.get(role, "main.index")
    return redirect(url_for(endpoint))


def role_requires_verification(role: str | None) -> bool:
    return role in VERIFICATION_REQUIRED_ROLES


def is_user_verified(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_admin", False):
        return True
    if not role_requires_verification(getattr(user, "role", None)):
        return True
    return getattr(user, "verification_status", "approved") == "approved"


def redirect_for_verification():
    return redirect(url_for("auth.verification_pending"))


def role_required(*allowed_roles: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))

            if current_user.is_admin:
                return view_func(*args, **kwargs)

            if not is_user_verified(current_user):
                flash("Your account is waiting for admin verification.", "warning")
                return redirect_for_verification()

            if current_user.role not in allowed_roles:
                flash(
                    f"This area is restricted for your role ({current_user.role.title()}).",
                    "warning",
                )
                return redirect_for_role(current_user.role)

            return view_func(*args, **kwargs)

        return wrapped

    return decorator
