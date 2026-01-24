from datetime import timedelta
from utils import get_connection

BASE_AIRPORT = "Ben-Gurion"  # default base airport


# ==============================
# Helper functions
# ==============================

def _get_flight_duration_minutes(cursor, origin, destination):
    """
    Returns the flight duration in minutes from the 'route' table.
    If no row exists for (origin, destination) -> returns None.
    """
    cursor.execute("""
        SELECT minutes
        FROM route
        WHERE origin = %s AND destination = %s
    """, (origin, destination))
    row = cursor.fetchone()
    return row["minutes"] if row else None


def _compute_arrival(cursor, departure_dt, origin, destination):
    """
    Computes arrival datetime as departure + duration (from 'route' table).
    If no route exists -> returns the original departure datetime (no change).
    """
    minutes = _get_flight_duration_minutes(cursor, origin, destination)
    if minutes is None:
        return departure_dt
    return departure_dt + timedelta(minutes=minutes)


def _travel_time_between(cursor, origin, destination):
    """
    Returns a timedelta representing travel time between two airports
    (used for moving a resource between flights).

    If origin == destination -> returns timedelta(0).
    If no route exists -> returns None.
    """
    if origin == destination:
        return timedelta(0)

    minutes = _get_flight_duration_minutes(cursor, origin, destination)
    if minutes is None:
        return None

    return timedelta(minutes=minutes)


def _get_resource_flights(cursor, plane_id=None, pilot_id=None, attendant_id=None):
    """
    Returns a list of flights for a given resource (plane / pilot / attendant),
    each item containing: flight_id, departure, arrival, origin, destination.
    Arrival is computed using _compute_arrival.
    """
    if plane_id is not None:
        cursor.execute("""
            SELECT f.flight_id,
                   f.departure_datetime,
                   f.origin,
                   f.destination
            FROM Flights f
            WHERE f.plane_id = %s
              AND f.flight_status IN ('Scheduled','Occurred')
            ORDER BY f.departure_datetime
        """, (plane_id,))
    elif pilot_id is not None:
        cursor.execute("""
            SELECT f.flight_id,
                   f.departure_datetime,
                   f.origin,
                   f.destination
            FROM Flights f
            JOIN PilotsFlights pf ON pf.flight_id = f.flight_id
            WHERE pf.pilot_id = %s
              AND f.flight_status IN ('Scheduled','Occurred')
            ORDER BY f.departure_datetime
        """, (pilot_id,))
    elif attendant_id is not None:
        cursor.execute("""
            SELECT f.flight_id,
                   f.departure_datetime,
                   f.origin,
                   f.destination
            FROM Flights f
            JOIN FlightAttendantsFlights faf ON faf.flight_id = f.flight_id
            WHERE faf.attendant_id = %s
              AND f.flight_status IN ('Scheduled','Occurred')
            ORDER BY f.departure_datetime
        """, (attendant_id,))
    else:
        return []

    rows = cursor.fetchall()

    flights = []
    for r in rows:
        arrival = _compute_arrival(cursor, r["departure_datetime"], r["origin"], r["destination"])
        flights.append({
            "flight_id": r["flight_id"],
            "departure": r["departure_datetime"],
            "arrival": arrival,
            "origin": r["origin"],
            "destination": r["destination"]
        })
    return flights


def _can_insert_flight_for_resource(cursor, existing_flights, new_dep, new_origin, new_dest):
    """
    Validates if a resource (plane / pilot / attendant) can be assigned to a new flight.

    Conditions:
    - No time overlap between existing flights and the new flight
    - Enough travel time between previous flight -> new flight
    - Enough travel time between new flight -> next flight
    - If no previous flights: resource starts at BASE_AIRPORT
    - If there is no route between locations: treat as instant transfer (0 minutes)
    """

    new_arr = _compute_arrival(cursor, new_dep, new_origin, new_dest)

    # 1) Check simple time overlap
    for fl in existing_flights:
        if fl["departure"] < new_arr and fl["arrival"] > new_dep:
            # Overlapping flights in time
            return False

    # 2) Find closest flight before and after the new flight
    before = [fl for fl in existing_flights if fl["arrival"] <= new_dep]
    after = [fl for fl in existing_flights if fl["departure"] >= new_arr]

    last_before = max(before, key=lambda x: x["arrival"]) if before else None
    first_after = min(after, key=lambda x: x["departure"]) if after else None

    # 2A) Check transfer from previous flight -> new flight
    if last_before:
        prev_loc = last_before["destination"]
        travel_time = _travel_time_between(cursor, prev_loc, new_origin)

        # No route -> assume instant transfer
        if travel_time is None:
            travel_time = timedelta(minutes=0)

        if last_before["arrival"] + travel_time > new_dep:
            # Not enough time to move from previous destination to new origin
            return False
    else:
        # No previous flights -> resource starts at BASE_AIRPORT
        travel_time = _travel_time_between(cursor, BASE_AIRPORT, new_origin)
        if travel_time is None:
            # No route from base to origin -> treat as instant transfer
            travel_time = timedelta(minutes=0)
        # No arrival check needed because there is no prior flight

    # 2B) Check transfer from new flight -> next flight
    if first_after:
        next_loc = first_after["origin"]
        travel_time = _travel_time_between(cursor, new_dest, next_loc)

        # No route -> treat as instant transfer
        if travel_time is None:
            travel_time = timedelta(minutes=0)

        if new_arr + travel_time > first_after["departure"]:
            # Not enough time to move from new destination to next origin
            return False

    # All checks passed
    return True


# ==============================
# Crew size by duration
# ==============================

def get_required_crew_by_duration(duration_hours):
    """
    Business rule:
    - Flights longer than 6 hours require more crew.
    Returns: (required_attendants, required_pilots)
    """
    if duration_hours > 6:
        return 6, 3
    else:
        return 3, 2


# ==============================
# Available planes
# ==============================

def get_available_planes(origin, destination, departure_datetime):
    """
    Returns a list of available planes for a new flight.

    A plane is available if:
    - The flight does not overlap in time with other flights of the same plane
    - There is enough transfer time between its existing flights and the new flight
    - If it has no previous flights -> it is assumed to be at BASE_AIRPORT

    Each returned dict includes:
    - plane_id
    - producer (model)
    - total_seats
    - is_long_flight (bool)
    - last_origin
    - last_destination
    - last_arrival
    """

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    # Compute new flight duration and type
    minutes = _get_flight_duration_minutes(cursor, origin, destination)
    if minutes is None:
        cursor.close()
        conn.close()
        return []

    is_long_flight = minutes > 360  # 6 hours

    # Size constraint: long flights must use large planes
    if is_long_flight:
        size_condition = "size = 'large'"
    else:
        size_condition = "size IN ('small', 'large')"

    # Fetch all planes that match the size condition
    cursor.execute(f"""
        SELECT p.plane_id,
               p.size,
               p.producer
        FROM planes p
        WHERE {size_condition}
    """)
    planes_rows = cursor.fetchall()

    available = []

    for p in planes_rows:
        plane_id = p["plane_id"]

        # Existing flights for this plane
        flights = _get_resource_flights(cursor, plane_id=plane_id)

        # Check if we can assign the new flight to this plane
        if not _can_insert_flight_for_resource(cursor, flights, departure_datetime, origin, destination):
            continue

        # Find last flight before the new flight, if any
        before = [fl for fl in flights if fl["arrival"] < departure_datetime]
        last_flight = max(before, key=lambda x: x["arrival"]) if before else None

        if last_flight:
            last_origin = last_flight["origin"]
            last_destination = last_flight["destination"]
            last_arrival = last_flight["arrival"]
        else:
            last_origin = BASE_AIRPORT
            last_destination = None
            last_arrival = None

        # Compute total seats for the plane
        cursor.execute("""
            SELECT SUM(pc.rows_number * pc.columns_number) AS total_seats
            FROM plane_class pc
            WHERE pc.plane_id = %s
        """, (plane_id,))
        seat_info = cursor.fetchone()
        total_seats = seat_info["total_seats"] or 0

        available.append({
            "plane_id": plane_id,
            "producer": p["producer"],
            "size": p["size"],
            "total_seats": total_seats,
            "is_long_flight": is_long_flight,
            "last_origin": last_origin,
            "last_destination": last_destination,
            "last_arrival": last_arrival
        })

    cursor.close()
    conn.close()
    return available


# ==============================
# Available attendants
# ==============================

