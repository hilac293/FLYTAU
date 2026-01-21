import matplotlib.pyplot as plt
import os
from utils import get_connection

def report_avg_capacity():

    import os
    import matplotlib.pyplot as plt
    from utils import get_connection

    os.makedirs("static/reports", exist_ok=True)

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT ROUND(AVG(flight_capacity), 2) AS avg_capacity_percentage
        FROM (
            SELECT 
                f.flight_id,
                COUNT(bs.seat_number) / s.total_seats * 100 AS flight_capacity
            FROM Flights f
            LEFT JOIN Orders o
                ON f.flight_id = o.flight_id
                AND o.order_status = 'COMPLETED'
            LEFT JOIN Booking_Seats bs
                ON o.order_id = bs.order_id
            JOIN (
                SELECT plane_id, COUNT(*) AS total_seats
                FROM Seats
                GROUP BY plane_id
            ) s ON f.plane_id = s.plane_id
            WHERE f.flight_status = 'Occurred'
            GROUP BY f.flight_id, s.total_seats
        ) t
    """)

    avg_capacity = cursor.fetchone()["avg_capacity_percentage"] or 0
    cursor.close()
    conn.close()

    # ===== גרף פאי (רק שינוי צבע החתך) =====
    plt.figure(figsize=(4, 4))
    plt.pie(
        [avg_capacity, 100 - avg_capacity],
        labels=["Occupied", "Free"],
        autopct="%1.0f%%",
        startangle=90,
        colors=["#4169E1", "#E0E0E0"],  # Royal Blue במקום ירוק
        wedgeprops={"edgecolor": "white"}
    )

    plt.tight_layout()
    plt.savefig("static/reports/avg_capacity.png", dpi=150)
    plt.close()

    return avg_capacity

def report_revenue():
    import matplotlib.pyplot as plt
    import os
    from utils import get_connection

    os.makedirs("static/reports", exist_ok=True)

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            p.producer AS plane_producer,
            bs.class_type AS seat_class,
            SUM(
                CASE
                    WHEN bs.class_type = 'Business' THEN f.business_price
                    WHEN bs.class_type = 'Economy'  THEN f.regular_price
                END
            ) AS total_revenue
        FROM Booking_Seats bs
        JOIN Orders o ON bs.order_id = o.order_id
        JOIN Flights f ON o.flight_id = f.flight_id
        JOIN planes p ON f.plane_id = p.plane_id
        WHERE o.order_status = 'COMPLETED'
        GROUP BY p.producer, bs.class_type
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    producers = sorted(set(r["plane_producer"] for r in rows))
    business = []
    economy = []

    for p in producers:
        business.append(
            sum(r["total_revenue"] for r in rows
                if r["plane_producer"] == p and r["seat_class"] == "Business")
        )
        economy.append(
            sum(r["total_revenue"] for r in rows
                if r["plane_producer"] == p and r["seat_class"] == "Economy")
        )

    x = range(len(producers))

    # ===== עיצוב הגרף =====
    plt.figure(figsize=(6, 4))
    plt.bar(x, business, width=0.4, label="Business", color="#1976D2")
    plt.bar([i + 0.4 for i in x], economy, width=0.4, label="Economy", color="#90CAF9")

    plt.xticks([i + 0.2 for i in x], producers)
    plt.ylabel("Revenue")
    plt.legend(frameon=False)
    plt.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig("static/reports/revenue.png", dpi=150)
    plt.close()

    return rows

def report_employee_hours():
    from utils import get_connection

    conn = get_connection("FLYTAU")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT employee_type, employee_name, length_flight,
               ROUND(SUM(total_m) / 60, 2) AS total_hours
        FROM (
            SELECT 'Pilot' AS employee_type,
                   CONCAT(p.first_name, ' ', p.last_name) AS employee_name,
                   CASE WHEN r.minutes <= 360 THEN 'Short' ELSE 'Long' END AS length_flight,
                   r.minutes AS total_m
            FROM Flights f
            JOIN route r ON f.origin = r.origin AND f.destination = r.destination
            JOIN PilotsFlights pf ON f.flight_id = pf.flight_id
            JOIN Pilots p ON pf.pilot_id = p.pilot_id
            WHERE f.flight_status = 'Occurred'

            UNION ALL

            SELECT 'Attendant',
                   CONCAT(fa.first_name, ' ', fa.last_name),
                   CASE WHEN r.minutes <= 360 THEN 'Short' ELSE 'Long' END,
                   r.minutes
            FROM Flights f
            JOIN route r ON f.origin = r.origin AND f.destination = r.destination
            JOIN FlightAttendantsFlights faf ON f.flight_id = faf.flight_id
            JOIN FlightAttendants fa ON faf.attendant_id = fa.attendant_id
            WHERE f.flight_status = 'Occurred'
        ) t
        GROUP BY employee_type, employee_name, length_flight
        ORDER BY employee_name
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows
