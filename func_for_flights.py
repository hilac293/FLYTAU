from datetime import timedelta
from utils import get_connection

def get_required_crew_by_duration(duration_hours):
    """
    Business rule:
    - Flights longer than 6 hours require more crew.
    """

    if duration_hours > 6:
        return 6, 3   # attendants, pilots
    else:
        return 3, 2


def get_available_attendants(flight_datetime):
    """
    Returns attendants that are not assigned to overlapping flights.
    Includes last flight information if exists.
    """

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            a.attendant_id,
            CONCAT(a.first_name, ' ', a.last_name) AS full_name,
            a.training_type,
            a.start_date,
            f.departure_datetime AS last_departure,
            f.destination AS last_destination
        FROM FlightAttendants a
        LEFT JOIN FlightAttendantsFlights faf ON a.attendant_id = faf.attendant_id
        LEFT JOIN Flights f ON f.flight_id = faf.flight_id
        WHERE a.attendant_id NOT IN (
            SELECT faf2.attendant_id
            FROM FlightAttendantsFlights faf2
            JOIN Flights f2 ON f2.flight_id = faf2.flight_id
            WHERE f2.departure_datetime = %s
        )
        ORDER BY full_name;

    """, (flight_datetime,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_available_pilots(flight_datetime):
    """
    Returns pilots that are not assigned to overlapping flights.
    Includes last flight information if exists.
    """

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            p.pilot_id,
            CONCAT(p.first_name, ' ', p.last_name) AS full_name,
            p.training_type,
            p.start_date,
            f.origin AS last_origin,
            f.destination AS last_destination
        FROM Pilots p
        LEFT JOIN PilotsFlights pf ON p.pilot_id = pf.pilot_id
        LEFT JOIN Flights f ON f.flight_id = pf.flight_id
        WHERE p.pilot_id NOT IN (
            SELECT pf2.pilot_id
            FROM PilotsFlights pf2
            JOIN Flights f2 ON f2.flight_id = pf2.flight_id
            WHERE f2.departure_datetime <= %s
        )
        ORDER BY full_name
    """, (flight_datetime,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_available_planes(origin, destination, departure_datetime):

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT minutes
        FROM Flight_time
        WHERE origin = %s AND destination = %s
    """, (origin, destination))

    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return []

    duration_minutes = row["minutes"]
    is_long_flight = duration_minutes > 360


    if is_long_flight:
        size_condition = "size = 'large'"
    else:
        size_condition = "size IN ('small', 'large')"


    buffer = timedelta(minutes=duration_minutes + 60)
    start_time = departure_datetime - buffer
    end_time = departure_datetime + buffer


    query = f"""
        SELECT *
        FROM planes
        WHERE {size_condition}
        AND plane_id NOT IN (
            SELECT plane_id
            FROM Flights
            WHERE departure_datetime BETWEEN %s AND %s
        )
    """

    cursor.execute(query, (start_time, end_time))
    planes = cursor.fetchall()

    cursor.close()
    conn.close()

    return planes

