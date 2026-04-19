import json
import hashlib
import math
import time
from csv import DictReader
from datetime import datetime, timedelta, time as time_obj
from io import StringIO
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from sqlalchemy.exc import IntegrityError

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from extensions import db
from forms import ContactForm, DeleteForm, SupportDonationForm, TREE_SPECIES_DEFAULT_PRICES, VolunteerCampaignCreateForm, VolunteerCampaignJoinForm
from models import Campaign, CuttingReport, GFWLocation, GFWLocationSyncState, MerchPurchase, SupportDonation, TreeRecord, User, VolunteerCampaignSignup
from permissions import CAMPAIGN_CREATOR_ROLES, redirect_for_role, role_required

main_bp = Blueprint("main", __name__)

GFW_FIRE_ALERTS_URL = "https://data-api.globalforestwatch.org/dataset/nasa_viirs_fire_alerts/latest/features"
COUNTRY_CENTROIDS_CSV_URL = "https://raw.githubusercontent.com/gavinr/world-countries-centroids/master/dist/countries.csv"
GFW_SYNC_STATE_NAME = "gfw_fire_alerts"
DEFAULT_GFW_SYNC_TIME = "06:00"
DEFAULT_GFW_SYNC_INTERVAL_DAYS = 7
DEFAULT_GFW_MAX_COUNTRIES = 20
DEFAULT_GFW_GLOBAL_ZOOM = 3
DEFAULT_GFW_MAX_GRID_POINTS = 24
DEFAULT_GFW_HTTP_TIMEOUT = 12
DEFAULT_GFW_HTTP_RETRIES = 2
GFW_FALLBACK_SYNC_POINTS = [
    {"country_name": "Brazil", "country_code": "BR",
        "lat": -54.3552, "lng": -11.5246, "zoom": 6},
    {"country_name": "Democratic Republic of the Congo",
        "country_code": "CD", "lat": 23.6439, "lng": -2.8503, "zoom": 6},
    {"country_name": "Indonesia", "country_code": "ID",
        "lat": 117.2401, "lng": -2.2334, "zoom": 6},
    {"country_name": "United States", "country_code": "US",
        "lat": -98.4168, "lng": 39.0, "zoom": 6},
    {"country_name": "Australia", "country_code": "AU",
        "lat": 134.4907, "lng": -25.7349, "zoom": 5},
]

GFW_GLOBAL_HOTSPOT_SYNC_POINTS = [
    {"country_name": "Brazil", "country_code": "BR",
        "lat": -8.8, "lng": -63.9, "zoom": 8},
    {"country_name": "Brazil", "country_code": "BR",
        "lat": -3.1, "lng": -60.0, "zoom": 8},
    {"country_name": "Peru", "country_code": "PE",
        "lat": -9.2, "lng": -74.9, "zoom": 8},
    {"country_name": "Colombia", "country_code": "CO",
        "lat": 3.5, "lng": -72.3, "zoom": 8},
    {"country_name": "Bolivia", "country_code": "BO",
        "lat": -16.8, "lng": -64.8, "zoom": 8},
    {"country_name": "Democratic Republic of the Congo",
        "country_code": "CD", "lat": -2.8, "lng": 23.6, "zoom": 8},
    {"country_name": "Republic of the Congo",
        "country_code": "CG", "lat": -0.8, "lng": 15.2, "zoom": 8},
    {"country_name": "Gabon", "country_code": "GA",
        "lat": -0.6, "lng": 11.7, "zoom": 8},
    {"country_name": "Cameroon", "country_code": "CM",
        "lat": 5.5, "lng": 12.3, "zoom": 8},
    {"country_name": "Indonesia", "country_code": "ID",
        "lat": -2.1, "lng": 113.8, "zoom": 8},
    {"country_name": "Indonesia", "country_code": "ID",
        "lat": -0.9, "lng": 101.4, "zoom": 8},
    {"country_name": "Malaysia", "country_code": "MY",
        "lat": 4.2, "lng": 102.0, "zoom": 8},
    {"country_name": "Papua New Guinea", "country_code": "PG",
        "lat": -6.3, "lng": 145.2, "zoom": 8},
    {"country_name": "Cambodia", "country_code": "KH",
        "lat": 14.0, "lng": 105.0, "zoom": 8},
    {"country_name": "Vietnam", "country_code": "VN",
        "lat": 16.2, "lng": 107.8, "zoom": 8},
    {"country_name": "Laos", "country_code": "LA",
        "lat": 19.8, "lng": 102.6, "zoom": 8},
    {"country_name": "Myanmar", "country_code": "MM",
        "lat": 20.5, "lng": 96.3, "zoom": 8},
    {"country_name": "India", "country_code": "IN",
        "lat": 22.1, "lng": 79.3, "zoom": 8},
    {"country_name": "Australia", "country_code": "AU",
        "lat": -20.2, "lng": 133.7, "zoom": 7},
    {"country_name": "United States", "country_code": "US",
        "lat": 37.6, "lng": -120.8, "zoom": 7},
    {"country_name": "Canada", "country_code": "CA",
        "lat": 55.0, "lng": -106.0, "zoom": 7},
    {"country_name": "Mexico", "country_code": "MX",
        "lat": 20.8, "lng": -99.2, "zoom": 8},
    {"country_name": "Spain", "country_code": "ES",
        "lat": 39.8, "lng": -3.1, "zoom": 7},
    {"country_name": "Greece", "country_code": "GR",
        "lat": 38.5, "lng": 22.2, "zoom": 8},
]

MERCH_ITEMS = [
    {
        "key": "eco_shirt",
        "name": "Eco Shirt",
        "price": 20,
        "points": 200,
        "trees": 2,
        "image": "images/products/shirt.jpeg",
    },
    {
        "key": "nature_mug",
        "name": "Nature Mug",
        "price": 12,
        "points": 120,
        "trees": 1,
        "image": "images/products/mug.jpeg",
    },
    {
        "key": "tote_bag",
        "name": "Tote Bag",
        "price": 18,
        "points": 180,
        "trees": 2,
        "image": "images/products/weekender-tote-bag.jpg.jpeg",
    },
    {
        "key": "eco_notebook",
        "name": "Eco Notebook",
        "price": 15,
        "points": 150,
        "trees": 1,
        "image": "images/products/notebook.jpeg",
    },
    {
        "key": "sweatshirt",
        "name": "Sweatshirt",
        "price": 10,
        "points": 100,
        "trees": 1,
        "image": "images/products/tshirt.jpeg",
    },
    {
        "key": "reusable_bottle",
        "name": "Bottle",
        "price": 25,
        "points": 250,
        "trees": 3,
        "image": "images/products/slim-water-bottle.jpg.jpeg",
    },
]


def build_map_payload() -> dict:
    trees = TreeRecord.query.all()
    reports = CuttingReport.query.filter(
        CuttingReport.status.in_(["reviewed", "resolved"])
    ).all()

    trees_json = [
        {
            "id": tree.id,
            "species": tree.species,
            "quantity": tree.quantity,
            "latitude": tree.latitude,
            "longitude": tree.longitude,
            "username": tree.user.username,
        }
        for tree in trees
    ]
    reports_json = [
        {
            "id": report.id,
            "description": report.description,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "status": report.status,
            "username": None,
        }
        for report in reports
    ]

    return {"trees": trees_json, "reports": reports_json}


def _parse_sync_time(sync_time_text: str) -> time_obj:
    try:
        parsed_time = datetime.strptime(sync_time_text, "%H:%M")
        return parsed_time.time()
    except ValueError:
        return time_obj(6, 0)


def _get_sync_cutoff(now: datetime | None = None) -> datetime:
    current_time = now or datetime.utcnow()
    interval_days = int(current_app.config.get(
        "GFW_SYNC_INTERVAL_DAYS", DEFAULT_GFW_SYNC_INTERVAL_DAYS)
    )
    interval_days = max(1, interval_days)
    return current_time - timedelta(days=interval_days)


def _is_gfw_sync_due(last_synced_at: datetime | None, now: datetime | None = None) -> bool:
    current_time = now or datetime.utcnow()
    cutoff = _get_sync_cutoff(current_time)
    return last_synced_at is None or last_synced_at < cutoff


def _build_alert_unique_key(alert: dict) -> str:
    latitude = float(alert.get("latitude", 0) or 0)
    longitude = float(alert.get("longitude", 0) or 0)
    alert_date = alert.get("alert__date") or ""
    alert_time_utc = alert.get("alert__time_utc") or ""
    confidence = alert.get("confidence__cat") or ""
    return f"{latitude:.4f}|{longitude:.4f}|{alert_date}|{alert_time_utc}|{confidence}"


def _extract_reforestation_type(alert: dict) -> str | None:
    reforestation_type = (
        alert.get("gfw_planted_forests__type")
        or alert.get("gfw_plantations__type")
        or alert.get("gfw_plantation__type")
    )
    if reforestation_type in (None, "", "null"):
        return None
    return str(reforestation_type)


