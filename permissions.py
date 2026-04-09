from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


ROLE_HOME = {
    "individual": "main.sponsorship_donations",
    "business": "main.business_dashboard",
    "volunteer": "main.volunteer_dashboard",
    "citizen": "main.profile",
}


def redirect_for_role(role: str):
    endpoint = ROLE_HOME.get(role, "main.index")
    return redirect(url_for(endpoint))


def role_required(*allowed_roles: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))

            if current_user.is_admin:
                return view_func(*args, **kwargs)

            if current_user.role not in allowed_roles:
                flash(
                    f"This area is restricted for your role ({current_user.role.title()}).",
                    "warning",
                )
                return redirect_for_role(current_user.role)

            return view_func(*args, **kwargs)

        return wrapped

    return decorator
