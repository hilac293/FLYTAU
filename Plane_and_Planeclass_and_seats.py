from datetime import date
from enum import Enum
from typing import List
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

class Seat:
    def __init__(self, seat_number: int, row_number: int, column_letter: str, plane_class: PlaneClass, status: str = "available"):
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
        self.status = status

    def is_available(self) -> bool:
        """Return True if the seat is available."""
        return self.status == "available"

    def occupy(self):
        """Mark the seat as occupied."""
        self.status = "occupied"

    def free(self):
        """Mark the seat as available."""
        self.status = "available"



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

