import re
from audioop import error
from collections import defaultdict

from flask import Flask, render_template, request, redirect, session, url_for, flash
from datetime import datetime, timedelta, date

from six import class_types
from unicodedata import category
from werkzeug.security import generate_password_hash, check_password_hash

from Customers import Registered, Guest
from Orders import Order
from Plane_and_Planeclass_and_seats import Seat
from utils import get_connection, is_expiry_valid
from flights_and_workers import Flight
from func_for_flights import (
    get_available_planes,
    get_available_attendants,
    get_available_pilots,
    get_required_crew_by_duration
)

from reports import (
    report_avg_capacity,
    report_revenue,
    report_employee_hours
)

app = Flask(__name__)
app.secret_key = "secret123"

# Steps for the progress bar
STEPS = [
    "פרטי לקוח",
    "בחירת מושבים",
    "סיכום פרטי הזמנה",
    "תשלום"
]

def update_flight_status():
    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    # טיסות רלוונטיות Scheduled
    cursor.execute("""
        SELECT f.flight_id, f.departure_datetime, f.plane_id, f.flight_status
        FROM Flights f
        WHERE f.flight_status = 'Scheduled'
    """)
    flights = cursor.fetchall()

    for flight in flights:
        flight_id = flight['flight_id']
        plane_id = flight['plane_id']
        departure = flight['departure_datetime']
        new_status = None

        # בדיקה אם הטיסה כבר קרתה
        if departure < datetime.now():
            new_status = 'Occurred'
        else:
            # בדיקה אם הטיסה מלאה
            cursor.execute("""
                SELECT COUNT(*) AS booked_count
                FROM Booking_Seats
                WHERE order_id IN (
                    SELECT order_id FROM Orders WHERE flight_id = %s AND order_status IN ('ACTIVE','COMPLETED')
                )
            """, (flight_id,))
            booked_count = cursor.fetchone()['booked_count']

            # ספירת מושבים של המטוס
            cursor.execute("""
                SELECT SUM(rows_number * columns_number) AS total_seats
                FROM Plane_Class
                WHERE plane_id = %s
            """, (plane_id,))
            total_seats = cursor.fetchone()['total_seats']

            if booked_count >= total_seats:
                new_status = 'Fully_Booked'

        # עדכון אם צריך
        if new_status:
            cursor.execute("""
                UPDATE Flights
                SET flight_status = %s
                WHERE flight_id = %s
            """, (new_status, flight_id))

    conn.commit()
    cursor.close()
    conn.close()


# @app.route("/")
# def root():
#     return redirect(url_for("homepage"))

# ======================================================
# Login
# ======================================================
@app.route("/manager-login", methods=["GET", "POST"])
def login():
    """
    Manager login page.
    """
    if request.method == "POST":
        manager_id = request.form["manager_id"]
        password = request.form["password"]

        # Simple authentication (can be improved later)
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT manager_id, first_name
            FROM Managers
            WHERE manager_id = %s AND password = %s
        """, (manager_id, password))

        manager = cursor.fetchone()
        cursor.close()
        conn.close()

        if manager:
            session["manager"] = True
            session["manager_name"] = manager["first_name"]
            return redirect("/dashboard")
        else:
            # raise error
            return render_template("login.html", error="תעודת זהות או סיסמה שגויים")

    return render_template("login.html")


# ======================================================
# Manager Dashboard
# ======================================================
@app.route("/dashboard")
def dashboard():
    """
    Main manager menu.
    """
    if "manager" not in session:
        return redirect(url_for("homepage"))

    return render_template("dashboard.html")

# ======================================================
# Create Flight - Step 1 (Flight Details)
# ======================================================
@app.route("/create-flight", methods=["GET", "POST"])
def create_flight():
    """
    Step 1: Collect flight details.
    """
    update_flight_status()

    if "manager" not in session:
        return redirect(url_for("homepage"))

    # =========================
    # POST – submit flight form
    # =========================
    if request.method == "POST":
        data = request.form

        # ---- Validate prices ----
        try:
            regular_price = float(data["regular_price"])
            business_price = float(data["business_price"])

            if regular_price <= 0 or business_price <= 0:
                raise ValueError

            if business_price <= regular_price:
                return render_template(
                    "create_flight.html",
                    error="Business price must be higher than regular price",
                    current_date=datetime.now().date().isoformat()
                )

        except ValueError:
            return render_template(
                "create_flight.html",
                error="Invalid price values",
                current_date=datetime.now().date().isoformat()
            )

        # ---- Parse datetime ----
        departure_datetime = datetime.strptime(
            f"{data['date']} {data['time']}",
            "%Y-%m-%d %H:%M"
        )

        today = datetime.now().date()
        if departure_datetime.date() < today:
            return render_template(
                "create_flight.html",
                error="לא ניתן לבחור תאריך שעבר",
                current_date=today.isoformat()
            )

        # ---- Origin & Destination (from dropdowns) ----
        origin = data["origin"]
        destination = data["destination"]

        # ---- Validate route exists ----
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT minutes
            FROM route
            WHERE origin = %s AND destination = %s
        """, (origin, destination))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return render_template(
                "create_flight.html",
                error="לא ניתן ליצור טיסה זו כי אין זמן טיסה מוגדר בין היעדים.",
                current_date=today.isoformat()
            )

        # ---- Calculate duration ----
        duration_hours = row["minutes"] / 60.0
        is_long_flight = duration_hours > 6

        # ---- Check available planes ----
        planes = get_available_planes(origin, destination, departure_datetime)
        if not planes:
            return render_template(
                "create_flight.html",
                error="לא ניתן ליצור טיסה זו בגלל חוסר במטוסים מתאימים.",
                current_date=today.isoformat()
            )

        # ---- Required crew ----
        required_attendants, required_pilots = get_required_crew_by_duration(duration_hours)

        attendants = get_available_attendants(
            departure_datetime,
            origin=origin,
            destination=destination,
            is_long_flight=is_long_flight
        )

        pilots = get_available_pilots(
            departure_datetime,
            origin=origin,
            destination=destination,
            is_long_flight=is_long_flight
        )

        if len(attendants) < required_attendants or len(pilots) < required_pilots:
            return render_template(
                "create_flight.html",
                error="לא ניתן ליצור טיסה זו בגלל חוסר באנשי צוות מתאימים.",
                current_date=today.isoformat()
            )

        # ---- Save data for next steps ----
        session["flight_data"] = dict(data)
        session["departure_datetime"] = departure_datetime.isoformat()

        plane_columns = list(planes[0].keys()) if planes else []

        return render_template(
            "select_plane.html",
            planes=planes,
            plane_columns=plane_columns
        )

    # =========================
    # GET – load form data
    # =========================
    conn = get_connection("FLYTAU")
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT origin FROM route ORDER BY origin")
    origins = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT destination FROM route ORDER BY destination")
    destinations = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template(
        "create_flight.html",
        origins=origins,
        destinations=destinations,
        current_date=datetime.now().date().isoformat()
    )