def _load_country_sync_points() -> list[dict]:
    cache = current_app.extensions.get("gfw_country_sync_points")
    if cache:
        return cache

    points: list[dict] = []
    request = Request(
        COUNTRY_CENTROIDS_CSV_URL,
        headers={"User-Agent": "GreenGuard/1.0", "Accept": "text/csv"},
    )

    try:
        with urlopen(request, timeout=15) as response:
            raw_csv = response.read().decode("utf-8")
        csv_rows = DictReader(StringIO(raw_csv))
        for row in csv_rows:
            country_name = (row.get("COUNTRY") or "").strip()
            country_code = (row.get("ISO") or "").strip().upper()
            if not country_name or not country_code or country_code == "AQ":
                continue

            try:
                longitude = float(row.get("longitude") or "")
                latitude = float(row.get("latitude") or "")
            except ValueError:
                continue

            points.append(
                {
                    "country_name": country_name,
                    "country_code": country_code,
                    "lat": latitude,
                    "lng": longitude,
                    "zoom": 6,
                }
            )
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        current_app.logger.warning(
            "Could not load country centroids CSV: %s", error)
        points = list(GFW_FALLBACK_SYNC_POINTS)

    points.sort(key=lambda item: (item["country_name"], item["country_code"]))
    max_countries = int(
        current_app.config.get("GFW_MAX_COUNTRIES", DEFAULT_GFW_MAX_COUNTRIES)
    )
    if max_countries > 0:
        points = points[:max_countries]

    current_app.extensions["gfw_country_sync_points"] = points
    return points


def _tile_center_lat_lng(tile_x: int, tile_y: int, zoom: int) -> tuple[float, float]:
    scale = 2 ** zoom
    lon_deg = ((tile_x + 0.5) / scale) * 360.0 - 180.0
    n = math.pi - (2.0 * math.pi * (tile_y + 0.5) / scale)
    lat_rad = math.atan(math.sinh(n))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def _load_global_tile_sync_points() -> list[dict]:
    cache = current_app.extensions.get("gfw_global_tile_sync_points")
    if cache:
        return cache

    zoom = int(current_app.config.get(
        "GFW_GLOBAL_ZOOM", DEFAULT_GFW_GLOBAL_ZOOM))
    zoom = max(2, min(5, zoom))

    scale = 2 ** zoom
    points: list[dict] = []
    for tile_x in range(scale):
        for tile_y in range(scale):
            lat, lng = _tile_center_lat_lng(tile_x, tile_y, zoom)
            points.append(
                {
                    "country_name": "Global",
                    "country_code": "GLB",
                    "lat": lat,
                    "lng": lng,
                    "zoom": zoom,
                }
            )

    current_app.extensions["gfw_global_tile_sync_points"] = points
    return points


def _load_worldwide_sync_points() -> list[dict]:
    country_points = _load_country_sync_points()
    grid_points = _load_global_tile_sync_points()

    max_grid_points = int(
        current_app.config.get("GFW_MAX_GRID_POINTS",
                               DEFAULT_GFW_MAX_GRID_POINTS)
    )
    if max_grid_points > 0:
        grid_points = grid_points[:max_grid_points]

    world_zoom = int(current_app.config.get(
        "GFW_GLOBAL_ZOOM", DEFAULT_GFW_GLOBAL_ZOOM))
    world_zoom = max(2, min(4, world_zoom))

    merged_points = list(GFW_GLOBAL_HOTSPOT_SYNC_POINTS) + \
        country_points + grid_points
    for point in merged_points:
        point["zoom"] = world_zoom

    return merged_points


def _build_location_description(region_label: str, alert: dict) -> str:
    alert_date = alert.get("alert__date") or "unknown date"
    alert_time = alert.get("alert__time_utc") or "unknown time"
    confidence = alert.get("confidence__cat") or "n/a"
    frp = alert.get("frp__MW")
    frp_text = f"{frp:.1f} MW" if isinstance(frp, (int, float)) else "n/a"

    reforestation_type = _extract_reforestation_type(alert)
    reforestation_sentence = (
        f" This location is also tagged as reforestation type: {reforestation_type}."
        if reforestation_type
        else ""
    )

    return (
        f"{region_label} was flagged by a recent NASA VIIRS fire alert on {alert_date} at {alert_time} UTC. "
        f"The alert confidence is {confidence}, with fire radiative power around {frp_text}. "
        "These coordinates are kept in the app as a persistent deforestation zone so the marker stays visible on the map."
        f"{reforestation_sentence}"
    )


def _build_country_summary(locations: list[GFWLocation]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for location in locations:
        country_code = (location.country_code or "UNK").upper()
        bucket = grouped.setdefault(
            country_code,
            {
                "country_code": country_code,
                "country_name": location.country_name or location.region_label,
                "total_locations": 0,
                "reforestation_locations": 0,
                "last_seen_at": None,
            },
        )

        bucket["total_locations"] += 1
        if location.reforestation_type:
            bucket["reforestation_locations"] += 1

        last_seen = bucket["last_seen_at"]
        if location.last_seen_at and (last_seen is None or location.last_seen_at > last_seen):
            bucket["last_seen_at"] = location.last_seen_at

    summary = list(grouped.values())
    summary.sort(
        key=lambda row: (-row["total_locations"], row["country_name"]))
    return summary


def _serialize_location(location: GFWLocation) -> dict:
    return {
        "id": location.id,
        "name": location.name,
        "region_label": location.region_label,
        "country_code": location.country_code,
        "country_name": location.country_name,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "alert_date": location.alert_date,
        "alert_time_utc": location.alert_time_utc,
        "confidence": location.confidence,
        "frp_mw": location.frp_mw,
        "reforestation_type": location.reforestation_type,
        "is_reforestation": bool(location.reforestation_type),
        "description": location.description,
        "source": location.source,
        "last_seen_at": location.last_seen_at.isoformat() if location.last_seen_at else None,
        "last_seen_label": location.last_seen_at.strftime("%Y-%m-%d %H:%M UTC") if location.last_seen_at else None,
        "detail_url": url_for("main.location_detail", location_id=location.id),
    }


def _build_fallback_location_payload() -> list[dict]:
    fallback_locations = []
    for index, point in enumerate(GFW_GLOBAL_HOTSPOT_SYNC_POINTS, start=1):
        fallback_locations.append(
            {
                "id": -index,
                "name": f"{point['country_name']} Deforestation Zone",
                "region_label": point["country_name"],
                "country_code": point.get("country_code") or "UNK",
                "country_name": point["country_name"],
                "latitude": point["lat"],
                "longitude": point["lng"],
                "alert_date": "Fallback",
                "alert_time_utc": None,
                "confidence": "n/a",
                "frp_mw": None,
                "reforestation_type": None,
                "is_reforestation": False,
                "description": "Fallback deforestation marker while live API data is syncing.",
                "source": "fallback_hotspot",
                "last_seen_at": None,
                "last_seen_label": "Fallback data",
                "detail_url": None,
            }
        )
    return fallback_locations


def _get_map_locations_payload() -> list[dict]:
    locations = load_gfw_locations()
    serialized = [_serialize_location(location) for location in locations]
    return serialized if serialized else _build_fallback_location_payload()


def calculate_donation_points(category: str, quantity: int, amount: float) -> int:
    quantity_multipliers = {
        "plants": 10,
        "tools": 7,
        "travel": 4,
    }
    amount_divisors = {
        "plants": 5,
        "tools": 8,
        "travel": 10,
    }

    base_points = quantity * quantity_multipliers.get(category, 5)
    amount_points = int(amount / amount_divisors.get(category, 10))
    return base_points + amount_points


def build_payment_transaction_id(user_id: int, payment_method: str, amount: float) -> str:
    salt = f"{time.time_ns()}|{user_id}|{payment_method}|{amount:.2f}"
    digest = hashlib.sha256(salt.encode("utf-8")).hexdigest()
    return f"PAY-{digest[:12].upper()}"


def _get_sync_state() -> GFWLocationSyncState:
    state = GFWLocationSyncState.query.filter_by(
        name=GFW_SYNC_STATE_NAME).first()
    if state:
        return state

    state = GFWLocationSyncState(name=GFW_SYNC_STATE_NAME)
    db.session.add(state)
    db.session.flush()
    return state


def fetch_gfw_fire_alerts(latitude: float, longitude: float, zoom: int) -> list[dict]:
    query_string = urlencode({"lat": latitude, "lng": longitude, "z": zoom})
    request_url = f"{GFW_FIRE_ALERTS_URL}?{query_string}"
    request = Request(
        request_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "GreenGuard/1.0",
        },
    )

    retries = int(current_app.config.get(
        "GFW_HTTP_RETRIES", DEFAULT_GFW_HTTP_RETRIES))
    timeout = int(current_app.config.get(
        "GFW_HTTP_TIMEOUT", DEFAULT_GFW_HTTP_TIMEOUT))

    last_error = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
            last_error = error
            if attempt >= retries:
                raise
            time.sleep(0.6 * (attempt + 1))

    if last_error and "payload" not in locals():
        raise last_error

    alerts = payload.get("data", [])
    if not isinstance(alerts, list):
        return []

    return alerts


