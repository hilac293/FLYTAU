from utils import get_connection
from datetime import datetime, timedelta

class Order:
    def __init__(self, total_amount, flight_id,
                 order_status="active",
                 email_guest=None, email_registered=None,
                 order_date=None):
  
        self.order_id = None  # Will be set after saving to DB
        self.total_amount = total_amount
        self.flight_id = flight_id
        self.order_status = order_status
        self.email_guest = email_guest
        self.email_registered = email_registered
        self.order_date = order_date or datetime.now().strftime("%Y-%m-%d %H:%M")
        self.seats = []  # List of seat_ids (for code side convenience)

    # --- Save order to DB ---
    def save_to_db(self):
  
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Orders
            (order_status, total_amount, order_date, email_guest, email_registered, flight_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (self.order_status, self.total_amount, self.order_date,
              self.email_guest, self.email_registered, self.flight_id))

        conn.commit()
        self.order_id = cursor.lastrowid
        cursor.close()
        conn.close()

    # --- Update order status ---
    def update_status(self, new_status):
 
        self.order_status = new_status
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()
        cursor.execute("UPDATE Orders SET order_status = %s WHERE order_id = %s",
                       (self.order_status, self.order_id))
        conn.commit()
        cursor.close()
        conn.close()

    # --- Assign seats to this order (smart version) ---
    def assign_seats(self, new_seat_ids):
  
        if not self.order_id:
            raise ValueError("Order must be saved in DB before assigning seats.")

        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        # --- Get existing seats ---
        cursor.execute("SELECT seat_id FROM Order_Seats WHERE order_id = %s", (self.order_id,))
        rows = cursor.fetchall()
        existing_seats = set(row['seat_id'] for row in rows)

        new_seats = set(new_seat_ids)

        # --- Add new seats ---
        seats_to_add = new_seats - existing_seats
        for seat_id in seats_to_add:
            cursor.execute("INSERT INTO Order_Seats (order_id, seat_id) VALUES (%s, %s)",
                           (self.order_id, seat_id))

        # --- Remove seats that were removed ---
        seats_to_remove = existing_seats - new_seats
        for seat_id in seats_to_remove:
            cursor.execute("DELETE FROM Order_Seats WHERE order_id = %s AND seat_id = %s",
                           (self.order_id, seat_id))

        conn.commit()
        cursor.close()
        conn.close()

        # Update the object's seat list
        self.seats = list(new_seat_ids)

    # --- Fetch seats for this order ---
    def get_seats(self):
        """
        Returns a list of seat_ids assigned to this order.
        """
        if not self.order_id:
            return []

        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT seat_id FROM Order_Seats WHERE order_id = %s", (self.order_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        self.seats = [row['seat_id'] for row in rows]
        return self.seats

    # --- Cancel order with 5% fee if >36h before flight ---
    def cancel_order(self):

        if not self.order_id:
            raise ValueError("Order must be saved in DB before cancellation.")

        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        # --- Get flight departure datetime ---
        cursor.execute("SELECT departure_datetime FROM Flights WHERE flight_id = %s", (self.flight_id,))
        flight = cursor.fetchone()
        if not flight:
            cursor.close()
            conn.close()
            raise ValueError("Flight not found in DB.")

        flight_datetime = flight['departure_datetime']
        now = datetime.now()

        # --- Check 36-hour rule ---
        if flight_datetime - now < timedelta(hours=36):
            cursor.close()
            conn.close()
            raise ValueError("Cannot cancel order less than 36 hours before the flight.")

        # --- Calculate refund and cancellation fee ---
        cancellation_fee = self.total_amount * 0.05
        refund_amount = self.total_amount - cancellation_fee
        self.total_amount = 0  # clear payment

        # --- Update order status in DB ---
        self.order_status = "cancelled_by_customer"
        cursor.execute("""
            UPDATE Orders
            SET order_status = %s, total_amount = %s
            WHERE order_id = %s
        """, (self.order_status, self.total_amount, self.order_id))

        # --- Release seats ---
        cursor.execute("DELETE FROM Order_Seats WHERE order_id = %s", (self.order_id,))

        conn.commit()
        cursor.close()
        conn.close()

        # Clear seats in object
        self.seats = []

        return refund_amount




        
