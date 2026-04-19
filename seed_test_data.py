from app import app
from extensions import db
from models import Campaign, CuttingReport, MerchPurchase, SupportDonation, TreeRecord, User, VolunteerCampaignSignup
from datetime import datetime, timedelta, timezone
import random
from werkzeug.security import generate_password_hash

TBILISI_LOCATIONS = [
    {
        "name": "Mtkvari River Park",
        "latitude": 41.7151,
        "longitude": 44.8271,
    },
    {
        "name": "Vake District",
        "latitude": 41.7318,
        "longitude": 44.7681,
    },
    {
        "name": "Saburtalo District",
        "latitude": 41.7549,
        "longitude": 44.8006,
    },
    {
        "name": "Old Town (Metekhi)",
        "latitude": 41.7167,
        "longitude": 44.8089,
    },
    {
        "name": "Botanical Garden",
        "latitude": 41.7089,
        "longitude": 44.7825,
    },
    {
        "name": "Narikala Fortress",
        "latitude": 41.7199,
        "longitude": 44.8097,
    },
]

PLANTING_IMAGES = [
    "images/forest img/planting/download.jpg",
    "images/forest img/planting/image.png",
    "images/forest img/planting/images.jpg",
]

CUTTING_IMAGES = [
    "images/forest img/cutting/download (1).jpg",
    "images/forest img/cutting/download.jpg",
    "images/forest img/cutting/images.jpg",
]

CAMPAIGN_RECORDS = [
    {
        "title": "Mtkvari River Recovery Drive",
        "location": "Mtkvari River Corridor",
        "description": "Volunteer teams are restoring the river edge with native trees and erosion control planting.",
        "target_trees": 120,
        "status": "open",
        "days_offset": 16,
        "creator_key": "judge_business",
    },
    {
        "title": "School Forest Recovery Day",
        "location": "Vake District School Zone",
        "description": "A school-led planting event focused on shade trees, cleanup, and student participation.",
        "target_trees": 75,
        "status": "ongoing",
        "days_offset": 9,
        "creator_key": "admin",
    },
    {
        "title": "Narikala Terrace Restoration",
        "location": "Old Town / Narikala",
        "description": "Terrace stabilization work paired with native tree planting and follow-up care.",
        "target_trees": 60,
        "status": "open",
        "days_offset": 22,
        "creator_key": "judge_business",
    },
]

TREE_RECORDS = [
    {
        "species": "Oak saplings",
        "quantity": 14,
        "location_notes": "Weekend riverbank cleanup planting near the Vake Park footpath.",
        "days_ago": 4,
        "user_key": "judge_business",
        "campaign_index": 0,
    },
    {
        "species": "Pine saplings",
        "quantity": 9,
        "location_notes": "School volunteer group planting along the district green belt.",
        "days_ago": 6,
        "user_key": "judge_volunteer",
        "campaign_index": 1,
    },
    {
        "species": "Maple saplings",
        "quantity": 6,
        "location_notes": "Terrace edge planting with erosion control on the old city slope.",
        "days_ago": 7,
        "user_key": "judge_sponsor",
        "campaign_index": 2,
    },
]

CUTTING_REPORTS = [
    {
        "description": "Fresh stump and sawdust found beside a courtyard access road after overnight cutting.",
        "location_text": "Vake district courtyard",
        "coords": {"latitude": 41.7312, "longitude": 44.7734},
        "status": "pending",
        "is_anonymous": True,
        "days_ago": 2,
        "user_key": "judge_volunteer",
    },
    {
        "description": "Three damaged pine trunks leaning toward a pedestrian path after strong winds.",
        "location_text": "Saburtalo greenbelt",
        "coords": {"latitude": 41.7541, "longitude": 44.7988},
        "status": "reviewed",
        "is_anonymous": False,
        "days_ago": 4,
        "user_key": "judge_business",
    },
    {
        "description": "Unauthorized trimming reported near the old city slope with visible branch piles.",
        "location_text": "Old Town slope",
        "coords": {"latitude": 41.7171, "longitude": 44.8102},
        "status": "resolved",
        "is_anonymous": False,
        "days_ago": 5,
        "user_key": "judge_sponsor",
    },
]

