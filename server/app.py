"""Main WSGI application for Car Service and Booking System.

Run with:
    python -m server.app
Then open http://localhost:8000
"""

from wsgiref.simple_server import make_server
import os
import mimetypes
import http.cookies as Cookie

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import auth, db

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)


def render_template(name, **context):
    template = env.get_template(name)
    return template.render(**context).encode("utf-8")


def redirect(start_response, location):
    start_response("302 Found", [("Location", location)])
    return [b""]


def serve_static(environ, start_response, rel_path):
    file_path = os.path.join(STATIC_DIR, rel_path.lstrip("/"))
    if not os.path.isfile(file_path):
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"File not found"]

    ctype, _ = mimetypes.guess_type(file_path)
    ctype = ctype or "application/octet-stream"
    start_response("200 OK", [("Content-Type", ctype)])
    with open(file_path, "rb") as f:
        return [f.read()]


def home(environ, start_response, session):
    body = render_template("index.html", session=session)
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def login_page(environ, start_response, session):
    if environ["REQUEST_METHOD"] == "GET":
        body = render_template("login.html", error=None, session=session)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    else:
        form = auth.parse_post(environ)
        email = form.get("email", "").strip()
        password = form.get("password", "").strip()

        user = auth.login_user(email, password)
        if not user:
            body = render_template("login.html", error="Invalid email or password", session=session)
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [body]

        session_id = auth.create_session(user)
        headers = [("Content-Type", "text/html; charset=utf-8")]
        cookie = Cookie.SimpleCookie()
        cookie["session_id"] = session_id
        cookie["session_id"]["path"] = "/"
        headers.append(("Set-Cookie", cookie.output(header="")))
        start_response("302 Found", headers + [("Location", "/dashboard")])
        return [b""]


def logout(environ, start_response, session):
    headers = [("Content-Type", "text/html; charset=utf-8")]
    auth.destroy_session(environ, headers)
    start_response("302 Found", headers + [("Location", "/")])
    return [b""]


def register_page(environ, start_response, session):
    if environ["REQUEST_METHOD"] == "GET":
        body = render_template("register.html", error=None, session=session)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    else:
        form = auth.parse_post(environ)
        full_name = form.get("full_name", "").strip()
        email = form.get("email", "").strip()
        phone = form.get("phone", "").strip()
        address = form.get("address", "").strip()
        city = form.get("city", "").strip()
        password = form.get("password", "").strip()
        confirm = form.get("confirm_password", "").strip()

        if password != confirm:
            body = render_template("register.html", error="Passwords do not match", session=session)
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [body]

        customer_id, err = auth.register_customer(full_name, email, phone, address, city, password)
        if err:
            body = render_template("register.html", error=err, session=session)
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [body]

        return redirect(start_response, "/login")


def dashboard(environ, start_response, session):
    if not session:
        return redirect(start_response, "/login")

    role = session.get("role")
    user_id = session.get("user_id")

    if role == "ADMIN":
        stats = {
            "customers": db.query_one("SELECT COUNT(*) AS c FROM customers") or {"c": 0},
            "mechanics": db.query_one("SELECT COUNT(*) AS c FROM mechanics") or {"c": 0},
            "vehicles": db.query_one("SELECT COUNT(*) AS c FROM vehicles") or {"c": 0},
            "bookings": db.query_one("SELECT COUNT(*) AS c FROM bookings") or {"c": 0},
        }
        body = render_template("admin_dashboard.html", session=session, stats=stats)
    elif role == "CUSTOMER":
        sql = """SELECT b.*, s.service_name, v.vehicle_number
                 FROM bookings b
                 JOIN services s ON b.service_id = s.service_id
                 JOIN vehicles v ON b.vehicle_id = v.vehicle_id
                 JOIN customers c ON b.customer_id = c.customer_id
                 WHERE c.user_id=%s
                 ORDER BY b.booking_date DESC"""
        bookings = db.query_all(sql, (user_id,))
        body = render_template("customer_dashboard.html", session=session, bookings=bookings)
    elif role == "MECHANIC":
        sql = """SELECT b.*, s.service_name, v.vehicle_number
                 FROM bookings b
                 JOIN services s ON b.service_id = s.service_id
                 JOIN vehicles v ON b.vehicle_id = v.vehicle_id
                 JOIN mechanics m ON b.assigned_mechanic_id = m.mechanic_id
                 WHERE m.user_id=%s
                 ORDER BY b.booking_date DESC"""
        tasks = db.query_all(sql, (user_id,))
        body = render_template("mechanic_dashboard.html", session=session, tasks=tasks)
    else:
        body = b"Unknown role"

    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


