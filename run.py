from app import create_app, db
from flask_bcrypt import Bcrypt

app = create_app()

with app.app_context():
    db.create_all()
    from app.models import User
    bcrypt = Bcrypt(app)
    existing = User.query.filter_by(email="admin@villa.com").first()
    if not existing:
        hashed = bcrypt.generate_password_hash("admin123").decode("utf-8")
        admin = User(
            name="Admin User",
            email="admin@villa.com",
            phone="9000000000",
            password_hash=hashed,
            role="admin",
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin created!")
    else:
        print("Admin already exists!")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)