SUPPORT_DONATIONS = [
    {
        "user_key": "judge_business",
        "category": "plants",
        "donation_item": "plants:oak_saplings",
        "quantity": 30,
        "amount": 150.00,
        "points": 300,
        "note": "Funding a riverbank restocking batch for the spring campaign.",
        "days_ago": 3,
    },
    {
        "user_key": "judge_sponsor",
        "category": "travel",
        "donation_item": "travel:bus_transport",
        "quantity": 1,
        "amount": 48.00,
        "points": 48,
        "note": "Volunteer transport support for hillside restoration work.",
        "days_ago": 6,
    },
]

MERCH_PURCHASES = [
    {
        "user_key": "judge_business",
        "merch_key": "tshirt-green-guard",
        "merch_name": "Green Guard T-Shirt",
        "quantity": 2,
        "payment_mode": "points",
        "amount_usd": 0,
        "points_spent": 180,
        "trees_supported": 2,
        "note": "Team uniforms for a sponsor event booth.",
        "days_ago": 2,
    },
    {
        "user_key": "judge_sponsor",
        "merch_key": "tote-forest",
        "merch_name": "Reforestation Tote Bag",
        "quantity": 1,
        "payment_mode": "money",
        "amount_usd": 18.00,
        "points_spent": 0,
        "trees_supported": 1,
        "note": "Small public-support purchase from the campaign shop.",
        "days_ago": 9,
    },
]

CAMPAIGN_SIGNUPS = [
    {
        "user_key": "judge_volunteer",
        "campaign_index": 0,
        "status": "pending",
        "motivation": "I can help with river cleanup and post-planting follow-up.",
        "days_ago": 1,
    },
    {
        "user_key": "judge_volunteer",
        "campaign_index": 1,
        "status": "approved",
        "motivation": "I want to support the school event and coordinate planting teams.",
        "days_ago": 5,
    },
]

JUDGE_ACCOUNTS = [
    {
        "username": "judge_volunteer",
        "email": "judge_volunteer@example.com",
        "role": "volunteer",
        "password": "JudgeDemo@123",
        "verification_status": "pending",
    },
    {
        "username": "judge_business",
        "email": "judge_business@example.com",
        "role": "business",
        "password": "JudgeDemo@123",
        "verification_status": "pending",
    },
    {
        "username": "judge_sponsor",
        "email": "judge_sponsor@example.com",
        "role": "individual",
        "password": "JudgeDemo@123",
        "verification_status": "approved",
    },
]

JUDGE_ADMIN_ACCOUNT = {
    "username": "judge_admin",
    "email": "judge_admin@example.com",
    "role": "individual",
    "password": "JudgeAdmin@123",
    "verification_status": "approved",
}


def upsert_judge_account(account: dict) -> tuple[User, bool]:
    user = User.query.filter_by(username=account["username"]).first()
    if not user:
        user = User.query.filter_by(email=account["email"]).first()

    created = False
    if not user:
        user = User(username=account["username"], email=account["email"])
        db.session.add(user)
        created = True

    user.username = account["username"]
    user.email = account["email"]
    user.password_hash = generate_password_hash(account["password"])
    user.role = account["role"]
    user.is_admin = False
    user.verification_status = account["verification_status"]
    user.verified_at = (
        datetime.now(timezone.utc)
        if account["verification_status"] == "approved"
        else None
    )
    user.verified_by_id = None
    return user, created