def sync_gfw_locations(force: bool = False) -> dict:
    state = _get_sync_state()
    now = datetime.utcnow()
    if not force and not _is_gfw_sync_due(state.last_synced_at, now):
        return {"created": 0, "updated": 0, "total": GFWLocation.query.count(), "synced": False}

    existing_locations = {
        location.unique_key: location for location in GFWLocation.query.all()
    }
    created_count = 0
    updated_count = 0
    fetched_any_alerts = False
    sync_had_errors = False
    retention_cutoff = now - timedelta(days=max(1, int(
        current_app.config.get("GFW_SYNC_INTERVAL_DAYS",
                               DEFAULT_GFW_SYNC_INTERVAL_DAYS)
    )))

    for sync_point in _load_worldwide_sync_points():
        sync_point_changed = False
        try:
            alerts = fetch_gfw_fire_alerts(
                sync_point["lat"], sync_point["lng"], sync_point["zoom"]
            )
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            current_app.logger.warning(
                "GFW sync failed for %s (%s): %s",
                sync_point.get("country_name"),
                sync_point.get("country_code"),
                error,
            )
            sync_had_errors = True
            continue

        fetched_any_alerts = True

        for alert in alerts:
            try:
                latitude = float(alert.get("latitude"))
                longitude = float(alert.get("longitude"))
            except (TypeError, ValueError):
                continue

            unique_key = _build_alert_unique_key(alert)
            location = existing_locations.get(unique_key)
            if location is None:
                try:
                    with db.session.begin_nested():
                        location = GFWLocation(unique_key=unique_key)
                        db.session.add(location)
                        db.session.flush()
                    existing_locations[unique_key] = location
                    created_count += 1
                    sync_point_changed = True
                except IntegrityError:
                    location = GFWLocation.query.filter_by(
                        unique_key=unique_key).first()
                    if location is None:
                        continue
                    existing_locations[unique_key] = location
                    updated_count += 1
            else:
                updated_count += 1

            country_code = str(
                alert.get("iso") or sync_point.get("country_code") or "UNK"
            ).upper()
            country_name = str(
                alert.get("adm0__name")
                or alert.get("country")
                or sync_point.get("country_name")
                or "Unknown country"
            )
            reforestation_type = _extract_reforestation_type(alert)

            location.name = f"{country_name} Deforestation Zone"
            location.region_label = country_name
            location.country_code = country_code
            location.country_name = country_name
            location.latitude = latitude
            location.longitude = longitude
            location.alert_date = str(alert.get("alert__date") or "Unknown")
            location.alert_time_utc = str(
                alert.get("alert__time_utc") or "") or None
            confidence = alert.get("confidence__cat")
            location.confidence = str(
                confidence) if confidence is not None else None
            frp_value = alert.get("frp__MW")
            location.frp_mw = float(frp_value) if isinstance(
                frp_value, (int, float)) else None
            location.reforestation_type = reforestation_type
            location.description = _build_location_description(
                country_name, alert)
            location.source = "nasa_viirs_fire_alerts"
            location.last_seen_at = now
            sync_point_changed = True

        if sync_point_changed:
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                current_app.logger.warning(
                    "Skipped a sync-point commit due to concurrent write conflict for %s (%s)",
                    sync_point.get("country_name"),
                    sync_point.get("country_code"),
                )

        time.sleep(0.1)

    if fetched_any_alerts:
        state.last_synced_at = now

        if not sync_had_errors:
            stale_locations = GFWLocation.query.filter(
                GFWLocation.last_seen_at < retention_cutoff
            ).all()
            for location in stale_locations:
                db.session.delete(location)

        db.session.commit()
    else:
        db.session.rollback()

    return {
        "created": created_count,
        "updated": updated_count,
        "total": GFWLocation.query.count(),
        "synced": fetched_any_alerts,
    }


def ensure_gfw_locations_current(force: bool = False) -> dict:
    state = _get_sync_state()
    now = datetime.utcnow()

    should_sync = force or _is_gfw_sync_due(state.last_synced_at, now)
    has_any_locations = GFWLocation.query.count() > 0

    if should_sync:
        started = trigger_gfw_sync_async(force=True)
        return {
            "scheduled": started,
            "synced": False,
            "has_data": has_any_locations,
        }

    return {
        "scheduled": False,
        "synced": False,
        "has_data": has_any_locations,
    }


def trigger_gfw_sync_async(force: bool = False) -> bool:
    app = current_app._get_current_object()
    if app.extensions.get("gfw_sync_in_progress"):
        return False

    app.extensions["gfw_sync_in_progress"] = True

    def _worker() -> None:
        with app.app_context():
            try:
                sync_gfw_locations(force=force)
            except Exception as error:  # pragma: no cover - background safety net
                current_app.logger.warning(
                    "Background GFW sync failed: %s", error)
            finally:
                app.extensions["gfw_sync_in_progress"] = False

    Thread(target=_worker, daemon=True).start()
    return True


def load_gfw_locations() -> list[GFWLocation]:
    ensure_gfw_locations_current()
    return GFWLocation.query.order_by(
        GFWLocation.last_seen_at.desc(), GFWLocation.created_at.desc()
    ).all()


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect_for_role(current_user.role)

    total_trees = TreeRecord.query.with_entities(TreeRecord.quantity).all()
    total_tree_count = sum(item.quantity for item in total_trees)
    total_reports = CuttingReport.query.count()
    total_users = User.query.filter(User.is_admin.is_(False)).count()
    total_donations = sum(float(item.amount)
                          for item in SupportDonation.query.all())
    participant_user_ids = set()
    participant_user_ids.update(
        user_id for (user_id,) in TreeRecord.query.with_entities(TreeRecord.user_id).all() if user_id
    )
    participant_user_ids.update(
        user_id for (user_id,) in CuttingReport.query.with_entities(CuttingReport.user_id).all() if user_id
    )
    participant_user_ids.update(
        user_id for (user_id,) in SupportDonation.query.with_entities(SupportDonation.user_id).all() if user_id
    )
    participant_user_ids.update(
        user_id for (user_id,) in VolunteerCampaignSignup.query.with_entities(VolunteerCampaignSignup.user_id).all() if user_id
    )
    participant_count = len(participant_user_ids)

    volunteer_users = User.query.filter(
        User.is_admin.is_(False),
        User.role != "business",
    ).all()
    volunteer_rows = []
    for user in volunteer_users:
        score_data = _calculate_volunteer_score(user)
        volunteer_rows.append(
            {
                "user": user,
                "points": score_data["total_points"],
                "trees": score_data["tree_count"],
            }
        )
    volunteer_rows.sort(
        key=lambda row: (row["points"], row["trees"],
                         row["user"].username.lower()),
        reverse=True,
    )
    top_volunteers = volunteer_rows[:3]

    sponsor_rows = []
    sponsors = User.query.filter(
        User.is_admin.is_(False),
        User.role.in_(["business", "individual"]),
    ).all()
    for sponsor in sponsors:
        total_amount = sum(
            float(item.amount)
            for item in SupportDonation.query.filter_by(user_id=sponsor.id).all()
        )
        sponsor_rows.append({"user": sponsor, "total_amount": total_amount})
    sponsor_rows.sort(
        key=lambda row: (row["total_amount"], row["user"].username.lower()),
        reverse=True,
    )
    top_sponsors = sponsor_rows[:3]

    latest_trees = (
        TreeRecord.query.order_by(TreeRecord.created_at.desc())
        .limit(20)
        .all()
    )
    latest_trees_json = [
        {
            "species": tree.species,
            "quantity": tree.quantity,
            "latitude": tree.latitude,
            "longitude": tree.longitude,
            "username": tree.user.username,
        }
        for tree in latest_trees
    ]

    co2_kg = total_tree_count * 21
    co2_display = f"{co2_kg} kg"
    if co2_kg >= 1000:
        co2_display = f"{co2_kg / 1000:.2f} tonnes"

    return render_template(
        "shared/home.html",
        total_trees=total_tree_count,
        total_reports=total_reports,
        total_users=total_users,
        participant_count=participant_count,
        total_donations=total_donations,
        co2_display=co2_display,
        top_volunteers=top_volunteers,
        top_sponsors=top_sponsors,
        latest_trees_json=latest_trees_json,
    )


@main_bp.route("/about")
def about():
    return render_template("shared/about.html")


@main_bp.route("/map")
def map_view():
    payload = build_map_payload()
    locations_json = _get_map_locations_payload()

    return render_template(
        "shared/map.html",
        trees_json=payload["trees"],
        reports_json=payload["reports"],
        locations_json=locations_json,
    )