# ---------- ADMIN VIEWS ----------

def admin_services(environ, start_response, session):
    if not session or session.get("role") != "ADMIN":
        return redirect(start_response, "/login")

    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        name = form.get("service_name", "").strip()
        price = form.get("base_price", "0").strip()
        desc = form.get("description", "").strip()
        duration = form.get("estimated_duration", "").strip() or None

        if name:
            try:
                db.execute(
                    "INSERT INTO services (service_name, description, base_price, estimated_duration, is_active) VALUES (%s,%s,%s,%s,1)",
                    (name, desc, price, duration),
                )
            except Exception as e:
                print("[ADMIN SERVICES] Error:", e)

    services = db.query_all("SELECT * FROM services ORDER BY service_id DESC")
    body = render_template("admin_services.html", session=session, services=services)
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def admin_slots(environ, start_response, session):
    if not session or session.get("role") != "ADMIN":
        return redirect(start_response, "/login")

    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        slot_date = form.get("slot_date", "").strip()
        start_time = form.get("start_time", "").strip()
        end_time = form.get("end_time", "").strip()
        max_bookings = form.get("max_bookings", "1").strip() or "1"

        if slot_date and start_time and end_time:
            try:
                db.execute(
                    "INSERT INTO time_slots (slot_date, start_time, end_time, max_bookings) VALUES (%s,%s,%s,%s)",
                    (slot_date, start_time, end_time, max_bookings),
                )
            except Exception as e:
                print("[ADMIN SLOTS] Error:", e)

    slots = db.query_all("SELECT * FROM time_slots ORDER BY slot_date, start_time")
    body = render_template("admin_slots.html", session=session, slots=slots)
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]

def admin_bookings(environ, start_response, session):
    if not session or session.get("role") != "ADMIN":
        return redirect(start_response, "/login")

    # Handle status / mechanic update
    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        booking_id = form.get("booking_id")
        status = form.get("status")
        mechanic_id = form.get("mechanic_id")

        if mechanic_id:
            db.execute(
                "UPDATE bookings SET assigned_mechanic_id=%s WHERE booking_id=%s",
                (mechanic_id, booking_id),
            )

        if status:
            db.execute(
                "UPDATE bookings SET current_status=%s WHERE booking_id=%s",
                (status, booking_id),
            )

    sql = """
        SELECT b.*, s.service_name, v.vehicle_number, c.full_name AS customer_name,
               t.slot_date, t.start_time, t.end_time,
               m.full_name AS mechanic_name
        FROM bookings b
        JOIN services s ON b.service_id = s.service_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN time_slots t ON b.slot_id = t.slot_id
        LEFT JOIN mechanics m ON b.assigned_mechanic_id = m.mechanic_id
        ORDER BY b.booking_date DESC
    """
    bookings = db.query_all(sql)
    mechanics = db.query_all("SELECT mechanic_id, full_name FROM mechanics")

    body = render_template(
        "admin_bookings.html",
        session=session,
        bookings=bookings,
        mechanics=mechanics,
    )
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]