def upsert_judge_admin_account(account: dict) -> tuple[User, bool]:
    user = User.query.filter_by(username=account["username"]).first()
    if not user:
        user = User.query.filter_by(email=account["email"]).first()

    created = False
    if not user:
        user = User(username=account["username"], email=account["email"])
        db.session.add(user)
        created = True

    user.username = account["username"]
    user.email = account["email"]
    user.password_hash = generate_password_hash(account["password"])
    user.role = account["role"]
    user.is_admin = True
    user.verification_status = account["verification_status"]
    user.verified_at = datetime.now(timezone.utc)
    user.verified_by_id = None
    return user, created


def user_by_key(admin: User, judge_users: dict[str, User], user_key: str) -> User:
    if user_key == "admin":
        return admin
    return judge_users[user_key]


def campaign_by_index(campaigns: list[Campaign], index: int) -> Campaign:
    return campaigns[index]


def seed_database():
    rng = random.SystemRandom()

    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            print("❌ Admin user not found!")
            return

        print(f"✅ Found admin user: {admin.username}")

        judge_admin, judge_admin_created = upsert_judge_admin_account(
            JUDGE_ADMIN_ACCOUNT)
        db.session.commit()
        judge_admin_action = "created" if judge_admin_created else "updated"
        print(f"  ✓ {judge_admin.username} (admin) {judge_admin_action}")

        print("\n👥 Ensuring judge demo accounts...")
        judge_users: dict[str, User] = {}
        for account in JUDGE_ACCOUNTS:
            user, created = upsert_judge_account(account)
            db.session.commit()
            judge_users[account["username"]] = user
            action = "created" if created else "updated"
            print(f"  ✓ {user.username} ({user.role}) {action}")

        VolunteerCampaignSignup.query.delete()
        Campaign.query.delete()
        MerchPurchase.query.delete()
        SupportDonation.query.delete()
        TreeRecord.query.delete()
        CuttingReport.query.delete()
        db.session.commit()
        print("🧹 Cleared existing test data")

        print("\n🌱 Adding campaign records...")
        campaigns: list[Campaign] = []
        for i, campaign_data in enumerate(CAMPAIGN_RECORDS):
            creator = user_by_key(admin, judge_users,
                                  campaign_data["creator_key"])
            campaign = Campaign(
                title=campaign_data["title"],
                location=campaign_data["location"],
                event_date=datetime.now(
                    timezone.utc) + timedelta(days=campaign_data["days_offset"]),
                description=campaign_data["description"],
                target_trees=campaign_data["target_trees"],
                status=campaign_data["status"],
                creator_user_id=creator.id,
                created_at=datetime.now(timezone.utc) - timedelta(days=i + 1),
            )
            db.session.add(campaign)
            campaigns.append(campaign)
            print(
                f"  ✓ Campaign: {campaign_data['title']} ({campaign_data['status']})")

        db.session.commit()

        print("\n🌳 Adding realistic planting records...")
        for i, tree_data in enumerate(TREE_RECORDS):
            location = TBILISI_LOCATIONS[i % len(TBILISI_LOCATIONS)]
            tree = TreeRecord(
                species=tree_data["species"],
                quantity=tree_data["quantity"],
                latitude=location["latitude"],
                longitude=location["longitude"],
                location_notes=tree_data["location_notes"],
                image_filename=rng.choice(PLANTING_IMAGES),
                user_id=user_by_key(admin, judge_users,
                                    tree_data["user_key"]).id,
                campaign_id=campaign_by_index(
                    campaigns, tree_data["campaign_index"]).id,
                created_at=datetime.now(
                    timezone.utc) - timedelta(days=tree_data["days_ago"], hours=i),
            )
            db.session.add(tree)
            print(
                f"  ✓ {tree_data['quantity']} {tree_data['species']} at {location['name']}")

        db.session.commit()

        print("\n⚠️  Adding realistic cutting reports...")
        for i, report_data in enumerate(CUTTING_REPORTS):
            report = CuttingReport(
                description=report_data["description"],
                latitude=report_data["coords"]["latitude"],
                longitude=report_data["coords"]["longitude"],
                location_text=report_data["location_text"],
                image_filename=rng.choice(CUTTING_IMAGES),
                is_anonymous=report_data["is_anonymous"],
                status=report_data["status"],
                user_id=user_by_key(admin, judge_users,
                                    report_data["user_key"]).id,
                created_at=datetime.now(
                    timezone.utc) - timedelta(days=report_data["days_ago"], hours=i),
            )
            db.session.add(report)
            print(f"  ✓ Report: {report_data['description'][:50]}...")

        db.session.commit()

        print("\n💰 Adding sponsor donations...")
        for i, donation_data in enumerate(SUPPORT_DONATIONS):
            donation = SupportDonation(
                category=donation_data["category"],
                donation_item=donation_data["donation_item"],
                quantity=donation_data["quantity"],
                amount=donation_data["amount"],
                points=donation_data["points"],
                note=donation_data["note"],
                user_id=user_by_key(admin, judge_users,
                                    donation_data["user_key"]).id,
                created_at=datetime.now(
                    timezone.utc) - timedelta(days=donation_data["days_ago"], hours=i),
            )
            db.session.add(donation)
            print(
                f"  ✓ Donation: {donation_data['donation_item']} ${donation_data['amount']:.2f}")

        print("\n🛍️  Adding merch purchases...")
        for i, purchase_data in enumerate(MERCH_PURCHASES):
            purchase = MerchPurchase(
                merch_key=purchase_data["merch_key"],
                merch_name=purchase_data["merch_name"],
                quantity=purchase_data["quantity"],
                payment_mode=purchase_data["payment_mode"],
                amount_usd=purchase_data["amount_usd"],
                points_spent=purchase_data["points_spent"],
                trees_supported=purchase_data["trees_supported"],
                note=purchase_data["note"],
                user_id=user_by_key(admin, judge_users,
                                    purchase_data["user_key"]).id,
                created_at=datetime.now(
                    timezone.utc) - timedelta(days=purchase_data["days_ago"], hours=i),
            )
            db.session.add(purchase)
            print(
                f"  ✓ Purchase: {purchase_data['merch_name']} x{purchase_data['quantity']}")

        print("\n🤝 Adding campaign signups...")
        for i, signup_data in enumerate(CAMPAIGN_SIGNUPS):
            signup = VolunteerCampaignSignup(
                user_id=user_by_key(admin, judge_users,
                                    signup_data["user_key"]).id,
                campaign_id=campaign_by_index(
                    campaigns, signup_data["campaign_index"]).id,
                motivation=signup_data["motivation"],
                status=signup_data["status"],
                created_at=datetime.now(
                    timezone.utc) - timedelta(days=signup_data["days_ago"], hours=i),
            )
            db.session.add(signup)
            print(
                f"  ✓ Signup: {signup_data['status']} for campaign #{signup_data['campaign_index'] + 1}")

        db.session.commit()

        tree_count = TreeRecord.query.count()
        report_count = CuttingReport.query.count()
        campaign_count = Campaign.query.count()
        donation_count = SupportDonation.query.count()
        merch_count = MerchPurchase.query.count()
        signup_count = VolunteerCampaignSignup.query.count()
        total_trees = db.session.query(
            db.func.sum(TreeRecord.quantity)).scalar() or 0

        total_content_records = (
            tree_count + report_count + campaign_count +
            donation_count + merch_count + signup_count
        )

        print("\n📊 Database seeding complete!")
        print(f"  Campaigns: {campaign_count}")
        print(f"  Trees records: {tree_count}")
        print(f"  Total trees planted: {total_trees}")
        print(f"  Cutting reports: {report_count}")
        print(f"  Donations: {donation_count}")
        print(f"  Merch purchases: {merch_count}")
        print(f"  Campaign signups: {signup_count}")
        print(f"  Total content records: {total_content_records}")
        print(f"\n✨ All test data added for Tbilisi, Georgia!")


if __name__ == "__main__":
    seed_database()