@main_bp.route("/explore", methods=["GET", "POST"])
def explore():
    active_tab = request.args.get("tab", "campaigns").strip().lower()
    if active_tab not in {"campaigns", "map"}:
        active_tab = "campaigns"

    join_form = VolunteerCampaignJoinForm()
    if request.method == "POST":
        action = (request.form.get("action") or "join").strip().lower()

        if action == "review":
            if not current_user.is_authenticated:
                flash("Please log in to manage campaign join requests.", "warning")
                return redirect(url_for("auth.login", next=url_for("main.explore", tab="campaigns")))

            campaign_id_raw = request.form.get("campaign_id")
            signup_id_raw = request.form.get("signup_id")
            decision = (request.form.get("decision") or "").strip().lower()

            if not (campaign_id_raw and signup_id_raw and campaign_id_raw.isdigit() and signup_id_raw.isdigit()):
                flash("Invalid join request action.", "warning")
                return redirect(url_for("main.explore", tab="campaigns"))

            campaign = Campaign.query.get_or_404(int(campaign_id_raw))
            if not (current_user.is_admin or campaign.creator_user_id == current_user.id):
                flash(
                    "Only campaign owners or admins can verify join requests.", "warning")
                return redirect(url_for("main.explore", tab="campaigns"))

            signup = VolunteerCampaignSignup.query.filter_by(
                id=int(signup_id_raw),
                campaign_id=campaign.id,
            ).first_or_404()

            if decision not in {"approved", "rejected"}:
                flash("Invalid decision.", "warning")
                return redirect(url_for("main.explore", tab="campaigns"))

            signup.status = decision
            db.session.commit()
            flash(f"Join request marked as {decision}.", "success")
            return redirect(url_for("main.explore", tab="campaigns"))

        if not current_user.is_authenticated:
            flash("Please log in to join campaigns.", "warning")
            return redirect(url_for("auth.login", next=url_for("main.explore", tab="campaigns")))

        campaign_id_raw = request.form.get(
            "campaign_id") or request.form.get("join-campaign_id")
        motivation_raw = request.form.get(
            "motivation") or request.form.get("join-motivation")

        if campaign_id_raw and str(campaign_id_raw).strip().isdigit():
            campaign = Campaign.query.get_or_404(
                int(str(campaign_id_raw).strip()))
            existing_signup = VolunteerCampaignSignup.query.filter_by(
                user_id=current_user.id,
                campaign_id=campaign.id,
            ).first()

            if existing_signup:
                flash("You already joined this campaign.", "info")
            else:
                signup = VolunteerCampaignSignup(
                    user_id=current_user.id,
                    campaign_id=campaign.id,
                    motivation=motivation_raw.strip() if motivation_raw else None,
                )
                db.session.add(signup)
                db.session.commit()
                flash(
                    "Join request sent. Wait for campaign owner/admin verification.", "success")
        else:
            flash("Could not join campaign from cached form. Please reload Explore and click Join again.", "warning")

        return redirect(url_for("main.explore", tab="campaigns"))

    payload = build_map_payload()
    locations = load_gfw_locations()
    country_summary = _build_country_summary(locations)
    location_filter = request.args.get("location", "").strip().lower()
    goal_filter = request.args.get("goal", "").strip().lower()
    urgency_filter = request.args.get("urgency", "all").strip().lower()
    if urgency_filter not in {"all", "high", "medium", "low"}:
        urgency_filter = "all"

    campaigns = Campaign.query.order_by(Campaign.event_date.asc()).all()
    planted_trees_by_campaign = {
        campaign.id: int(
            db.session.query(db.func.coalesce(
                db.func.sum(TreeRecord.quantity), 0))
            .filter(TreeRecord.campaign_id == campaign.id)
            .scalar()
            or 0
        )
        for campaign in campaigns
    }
    participant_counts = {
        campaign.id: VolunteerCampaignSignup.query.filter_by(
            campaign_id=campaign.id,
            status="approved",
        ).count()
        for campaign in campaigns
    }
    user_signups = []
    if current_user.is_authenticated:
        user_signups = VolunteerCampaignSignup.query.filter_by(
            user_id=current_user.id).all()
    signup_map = {signup.campaign_id: signup for signup in user_signups}

    pending_requests_by_campaign = {}
    if current_user.is_authenticated:
        manageable_campaign_ids = {
            campaign.id
            for campaign in campaigns
            if current_user.is_admin or campaign.creator_user_id == current_user.id
        }
        if manageable_campaign_ids:
            pending_signups = (
                VolunteerCampaignSignup.query.filter(
                    VolunteerCampaignSignup.campaign_id.in_(
                        manageable_campaign_ids),
                    VolunteerCampaignSignup.status == "pending",
                )
                .order_by(VolunteerCampaignSignup.created_at.asc())
                .all()
            )

            for signup in pending_signups:
                pending_requests_by_campaign.setdefault(signup.campaign_id, []).append(
                    {
                        "id": signup.id,
                        "username": signup.user.username,
                        "motivation": signup.motivation,
                    }
                )

    recent_trees = (
        TreeRecord.query.order_by(TreeRecord.created_at.desc())
        .limit(8)
        .all()
    )
    recent_reports = (
        CuttingReport.query.order_by(CuttingReport.created_at.desc())
        .limit(8)
        .all()
    )
    campaign_rows = [
        {
            "id": campaign.id,
            "title": campaign.title,
            "creator_name": campaign.creator.username if campaign.creator else "Green Guard",
            "description": campaign.description,
            "location": campaign.location,
            "event_date_text": campaign.event_date.strftime("%Y-%m-%d"),
            "target_trees": campaign.target_trees,
            "goal_text": f"{campaign.target_trees} trees",
            "urgency": "high" if campaign.event_date <= datetime.utcnow() + timedelta(days=7) else ("medium" if campaign.event_date <= datetime.utcnow() + timedelta(days=21) else "low"),
            "participants": participant_counts.get(campaign.id, 0),
            "is_joined": campaign.id in signup_map,
            "join_status": signup_map[campaign.id].status if campaign.id in signup_map else None,
            "can_manage_requests": current_user.is_authenticated and (current_user.is_admin or campaign.creator_user_id == current_user.id),
            "pending_requests": pending_requests_by_campaign.get(campaign.id, []),
            "has_started": campaign.status == "ongoing",
            "planted_trees": planted_trees_by_campaign.get(campaign.id, 0),
            "progress_percent": min(
                100,
                int(
                    (
                        (planted_trees_by_campaign.get(campaign.id, 0)
                         / max(campaign.target_trees, 1))
                        * 100
                    )
                ),
            ),
        }
        for campaign in campaigns
    ]
    if location_filter:
        campaign_rows = [
            row for row in campaign_rows if location_filter in row["location"].lower() or location_filter in row["title"].lower()
        ]
    if goal_filter:
        campaign_rows = [
            row for row in campaign_rows if goal_filter in row["goal_text"].lower() or goal_filter in row["description"].lower()
        ]
    if urgency_filter != "all":
        campaign_rows = [
            row for row in campaign_rows if row["urgency"] == urgency_filter
        ]
    recent_tree_rows = [
        {
            "username": tree.user.username,
            "quantity": tree.quantity,
            "species": tree.species,
            "created_at_text": tree.created_at.strftime("%Y-%m-%d"),
        }
        for tree in recent_trees
    ]
    recent_report_rows = [
        {
            "username": "Anonymous" if report.is_anonymous else report.user.username,
            "description": report.description,
        }
        for report in recent_reports
    ]

    return render_template(
        "shared/explore.html",
        active_tab=active_tab,
        join_form=join_form,
        campaigns=campaigns,
        campaign_rows=campaign_rows,
        participant_counts=participant_counts,
        signup_map=signup_map,
        trees_json=payload["trees"],
        reports_json=payload["reports"],
        locations_json=_get_map_locations_payload(),
        locations=locations,
        country_summary=country_summary,
        recent_trees=recent_trees,
        recent_reports=recent_reports,
        recent_tree_rows=recent_tree_rows,
        recent_report_rows=recent_report_rows,
        location_filter=location_filter,
        goal_filter=goal_filter,
        urgency_filter=urgency_filter,
    )


@main_bp.route("/campaigns/join/<int:campaign_id>", methods=["GET", "POST"])
@login_required
def join_campaign(campaign_id: int):
    campaign = Campaign.query.get_or_404(campaign_id)
    existing_signup = VolunteerCampaignSignup.query.filter_by(
        user_id=current_user.id,
        campaign_id=campaign.id,
    ).first()

    if existing_signup:
        flash("You already joined this campaign.", "info")
    else:
        signup = VolunteerCampaignSignup(
            user_id=current_user.id,
            campaign_id=campaign.id,
            motivation=None,
        )
        db.session.add(signup)
        db.session.commit()
        flash("Join request sent. Wait for campaign owner/admin verification.", "success")

    return redirect(url_for("main.explore", tab="campaigns"))


@main_bp.route("/action", methods=["GET", "POST"])
@login_required
def create_or_report():
    can_create_campaign = current_user.is_authenticated and (
        current_user.is_admin or current_user.role in CAMPAIGN_CREATOR_ROLES
    )

    campaign_form = VolunteerCampaignCreateForm(prefix="campaign")

    if campaign_form.submit.data and campaign_form.validate_on_submit():
        if not can_create_campaign:
            flash(
                "Campaign creation is available for business sponsors and admins only.", "warning")
            return redirect(url_for("main.create_or_report"))

        try:
            event_date = datetime.strptime(
                campaign_form.event_date.data.strip(), "%Y-%m-%d")
        except ValueError:
            flash("Use date format YYYY-MM-DD.", "warning")
            return redirect(url_for("main.create_or_report", mode="campaign"))

        campaign = Campaign(
            title=campaign_form.title.data.strip(),
            location=campaign_form.location.data.strip(),
            description=campaign_form.description.data.strip(),
            target_trees=campaign_form.target_trees.data,
            event_date=event_date,
            status="open",
            creator_user_id=current_user.id,
        )
        db.session.add(campaign)
        db.session.flush()

        db.session.add(
            VolunteerCampaignSignup(
                user_id=current_user.id,
                campaign_id=campaign.id,
                motivation="Campaign creator",
                status="approved",
            )
        )
        db.session.commit()
        flash("Campaign created and added to your profile.", "success")
        return redirect(url_for("main.profile"))

    return render_template(
        "shared/action.html",
        campaign_form=campaign_form,
        can_create_campaign=can_create_campaign,
    )


@main_bp.route("/api/map-data")
def map_data():
    return jsonify(build_map_payload())