# ======================================================
# Create Flight - Step 2 (Plane Selection)
# ======================================================
@app.route("/select-crew", methods=["POST"])
def select_crew():
    """
    Step 2:
    - Save the flight in DB after plane selection
    - Calculate required crew
    - Show available attendants and pilots
    """
    if "manager" not in session or "flight_data" not in session:
        return redirect(url_for("homepage"))

    plane_id = request.form.get("plane_id")
    if not plane_id:
        return redirect("/create-flight")

    data = session["flight_data"]
    departure_datetime = datetime.fromisoformat(session["departure_datetime"])

    # Create flight object
    flight = Flight(
        data["date"],
        data["time"],
        data["origin"],
        data["destination"],
        float(data["regular_price"]),
        float(data["business_price"]),
        int(plane_id)
    )

    flight.send_to_db()

    session["created_flight_id"] = flight.flight_id
    session["selected_plane_id"] = int(plane_id)

    # Calculate flight duration
    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT minutes
        FROM route
        WHERE origin = %s AND destination = %s
    """, (data["origin"], data["destination"]))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    duration_hours = row["minutes"] / 60

    # Determine required crew by business rule
    required_attendants, required_pilots = get_required_crew_by_duration(duration_hours)

    # Fetch available crew members
    # לחשב משך הטיסה כדי לדעת אם היא ארוכה
    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT minutes
        FROM route
        WHERE origin = %s AND destination = %s
    """, (data["origin"], data["destination"]))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    duration_hours = row["minutes"] / 60

    # fetch data
    attendants = get_available_attendants(
        departure_datetime,
        origin=data["origin"],
        destination=data["destination"],
        is_long_flight=(duration_hours > 6)
    )

    pilots = get_available_pilots(
        departure_datetime,
        origin=data["origin"],
        destination=data["destination"],
        is_long_flight=(duration_hours > 6)
    )

    return render_template(
        "select_crew.html",
        attendants=attendants,
        pilots=pilots,
        required_attendants=required_attendants,
        required_pilots=required_pilots
    )


# ======================================================
# Create Flight - Step 3 (Crew Assignment)
# ======================================================
@app.route("/finalize-flight", methods=["POST"])
def finalize_flight():
    """
    Step 3:
    - Assign attendants and pilots to the flight
    - Validate required crew count
    """
    if (
        "manager" not in session or
        "created_flight_id" not in session or
        "departure_datetime" not in session
    ):
        return redirect(url_for("homepage"))

    flight_id = int(session["created_flight_id"])
    departure_datetime = datetime.fromisoformat(session["departure_datetime"])

    attendant_ids = request.form.getlist("attendant_ids")
    pilot_ids = request.form.getlist("pilot_ids")

    # Recalculate required crew to prevent client-side manipulation
    # Calculate flight duration directly from DB
    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT minutes
        FROM route
        WHERE origin = %s AND destination = %s
    """, (
        session["flight_data"]["origin"],
        session["flight_data"]["destination"]
    ))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    duration_hours = row["minutes"] / 60
    required_attendants, required_pilots = get_required_crew_by_duration(duration_hours)

    # Validate crew count
    if (
        len(attendant_ids) != required_attendants or
        len(pilot_ids) != required_pilots
    ):
        attendants = get_available_attendants(departure_datetime)
        pilots = get_available_pilots(departure_datetime)

        return render_template(
            "select_crew.html",
            attendants=attendants,
            pilots=pilots,
            required_attendants=required_attendants,
            required_pilots=required_pilots,
            error="Incorrect number of crew members selected"
        )

    # Assign crew to flight using flight_id
    flight = Flight(
        session["flight_data"]["date"],
        session["flight_data"]["time"],
        session["flight_data"]["origin"],
        session["flight_data"]["destination"],
        float(session["flight_data"]["regular_price"]),
        float(session["flight_data"]["business_price"]),
        session["selected_plane_id"]
    )

    # Manually set existing flight id
    flight.flight_id = flight_id

    flight.assign_attendants([int(a) for a in attendant_ids])
    flight.assign_pilots([int(p) for p in pilot_ids])

    # Clear session data related to flight creation
    session.pop("flight_data", None)
    session.pop("departure_datetime", None)
    session.pop("created_flight_id", None)
    session.pop("selected_plane_id", None)

    return render_template("success.html")

@app.route("/cancel-flight", methods=["GET", "POST"])
def cancel_flight_route():
    if "manager" not in session:
        return redirect(url_for("homepage"))

    flights = Flight.get_all()

    if request.method == "POST":
        flight_id = request.form.get("flight_id")
        data = Flight.get_by_id(flight_id)

        if not data:
            return render_template("cancel_flight.html", flights=flights, error="טיסה לא נמצאה")

        dep_time = data["departure_datetime"]

        if not Flight.can_cancel(dep_time):
            return render_template("cancel_flight.html", flights=flights, error="ניתן לבטל רק עד 72 שעות לפני")

        Flight.cancel_flight(flight_id)

        Order.refund_orders_by_flight(flight_id)

        return render_template("cancel_flight.html", flights=Flight.get_all(), success="טיסה בוטלה בהצלחה")

    return render_template("cancel_flight.html", flights=flights)


@app.route("/reports-dashboard")
def reports_dashboard():
    if "manager" not in session:
        return redirect(url_for("homepage"))

    avg_capacity = report_avg_capacity()
    report_revenue()
    employee_hours = report_employee_hours()

    return render_template(
        "reports_dashboard.html",
        avg_capacity=avg_capacity,
        employee_hours=employee_hours
    )


@app.route("/flights-board", methods=["GET", "POST"])
def flights_board():
    if "manager" not in session:
        return redirect(url_for("homepage"))

    # --- הוספה: שליפת רשימות מוצא ויעד מהדאטהבייס ---
    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT DISTINCT origin FROM route ORDER BY origin")
    origins_list = [row['origin'] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT destination FROM route ORDER BY destination")
    destinations_list = [row['destination'] for row in cursor.fetchall()]
    # ---------------------------------------------

    # --- בסיס השאילתה ---
    query = """
        SELECT flight_id, departure_datetime, origin, destination,
               flight_status, regular_price, business_price, plane_id
        FROM Flights
        WHERE 1 = 1
    """
    params = []

    # --- סינונים ---
    if request.method == "POST":
        date = request.form.get("date")
        origin = request.form.get("origin")
        destination = request.form.get("destination")
        status = request.form.get("status")

        if date:
            query += " AND DATE(departure_datetime) = %s"
            params.append(date)

        if origin:
            query += " AND origin = %s"
            params.append(origin)

        if destination:
            query += " AND destination = %s"
            params.append(destination)

        if status:
            query += " AND flight_status = %s"
            params.append(status)

    # --- שליפת נתונים ---
    cursor.execute(query, params)
    flights = cursor.fetchall()
    cursor.close()
    conn.close()

    statuses = [
        ("Scheduled", "פעילה"),
        ("Fully_Booked", "תפוסה מלאה"),
        ("Occurred", "התקיימה"),
        ("Cancelled", "בוטלה")
    ]

    return render_template(
        "flight_board_managers.html",
        flights=flights,
        statuses=statuses,
        origins=origins_list,  # הוספה
        destinations=destinations_list  # הוספה
    )



# ======================================================
# Logout
# ======================================================
@app.route("/logout")
def logout():
    update_flight_status()
    session.pop("manager", None)
    session.pop("manager_id", None)
    session.pop("manager_name", None)
    session.modified = True
    session.clear()
    return redirect(url_for("login"))
  # מחזיר למסך התחברות מנהלים

@app.route("/")
def homepage():
    # --- Get min and max dates for the date input ---
    now = datetime.now()
    min_date = now.date()
    max_date = now.date() + timedelta(days=365)

    # --- Connect to DB and fetch routes ---
    conn = get_connection("FLYTAU")
    cursor = conn.cursor()

    # Fetch distinct origins
    cursor.execute("SELECT DISTINCT origin FROM route WHERE origin IS NOT NULL AND origin != '' ORDER BY origin")
    origins = [row[0] for row in cursor.fetchall()]

    cursor.execute(
        "SELECT DISTINCT destination FROM route WHERE destination IS NOT NULL AND destination != '' ORDER BY destination")
    destinations = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    # --- Render template with variables ---
    return render_template(
        "homepage.html",
        origins=origins,
        destinations=destinations,
        min_date=min_date.strftime("%Y-%m-%d"),
        max_date=max_date.strftime("%Y-%m-%d"),
        prev_source=None,
        prev_destination=None,
        prev_departure=None,
        prev_passengers=1
    )




@app.route("/contact-us", methods=["GET", "POST"])
def contact_us():
    message_sent = False
    if request.method == "POST":
        title = request.form.get("title")
        email = request.form.get("email")
        details = request.form.get("details")

        # כאן אפשר לשלוח לדאטהבייס או אימייל אם רוצים
        # לדוגמה: save_contact(title, email, details)

        message_sent = True  # נשתמש בזה כדי להציג את ההודעה בצד הכפתור

    return render_template("contact_us.html", message_sent=message_sent)

@app.route("/search-flights", methods=["POST"])
def search_flights():
    # 🚫 Manager cannot book flights
    if session.get("manager"):
        return render_template("manager_cannot_book.html")
    origin = request.form.get("source")
    destination = request.form.get("destination")
    departure_date = request.form.get("departure")
    passengers = int(request.form.get("passengers", 1))
    if origin == destination:
        flash("אופס, נראה שהמקור והיעד בחרתם זהים", category="error")
        return redirect(url_for("homepage"))



    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

   #choose flies by destination, origin, date
    cursor.execute("""
        SELECT f.flight_id, f.departure_datetime, f.origin, f.destination,
               f.regular_price, f.business_price, f.plane_id
        FROM Flights f
        WHERE f.origin = %s AND f.destination = %s
          AND DATE(f.departure_datetime) = %s
          AND f.flight_status = 'Scheduled'
          AND f.departure_datetime > NOW()
    """, (origin, destination, departure_date))

    flights = cursor.fetchall()
    results = []

    for flight in flights:
        # check how much free seats
        cursor.execute("""
            SELECT SUM(pc.rows_number * pc.columns_number) AS total_seats
            FROM plane_class pc
            WHERE pc.plane_id = %s
        """, (flight['plane_id'],))
        plane_info = cursor.fetchone()
        total_seats = plane_info['total_seats'] or 0

        cursor.execute("""
            SELECT COUNT(bs.seat_number) AS occupied_seats
            FROM Booking_Seats bs
            JOIN orders o ON o.order_id = bs.order_id
            WHERE o.flight_id = %s AND o.order_status = 'ACTIVE'
        """, (flight['flight_id'],))
        occupied_info = cursor.fetchone()
        occupied_seats = occupied_info['occupied_seats'] or 0

        available_seats = total_seats - occupied_seats

        if available_seats >= passengers:

            #  using 'minutes' from route table
            cursor.execute("""
                SELECT minutes
                FROM Route
                WHERE origin = %s AND destination = %s
            """, (flight['origin'], flight['destination']))
            route_info = cursor.fetchone()
            minutes = route_info['minutes'] if route_info else 0

            flight['arrival_datetime'] = flight['departure_datetime'] + timedelta(minutes=minutes)

            results.append(flight)

    cursor.close()
    conn.close()

    session['search_results'] = results
    session['search_passengers'] = passengers

    return render_template("flights_results.html", flights=results, passengers=passengers)

@app.route("/book-flight", methods=["POST"])
def book_flight():
    # Get flight_id and passengers from form
    flight_id = request.form.get("flight_id")
    passengers = request.form.get("passengers")
    departure_datetime = request.form.get("departure_datetime")
    arrival_datetime = request.form.get("arrival_datetime")
    origin=request.form.get("origin")
    destination=request.form.get("destination")
    business_price = request.form.get("business_price")
    regular_price = request.form.get("regular_price")
    # Convert to datetime objects
    dep_dt = datetime.strptime(departure_datetime, "%Y-%m-%d %H:%M:%S")
    arr_dt = datetime.strptime(arrival_datetime, "%Y-%m-%d %H:%M:%S")

    data = Flight.get_by_id(flight_id)
    flight= Flight(
        departure_date=data['departure_datetime'].strftime("%Y-%m-%d"),
        departure_time=data['departure_datetime'].strftime("%H:%M"),
        origin=data['origin'],
        destination=data['destination'],
        regular_price=data['regular_price'],
        business_price=data['business_price'],
        plane_id=data['plane_id'],
        status=data['flight_status']
    )
    plane_id = data['plane_id']
    duration = flight.get_duration_hours()

    # Save flight info in session['booking']
    session['booking'] = {
        "plane_id": plane_id,
        "flight_id": flight_id,
        "passengers_count": passengers,
        "origin": origin,
        "destination": destination,
        "business_price": business_price,
        "regular_price": regular_price,
        "duration": duration,

    }

    # Format without seconds
    session['booking']['departure_datetime'] = dep_dt.strftime("%Y-%m-%d %H:%M")
    session['booking']['arrival_datetime'] = arr_dt.strftime("%Y-%m-%d %H:%M")


    # Check if user is logged in
    if not session.get("user"):
        # User not logged in → redirect to flight login page
        return redirect(url_for("flight_login"))

    user = session.get("user")
    session["booking"]["customer"] = {
        "first_name": user['first_name'],
        "last_name": user['last_name'],
        "email": user['email'],
        "phones": user['phones']
    }

    # User is logged in → redirect to booking page (or payment page)
    return redirect(url_for("select_seat"))


#flight login

@app.route("/flight-login", methods=["GET"])
def flight_login():
    # Disconnect previous login only for flight flow
    if session.get("logged_in"):
        session.pop("logged_in", None)
        session.pop("user", None)
        session["booking"]["logged_in"] = False

    email = session.pop("login_email", "")
    return render_template("flight_login.html", email=email)


#coniniue as a guest
@app.route("/guest", methods=["POST"])
def continue_as_guest():
    # Explicitly mark user as not logged in
    session["logged_in"] = False
    session.pop("user", None)

    # Update booking info
    session["booking"] = session.get("booking", {})
    session["booking"]["logged_in"] = False
    session["booking"]["customer"] = {}  # clear previous user info

    return redirect(url_for("customer_details"))


@app.route("/flight-customer-login", methods=["GET", "POST"])
def flight_customer_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = Registered.find_by_email(email)

        if not user:
            flash("משתמש עם המייל הזה לא נמצא", "error")
            session["login_email"] = email

        elif not check_password_hash(user.password, password):
            flash("סיסמה שגויה", "error")
            session["login_email"] = email

        else:
            # התחברות הצליחה
            session.pop("login_email", None)

            session["logged_in"] = True
            # 🔹 Log the user in via session
            session["user"] = {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "passport_number": user.passport_number,
                "phones": user.phones
            }

            session["booking"] = session.get("booking", {})
            session["booking"]["customer"] = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phones": user.phones
            }
            session["booking"]["logged_in"] = True

            return redirect(url_for("select_seat"))


    # GET
    email = session.pop("login_email", "")
    return render_template("flight_login.html", email=email)


@app.route("/customer-login", methods=["GET", "POST"])
def customer_login():
    """
    Login route for users coming from homepage.
    Always shows the nice login form and redirects back to homepage after login.
    """
    # Disconnect temporary login for this flow
    session.pop("logged_in", None)
    session.pop("user", None)
    # Default email value (in case of previous failed login)
    email = session.get("login_email", "")

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = Registered.find_by_email(email)

        if not user:
            flash("משתמש עם המייל הזה לא נמצא", "error")
            session["login_email"] = email
            return redirect(url_for("customer_login"))

        if not check_password_hash(user.password, password):
            flash("סיסמה שגויה", "error")
            session["login_email"] = email
            return redirect(url_for("customer_login"))

        # Login success
        session.pop("login_email", None)
        session["logged_in"] = True
        session["user"] = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "passport_number": user.passport_number,
            "phones": user.phones
        }

        # Also update booking if it exists
        if session.get("booking"):
            session["booking"] = session.get("booking")
            session["booking"]["customer"] = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phones": user.phones
            }
            session["booking"]["logged_in"] = True
            return redirect(url_for("select_seat"))

            # After login, always return to homepage
        return redirect(url_for("homepage"))

    # GET request – render nice login form
    return render_template("customer_login.html", email=email)




#register

@app.route("/register", methods=["GET", "POST"])
def register():
    print("Register started")

    if request.method == "POST":
        print("Register POST")

        # 1. Get data from form
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        passport = request.form.get("passport")
        birth_date = request.form.get("birth_date")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        phone_1 = request.form.get("phone_1")
        phone_2 = request.form.get("phone_2")

        phones = []
        if phone_1:
            phones.append(phone_1)
        if phone_2:
            phones.append(phone_2)

        # 2. Check required fields
        if not all([first_name, last_name, email, passport, birth_date, password, confirm_password]):
            flash("נא למלא את כל השדות")
            return redirect(url_for("register"))

        # Check if a guest already exists with this email
        existing_guest = Guest.get_by_email(email)
        if existing_guest:
            # Delete the guest to allow registration
            Guest.delete_by_email(email)

        # 3. Check if email already exists
        if Registered.find_by_email(email):
            flash("מייל זה כבר קיים במערכת, התחבר או הירשם עם מייל אחר", "error")
            return render_template(
                "register.html",
                prev_data=request.form
                )

        # Check if passport number already exists
        existing_passport = Registered.get_by_passport(passport)
        if existing_passport:
            flash("מספר דרכון זה כבר קיים במערכת", "error")
            return render_template(
                "register.html",
                prev_data=request.form
                )

        # Regex: only English letters (uppercase or lowercase)
        english_only = re.compile(r'^[A-Za-z\s\-]+$')  # letters, spaces, dashes allowed

        if not english_only.match(first_name):
            flash("שם פרטי צריך להיות באנגלית בלבד")
            return redirect(url_for("register"))

        if not english_only.match(last_name):
            flash("שם משפחה צריך להיות באנגלית בלבד")
            return redirect(url_for("register"))

        # 3. Check password match
        if password != confirm_password:
            flash("הסיסמאות אינן תואמות")
            return redirect(url_for("register"))


        # 4. Validate password pattern
        # Must be at least 6 characters, include letters and numbers
        pattern = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$')
        if not pattern.match(password):
            flash("סיסמה חייבת להיות לפחות 6 תווים, עם אותיות ומספרים")
            # return redirect(url_for("register"))

        # 5. Hash password+

        hashed_password = generate_password_hash(password)

        # 6. Create user object and save to DB
        user = Registered(
            passport_number=passport,
            first_name=first_name,
            last_name=last_name,
            email=email,
            birth_date=birth_date,
            password=hashed_password,
            phones=phones,
            registration_date=date.today()
        )

        try:
            user.save_to_db()
        except Exception as e:
            flash(f"שגיאה בשמירה למסד הנתונים: {e}")
            return redirect(url_for("register"))

        # 🔹 Log the user in via session
        session["user"] = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "passport_number": user.passport_number,
            "phones": user.phones
        }
        session["logged_in"] = True

        if "booking" in session:
            # Add user info to booking
            session["booking"]["logged_in"] = True
            session["booking"]["customer"] = {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phones": user.phones
                }

            return redirect(url_for("select_seat"))

        # --- No booking in session → redirect to home/profile ---
        return redirect(url_for("homepage"))

    # GET → show form
    return render_template("register.html")




@app.route("/customer-details", methods=["GET", "POST"])
def customer_details():
    booking = session.get("booking")

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone_1 = request.form.get("phone_1")
        phone_2 = request.form.get("phone_2")

        phones = []
        if phone_1:
            phones.append(phone_1)
        if phone_2:
            phones.append(phone_2)

        existing_user = Registered.find_by_email(email)
        if existing_user:
            flash("המייל הזה כבר רשום במערכת. אנא הזן מייל אחר או התחבר כדי להמשיך.", "error")
            return render_template(
            "customer_details.html",
            num_passengers=booking.get("passengers_count", 1),
            logged_in=booking.get("logged_in", False),
            steps=STEPS,
            current_step=1
        )
        # Save to session
        booking["customer"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phones": phones
        }
        session["booking"] = booking

        # Force guest mode: remove any registered user data from session
        session["logged_in"] = False
        session.pop("user_email", None)
        session.pop("user_name", None)
        session.pop("user_passport", None)
        session.pop("order_id", None)

        session.modified = True

        # Save guest if not logged in
        if not booking.get("logged_in"):
            guest = Guest(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phones=phones
            )
            guest.save_to_db()

        return redirect(url_for("select_seat"))  # continue to next step

    # GET request: autofill
    customer = booking.get("user") if booking.get("logged_in") else booking.get("customer")

    return render_template(
        "customer_details.html",
        num_passengers=booking.get("passengers_count", 1),
        logged_in=booking.get("logged_in", False),
        user=customer,
        steps=STEPS,
        current_step=1
    )

@app.route("/select-seat", methods=["GET", "POST"])
def select_seat():
    passengers_count = int(session['booking']['passengers_count'])
    flight_id = session['booking']['flight_id']
    flight = Flight.get_by_id(flight_id)
    if not flight:
        return "Flight not found", 404

    plane_id = flight["plane_id"]

    # --- get all seats of the plane ---
    seats = Seat.get_seats_for_plane(plane_id)

    # --- get taken seats for this flight ---
    taken_seats = Seat.get_taken_seats_for_flight(flight_id)

    # --- organize seats by rows ---
    from collections import defaultdict
    rows = defaultdict(list)
    for seat in seats:
        rows[seat.row_number].append(seat)

    # --- Seats already selected in session ---
    booking = session.get("booking", {})
    selected_seat_numbers = booking.get("seat_numbers", [])
    selected_business = booking.get("business_seats_count", 0)
    selected_economy = booking.get("economy_seats_count", 0)

    if request.method == "POST":
        selected = request.form.getlist("seat_number")

        # Remove seats that are already taken (extra safety)
        selected = [s for s in selected if s not in taken_seats]

        # 🔸 Save current selection in session so it won't be lost on errors
        booking["seat_numbers"] = selected
        session["booking"] = booking

        # 1️⃣ Check that at least one seat was selected
        if not selected:
            flash("יש לבחור מושבים לפני שממשיכים לשלב הבא", "error")
            return redirect(url_for("select_seat"))

        # 2️⃣ Check that the number of seats equals passengers count
        if len(selected) != passengers_count:
            flash(
                f"יש לבחור בדיוק {passengers_count} מושבים. "
                f"בחרתם {len(selected)}.",
                "error"
            )
            return redirect(url_for("select_seat"))

        # 3️⃣ Re-check availability in the database (race condition protection)
        taken_seats_now = Seat.get_taken_seats_for_flight(flight_id)
        conflict = set(selected) & set(taken_seats_now)

        if conflict:
            flash(
                "אחד או יותר מהמושבים שבחרתם נתפסו בינתיים. "
                "אנא בחרו מושבים אחרים.",
                "error"
            )
            return redirect(url_for("select_seat"))

        # ✅ All validations passed – now we finalize the booking seats

        seat_map = {s.seat_number: s for s in seats}

        selected_seats = []
        business_count = 0
        economy_count = 0

        for seat_num in selected:
            seat_obj = seat_map.get(seat_num)
            if seat_obj:
                class_type = seat_obj.plane_class.class_type

                selected_seats.append({
                    "seat_number": seat_num,
                    "class_type": class_type
                })

                if class_type == "Business":
                    business_count += 1
                else:
                    economy_count += 1

        booking["seats"] = selected_seats
        booking["business_seats_count"] = business_count
        booking["economy_seats_count"] = economy_count

        # After successful validation, we can even clean seat_numbers if you want:
        # booking.pop("seat_numbers", None)

        session["booking"] = booking

        return redirect(url_for("summary"))

    # --- prepare seat_map for template ---
    seat_map = {}
    for seat in seats:
        seat_map[seat.seat_number] = {
            "column_letter": seat.column_letter,
            "is_taken": seat.seat_number in taken_seats,
            "class_type": seat.plane_class.class_type
        }

    return render_template(
        "select_seat.html",
        rows=rows,
        selected_seat_numbers=selected_seat_numbers,
        seat_map=seat_map,
        passengers_count=passengers_count,
        current_step=2
    )


@app.route("/summary")
def summary():
    booking = session.get("booking", {})

    # Convert counts and prices safely
    business_seats = int(booking.get("business_seats_count", 0))
    economy_seats = int(booking.get("economy_seats_count", 0))
    business_price = float(booking.get("business_price", 0))
    regular_price = float(booking.get("regular_price", 0))

    # Calculate total
    total_amount = business_seats * business_price + economy_seats * regular_price

    # Save in session (optional, useful if you want to reuse later)
    booking["total_amount"] = total_amount
    session["booking"] = booking

    # Send data to template
    return render_template(
        "summary.html",
        booking=booking,
        steps=STEPS,
        current_step=3  # Summary step
    )

@app.route("/payment", methods=["GET", "POST"])
def payment():
    if "booking" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        expiry = request.form.get("expiry")
        cvv = request.form.get("cvv")

        # check the expiry date
        if not is_expiry_valid(expiry):
            return render_template(
                "payment.html",
                error="תוקף הכרטיס פג או לא תקין",
                booking=session.get("booking"),
                steps=STEPS,
                current_step=4
            )

        booking = session["booking"]

        # 1. Determine if the customer is registered or a guest
        if booking["customer"].get("is_registered"):
            email_registered = booking["customer"]["email"]
            email_guest = None
        else:
            email_registered = None
            email_guest = booking["customer"]["email"]

        # 2. Create Order object
        order = Order(
            order_status="ACTIVE",
            total_amount=booking["total_amount"],
            flight_id=booking["flight_id"],
            email_guest=email_guest,
            email_registered=email_registered,
            order_date = datetime.now().strftime("%Y-%m-%d")
        )

        # 3. Save order to DB
        order.save_to_db()

        # 4. Add seats to the order object
        # booking["seat_numbers"] example: ["12A", "12B"]
        for seat in booking["seats"]:
            order.seats.append({
                "plane_id": booking["plane_id"],
                "class_type": seat["class_type"],
                "seat_number": seat["seat_number"]
            })

        # 5. Save seats to booking_seats table
        order.save_seats_to_db()

        # 6. Optional: store order_id in session (nice for confirmation page)
        session["order_id"] = order.order_id

        # 7. Redirect to confirmation page
        return redirect(url_for("confirmation"))

    # GET request
    return render_template(
        "payment.html",
        booking=session["booking"],
        steps=STEPS,
        current_step=4
    )

@app.route("/confirmation")
def confirmation():
    """
    This route displays the final confirmation page after a successful order.
    It should only be accessible after completing the payment process.
    """
    # Get the last order_id from session
    order_id = session.pop("order_id", None)

    if not order_id:
        # אם אין order_id בסשן, נחזיר לדף הבית
        flash("לא נמצאה הזמנה להצגה.", "error")
        return redirect(url_for("homepage"))

    # שליפת פרטי ההזמנה מהמסד
    order = Order.get_by_id(order_id)
    session.pop("booking", None)

    return render_template(
        "confirmation.html",
        order=order
    )



@app.route("/customer-logout")
def customer_logout():

        session.pop("user", None)  # מוחק את פרטי המשתמש
        session["logged_in"] = False  # או session.pop("logged_in", None)
        session.pop("booking", None)
        return redirect(url_for("homepage"))

# ======================================
# Route: Guest Booking Lookup Form
# ======================================
@app.route("/guest-booking-lookup", methods=["GET", "POST"])
def guest_booking_lookup():
    """
    Guest booking lookup by email + booking code.
    Only allow bookings for flights that have not departed yet.
    """
    # Initialize empty values for the form
    email = ""
    booking_code = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        booking_code = request.form.get("booking_code", "").strip()

        # 1️⃣ Validate input
        if not email or not booking_code:
            flash("יש להזין אימייל וקוד הזמנה", "error")
            # Instead of redirect, render template with the current values
            return render_template(
                "guest_booking_lookup.html",
                email=email,
                booking_code=booking_code
            )

        # 2️⃣ Lookup booking
        booking = Order.get_by_email_and_code(email, booking_code)
        if not booking:
            flash("ההזמנה לא נמצאה. אנא בדקו את האימייל וקוד ההזמנה שהזנתם.", "error")
            return render_template(
                "guest_booking_lookup.html",
                email=email,
                booking_code=booking_code
            )

        # 3️⃣ Lookup flight for this booking
        flight = Flight.get_by_id(booking.flight_id)
        if not flight:
            flash("לא נמצאו פרטי הטיסה עבור הזמנה זו.", "error")
            return render_template(
                "guest_booking_lookup.html",
                email=email,
                booking_code=booking_code
            )

        # 4️⃣ Check if flight has departed
        departure_dt = flight["departure_datetime"]
        if departure_dt < datetime.now():
            flash("טיסה זו כבר המריאה ולא ניתן לצפות בה.", "error")
            return render_template(
                "guest_booking_lookup.html",
                email=email,
                booking_code=booking_code
            )

        # 5️⃣ Flight is valid and in the future -> redirect to summary
        return redirect(url_for("booking_summary", booking_id=booking.order_id))

    # GET request -> show lookup form
    return render_template(
        "guest_booking_lookup.html",
        email=email,
        booking_code=booking_code
    )



# ======================================
# Route: Guest Booking Summary
# ======================================
@app.route("/booking-summary/<int:booking_id>")
def booking_summary(booking_id):
    """
    Show booking summary with customer info, seats, and cancellation eligibility.
    """
    booking = Order.get_by_id(booking_id)
    if not booking:
        flash("לא נמצאה הזמנה זו.", "error")
        return redirect(url_for("home"))

    # Get flight departure datetime
    flight = Flight.get_by_id(booking.flight_id)
    departure_dt = flight["departure_datetime"]
    now = datetime.now()

    # Calculate hours until flight
    hours_to_departure = (departure_dt - now).total_seconds() / 3600

    # Flag to check if cancellation is allowed
    can_cancel = booking.order_status == "ACTIVE" and hours_to_departure >= 36

    # Calculate cancellation fee for display (5%)
    cancellation_fee = booking.total_amount * 0.05 if can_cancel else 0

    return render_template(
        "booking_summary.html",
        booking=booking,
        can_cancel=can_cancel,
        cancellation_fee=cancellation_fee
    )


@app.route("/cancel-booking/<int:order_id>", methods=["GET", "POST"])
def cancel_booking(order_id):
    booking = Order.get_by_id(order_id)
    if not booking:
        flash("לא נמצאה הזמנה זו.", "error")
        return redirect(url_for("home"))

    # Get flight info
    flight = Flight.get_by_id(booking.flight_id)
    departure_dt = flight["departure_datetime"]
    now = datetime.now()
    hours_to_departure = (departure_dt - now).total_seconds() / 3600

    if hours_to_departure < 36:
        flash("מועד הטיסה הינו פחות מ-36 שעות ולכן הזמנה זו אינה ניתנת לביטול", "error")
        return redirect(url_for("booking_summary", booking_id=order_id))

    if request.method == "POST":
        # Process cancellation
        try:
            refund_amount, cancellation_fee = booking.cancel_order()
            # ✅ Pass ready-to-display numbers to template
            return render_template("cancel_success.html",
                                   booking=booking,
                                   refund_amount=round(refund_amount,2),
                                   cancellation_fee=round(cancellation_fee,2))
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("booking_summary", booking_id=order_id))

    # GET request -> show confirmation page
    cancellation_fee = float(booking.total_amount) * 0.05
    return render_template("cancel_booking.html",
                           booking=booking,
                           cancellation_fee=round(cancellation_fee,2))


@app.route("/cancel-success/<int:order_id>")
def cancel_success(order_id):
    # Fetch order to show info if needed
    booking = Order.get_by_id(order_id)

    if not booking:
        flash("לא נמצאה הזמנה עם מספר זה.", "error")
        return redirect(url_for("home"))

    return render_template("cancel_success.html", booking=booking)

@app.route("/my-bookings")
def my_bookings():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    email = session["user"]["email"]

    # ⬅️ כאן אנחנו לוקחים את הערך מה-select
    selected_status = request.args.get("status")

    # 1️⃣ קח את כל ההזמנות של המשתמש
    orders = Order.get_by_registered_email(email)

    bookings_with_flights = []
    now = datetime.now()

    for order in orders:
        flight = Flight.get_by_id(order.flight_id)  # dict

        # 2️⃣ אם הטיסה עברה ועדיין ACTIVE → נסמן כ-COMPLETED
        if order.order_status == "ACTIVE" and flight["departure_datetime"] < now:
            order.order_status = "COMPLETED"

        # 3️⃣ סינון לפי סטטוס אם נבחר כזה
        if selected_status:
            if order.order_status != selected_status:
                continue

        bookings_with_flights.append({
            "order": order,
            "flight": flight
        })

    return render_template(
        "my_bookings.html",
        bookings=bookings_with_flights,
        selected_status=selected_status
    )




if __name__ == "__main__":
    app.run(debug=True)