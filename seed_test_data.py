from app import app
from extensions import db
from models import User, TreeRecord, CuttingReport
from datetime import datetime, timedelta, timezone

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

TREE_SPECIES = [
    ("Oak", 3),
    ("Pine", 5),
    ("Birch", 2),
    ("Walnut", 4),
    ("Maple", 3),
    ("Ash", 2),
]


def seed_database():
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            print("❌ Admin user not found!")
            return

        print(f"✅ Found admin user: {admin.username}")

        TreeRecord.query.delete()
        CuttingReport.query.delete()
        db.session.commit()
        print("🧹 Cleared existing test data")

        print("\n🌳 Adding test trees...")
        for i, (species, quantity) in enumerate(TREE_SPECIES):
            location = TBILISI_LOCATIONS[i % len(TBILISI_LOCATIONS)]
            tree = TreeRecord(
                species=species,
                quantity=quantity,
                latitude=location["latitude"],
                longitude=location["longitude"],
                location_notes=f"Planted in {location['name']}, Tbilisi",
                user_id=admin.id,
                created_at=datetime.now(timezone.utc) - timedelta(days=i),
            )
            db.session.add(tree)
            print(f"  ✓ {quantity} {species} trees at {location['name']}")

        db.session.commit()

        print("\n⚠️  Adding test cutting reports...")
        test_reports = [
            {
                "description": "Dead pine tree blocking pathway near Metekhi",
                "location_text": "Metekhi area",
                "coords": {"latitude": 41.7167, "longitude": 44.8089},
            },
            {
                "description": "Large oak needs trimming, safety hazard",
                "location_text": "Vake District",
                "coords": {"latitude": 41.7318, "longitude": 44.7681},
            },
            {
                "description": "Damaged walnut tree after storm",
                "location_text": "Old Town",
                "coords": {"latitude": 41.7167, "longitude": 44.8089},
            },
            {
                "description": "Illegal cutting in Botanical Garden area",
                "location_text": "Botanical Garden",
                "coords": {"latitude": 41.7089, "longitude": 44.7825},
            },
            {
                "description": "Hurricane-damaged trees near river",
                "location_text": "Mtkvari River",
                "coords": {"latitude": 41.7151, "longitude": 44.8271},
            },
        ]

        for i, report_data in enumerate(test_reports):
            report = CuttingReport(
                description=report_data["description"],
                latitude=report_data["coords"]["latitude"],
                longitude=report_data["coords"]["longitude"],
                location_text=report_data["location_text"],
                status="pending" if i % 2 == 0 else "reviewed",
                user_id=admin.id,
                created_at=datetime.now(timezone.utc) - timedelta(days=i),
            )
            db.session.add(report)
            print(f"  ✓ Report: {report_data['description'][:50]}...")

        db.session.commit()

        tree_count = TreeRecord.query.count()
        report_count = CuttingReport.query.count()
        total_trees = db.session.query(
            db.func.sum(TreeRecord.quantity)).scalar() or 0

        print("\n📊 Database seeding complete!")
        print(f"  Trees records: {tree_count}")
        print(f"  Total trees planted: {total_trees}")
        print(f"  Cutting reports: {report_count}")
        print(f"\n✨ All test data added for Tbilisi, Georgia!")


if __name__ == "__main__":
    seed_database()