@main_bp.route("/api/gfw-locations")
def gfw_locations_api():
    locations = load_gfw_locations()
    serialized_locations = [_serialize_location(
        location) for location in locations]
    if serialized_locations:
        country_summary = _build_country_summary(locations)
    else:
        serialized_locations = _build_fallback_location_payload()
        country_summary = []
    return jsonify(
        {
            "locations": serialized_locations,
            "count": len(serialized_locations),
            "countries": country_summary,
            "synced_at": _get_sync_state().last_synced_at.isoformat() if _get_sync_state().last_synced_at else None,
        }
    )


@main_bp.route("/api/gfw-restoration")
def gfw_restoration():
    return gfw_locations_api()


@main_bp.route("/locations")
def locations_view():
    locations = load_gfw_locations()
    country_summary = _build_country_summary(locations)
    return render_template("shared/locations.html", locations=locations, country_summary=country_summary)


@main_bp.route("/locations/<int:location_id>")
def location_detail(location_id):
    ensure_gfw_locations_current()
    location = GFWLocation.query.get_or_404(location_id)
    return render_template(
        "shared/location_detail.html",
        location=location,
        frp_display=location.frp_mw if location.frp_mw is not None else "n/a",
        last_seen_display=location.last_seen_at.strftime(
            "%Y-%m-%d %H:%M UTC") if location.last_seen_at else "Unknown",
        reforestation_display=location.reforestation_type or "Not tagged",
    )


def _build_sponsor_leaderboard_rows() -> list[dict]:
    sponsor_users = User.query.filter(
        User.is_admin.is_(False),
        User.role.in_(["business", "individual"]),
    ).all()

    rows = []
    for user in sponsor_users:
        total_amount = sum(
            float(donation.amount)
            for donation in SupportDonation.query.filter_by(user_id=user.id).all()
        )
        rows.append({"user": user, "total_amount": total_amount})

    rows.sort(
        key=lambda item: (
            item["total_amount"],
            item["user"].username.lower(),
        ),
        reverse=True,
    )

    for index, item in enumerate(rows, start=1):
        item["rank"] = index

    return rows


def _build_volunteer_leaderboard_rows() -> list[dict]:
    volunteer_users = User.query.filter(
        User.is_admin.is_(False),
        User.role.in_(["volunteer", "individual"]),
    ).all()

    rows = []
    for user in volunteer_users:
        score_data = _calculate_volunteer_score(user)
        rows.append(
            {
                "user": user,
                "tree_count": score_data["tree_count"],
                "report_count": score_data["report_count"],
                "campaigns_created": score_data["campaigns_created"],
                "total_points": score_data["total_points"],
            }
        )

    rows.sort(
        key=lambda item: (
            item["total_points"],
            item["tree_count"],
            item["report_count"],
            item["campaigns_created"],
            item["user"].username.lower(),
        ),
        reverse=True,
    )

    for index, item in enumerate(rows, start=1):
        item["rank"] = index

    return rows


@main_bp.route("/leaderboard")
def leaderboard():
    return render_template(
        "shared/leaderboards.html",
        sponsor_leaderboard=_build_sponsor_leaderboard_rows(),
        volunteer_leaderboard=_build_volunteer_leaderboard_rows(),
    )


def _calculate_volunteer_score(user: User) -> dict:
    trees = TreeRecord.query.filter_by(user_id=user.id).all()
    reports = CuttingReport.query.filter_by(user_id=user.id).all()
    campaigns_created = Campaign.query.filter_by(
        creator_user_id=user.id).count()

    tree_count = sum(tree.quantity or 0 for tree in trees)
    report_count = len(reports)
    tree_points = tree_count * 10
    report_points = report_count * 15
    campaign_points = campaigns_created * 30
    total_points = tree_points + report_points + campaign_points

    return {
        "tree_count": tree_count,
        "report_count": report_count,
        "campaigns_created": campaigns_created,
        "total_points": total_points,
    }


def _calculate_tree_impact(tree_records: list[TreeRecord]) -> dict:
    now = datetime.utcnow()
    total_trees = sum(tree.quantity or 0 for tree in tree_records)

    total_tree_years = 0.0
    for tree in tree_records:
        quantity = tree.quantity or 0
        if quantity <= 0 or not tree.created_at:
            continue

        elapsed_days = max(
            (now - tree.created_at).total_seconds() / 86400.0, 0.0)
        elapsed_years = elapsed_days / 365.25
        total_tree_years += quantity * elapsed_years

    co2_absorbed_kg = total_tree_years * 22.0
    oxygen_produced_kg = total_tree_years * 110.0
    wildlife_supported = total_trees * 10

    if total_trees >= 300:
        cooling_effect = "Strong neighborhood cooling and shade contribution"
    elif total_trees >= 100:
        cooling_effect = "Noticeable local cooling and shade contribution"
    elif total_trees >= 25:
        cooling_effect = "Growing cooling effect in your planted areas"
    elif total_trees > 0:
        cooling_effect = "Early-stage cooling effect that will grow each year"
    else:
        cooling_effect = "Plant trees to start generating local cooling benefits"

    equivalent_car_km = co2_absorbed_kg / 0.192 if co2_absorbed_kg > 0 else 0.0
    equivalent_person_years = co2_absorbed_kg / \
        4600.0 if co2_absorbed_kg > 0 else 0.0

    message = (
        f"You helped remove about {co2_absorbed_kg:.1f} kg of CO2 from the atmosphere. "
        "Your trees will continue working for years as they grow."
    )

    return {
        "total_trees": total_trees,
        "tree_years": total_tree_years,
        "co2_absorbed_kg": co2_absorbed_kg,
        "oxygen_produced_kg": oxygen_produced_kg,
        "wildlife_supported": wildlife_supported,
        "cooling_effect": cooling_effect,
        "equivalent_car_km": equivalent_car_km,
        "equivalent_person_years": equivalent_person_years,
        "message": message,
    }


def _calculate_sponsorship_impact(donations: list[SupportDonation]) -> dict:
    now = datetime.utcnow()
    plant_donations = [
        donation
        for donation in donations
        if donation.category == "plants" and (donation.quantity or 0) > 0
    ]
    total_trees = sum(donation.quantity or 0 for donation in plant_donations)

    total_tree_years = 0.0
    for donation in plant_donations:
        quantity = donation.quantity or 0
        if quantity <= 0 or not donation.created_at:
            continue

        elapsed_days = max(
            (now - donation.created_at).total_seconds() / 86400.0, 0.0)
        elapsed_years = elapsed_days / 365.25
        total_tree_years += quantity * elapsed_years

    co2_absorbed_kg = total_tree_years * 22.0
    oxygen_produced_kg = total_tree_years * 110.0
    wildlife_supported = total_trees * 10
    equivalent_car_km = co2_absorbed_kg / 0.192 if co2_absorbed_kg > 0 else 0.0
    equivalent_person_years = co2_absorbed_kg / \
        4600.0 if co2_absorbed_kg > 0 else 0.0

    if total_trees >= 300:
        cooling_effect = "Strong neighborhood cooling and shade contribution"
    elif total_trees >= 100:
        cooling_effect = "Noticeable local cooling and shade contribution"
    elif total_trees >= 25:
        cooling_effect = "Growing cooling effect in your planted areas"
    elif total_trees > 0:
        cooling_effect = "Early-stage cooling effect that will grow each year"
    else:
        cooling_effect = "Sponsor trees to start generating local cooling benefits"

    message = (
        f"Your sponsored trees removed about {co2_absorbed_kg:.1f} kg of CO2 over time. "
        "Their impact keeps increasing as months and years pass."
    )

    return {
        "total_trees": total_trees,
        "tree_years": total_tree_years,
        "co2_absorbed_kg": co2_absorbed_kg,
        "oxygen_produced_kg": oxygen_produced_kg,
        "wildlife_supported": wildlife_supported,
        "cooling_effect": cooling_effect,
        "equivalent_car_km": equivalent_car_km,
        "equivalent_person_years": equivalent_person_years,
        "message": message,
    }


def _merge_impact_data(primary: dict, secondary: dict) -> dict:
    total_trees = (primary.get("total_trees", 0) or 0) + \
        (secondary.get("total_trees", 0) or 0)
    tree_years = (primary.get("tree_years", 0.0) or 0.0) + \
        (secondary.get("tree_years", 0.0) or 0.0)
    co2_absorbed_kg = (primary.get("co2_absorbed_kg", 0.0) or 0.0) + \
        (secondary.get("co2_absorbed_kg", 0.0) or 0.0)
    oxygen_produced_kg = (primary.get("oxygen_produced_kg", 0.0) or 0.0) + \
        (secondary.get("oxygen_produced_kg", 0.0) or 0.0)
    wildlife_supported = (primary.get("wildlife_supported", 0) or 0) + \
        (secondary.get("wildlife_supported", 0) or 0)

    if total_trees >= 300:
        cooling_effect = "Strong neighborhood cooling and shade contribution"
    elif total_trees >= 100:
        cooling_effect = "Noticeable local cooling and shade contribution"
    elif total_trees >= 25:
        cooling_effect = "Growing cooling effect in your planted areas"
    elif total_trees > 0:
        cooling_effect = "Early-stage cooling effect that will grow each year"
    else:
        cooling_effect = "Plant or sponsor trees to start generating local cooling benefits"

    equivalent_car_km = co2_absorbed_kg / 0.192 if co2_absorbed_kg > 0 else 0.0
    equivalent_person_years = co2_absorbed_kg / \
        4600.0 if co2_absorbed_kg > 0 else 0.0
    message = (
        f"Your combined planting and sponsorship impact removed about {co2_absorbed_kg:.1f} kg of CO2. "
        "This grows automatically over time."
    )

    return {
        "total_trees": total_trees,
        "tree_years": tree_years,
        "co2_absorbed_kg": co2_absorbed_kg,
        "oxygen_produced_kg": oxygen_produced_kg,
        "wildlife_supported": wildlife_supported,
        "cooling_effect": cooling_effect,
        "equivalent_car_km": equivalent_car_km,
        "equivalent_person_years": equivalent_person_years,
        "message": message,
    }


