from datetime import datetime, timedelta
from utils import get_connection

class Flight:
        def __init__(
                self,
                departure_date,
                departure_time,
                origin,
                destination,
                regular_price,
                business_price,
                plane_id,
                status="Scheduled"
        ):
            """
            Represents a flight entity.
            """

            self.departure_datetime = datetime.strptime(
                f"{departure_date} {departure_time}",
                "%Y-%m-%d %H:%M"
            )

            self.origin = origin
            self.destination = destination
            self.regular_price = regular_price
            self.business_price = business_price
            self.plane_id = plane_id
            self.status = status
            self.flight_id = None  # will be set after insert

        def get_duration_hours(self):
            """
            Returns flight duration in hours based on origin and destination.
            """

            conn = get_connection("FLYTAU")
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT minutes
                FROM Route
                WHERE origin = %s AND destination = %s
            """, (self.origin, self.destination))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row:
                raise ValueError("Flight duration not found")

            return row["minutes"] / 60

        def get_arrival_datetime(self):
            """
            Calculate the arrival datetime based on departure_datetime and flight duration.
            Assumes no timezone differences.
            """
            try:
                duration_hours = self.get_duration_hours()  # from your existing method
            except ValueError:
                # fallback if duration not found
                duration_hours = 0

            arrival_datetime = self.departure_datetime + timedelta(hours=duration_hours)
            return arrival_datetime

        def send_to_db(self):
            """
            Insert flight into DB and store generated flight_id.
            """

            conn = get_connection("FLYTAU")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO Flights (
                    departure_datetime,
                    origin,
                    destination,
                    flight_status,
                    regular_price,
                    business_price,
                    plane_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                self.departure_datetime,
                self.origin,
                self.destination,
                self.status,
                self.regular_price,
                self.business_price,
                self.plane_id
            ))

            conn.commit()

            # Get auto-generated flight_id
            self.flight_id = cursor.lastrowid

            cursor.close()
            conn.close()

        def assign_attendants(self, attendant_ids):
            """
            Assigns attendants to the flight.
            """

            conn = get_connection("FLYTAU")
            cursor = conn.cursor()

            for attendant_id in attendant_ids:
                cursor.execute("""
                    INSERT INTO FlightAttendantsFlights (flight_id, attendant_id)
                    VALUES (%s, %s)
                """, (self.flight_id, attendant_id))

            conn.commit()
            cursor.close()
            conn.close()

        def assign_pilots(self, pilot_ids):
            """
            Assigns pilots to the flight.
            """

            conn = get_connection("FLYTAU")
            cursor = conn.cursor()

            for pilot_id in pilot_ids:
                cursor.execute("""
                    INSERT INTO PilotsFlights (flight_id, pilot_id)
                    VALUES (%s, %s)
                """, (self.flight_id, pilot_id))

            conn.commit()
            cursor.close()
            conn.close()

        @staticmethod
        def get_by_id(flight_id):
            conn = get_connection("FLYTAU")
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT flight_id, departure_datetime, origin, destination,
                       flight_status, regular_price, business_price, plane_id
                FROM Flights
                WHERE flight_id = %s
            """
            cursor.execute(query, (flight_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            return row

        @staticmethod
        def cancel_flight(flight_id):
            conn = get_connection("FLYTAU")
            cursor = conn.cursor()

            cursor.execute("DELETE FROM PilotsFlights WHERE flight_id = %s", (flight_id,))
            cursor.execute("DELETE FROM FlightAttendantsFlights WHERE flight_id = %s", (flight_id,))

            cursor.execute("""
                UPDATE Flights
                SET flight_status = 'Cancelled'
                WHERE flight_id = %s
            """, (flight_id,))

            conn.commit()
            cursor.close()
            conn.close()

        @staticmethod
        def get_all():
            conn = get_connection("FLYTAU")
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT flight_id, departure_datetime, origin, destination, flight_status
                FROM Flights
                ORDER BY departure_datetime ASC
            """)

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            return rows

        @staticmethod
        def can_cancel(flight_datetime):
            now = datetime.now()
            diff = flight_datetime - now
            return diff.total_seconds() >= 72 * 3600


class Employee:
    def __init__(self, employee_id, first_name, last_name,
                 city, street, house_number, start_date):
        self.employee_id = employee_id
        self.first_name = first_name
        self.last_name = last_name
        self.address = (city, street, house_number)
        self.start_date = start_date
        self.phone_numbers = []

class Pilot(Employee):
    def __init__(self, pilot_id, first_name, last_name,
                 city, street, house_number, start_date, training_type):
        super().__init__(pilot_id, first_name, last_name,
                         city, street, house_number, start_date)
        self.training_type = training_type  # short / long

class Manager(Employee):
    def __init__(self, manager_id, first_name, last_name,
                 city, street, house_number, start_date, password):
        super().__init__(manager_id, first_name, last_name,
                         city, street, house_number, start_date)
        self.password = password



