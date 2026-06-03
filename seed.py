"""
seed.py – Run once to populate the database with initial data.

Usage:
    python seed.py
"""
from app import create_app, db, bcrypt
from app.models import Villa, Amenity, User, AmenityType, UserRole


def seed():
    app = create_app("development")
    with app.app_context():
        db.create_all()

        # ── 100 Villas ────────────────────────────────────────────────────
        if Villa.query.count() == 0:
            blocks = ["A", "B", "C", "D"]
            count = 0
            for block in blocks:
                for num in range(1, 26):   # 4 blocks × 25 = 100 villas
                    count += 1
                    v = Villa(
                        villa_number=f"{block}-{num:03d}",
                        block=block,
                        floor=0,
                        bedrooms=3,
                        area_sqft=2200.0,
                        is_occupied=False,
                    )
                    db.session.add(v)
            db.session.commit()
            print(f"✅  Created {count} villas")
        else:
            print("⏭️  Villas already seeded")

        # ── Amenities ─────────────────────────────────────────────────────
        if Amenity.query.count() == 0:
            amenities = [
                Amenity(
                    name="Tennis Court 1",
                    amenity_type=AmenityType.TENNIS_COURT,
                    description="Full-size hard court with floodlights",
                    capacity=4,
                    slot_duration_minutes=60,
                    open_time="06:00",
                    close_time="22:00",
                    rules="Proper tennis shoes required. Max 4 players per slot.",
                ),
                Amenity(
                    name="Tennis Court 2",
                    amenity_type=AmenityType.TENNIS_COURT,
                    description="Full-size clay court",
                    capacity=4,
                    slot_duration_minutes=60,
                    open_time="06:00",
                    close_time="21:00",
                    rules="Clay court – no hard-soled shoes.",
                ),
                Amenity(
                    name="Swimming Pool",
                    amenity_type=AmenityType.SWIMMING_POOL,
                    description="Olympic-length pool with lane dividers. Separate kids' pool.",
                    capacity=20,
                    slot_duration_minutes=60,
                    open_time="06:00",
                    close_time="21:00",
                    rules="Swimming attire mandatory. No food inside pool area.",
                ),
                Amenity(
                    name="Clubhouse",
                    amenity_type=AmenityType.CLUBHOUSE,
                    description="Multi-purpose hall for events and gatherings",
                    capacity=100,
                    slot_duration_minutes=120,
                    open_time="08:00",
                    close_time="23:00",
                    rules="Advance booking required. Cleaning deposit applies.",
                ),
            ]
            for a in amenities:
                db.session.add(a)
            db.session.commit()
            print(f"✅  Created {len(amenities)} amenities")
        else:
            print("⏭️  Amenities already seeded")

        # ── Admin User ────────────────────────────────────────────────────
        if not User.query.filter_by(email="admin@villacommunity.com").first():
            admin = User(
                name="Community Admin",
                email="admin@villacommunity.com",
                phone="9999999999",
                password_hash=bcrypt.generate_password_hash("Admin@1234").decode("utf-8"),
                role=UserRole.ADMIN,
                villa_id=None,
                is_active=True,
            )
            db.session.add(admin)
            db.session.commit()
            print("✅  Admin user created  →  admin@villacommunity.com / Admin@1234")
        else:
            print("⏭️  Admin user already exists")

        # ── Security Guard ────────────────────────────────────────────────
        if not User.query.filter_by(email="security@villacommunity.com").first():
            guard = User(
                name="Gate Security",
                email="security@villacommunity.com",
                phone="8888888888",
                password_hash=bcrypt.generate_password_hash("Guard@1234").decode("utf-8"),
                role=UserRole.SECURITY,
                is_active=True,
            )
            db.session.add(guard)
            db.session.commit()
            print("✅  Security user created  →  security@villacommunity.com / Guard@1234")
        else:
            print("⏭️  Security user already exists")

        print("\n🏘️  Database seeded successfully!")


if __name__ == "__main__":
    seed()