@main_bp.route("/leaderboard/volunteers")
def volunteer_leaderboard():
    return redirect(url_for("main.leaderboard") + "#volunteers")


@main_bp.route("/volunteer/dashboard")
@login_required
@role_required("volunteer")
def volunteer_dashboard():
    score_data = _calculate_volunteer_score(current_user)

    user_trees = TreeRecord.query.filter_by(user_id=current_user.id).all()
    recent_trees = (
        TreeRecord.query.filter_by(user_id=current_user.id)
        .order_by(TreeRecord.created_at.desc())
        .limit(5)
        .all()
    )
    recent_reports = (
        CuttingReport.query.filter_by(user_id=current_user.id)
        .order_by(CuttingReport.created_at.desc())
        .limit(5)
        .all()
    )
    joined_campaigns = (
        VolunteerCampaignSignup.query.filter_by(user_id=current_user.id)
        .order_by(VolunteerCampaignSignup.created_at.desc())
        .limit(5)
        .all()
    )
    impact_data = _calculate_tree_impact(user_trees)

    return render_template(
        "volunteers/volunteer_dashboard.html",
        score_data=score_data,
        recent_trees=recent_trees,
        recent_reports=recent_reports,
        joined_campaigns=joined_campaigns,
        impact_data=impact_data,
    )


@main_bp.route("/business/dashboard")
@login_required
@role_required("business")
def business_dashboard():
    all_trees = TreeRecord.query.filter_by(user_id=current_user.id).all()
    business_donations = SupportDonation.query.filter_by(
        user_id=current_user.id).all()
    recent_trees = (
        TreeRecord.query.filter_by(user_id=current_user.id)
        .order_by(TreeRecord.created_at.desc())
        .limit(10)
        .all()
    )

    funded_trees = sum(tree.quantity for tree in all_trees)
    sponsorship_records = len(all_trees)
    donation_trees = sum(
        donation.quantity or 0
        for donation in business_donations
        if donation.category == "plants"
    )
    total_trees_supported = funded_trees + donation_trees
    total_contribution_usd = sum(float(donation.amount)
                                 for donation in business_donations)

    total_commission_usd = 0.0
    for donation in business_donations:
        amount = float(donation.amount)
        if amount < 1000:
            rate = 0.05
        elif amount < 5000:
            rate = 0.10
        else:
            rate = 0.15
        total_commission_usd += amount * rate

    co2_reduction_kg = total_trees_supported * 21
    co2_reduction_tons = co2_reduction_kg / 1000

    if total_trees_supported >= 1000:
        recognition_badge = "Eco Champion"
    elif total_trees_supported >= 500:
        recognition_badge = "Eco Partner"
    elif total_trees_supported >= 100:
        recognition_badge = "Green Supporter"
    else:
        recognition_badge = "Growing Contributor"

    impact_score = int(total_trees_supported * 1.8 +
                       total_contribution_usd / 100)

    proof_gallery = [tree for tree in recent_trees if tree.image_filename][:4]
    sponsor_rows = []
    all_sponsors = User.query.filter(
        User.is_admin.is_(False),
        User.role.in_(["business", "individual"]),
    ).all()
    for sponsor_user in all_sponsors:
        sponsor_total = sum(
            float(donation.amount)
            for donation in SupportDonation.query.filter_by(user_id=sponsor_user.id).all()
        )
        sponsor_rows.append(
            {"user_id": sponsor_user.id, "total": sponsor_total})

    sponsor_rows.sort(key=lambda row: row["total"], reverse=True)
    public_sponsor_rank = "-"
    for index, row in enumerate(sponsor_rows, start=1):
        if row["user_id"] == current_user.id:
            public_sponsor_rank = index
            break

    map_payload = build_map_payload()
    recent_volunteer_proofs = (
        TreeRecord.query.join(User)
        .filter(
            User.is_admin.is_(False),
            User.role.in_(["volunteer", "individual"]),
            TreeRecord.image_filename.isnot(None),
        )
        .order_by(TreeRecord.created_at.desc())
        .limit(6)
        .all()
    )
    sponsor_impact_data = _calculate_sponsorship_impact(business_donations)

    return render_template(
        "businesses/sponsors/business_dashboard.html",
        funded_trees=funded_trees,
        donation_trees=donation_trees,
        total_trees_supported=total_trees_supported,
        total_contribution_usd=total_contribution_usd,
        total_commission_usd=total_commission_usd,
        co2_reduction_kg=co2_reduction_kg,
        co2_reduction_tons=co2_reduction_tons,
        recognition_badge=recognition_badge,
        proof_gallery=proof_gallery,
        public_sponsor_rank=public_sponsor_rank,
        sponsorship_records=sponsorship_records,
        impact_score=impact_score,
        recent_trees=recent_trees,
        trees_json=map_payload["trees"],
        reports_json=map_payload["reports"],
        recent_volunteer_proofs=recent_volunteer_proofs,
        sponsor_impact_data=sponsor_impact_data,
    )


@main_bp.route("/business/certificate")
@login_required
@role_required("business")
def business_certificate():
    business_donations = SupportDonation.query.filter_by(
        user_id=current_user.id).all()
    funded_trees = sum(
        tree.quantity for tree in TreeRecord.query.filter_by(user_id=current_user.id).all()
    )
    donation_trees = sum(
        donation.quantity or 0
        for donation in business_donations
        if donation.category == "plants"
    )
    total_trees_supported = funded_trees + donation_trees
    total_contribution_usd = sum(float(donation.amount)
                                 for donation in business_donations)
    co2_reduction_kg = total_trees_supported * 21

    return render_template(
        "businesses/sponsors/business_certificate.html",
        total_trees_supported=total_trees_supported,
        total_contribution_usd=total_contribution_usd,
        co2_reduction_kg=co2_reduction_kg,
        current_time=datetime.utcnow(),
    )


