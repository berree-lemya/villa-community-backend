# 🏘️ Villa Community – Backend API

A Flask REST API for a gated apartment/villa community with 100 villas.

## Features
- 🔐 JWT Authentication (Login / Register / Refresh / Logout)
- 🎾 Amenity Booking (Tennis Courts, Swimming Pool, Clubhouse)
- 🔧 Maintenance Requests (Electrician, Plumber, Carpenter)
- 🚪 Gate Access Management (Visitors, Maids, Deliveries)
- 🔔 In-app Notifications
- 👑 Admin Dashboard with Stats

---

## ⚡ Quick Start

```bash
# 1. Clone / open in VS Code
cd villa_community

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env          # Edit SECRET_KEY and JWT_SECRET_KEY

# 5. Seed database (creates 100 villas, amenities, admin user)
python seed.py

# 6. Start the server
python run.py
```

Server starts at: **http://localhost:5000**

---

## 🔑 Default Credentials (after seed)

| Role     | Email                          | Password    |
|----------|-------------------------------|-------------|
| Admin    | admin@villacommunity.com      | Admin@1234  |
| Security | security@villacommunity.com   | Guard@1234  |

---

## 📡 API Endpoints

### Auth  `/api/auth`
| Method | Endpoint            | Description              | Auth |
|--------|---------------------|--------------------------|------|
| POST   | `/register`         | Register owner/tenant    | ❌   |
| POST   | `/login`            | Login → get tokens       | ❌   |
| POST   | `/refresh`          | Get new access token     | Refresh token |
| DELETE | `/logout`           | Revoke access token      | ✅   |
| GET    | `/me`               | Get current user info    | ✅   |
| PUT    | `/change-password`  | Change password          | ✅   |

**Login Request:**
```json
{ "email": "user@example.com", "password": "Pass@1234" }
```

