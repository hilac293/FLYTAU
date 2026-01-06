import re

from flask import Flask, render_template, request, redirect, session, url_for, flash
from datetime import datetime, date

from werkzeug.security import generate_password_hash, check_password_hash

from Customers import Registered, Guest
from utils import get_connection, ensure_booking
from flights_and_workers import Flight
from func_for_flights import (
    get_available_planes,
    get_available_attendants,
    get_available_pilots,
    get_required_crew_by_duration
)

app = Flask(__name__)
app.secret_key = "secret123"

# Steps for the progress bar
STEPS = [
    "פרטי נוסעים",
    "בחירת מושבים",
    "סיכום פרטי הזמנה",
    "תשלום"
]


# ======================================================
# Login
# ======================================================
@app.route("/", methods=["GET", "POST"])
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
            SELECT manager_id
            FROM Managers
            WHERE manager_id = %s AND password = %s
        """, (manager_id, password))

        manager = cursor.fetchone()
        cursor.close()
        conn.close()

        if manager:
            session["manager"] = manager_id
            return redirect("/dashboard")

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
        return redirect("/")

    return render_template("dashboard.html")


# ======================================================
# Create Flight - Step 1 (Flight Details)
# ======================================================
@app.route("/create-flight", methods=["GET", "POST"])
def create_flight():
    """
    Step 1: Collect flight details.
    """

    if "manager" not in session:
        return redirect("/")

    if request.method == "POST":
        data = request.form

        # Basic price validation
        try:
            regular_price = float(data["regular_price"])
            business_price = float(data["business_price"])

            if regular_price <= 0 or business_price <= 0:
                return render_template(
                    "create_flight.html",
                    error="Prices must be positive numbers"
                )

            if business_price <= regular_price:
                return render_template(
                    "create_flight.html",
                    error="Business price must be higher than regular price"
                )

        except ValueError:
            return render_template(
                "create_flight.html",
                error="Invalid price values"
            )

        # Parse departure datetime
        departure_datetime = datetime.strptime(
            f"{data['date']} {data['time']}",
            "%Y-%m-%d %H:%M"
        )

        # Find available planes
        planes = get_available_planes(
            data["origin"],
            data["destination"],
            departure_datetime
        )

        # Save flight data in session until final confirmation
        session["flight_data"] = dict(data)
        session["departure_datetime"] = departure_datetime.isoformat()

        # Extract plane table columns dynamically
        plane_columns = []
        if planes:
            plane_columns = list(planes[0].keys())

        return render_template(
            "select_plane.html",
            planes=planes,
            plane_columns=plane_columns
        )

    return render_template("create_flight.html")


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
        return redirect("/")

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
        FROM Flight_time
        WHERE origin = %s AND destination = %s
    """, (data["origin"], data["destination"]))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    duration_hours = row["minutes"] / 60

    # Determine required crew by business rule
    required_attendants, required_pilots = get_required_crew_by_duration(duration_hours)

    # Fetch available crew members
    attendants = get_available_attendants(departure_datetime)
    pilots = get_available_pilots(departure_datetime)

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
        return redirect("/")

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
        FROM Flight_time
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


# ======================================================
# Logout
# ======================================================
@app.route("/logout")
def logout():
    """
    Clear session and return to login page.
    """

    session.clear()
    return redirect("/")


#flight login

@app.route("/flight-login", methods=["GET"])
def flight_login():
    return render_template("flight_login.html")

#coniniue as a guest
@app.route("/guest", methods=["POST"])
def continue_as_guest():
    session["booking"] = {
        "logged_in": False
    }
    return redirect(url_for("customer_details"))

@app.route("/customer-login", methods=["GET", "POST"])
def customer_login():
    error = None  # variable to store the message

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = Registered.find_by_email(email)
        if not user:
            error = "משתמש עם המייל הזה לא נמצא"
        elif not check_password_hash(user.password, password):
            error = "סיסמה שגויה"
        else:
            # Login successful
            session["logged_in"] = True
            session["user_email"] = user.email
            session["user_name"] = f"{user.first_name} {user.last_name}"
            return redirect(url_for("customer_details"))
            # Add user info to booking for autofill
            session["booking"] = session.get("booking", {})
            session["booking"]["user"] = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phones": user.phones
            }
            session["booking"]["logged_in"] = True

    return render_template("flight_login.html", error=error)




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
        session["logged_in"] = True
        session["user_passport"] = user.passport_number
        session["user_email"] = user.email
        session["user_name"] = f"{user.first_name} {user.last_name}"
        # Ensure session['booking'] exists
        if "booking" not in session:
            session["booking"] = {}
        # Add user info to booking
        session["booking"]["logged_in"] = True
        session["booking"]["user"] = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": user.phones
            }

        flash("הרשמה בוצעה בהצלחה! אתה מחובר עכשיו.")
        return redirect(url_for("debug_start"))

    else:
        # GET → show form
        return render_template("register.html")


#TODO: delete this when will be a real session

@app.route("/debug/start")
def debug_start():
    """
    Fake session for development.
    Only sets default booking values for testing.
    Does NOT overwrite existing 'user' to preserve real registered user info.
    """
    if "booking" not in session:
        session["booking"] = {}

    booking = session["booking"]
    # Set default number of passengers if not already set
    booking.setdefault("num_passengers", 3)
    # Set default logged_in status if not already set
    booking.setdefault("logged_in", False)
    # Do NOT overwrite 'user' if it already exists
    session["booking"] = booking

    # Redirect to customer details page
    return redirect(url_for("customer_details"))





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

        # Save to session
        booking["customer"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phones": phones
        }
        session["booking"] = booking

        # Save guest if not logged in
        if not booking.get("logged_in"):
            guest = Guest(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phones=phones
            )
            guest.save_to_db()

        return redirect(url_for("next_step"))  # continue to next step

    # GET request: autofill
    customer = booking.get("user") if booking.get("logged_in") else booking.get("customer")

    return render_template(
        "customer_details.html",
        num_passengers=booking.get("num_passengers", 1),
        logged_in=booking.get("logged_in", False),
        user=customer,
        steps=STEPS,
        current_step=1
    )





if __name__ == "__main__":
    app.run(debug=True)