@main_bp.route("/sponsorship/donations", methods=["GET", "POST"])
@login_required
@role_required("business", "individual")
def sponsorship_donations():
    form = SupportDonationForm()
    campaigns = Campaign.query.order_by(Campaign.event_date.asc()).all()
    campaign_choices = [(0, "Any Campaign")]
    campaign_choices.extend(
        [(campaign.id, f"{campaign.title} ({campaign.location})")
         for campaign in campaigns]
    )
    form.campaign_id.choices = campaign_choices

    package_options = {
        "50": {"trees": 50, "amount": 200},
        "100": {"trees": 100, "amount": 380},
        "500": {"trees": 500, "amount": 1750},
    }

    package_key = request.args.get("package", "").strip()
    campaign_key = request.args.get("campaign", "").strip()

    if request.method == "GET" and package_key in package_options:
        package = package_options[package_key]
        form.category.data = "plants"
        form.donation_item.data = "plants:mixed_native_pack"
        form.tree_species.data = "mixed_native_pack"
        form.price_per_tree.data = round(
            package["amount"] / package["trees"], 2)
        form.quantity.data = package["trees"]
        form.amount.data = package["amount"]

    if request.method == "GET" and campaign_key.isdigit():
        selected_campaign_id = int(campaign_key)
        if any(choice_id == selected_campaign_id for choice_id, _ in campaign_choices):
            form.campaign_id.data = selected_campaign_id

    if form.validate_on_submit():
        quantity_value = int(
            form.quantity.data) if form.quantity.data is not None else 0
        amount_value = float(
            form.amount.data) if form.amount.data is not None else 0.0
        item_key = ""

        if form.category.data == "plants":
            item_key = form.tree_species.data
            unit_price = float(form.price_per_tree.data)
            amount_value = round(quantity_value * unit_price, 2)
        else:
            selected_item = form.donation_item.data
            _, item_key = selected_item.split(":", 1)

            if quantity_value <= 0 and amount_value > 0:
                quantity_value = max(1, int(round(amount_value / 4)))
            if amount_value <= 0 and quantity_value > 0:
                amount_value = float(quantity_value * 4)

        points = calculate_donation_points(
            form.category.data, quantity_value, amount_value)

        if amount_value < 1000:
            commission_rate = 0.05
        elif amount_value < 5000:
            commission_rate = 0.10
        else:
            commission_rate = 0.15

        commission_amount = amount_value * commission_rate
        project_funding_amount = amount_value - commission_amount

        note_segments = []
        if form.note.data:
            note_segments.append(form.note.data.strip())
        if form.category.data == "plants":
            note_segments.append(
                f"Tree species: {item_key} | Unit price: ${float(form.price_per_tree.data):.2f}"
            )
        if form.campaign_id.data:
            selected_campaign = next(
                (campaign for campaign in campaigns if campaign.id ==
                 form.campaign_id.data),
                None,
            )
            if selected_campaign:
                note_segments.append(
                    f"[campaign:{selected_campaign.id}] Funded campaign: {selected_campaign.title}"
                )
        note_segments.append(
            f"Commission {int(commission_rate * 100)}% (${commission_amount:.2f})")
        note_segments.append(
            f"Project allocation ${project_funding_amount:.2f}")

        session["pending_sponsorship_payment"] = {
            "user_id": current_user.id,
            "category": form.category.data,
            "donation_item": item_key,
            "quantity": quantity_value,
            "amount": round(amount_value, 2),
            "points": points,
            "campaign_id": int(form.campaign_id.data or 0),
            "note": " | ".join(note_segments),
        }
        return redirect(url_for("main.sponsorship_checkout"))

    user_donations = (
        SupportDonation.query.filter_by(user_id=current_user.id)
        .order_by(SupportDonation.created_at.desc())
        .all()
    )
    all_donations = SupportDonation.query.all()
    business_donations = SupportDonation.query.join(User).filter(
        User.role == "business", User.is_admin.is_(False)
    ).all()
    top_businesses = (
        db.session.query(User, db.func.sum(
            SupportDonation.amount).label("total_amount"))
        .join(SupportDonation, SupportDonation.user_id == User.id)
        .filter(User.role == "business", User.is_admin.is_(False))
        .group_by(User.id)
        .order_by(db.func.sum(SupportDonation.amount).desc())
        .limit(5)
        .all()
    )

    category_labels = {
        "plants": "Plants and Seedlings",
        "tools": "Planting Tools and Equipment",
        "travel": "Volunteer Trip and Transport Money",
    }
    donation_item_labels = {
        "oak_saplings": "Oak Saplings",
        "pine_seedlings": "Pine Seedlings",
        "maple_seedlings": "Maple Seedlings",
        "cedar_seedlings": "Cedar Seedlings",
        "mixed_native_pack": "Mixed Native Tree Pack",
        "shovel_set": "Shovel Set",
        "watering_can": "Watering Can",
        "protective_gloves": "Protective Gloves",
        "soil_testing_kit": "Soil Testing Kit",
        "wheelbarrow": "Wheelbarrow",
        "fuel_support": "Volunteer Fuel Support",
        "bus_transport": "Volunteer Bus Transport",
        "logistics_support": "Field Logistics Support",
    }
    totals_by_category = {key: 0.0 for key in category_labels}
    total_amount = 0.0
    total_points = 0
    total_commission_amount = 0.0
    total_project_amount = 0.0
    total_plants_quantity = 0
    user_total_amount = 0.0
    user_total_trees = 0

    for donation in all_donations:
        amount = float(donation.amount)
        totals_by_category[donation.category] = totals_by_category.get(
            donation.category, 0.0) + amount
        total_amount += amount
        total_points += donation.points or 0

    for donation in business_donations:
        amount = float(donation.amount)
        if amount < 1000:
            rate = 0.05
        elif amount < 5000:
            rate = 0.10
        else:
            rate = 0.15
        commission = amount * rate
        total_commission_amount += commission
        total_project_amount += amount - commission
        if donation.category == "plants":
            total_plants_quantity += donation.quantity or 0

    for donation in user_donations:
        user_total_amount += float(donation.amount)
        if donation.category == "plants":
            user_total_trees += donation.quantity or 0

    user_co2_kg = user_total_trees * 21
    if user_total_trees < 100:
        sponsor_badge = "Green Supporter"
    elif user_total_trees < 500:
        sponsor_badge = "Eco Partner"
    else:
        sponsor_badge = "Eco Champion"

    return render_template(
        "businesses/sponsors/sponsorship_donations.html",
        form=form,
        user_donations=user_donations,
        top_businesses=top_businesses,
        package_options=package_options,
        category_labels=category_labels,
        donation_item_labels=donation_item_labels,
        tree_species_default_prices=TREE_SPECIES_DEFAULT_PRICES,
        sponsor_badge=sponsor_badge,
        campaigns=campaigns,
        totals_by_category=totals_by_category,
        total_amount=total_amount,
        total_points=total_points,
        total_commission_amount=total_commission_amount,
        total_project_amount=total_project_amount,
        total_plants_quantity=total_plants_quantity,
        user_total_amount=user_total_amount,
        user_total_trees=user_total_trees,
        user_co2_kg=user_co2_kg,
    )


@main_bp.route("/sponsorship/checkout", methods=["GET", "POST"])
@login_required
@role_required("business", "individual")
def sponsorship_checkout():
    pending_payment = session.get("pending_sponsorship_payment")
    if not pending_payment:
        flash("No pending payment found. Please create a sponsorship first.", "warning")
        return redirect(url_for("main.sponsorship_donations"))

    if pending_payment.get("user_id") != current_user.id:
        session.pop("pending_sponsorship_payment", None)
        flash("Pending payment session expired. Please try again.", "warning")
        return redirect(url_for("main.sponsorship_donations"))

    payment_methods = {
        "paypal": "PayPal",
        "google_pay": "Google Pay",
        "apple_pay": "Apple Pay",
        "credit_card": "Credit Card",
    }

    if request.method == "POST":
        payment_method = (request.form.get("payment_method") or "").strip()
        if payment_method not in payment_methods:
            flash("Please select a valid payment method.", "danger")
            return render_template(
                "businesses/sponsors/sponsorship_checkout.html",
                pending_payment=pending_payment,
                payment_methods=payment_methods,
            )

        transaction_id = build_payment_transaction_id(
            user_id=current_user.id,
            payment_method=payment_method,
            amount=float(pending_payment["amount"]),
        )

        note_segments = []
        if pending_payment.get("note"):
            note_segments.append(pending_payment["note"])
        note_segments.append(
            f"Payment completed via {payment_methods[payment_method]} (tx {transaction_id})"
        )

        donation = SupportDonation(
            user_id=current_user.id,
            category=pending_payment["category"],
            donation_item=pending_payment["donation_item"],
            quantity=int(pending_payment["quantity"]),
            amount=float(pending_payment["amount"]),
            points=int(pending_payment["points"]),
            note=" | ".join(note_segments),
        )
        db.session.add(donation)
        db.session.commit()
        session.pop("pending_sponsorship_payment", None)

        flash(
            f"Payment successful ({transaction_id}). Sponsorship has been recorded.",
            "success",
        )
        return redirect(url_for("main.sponsorship_donations"))

    return render_template(
        "businesses/sponsors/sponsorship_checkout.html",
        pending_payment=pending_payment,
        payment_methods=payment_methods,
    )


@main_bp.route("/sponsors")
def sponsors_page():
    sponsors = User.query.filter(
        User.is_admin.is_(False),
        User.role.in_(["business", "individual"]),
    ).all()

    sponsor_showcase = []
    for sponsor in sponsors:
        donations = SupportDonation.query.filter_by(user_id=sponsor.id).all()
        amount_total = sum(float(item.amount) for item in donations)
        trees_total = sum(
            item.quantity or 0 for item in donations if item.category == "plants"
        )
        if amount_total <= 0 and trees_total <= 0:
            continue
        sponsor_showcase.append(
            {
                "user": sponsor,
                "amount_total": amount_total,
                "trees_total": trees_total,
            }
        )

    sponsor_showcase.sort(
        key=lambda row: (row["amount_total"], row["trees_total"]),
        reverse=True,
    )

    return render_template(
        "businesses/sponsors/sponsors.html",
        sponsor_showcase=sponsor_showcase[:12],
    )


def start_gfw_location_scheduler(app) -> None:
    if app.extensions.get("gfw_location_scheduler_started"):
        return

    def scheduler_loop() -> None:
        while True:
            sync_time_text = app.config.get(
                "GFW_DAILY_SYNC_TIME", DEFAULT_GFW_SYNC_TIME)
            sync_time = _parse_sync_time(sync_time_text)
            now = datetime.utcnow()
            next_sync = datetime.combine(now.date(), sync_time)
            if now >= next_sync:
                next_sync += timedelta(days=1)

            sleep_seconds = max(60, (next_sync - now).total_seconds())
            time.sleep(sleep_seconds)

            with app.app_context():
                try:
                    trigger_gfw_sync_async(force=True)
                except Exception as error:  # pragma: no cover - background safety net
                    current_app.logger.warning(
                        "Scheduled GFW sync failed: %s", error)

    app.extensions["gfw_location_scheduler_started"] = True
    Thread(target=scheduler_loop, daemon=True).start()


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()

    if form.validate_on_submit():
        flash("Thank you for contacting Green Guard. We received your message.", "success")
        return redirect(url_for("main.contact"))

    return render_template("shared/contact.html", form=form)