def get_available_attendants(flight_datetime, origin=None, destination=None, is_long_flight=None):
    """
    Returns attendants that can be assigned to the given flight.

    Conditions:
    - No overlapping flights
    - Enough transfer time between their previous/next flights and the new flight
    - If they have no previous flights -> they start at BASE_AIRPORT
    - If the flight is long:
        * attendant.training_type must be suitable (e.g. 'long' or 'both')
    """

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    # If origin/destination are missing -> simple fallback (no transfer logic)
    if origin is None or destination is None:
        cursor.execute("""
            SELECT
                a.attendant_id,
                CONCAT(a.first_name, ' ', a.last_name) AS full_name,
                a.training_type,
                a.start_date,
                NULL AS last_departure,
                NULL AS last_destination
            FROM FlightAttendants a
            ORDER BY full_name
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    # Flight duration and "long flight" flag
    minutes = _get_flight_duration_minutes(cursor, origin, destination)
    if minutes is None:
        cursor.close()
        conn.close()
        return []

    if is_long_flight is None:
        is_long_flight = minutes > 360

    # Fetch all attendants
    cursor.execute("""
        SELECT
            a.attendant_id,
            a.first_name,
            a.last_name,
            a.training_type,
            a.start_date
        FROM FlightAttendants a
        ORDER BY a.first_name, a.last_name
    """)
    attendants = cursor.fetchall()

    available = []

    for a in attendants:
        att_id = a["attendant_id"]
        training_type = (a["training_type"] or "").lower()

        # Long flight -> require proper training
        if is_long_flight:
            # adapt these values to your actual training_type domain
            if training_type not in ("long", "both"):
                continue

        # All existing flights of this attendant
        flights = _get_resource_flights(cursor, attendant_id=att_id)

        # Check if he/she can be assigned
        if not _can_insert_flight_for_resource(cursor, flights, flight_datetime, origin, destination):
            continue

        # Last flight before the new one (for display)
        before = [fl for fl in flights if fl["arrival"] < flight_datetime]
        last_flight = max(before, key=lambda x: x["arrival"]) if before else None

        if last_flight:
            last_arrival = last_flight["arrival"]
            last_destination = last_flight["destination"]
        else:
            last_arrival = None
            last_destination = BASE_AIRPORT

        available.append({
            "attendant_id": att_id,
            "full_name": f"{a['first_name']} {a['last_name']}",
            "training_type": a["training_type"],
            "start_date": a["start_date"],
            "last_arrival": last_arrival,
            "last_destination": last_destination
        })

    cursor.close()
    conn.close()
    return available


# ==============================
# Available pilots
# ==============================

def get_available_pilots(flight_datetime, origin=None, destination=None, is_long_flight=None):
    """
    Same logic as get_available_attendants, but for pilots.
    """

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    # Fallback if origin/destination missing
    if origin is None or destination is None:
        cursor.execute("""
            SELECT
                p.pilot_id,
                CONCAT(p.first_name, ' ', p.last_name) AS full_name,
                p.training_type,
                p.start_date,
                NULL AS last_origin,
                NULL AS last_destination
            FROM Pilots p
            ORDER BY full_name
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    minutes = _get_flight_duration_minutes(cursor, origin, destination)
    if minutes is None:
        cursor.close()
        conn.close()
        return []

    if is_long_flight is None:
        is_long_flight = minutes > 360

    cursor.execute("""
        SELECT
            p.pilot_id,
            p.first_name,
            p.last_name,
            p.training_type,
            p.start_date
        FROM Pilots p
        ORDER BY p.first_name, p.last_name
    """)
    pilots = cursor.fetchall()

    available = []

    for p_row in pilots:
        pilot_id = p_row["pilot_id"]
        training_type = (p_row["training_type"] or "").lower()

        if is_long_flight:
            if training_type not in ("long", "both"):
                continue

        flights = _get_resource_flights(cursor, pilot_id=pilot_id)

        if not _can_insert_flight_for_resource(cursor, flights, flight_datetime, origin, destination):
            continue

        before = [fl for fl in flights if fl["arrival"] < flight_datetime]
        last_flight = max(before, key=lambda x: x["arrival"]) if before else None

        if last_flight:
            last_origin = last_flight["origin"]
            last_destination = last_flight["destination"]
            last_arrival = last_flight["arrival"]  # הוסף שעת נחיתה
        else:
            last_origin = BASE_AIRPORT
            last_destination = BASE_AIRPORT
            last_arrival = None

        available.append({
            "pilot_id": pilot_id,
            "full_name": f"{p_row['first_name']} {p_row['last_name']}",
            "training_type": p_row["training_type"],
            "start_date": p_row["start_date"],
            "last_origin": last_origin,
            "last_destination": last_destination,
            "last_arrival": last_arrival  # הוסף לשם שימוש ב-HTML
        })

    cursor.close()
    conn.close()
    return available
