from flask import Flask, render_template, request, redirect, session
from datetime import datetime

from utils import get_connection
from flights_and_workers import Flight
from func_for_flights import (
    get_available_planes,
    get_available_attendants,
    get_available_pilots,
    get_required_crew_by_duration
)

app = Flask(__name__)
app.secret_key = "secret123"


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

@app.route("/homepage")
def idan_home():
    # ברירת מחדל: הלוך-חזור
    flight_type = "2way"
    return render_template("HomePage-idan.html", flight_type=flight_type)

@app.route("/homepage/1way")
def idan_home_1way():
    return render_template("HomePage-idan-1way.html")  # יעד, תאריך יציאה, נוסעים

@app.route("/homepage/all")
def idan_home_all():
    return render_template("HomePage-idan-all.html")  # תאריך יציאה, נוסעים



if __name__ == "__main__":
    app.run(debug=True)