@main_bp.route("/merch", methods=["GET", "POST"])
def merch_shop():
    item_by_key = {item["key"]: item for item in MERCH_ITEMS}

    available_points = None
    if current_user.is_authenticated and current_user.role == "volunteer":
        earned_points = _calculate_volunteer_score(current_user)[
            "total_points"]
        spent_points = (
            db.session.query(db.func.sum(MerchPurchase.points_spent))
            .filter(MerchPurchase.user_id == current_user.id)
            .scalar()
            or 0
        )
        available_points = max(0, earned_points - int(spent_points))

    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Please log in to complete a merch purchase.", "warning")
            return redirect(url_for("auth.login", next=url_for("main.merch_shop")))

        merch_key = (request.form.get("merch_key") or "").strip()
        payment_mode = (request.form.get("payment_mode")
                        or "money").strip().lower()
        quantity_raw = (request.form.get("quantity") or "1").strip()

        if not quantity_raw.isdigit() or int(quantity_raw) <= 0:
            flash("Please enter a valid quantity.", "danger")
            return redirect(url_for("main.merch_shop"))

        quantity = min(int(quantity_raw), 20)
        item = item_by_key.get(merch_key)
        if not item:
            flash("Selected merch item is not available.", "danger")
            return redirect(url_for("main.merch_shop"))

        total_price = float(item["price"] * quantity)
        total_points = int(item["points"] * quantity)
        trees_supported = int(item["trees"] * quantity)

        if payment_mode == "points":
            if current_user.role != "volunteer":
                flash("Only volunteers can buy merch with points.", "warning")
                return redirect(url_for("main.merch_shop"))

            volunteer_points = available_points if available_points is not None else 0
            if volunteer_points < total_points:
                flash(
                    f"Not enough points. You need {total_points} points but have {volunteer_points}.",
                    "danger",
                )
                return redirect(url_for("main.merch_shop"))

            purchase = MerchPurchase(
                user_id=current_user.id,
                merch_key=item["key"],
                merch_name=item["name"],
                quantity=quantity,
                payment_mode="points",
                amount_usd=0,
                points_spent=total_points,
                trees_supported=trees_supported,
                note=f"Paid with points ({total_points} pts)",
            )
            db.session.add(purchase)
            db.session.commit()
            flash(
                f"Purchase complete: {item['name']} x{quantity} paid with {total_points} points.",
                "success",
            )
            return redirect(url_for("main.merch_shop"))

        purchase = MerchPurchase(
            user_id=current_user.id,
            merch_key=item["key"],
            merch_name=item["name"],
            quantity=quantity,
            payment_mode="money",
            amount_usd=total_price,
            points_spent=0,
            trees_supported=trees_supported,
            note=f"Paid with USD (${total_price:.2f})",
        )
        db.session.add(purchase)
        db.session.commit()
        flash(
            f"Purchase complete: {item['name']} x{quantity} for ${total_price:.2f}.",
            "success",
        )
        return redirect(url_for("main.merch_shop"))

    recent_purchases = []
    if current_user.is_authenticated:
        recent_purchases = (
            MerchPurchase.query.filter_by(user_id=current_user.id)
            .order_by(MerchPurchase.created_at.desc())
            .limit(10)
            .all()
        )

    return render_template(
        "shared/merch.html",
        merch_items=MERCH_ITEMS,
        available_points=available_points,
        recent_purchases=recent_purchases,
    )


@main_bp.route("/profile")
@login_required
def profile():
    user_trees = (
        TreeRecord.query.filter_by(user_id=current_user.id)
        .order_by(TreeRecord.created_at.desc())
        .all()
    )
    user_reports = (
        CuttingReport.query.filter_by(user_id=current_user.id)
        .order_by(CuttingReport.created_at.desc())
        .all()
    )
    created_campaigns = (
        Campaign.query.filter_by(creator_user_id=current_user.id)
        .order_by(Campaign.event_date.desc())
        .all()
    )
    joined_campaigns = (
        VolunteerCampaignSignup.query.filter_by(user_id=current_user.id)
        .order_by(VolunteerCampaignSignup.created_at.desc())
        .all()
    )

    volunteer_rows = []
    volunteer_users = User.query.filter(
        User.is_admin.is_(False),
        User.role.in_(["volunteer", "individual"]),
    ).all()
    for user in volunteer_users:
        score_data = _calculate_volunteer_score(user)
        volunteer_rows.append(
            {
                "user_id": user.id,
                "total_points": score_data["total_points"],
                "tree_count": score_data["tree_count"],
                "report_count": score_data["report_count"],
                "campaigns_created": score_data["campaigns_created"],
            }
        )

    volunteer_rows.sort(
        key=lambda item: (
            item["total_points"],
            item["tree_count"],
            item["report_count"],
            item["campaigns_created"],
        ),
        reverse=True,
    )

    volunteer_rank = None
    for index, item in enumerate(volunteer_rows, start=1):
        if item["user_id"] == current_user.id:
            volunteer_rank = index
            break
    volunteer_rank_display = volunteer_rank if volunteer_rank else "-"

    profile_points = _calculate_volunteer_score(current_user)
    created_campaign_rows = [
        {
            "title": campaign.title,
            "location": campaign.location,
            "event_date_text": campaign.event_date.strftime("%Y-%m-%d"),
        }
        for campaign in created_campaigns
    ]
    joined_campaign_rows = [
        {
            "campaign_id": signup.campaign_id,
            "title": signup.campaign.title,
            "status": signup.status,
            "event_date_text": signup.campaign.event_date.strftime("%Y-%m-%d"),
            "has_started": signup.campaign.status == "ongoing",
        }
        for signup in joined_campaigns
    ]
    user_tree_rows = [
        {
            "species": tree.species,
            "quantity": tree.quantity,
            "created_at_text": tree.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for tree in user_trees
    ]
    tree_impact_data = _calculate_tree_impact(user_trees)
    sponsor_donations = (
        SupportDonation.query.filter_by(user_id=current_user.id)
        .order_by(SupportDonation.created_at.desc())
        .all()
    )
    sponsor_impact_data = _calculate_sponsorship_impact(sponsor_donations)
    if current_user.role == "individual":
        impact_data = _merge_impact_data(tree_impact_data, sponsor_impact_data)
    else:
        impact_data = tree_impact_data
    user_report_rows = [
        {
            "description": report.description,
            "status": report.status,
            "is_anonymous": report.is_anonymous,
            "created_at_text": report.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for report in user_reports
    ]

    business_profile = None
    if current_user.role == "business":
        business_donations = sponsor_donations
        total_donated = sum(float(item.amount) for item in business_donations)
        trees_funded = sum(item.quantity or 0 for item in business_donations)
        points = sum(item.points or 0 for item in business_donations)

        if trees_funded >= 1000:
            badge = "Eco Champion"
        elif trees_funded >= 500:
            badge = "Eco Partner"
        elif trees_funded >= 100:
            badge = "Green Supporter"
        else:
            badge = "Growing Contributor"

        sponsor_rows = []
        sponsor_users = User.query.filter(
            User.is_admin.is_(False),
            User.role.in_(["business", "individual"]),
        ).all()
        for sponsor_user in sponsor_users:
            sponsor_total = sum(
                float(item.amount)
                for item in SupportDonation.query.filter_by(user_id=sponsor_user.id).all()
            )
            sponsor_rows.append(
                {"user_id": sponsor_user.id, "total": sponsor_total})
        sponsor_rows.sort(key=lambda row: row["total"], reverse=True)

        rank = "-"
        for index, row in enumerate(sponsor_rows, start=1):
            if row["user_id"] == current_user.id:
                rank = index
                break

        business_profile = {
            "total_donated": total_donated,
            "trees_funded": trees_funded,
            "badge": badge,
            "rank": rank,
            "points": points,
            "impact": sponsor_impact_data,
            "history": [
                {
                    "category": donation.category,
                    "quantity": donation.quantity,
                    "amount": float(donation.amount),
                    "created_at": donation.created_at.strftime("%Y-%m-%d %H:%M"),
                }
                for donation in business_donations
            ],
        }

    delete_form = DeleteForm()
    return render_template(
        "shared/profile.html",
        user_trees=user_trees,
        user_reports=user_reports,
        created_campaigns=created_campaigns,
        joined_campaigns=joined_campaigns,
        created_campaign_rows=created_campaign_rows,
        joined_campaign_rows=joined_campaign_rows,
        user_tree_rows=user_tree_rows,
        user_report_rows=user_report_rows,
        profile_points=profile_points,
        volunteer_rank=volunteer_rank,
        volunteer_rank_display=volunteer_rank_display,
        impact_data=impact_data,
        business_profile=business_profile,
        delete_form=delete_form,
    )


@main_bp.route("/api/search-location", methods=["GET"])
def search_location():
    """
    Search for location by street name, city, or landmark.
    Uses OpenStreetMap Nominatim API for geocoding.
    Query parameter: q (search query)
    Returns: JSON list of matching locations with lat/lon coordinates
    """
    query = current_app.request.args.get("q", "").strip()

    if not query or len(query) < 2:
        return jsonify({"results": []})

    try:
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 10,
            "addressdetails": 1
        }

        url = f"{nominatim_url}?{urlencode(params)}"

        req = Request(url, headers={"User-Agent": "Green-Guard-App"})

        with urlopen(req, timeout=5) as response:
            if response.status != 200:
                return jsonify({"results": []})

            data = json.loads(response.read().decode())

            results = []
            for location in data:
                result = {
                    "name": location.get("name", ""),
                    "display_name": location.get("display_name", ""),
                    "latitude": float(location.get("lat", 0)),
                    "longitude": float(location.get("lon", 0)),
                    "type": location.get("type", ""),
                    "address": location.get("address", {})
                }
                results.append(result)

            return jsonify({"results": results})

    except (HTTPError, URLError, ValueError, json.JSONDecodeError, Exception):
        return jsonify({"results": []})