def admin_mechanics(environ, start_response, session):
    if not session or session.get("role") != "ADMIN":
        return redirect(start_response, "/login")

    message = None

    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        action = form.get("action", "add")

        if action == "add":
            full_name = form.get("full_name", "").strip()
            email = form.get("email", "").strip()
            phone = form.get("phone", "").strip()
            specialization = form.get("specialization", "").strip()
            password = form.get("password", "").strip()

            if full_name and email and phone and password:
                # Check duplicate email
                existing = db.query_one(
                    "SELECT user_id FROM users WHERE email=%s", (email,)
                )
                if existing:
                    message = "Email already exists."
                else:
                    pwd_hash = auth.hash_password(password)
                    user_id = db.execute(
                        "INSERT INTO users (email, password_hash, role) VALUES (%s,%s,'MECHANIC')",
                        (email, pwd_hash),
                    )
                    db.execute(
                        "INSERT INTO mechanics (user_id, full_name, phone, specialization, is_active) VALUES (%s,%s,%s,%s,1)",
                        (user_id, full_name, phone, specialization),
                    )
                    message = "Mechanic added."
            else:
                message = "Please fill all required fields."

        elif action == "toggle":
            mechanic_id = form.get("mechanic_id")
            new_status = form.get("new_status")
            if mechanic_id and new_status is not None:
                db.execute(
                    "UPDATE mechanics SET is_active=%s WHERE mechanic_id=%s",
                    (new_status, mechanic_id),
                )
                message = "Status updated."

    mechanics = db.query_all(
        "SELECT m.*, u.email FROM mechanics m JOIN users u ON m.user_id=u.user_id ORDER BY m.mechanic_id DESC"
    )

    body = render_template(
        "admin_mechanics.html",
        session=session,
        mechanics=mechanics,
        message=message,
    )
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]

def admin_payments(environ, start_response, session):
    if not session or session.get("role") != "ADMIN":
        return redirect(start_response, "/login")

    message = None

    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        booking_id = form.get("booking_id")
        amount = form.get("amount")
        mode = form.get("payment_mode")
        status = form.get("payment_status")
        txref = form.get("transaction_ref", "").strip()

        if booking_id and amount and mode and status:
            db.execute(
                "INSERT INTO payments (booking_id, amount, payment_mode, payment_status, transaction_ref) VALUES (%s,%s,%s,%s,%s)",
                (booking_id, amount, mode, status, txref),
            )
            message = "Payment recorded."
        else:
            message = "Please fill all required fields."

    payments = db.query_all(
        """
        SELECT p.*, c.full_name AS customer_name, s.service_name, b.booking_date
        FROM payments p
        JOIN bookings b ON p.booking_id = b.booking_id
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN services s ON b.service_id = s.service_id
        ORDER BY p.payment_date DESC
        """
    )

    bookings = db.query_all(
        """
        SELECT b.booking_id, c.full_name AS customer_name, s.service_name
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN services s ON b.service_id = s.service_id
        ORDER BY b.booking_id DESC
        """
    )

    body = render_template(
        "admin_payments.html",
        session=session,
        payments=payments,
        bookings=bookings,
        message=message,
    )
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]
def admin_feedback(environ, start_response, session):
    if not session or session.get("role") != "ADMIN":
        return redirect(start_response, "/login")

    sql = """
        SELECT f.*, c.full_name AS customer_name,
               s.service_name, b.booking_date
        FROM feedback f
        JOIN bookings b ON f.booking_id = b.booking_id
        JOIN customers c ON f.customer_id = c.customer_id
        JOIN services s ON b.service_id = s.service_id
        ORDER BY f.created_at DESC
    """
    feedback_list = db.query_all(sql)

    body = render_template(
        "admin_feedback.html",
        session=session,
        feedback_list=feedback_list,
    )
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]





# ---------- CUSTOMER VIEWS ----------

def customer_profile(environ, start_response, session):
    if not session or session.get("role") != "CUSTOMER":
        return redirect(start_response, "/login")

    user_id = session["user_id"]
    customer = db.query_one("SELECT * FROM customers WHERE user_id=%s", (user_id,))

    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        full_name = form.get("full_name", "").strip()
        phone = form.get("phone", "").strip()
        address = form.get("address", "").strip()
        city = form.get("city", "").strip()
        if customer:
            db.execute(
                "UPDATE customers SET full_name=%s, phone=%s, address=%s, city=%s WHERE customer_id=%s",
                (full_name, phone, address, city, customer["customer_id"]),
            )
        customer = db.query_one("SELECT * FROM customers WHERE user_id=%s", (user_id,))

    body = render_template("customer_profile.html", session=session, customer=customer)
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def customer_vehicles(environ, start_response, session):
    if not session or session.get("role") != "CUSTOMER":
        return redirect(start_response, "/login")

    user_id = session["user_id"]
    customer = db.query_one("SELECT * FROM customers WHERE user_id=%s", (user_id,))
    customer_id = customer["customer_id"] if customer else None

    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        action = form.get("action", "add")
        if action == "add":
            vehicle_number = form.get("vehicle_number", "").strip()
            brand = form.get("brand", "").strip()
            model = form.get("model", "").strip()
            fuel_type = form.get("fuel_type", "").strip() or "PETROL"
            year = form.get("manufacture_year", "").strip() or None
            color = form.get("color", "").strip() or None
            if vehicle_number and customer_id:
                try:
                    db.execute(
                        """INSERT INTO vehicles
                            (customer_id, vehicle_number, brand, model, fuel_type, manufacture_year, color)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (customer_id, vehicle_number, brand, model, fuel_type, year, color),
                    )
                except Exception as e:
                    print("[CUSTOMER VEHICLES] Error:", e)
        elif action == "delete":
            vid = form.get("vehicle_id", "")
            if vid:
                db.execute("DELETE FROM vehicles WHERE vehicle_id=%s AND customer_id=%s", (vid, customer_id))

    vehicles = db.query_all("SELECT * FROM vehicles WHERE customer_id=%s ORDER BY vehicle_id DESC", (customer_id,))
    body = render_template("customer_vehicles.html", session=session, vehicles=vehicles)
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def customer_services(environ, start_response, session):
    if not session or session.get("role") != "CUSTOMER":
        return redirect(start_response, "/login")
    services = db.query_all("SELECT * FROM services WHERE is_active=1 ORDER BY service_name")
    body = render_template("customer_services.html", session=session, services=services)
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def customer_book(environ, start_response, session):
    if not session or session.get("role") != "CUSTOMER":
        return redirect(start_response, "/login")

    user_id = session["user_id"]
    customer = db.query_one("SELECT * FROM customers WHERE user_id=%s", (user_id,))
    customer_id = customer["customer_id"] if customer else None

    services = db.query_all("SELECT * FROM services WHERE is_active=1 ORDER BY service_name")
    vehicles = db.query_all("SELECT * FROM vehicles WHERE customer_id=%s ORDER BY vehicle_id", (customer_id,))
    slots = db.query_all("SELECT * FROM time_slots ORDER BY slot_date, start_time")

    message = None

    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        service_id = form.get("service_id", "")
        vehicle_id = form.get("vehicle_id", "")
        slot_id = form.get("slot_id", "")

        if not (service_id and vehicle_id and slot_id and customer_id):
            message = "Please select service, vehicle and time slot."
        else:
            # Check simple availability: count bookings for that slot
            count_row = db.query_one(
                "SELECT COUNT(*) AS c FROM bookings WHERE slot_id=%s",
                (slot_id,),
            )
            max_row = db.query_one("SELECT max_bookings FROM time_slots WHERE slot_id=%s", (slot_id,))
            if not max_row:
                message = "Invalid slot."
            else:
                max_bookings = max_row["max_bookings"]
                current = count_row["c"] if count_row else 0
                if current >= max_bookings:
                    message = "Selected slot is full. Please choose another."
                else:
                    db.execute(
                        """INSERT INTO bookings
                            (customer_id, vehicle_id, service_id, slot_id, current_status)
                            VALUES (%s,%s,%s,%s,'BOOKED')""",
                        (customer_id, vehicle_id, service_id, slot_id),
                    )
                    message = "Booking created successfully!"

    body = render_template(
        "customer_book.html",
        session=session,
        services=services,
        vehicles=vehicles,
        slots=slots,
        message=message,
    )
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def customer_bookings(environ, start_response, session):
    if not session or session.get("role") != "CUSTOMER":
        return redirect(start_response, "/login")
    user_id = session["user_id"]
    sql = """SELECT b.*, s.service_name, v.vehicle_number, t.slot_date, t.start_time, t.end_time
             FROM bookings b
             JOIN services s ON b.service_id = s.service_id
             JOIN vehicles v ON b.vehicle_id = v.vehicle_id
             JOIN customers c ON b.customer_id = c.customer_id
             JOIN time_slots t ON b.slot_id = t.slot_id
             WHERE c.user_id=%s
             ORDER BY b.booking_date DESC"""
    bookings = db.query_all(sql, (user_id,))
    body = render_template("customer_bookings.html", session=session, bookings=bookings)
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def customer_feedback(environ, start_response, session):
    if not session or session.get("role") != "CUSTOMER":
        return redirect(start_response, "/login")

    user_id = session["user_id"]
    customer = db.query_one("SELECT * FROM customers WHERE user_id=%s", (user_id,))
    customer_id = customer["customer_id"] if customer else None

    message = None

    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        booking_id = form.get("booking_id", "")
        rating = form.get("rating", "")
        comments = form.get("comments", "").strip()
        if booking_id and rating:
            try:
                db.execute(
                    "INSERT INTO feedback (booking_id, customer_id, rating, comments) VALUES (%s,%s,%s,%s)",
                    (booking_id, customer_id, rating, comments),
                )
                message = "Feedback submitted."
            except Exception as e:
                print("[FEEDBACK] Error:", e)
                message = "Error saving feedback."

    # Show only completed/delivered bookings & join with services
    sql = """SELECT b.booking_id, s.service_name, b.current_status
             FROM bookings b
             JOIN services s ON b.service_id = s.service_id
             WHERE b.customer_id=%s
             AND b.current_status IN ('COMPLETED','DELIVERED')
             ORDER BY b.booking_date DESC"""
    eligible = db.query_all(sql, (customer_id,))
    body = render_template("customer_feedback.html", session=session, eligible=eligible, message=message)
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]



# mechanic views

def mechanic_tasks(environ, start_response, session):
    if not session or session.get("role") != "MECHANIC":
        return redirect(start_response, "/login")

    # Find which mechanic is logged in
    user_id = session["user_id"]
    mech = db.query_one("SELECT mechanic_id FROM mechanics WHERE user_id=%s", (user_id,))
    if not mech:
        # no mechanic profile linked
        body = render_template(
            "mechanic_tasks.html",
            session=session,
            tasks=[],
            message="No mechanic profile linked to this user."
        )
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    mechanic_id = mech["mechanic_id"]
    message = None

    # Handle status/remark update
    if environ["REQUEST_METHOD"] == "POST":
        form = auth.parse_post(environ)
        booking_id = form.get("booking_id")
        status = form.get("status")
        remarks = form.get("remarks", "").strip()

        if booking_id and status:
            db.execute(
                "UPDATE bookings SET current_status=%s, remarks=%s WHERE booking_id=%s AND assigned_mechanic_id=%s",
                (status, remarks, booking_id, mechanic_id),
            )
            message = "Task updated."

    # Load current tasks (Booked / In progress / Waiting for parts)
    sql = """
        SELECT b.booking_id, b.current_status, b.remarks,
               s.service_name,
               v.vehicle_number, v.brand, v.model,
               c.full_name AS customer_name,
               t.slot_date, t.start_time, t.end_time
        FROM bookings b
        JOIN services s ON b.service_id = s.service_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN time_slots t ON b.slot_id = t.slot_id
        WHERE b.assigned_mechanic_id = %s
          AND b.current_status IN ('BOOKED','IN_PROGRESS','WAITING_FOR_PARTS')
        ORDER BY t.slot_date, t.start_time
    """
    tasks = db.query_all(sql, (mechanic_id,))

    body = render_template(
        "mechanic_tasks.html",
        session=session,
        tasks=tasks,
        message=message,
    )
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def mechanic_history(environ, start_response, session):
    if not session or session.get("role") != "MECHANIC":
        return redirect(start_response, "/login")

    user_id = session["user_id"]
    mech = db.query_one("SELECT mechanic_id FROM mechanics WHERE user_id=%s", (user_id,))
    mechanic_id = mech["mechanic_id"] if mech else None

    # Completed / delivered jobs + any feedback
    sql = """
        SELECT b.booking_id, b.current_status, b.booking_date,
               s.service_name,
               v.vehicle_number,
               c.full_name AS customer_name,
               f.rating, f.comments, f.created_at AS feedback_date
        FROM bookings b
        JOIN services s ON b.service_id = s.service_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        JOIN customers c ON b.customer_id = c.customer_id
        LEFT JOIN feedback f ON f.booking_id = b.booking_id
        WHERE b.assigned_mechanic_id = %s
          AND b.current_status IN ('COMPLETED','DELIVERED')
        ORDER BY b.booking_date DESC
    """
    history = db.query_all(sql, (mechanic_id,))

    body = render_template(
        "mechanic_history.html",
        session=session,
        history=history,
    )
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]





def app(environ, start_response):
    path = environ.get("PATH_INFO", "") or "/"

    session_id, session = auth.get_session(environ)

    # Static files
    if path.startswith("/static/"):
        rel = path[len("/static/"):]
        return serve_static(environ, start_response, rel)

    if path == "/":
        return home(environ, start_response, session)
    elif path == "/login":
        return login_page(environ, start_response, session)
    elif path == "/logout":
        return logout(environ, start_response, session)
    elif path == "/register":
        return register_page(environ, start_response, session)
    elif path == "/dashboard":
        return dashboard(environ, start_response, session)
    # Admin
    elif path == "/admin/services":
        return admin_services(environ, start_response, session)
    elif path == "/admin/slots":
        return admin_slots(environ, start_response, session)
    elif path == "/admin/bookings":
        return admin_bookings(environ, start_response, session)
    elif path == "/admin/mechanics":
        return admin_mechanics(environ, start_response, session)
    elif path == "/admin/payments":
        return admin_payments(environ, start_response, session)
    elif path == "/admin/feedback":
        return admin_feedback(environ, start_response, session)



    # Customer
    elif path == "/customer/profile":
        return customer_profile(environ, start_response, session)
    elif path == "/customer/vehicles":
        return customer_vehicles(environ, start_response, session)
    elif path == "/customer/services":
        return customer_services(environ, start_response, session)
    elif path == "/customer/book":
        return customer_book(environ, start_response, session)
    elif path == "/customer/bookings":
        return customer_bookings(environ, start_response, session)
    elif path == "/customer/feedback":
        return customer_feedback(environ, start_response, session)
    
        # Mechanic routes
    elif path == "/mechanic/tasks":
        return mechanic_tasks(environ, start_response, session)
    elif path == "/mechanic/history":
        return mechanic_history(environ, start_response, session)

    
    
    else:
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Not Found"]
    

 
    



def main():
    port = 8000
    with make_server("", port, app) as httpd:
        print(f"Serving on http://localhost:{port} ...")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
