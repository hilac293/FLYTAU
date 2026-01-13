from datetime import date
from enum import Enum
from typing import List
from utils import get_connection
from utils import get_connection

# --- Enums ---
class PlaneSize(Enum):
    SMALL = "Small"
    LARGE = "Large"

    @classmethod
    def from_string(cls, value: str):
        return cls[value.strip().upper()]

class PlaneProducer(Enum):
    BOEING = "Boeing"
    AIRBUS = "Airbus"
    DASSAULT = "Dassault"

class SeatClass(Enum):
    ECONOMY = "Economy"
    BUSINESS = "Business"

class FlightType(Enum):
    SHORT = "Short"
    LONG = "Long"

# --- PlaneClass represents a single class inside a plane ---
class PlaneClass:
    def __init__(self, class_type: SeatClass, rows_number: int, columns_number: int):
        self.class_type = class_type
        self.rows_number = rows_number
        self.columns_number = columns_number
        self.seats: List[Seat] = []  # רשימת מושבים במחלקה

    def seats_sum(self) -> int:
        """Return total seats in this class."""
        return self.rows_number * self.columns_number

    def generate_seats(self):
        """Automatically create Seat objects for this class."""
        self.seats = []
        for row in range(1, self.rows_number + 1):
            for col in range(self.columns_number):
                column_letter = chr(ord('A') + col)  # A, B, C...
                seat_number = (row - 1) * self.columns_number + col + 1
                self.seats.append(Seat(seat_number, row, column_letter, self))
        return self.seats

    def get_plane_classes_map(plane_id):
        """
        Fetch all PlaneClass objects for a given plane from DB,
        and return a mapping: class_type string -> PlaneClass object
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT class_type, rows_number, columns_number
            FROM plane_class
            WHERE plane_id = %s
        """
        cursor.execute(query, (plane_id,))
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        # Create mapping: class_type string -> PlaneClass object
        classes_map = {}
        for row in rows:
            plane_class_obj = PlaneClass(
                class_type=row["class_type"],  # or SeatClass enum if needed
                rows_number=row["rows_number"],
                columns_number=row["columns_number"]
            )
            classes_map[row["class_type"]] = plane_class_obj

        return classes_map


class Seat:
    def __init__(self,plane_id,  seat_number: int, row_number: int, column_letter: str, plane_class: PlaneClass):
        """
        seat_number: מספר המושב הייחודי בתוך המחלקה
        row_number: מספר השורה
        column_letter: אות הטור (A, B, C...)
        plane_class: האובייקט PlaneClass שבו המושב נמצא
        status: מצב המושב, לדוגמה 'available' או 'occupied'
        """
        self.seat_number = seat_number
        self.row_number = row_number
        self.column_letter = column_letter
        self.plane_class = plane_class
        self.class_type = plane_class.class_type  # יורש את סוג הכיתה
        self.plane_id = plane_id



    @staticmethod
    def get_seats_for_plane(plane_id):
        """
        Returns all Seat objects for a given plane.
        Each seat is connected to its PlaneClass object.
        This method DOES NOT care about availability.
        """

        # Step 1: get all plane classes for this plane as a dictionary
        # key = class_type, value = PlaneClass object
        classes_map = PlaneClass.get_plane_classes_map(plane_id)

        # Step 2: fetch all seats from DB
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT plane_id, class_type, seat_number, rownumber, column_letter
            FROM Seats
            WHERE plane_id = %s
            ORDER BY rownumber, column_letter
        """
        cursor.execute(query, (plane_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Step 3: create Seat objects and attach them to PlaneClass
        seats = []
        for row in rows:
            plane_class_obj = classes_map.get(row["class_type"])

            # Safety fallback (should normally not happen)
            if not plane_class_obj:
                plane_class_obj = PlaneClass(row["class_type"], 0, 0)
                classes_map[row["class_type"]] = plane_class_obj

            seat = Seat(
                plane_id=row["plane_id"],
                plane_class=plane_class_obj,
                seat_number=row["seat_number"],
                row_number=row["rownumber"],
                column_letter=row["column_letter"]
            )
            seats.append(seat)

        return seats

    @staticmethod
    def get_taken_seats_for_flight(flight_id):
        """
        Returns a set of seat_numbers that are currently taken for a given flight.

        A seat is considered taken if:
        - It appears in Booking_Seats
        - And its order is still ACTIVE

        If an order is cancelled (by customer or manager),
        the seat becomes available automatically.
        """

        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT bs.seat_number
            FROM Booking_Seats bs
            JOIN Orders o ON o.order_id = bs.order_id
            WHERE o.flight_id = %s
              AND o.order_status IN ('ACTIVE', 'COMPLETED')
        """

        cursor.execute(query, (flight_id,))
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convert list of dicts into a set for fast lookup
        taken_seats = {row["seat_number"] for row in rows}
        return taken_seats




# --- Planes represents a single plane with all its classes ---
class Planes:
    def __init__(self, plane_id: int, size: PlaneSize, producer: PlaneProducer, purchase_date: date):
        self.plane_id = plane_id
        self.size = size
        self.producer = producer
        self.purchase_date = purchase_date
        self.classes: List[PlaneClass] = []

    def required_pilots(self) -> int:
        return 3 if self.size == PlaneSize.LARGE else 2

    def required_attendants(self) -> int:
        return 6 if self.size == PlaneSize.LARGE else 3

    def allowed_flight_types(self) -> List[FlightType]:
        if self.size == PlaneSize.LARGE:
            return [FlightType.SHORT, FlightType.LONG]
        return [FlightType.SHORT]

    def allowed_classes(self) -> List[SeatClass]:
        if self.size == PlaneSize.LARGE:
            return [SeatClass.ECONOMY, SeatClass.BUSINESS]
        return [SeatClass.ECONOMY]

    def is_large(self) -> bool:
        return self.size == PlaneSize.LARGE

    def add_class(self, plane_class: PlaneClass):
        self.classes.append(plane_class)

    def total_seats(self) -> int:
        """Return total seats in the plane (all classes)."""
        return sum(c.seats_sum() for c in self.classes)

    # --- Optional: methods to sync with DB ---
    def save_to_db(self):
        """Insert plane and its classes into DB."""
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO planes (plane_id, size, producer, purchase_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE size=%s, producer=%s, purchase_date=%s
        """, (self.plane_id, self.size.value, self.producer.value, self.purchase_date,
              self.size.value, self.producer.value, self.purchase_date))

        # Insert plane classes
        for plane_class in self.classes:
            cursor.execute("""
                INSERT INTO plane_class (plane_id, class_type, rows_number, columns_number)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE rows_number=%s, columns_number=%s
            """, (self.plane_id, plane_class.class_type.value, plane_class.rows_number, plane_class.columns_number,
                  plane_class.rows_number, plane_class.columns_number))

        conn.commit()
        cursor.close()
        conn.close()

