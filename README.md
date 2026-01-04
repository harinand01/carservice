# Car Service and Booking System (Pure Python)

Implements the main DFD customer functions:

- Manage profile & vehicles
- Browse services & time slots
- Book a service
- Track booking status
- Give feedback & rating

Plus admin functions:

- Manage services (D3)
- Manage time slots (D4)

## 1. Requirements

- Python 3.8+
- MySQL server
- Libraries:

```bash
pip install mysql-connector-python jinja2
```

## 2. Database Setup

1. Create database:

```sql
CREATE DATABASE car_service_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. From **CMD** (not PowerShell), run:

```cmd
cd path\to\car_service_booking
mysql -u root -p car_service_db < sql\schema.sql
```

This creates all tables and adds:

- Admin email: `admin@example.com`
- Admin password: `admin123`

3. Edit `server/db.py` if your MySQL password is not empty:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_PASSWORD_HERE",
    "database": "car_service_db",
}
```

## 3. Run the Server

From project root:

```bash
python -m server.app
```

Open:

- Home: <http://localhost:8000>
- Login: <http://localhost:8000/login>
- Register: <http://localhost:8000/register>

## 4. Usage Flow (Customer)

1. Register as Customer
2. Login
3. Open **Profile** → fill details (D1 Customers)
4. Open **Vehicles** → add vehicle(s) (D2 Vehicles)
5. Admin logs in as `admin@example.com` → adds services & time slots
6. Customer:
   - Open **Services** → view services (D3)
   - Open **Book** → select vehicle + service + slot → create booking (D5)
   - Open **My Bookings** → track status (D5)
   - After admin/mechanic sets status to COMPLETED/DELIVERED (future extension), use **Feedback** to submit rating (D6)

This gives you a working prototype that matches your Level-1 DFD for the customer side.