**Login Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": { "id": 1, "name": "John", "role": "owner", "villa_number": "A-001" }
}
```

---

### Bookings  `/api/bookings`
| Method | Endpoint                                | Description                   | Role      |
|--------|-----------------------------------------|-------------------------------|-----------|
| GET    | `/amenities`                            | List all amenities            | Any       |
| GET    | `/amenities/<id>/availability?date=`    | Check booked slots on a date  | Any       |
| POST   | `/`                                     | Create booking                | Resident  |
| GET    | `/my`                                   | My bookings                   | Resident  |
| GET    | `/<id>`                                 | Get booking detail            | Owner/Admin |
| PUT    | `/<id>/cancel`                          | Cancel booking                | Owner/Admin |
| GET    | `/all`                                  | All bookings                  | Admin     |

**Create Booking Request:**
```json
{
  "amenity_id": 1,
  "booking_date": "2026-06-15",
  "start_time": "08:00",
  "end_time": "09:00",
  "num_guests": 2,
  "notes": "Bringing rackets"
}
```

---

### Maintenance  `/api/maintenance`
| Method | Endpoint          | Description                     | Role      |
|--------|-------------------|---------------------------------|-----------|
| POST   | `/`               | Submit request                  | Resident  |
| GET    | `/my`             | My requests                     | Resident  |
| GET    | `/<id>`           | Get request detail              | Owner/Admin |
| PUT    | `/<id>`           | Update request (if OPEN)        | Owner/Admin |
| PUT    | `/<id>/cancel`    | Cancel request                  | Owner/Admin |
| PUT    | `/<id>/rate`      | Rate resolved request (1–5)     | Owner     |
| GET    | `/all`            | All requests                    | Admin     |
| PUT    | `/<id>/assign`    | Assign technician               | Admin     |
| PUT    | `/<id>/resolve`   | Mark as resolved                | Admin     |

**Categories:** `electrician` · `plumber` · `carpenter` · `other`  
**Priorities:** `low` · `normal` · `high` · `urgent`

**Submit Request:**
```json
{
  "category": "plumber",
  "title": "Leaking tap in kitchen",
  "description": "The kitchen tap has been leaking since yesterday",
  "priority": "high",
  "preferred_date": "2026-06-10",
  "preferred_time_slot": "morning"
}
```

---

### Gate Access  `/api/gate`
| Method | Endpoint              | Description                    | Role          |
|--------|-----------------------|--------------------------------|---------------|
| POST   | `/`                   | Create gate pass               | Resident      |
| GET    | `/my`                 | My gate passes                 | Resident      |
| GET    | `/<id>`               | Pass detail                    | Owner/Security|
| PUT    | `/<id>/revoke`        | Revoke pass                    | Owner/Admin   |
| GET    | `/verify/<pass_code>` | Verify pass code at gate       | Security      |
| PUT    | `/<id>/checkin`       | Check in visitor               | Security      |
| PUT    | `/<id>/checkout`      | Check out visitor              | Security      |
| GET    | `/active`             | All active passes              | Security      |
| GET    | `/all`                | All passes with filters        | Admin         |

**Pass Types:** `visitor` · `maid` · `delivery` · `contractor`

**Create Gate Pass:**
```json
{
  "pass_type": "visitor",
  "visitor_name": "Rajesh Kumar",
  "visitor_phone": "9876543210",
  "visitor_vehicle": "TN01AB1234",
  "purpose": "Birthday party",
  "valid_from": "2026-06-15T18:00:00",
  "valid_until": "2026-06-15T23:00:00"
}
```

**Maid (recurring) pass:**
```json
{
  "pass_type": "maid",
  "visitor_name": "Meena",
  "valid_from": "2026-06-01T07:00:00",
  "valid_until": "2026-12-31T10:00:00",
  "is_recurring": true,
  "recurring_days": "Mon,Tue,Wed,Thu,Fri,Sat"
}
```

---

### Users  `/api/users`
| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| GET    | `/profile`                        | Get own profile          |
| PUT    | `/profile`                        | Update own profile       |
| GET    | `/notifications`                  | Get notifications        |
| PUT    | `/notifications/<id>/read`        | Mark one as read         |
| PUT    | `/notifications/read-all`         | Mark all as read         |

---

### Admin  `/api/admin`
| Method | Endpoint                          | Description                |
|--------|-----------------------------------|----------------------------|
| GET    | `/stats`                          | Dashboard statistics       |
| GET    | `/users`                          | List all users             |
| POST   | `/users`                          | Create any user/role       |
| GET    | `/users/<id>`                     | Get user detail            |
| PUT    | `/users/<id>/deactivate`          | Deactivate user            |
| PUT    | `/users/<id>/activate`            | Activate user              |
| PUT    | `/users/<id>/assign-villa`        | Assign villa to user       |

---

### Villas  `/api/villas`
| Method | Endpoint    | Description        |
|--------|-------------|--------------------|
| GET    | `/`         | List all villas    |
| GET    | `/<id>`     | Get villa detail   |
| POST   | `/`         | Create villa       |

---

## 🗂️ Project Structure

```
villa_community/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Dev / Prod / Test configs
│   ├── models/
│   │   └── __init__.py      # All SQLAlchemy models
│   ├── routes/
│   │   ├── auth.py          # Login, register, JWT
│   │   ├── bookings.py      # Amenity bookings
│   │   ├── maintenance.py   # Maintenance requests
│   │   ├── gate_access.py   # Gate passes
│   │   ├── users.py         # Profile & notifications
│   │   ├── villas.py        # Villa management
│   │   └── admin.py         # Admin panel routes
│   └── utils.py             # Role decorators
├── instance/                # SQLite DB lives here
├── seed.py                  # Database seed script
├── run.py                   # Entry point
├── requirements.txt
└── .env.example
```

---

## 🔒 Authentication

All protected routes require the header:
```
Authorization: Bearer <access_token>
```

Roles: `owner` · `tenant` · `admin` · `security`

---

## 🚀 Production Notes

1. Replace SQLite with **PostgreSQL**: set `DATABASE_URL` in `.env`
2. Run migrations: `flask db init && flask db migrate && flask db upgrade`
3. Use **Redis** for JWT blocklist (replace the in-memory set in `auth.py`)
4. Use **gunicorn** as the WSGI server: `gunicorn "app:create_app()" -w 4`
