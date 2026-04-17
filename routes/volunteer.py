from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import VolunteerCampaignJoinForm
from models import Campaign, VolunteerCampaignSignup

volunteer_bp = Blueprint("volunteer", __name__)


DEFAULT_CAMPAIGNS = [
    {
        "title": "Riverbank Reforestation Sprint",
        "location": "Mtkvari River Corridor",
        "description": "Plant mixed native trees in erosion-prone riverbank zones funded by local sponsors.",
        "days_offset": 10,
    },
    {
        "title": "School Forest Recovery Day",
        "location": "Rustavi Community District",
        "description": "Support a school-adjacent planting campaign with community monitoring and follow-up care.",
        "days_offset": 18,
    },
    {
        "title": "Hillside Protection Campaign",
        "location": "Tbilisi Outskirts Hills",
        "description": "Join teams restoring recently cleared hillsides with verified geo-tagged planting checkpoints.",
        "days_offset": 26,
    },
]


def ensure_default_campaigns() -> None:
    if Campaign.query.count() > 0:
        return

    now = datetime.utcnow()
    for item in DEFAULT_CAMPAIGNS:
        db.session.add(
            Campaign(
                title=item["title"],
                location=item["location"],
                description=item["description"],
                event_date=now + timedelta(days=item["days_offset"]),
                target_trees=150,
                status="open",
                creator_user_id=None,
            )
        )

    db.session.commit()


@volunteer_bp.route("/volunteer/campaigns", methods=["GET", "POST"])
@volunteer_bp.route("/campaigns/explore", methods=["GET", "POST"])
@login_required
def campaigns_explore():
    ensure_default_campaigns()

    join_form = VolunteerCampaignJoinForm(prefix="join")

    if join_form.submit.data and join_form.validate_on_submit():
        campaign = Campaign.query.get_or_404(int(join_form.campaign_id.data))
        existing_signup = VolunteerCampaignSignup.query.filter_by(
            user_id=current_user.id,
            campaign_id=campaign.id,
        ).first()

        if existing_signup:
            flash("You already requested to join this campaign.", "info")
            return redirect(url_for("volunteer.campaigns_explore"))

        signup = VolunteerCampaignSignup(
            user_id=current_user.id,
            campaign_id=campaign.id,
            motivation=join_form.motivation.data.strip() if join_form.motivation.data else None,
        )
        db.session.add(signup)
        db.session.commit()
        flash("Join request sent. Wait for campaign owner/admin verification.", "success")
        return redirect(url_for("volunteer.campaigns_explore"))

    location_filter = request.args.get("location", "").strip()
    date_filter = request.args.get("date", "").strip()
    sort_by = request.args.get("sort", "popular").strip().lower()

    campaigns_query = Campaign.query
    if location_filter:
        campaigns_query = campaigns_query.filter(
            Campaign.location.ilike(f"%{location_filter}%")
        )
    if date_filter:
        try:
            requested_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_of_day = datetime.combine(
                requested_date, datetime.min.time())
            end_of_day = datetime.combine(requested_date, datetime.max.time())
            campaigns_query = campaigns_query.filter(
                Campaign.event_date >= start_of_day,
                Campaign.event_date <= end_of_day,
            )
        except ValueError:
            pass

    campaigns_data = campaigns_query.all()

    participant_counts = {
        campaign.id: VolunteerCampaignSignup.query.filter_by(
            campaign_id=campaign.id,
            status="approved",
        ).count()
        for campaign in campaigns_data
    }

    if sort_by == "new":
        campaigns_data.sort(key=lambda c: c.created_at, reverse=True)
    elif sort_by == "date":
        campaigns_data.sort(key=lambda c: c.event_date)
    else:
        campaigns_data.sort(
            key=lambda c: (participant_counts.get(c.id, 0), c.created_at),
            reverse=True,
        )

    signups = VolunteerCampaignSignup.query.filter_by(
        user_id=current_user.id).all()
    signup_map = {signup.campaign_id: signup for signup in signups}

    return render_template(
        "volunteers/explore_campaigns.html",
        campaigns=campaigns_data,
        participant_counts=participant_counts,
        signup_map=signup_map,
        join_form=join_form,
        location_filter=location_filter,
        date_filter=date_filter,
        sort_by=sort_by,
    )


@volunteer_bp.route("/campaigns/create", methods=["GET", "POST"])
@login_required
def campaigns_create():
    flash("Campaign creation from volunteer pages has been removed.", "warning")
    return redirect(url_for("main.create_or_report", mode="campaign"))
