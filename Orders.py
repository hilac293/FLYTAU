import mysql
from flask import session

from utils import get_connection
from datetime import datetime, timedelta
from flights_and_workers import Flight

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
        self.order_date = order_date or datetime.now().strftime("%Y-%m-%d")

        # Each seat will be a dict:
        # { plane_id, class_type, seat_number }
        self.seats = []

    # -----------------------------
    # Save the order to Orders table
    # -----------------------------
    def save_to_db(self):
        """
        Save the order to the database.
        Inserts NULL for guest_email if it's a registered user.
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        try:
            print("CURRENT SESSION:", dict(session))

            # --- Choose correct emails ---
            if session["logged_in"]:
                registered_email = session["user"]["email"]
                guest_email = None
            else:
                guest_email = session["booking"]["customer"]["email"]
                print(guest_email)
                registered_email = None
            

            # --- Insert order ---
            cursor.execute("""
                INSERT INTO Orders
                (order_status, total_amount, guest_email, registered_email, flight_id, order_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                self.order_status,
                self.total_amount,
                guest_email,  # None if registered user
                registered_email,  # None if guest
                self.flight_id,
                self.order_date
            ))

            conn.commit()
            self.order_id = cursor.lastrowid

        except mysql.connector.Error as e:
            print("Database error:", e)
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    # -----------------------------------
    # Save all seats to booking_seats table
    # -----------------------------------
    def save_seats_to_db(self):
        """
        Saves each selected seat to booking_seats table.
        booking_seats:
        (order_id, plane_id, class_type, seat_number)
        """

        if self.order_id is None:
            raise Exception("Order must be saved before saving seats")



        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        for seat in self.seats:
            cursor.execute("""
                INSERT INTO booking_seats
                (order_id, plane_id, class_type, seat_number)
                VALUES (%s, %s, %s, %s)
            """, (
                self.order_id,
                seat["plane_id"],
                seat["class_type"],
                seat["seat_number"]
            ))

        conn.commit()
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

    def load_customer_details(self):
        """
        Load customer details into self.customer.
        Works for both guest and registered users.
        Result:
        self.customer = {
            first_name,
            last_name,
            email,
            phones: []
        }
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        # Case 1: Guest order
        if self.email_guest:
            # Get guest basic info
            cursor.execute("""
                SELECT first_name, last_name, email
                FROM Guests
                WHERE email = %s
            """, (self.email_guest,))
            guest = cursor.fetchone()

            # Get guest phones
            cursor.execute("""
                SELECT phone_number
                FROM guest_phones
                WHERE email = %s
            """, (self.email_guest,))
            phones = [row["phone_number"] for row in cursor.fetchall()]

            self.customer = {
                "first_name": guest["first_name"],
                "last_name": guest["last_name"],
                "email": guest["email"],
                "phones": phones,
                "type": "guest"
            }

        # Case 2: Registered order
        elif self.email_registered:
            # Get registered user basic info
            cursor.execute("""
                SELECT passport_number, first_name, last_name, email
                FROM Registered
                WHERE email = %s
            """, (self.email_registered,))
            user = cursor.fetchone()

            # Get registered phones
            cursor.execute("""
                SELECT phone_number
                FROM registered_phones
                WHERE passport_number = %s
            """, (user["passport_number"],))
            phones = [row["phone_number"] for row in cursor.fetchall()]

            self.customer = {
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "phones": phones,
                "type": "registered"
            }

        else:
            self.customer = None

        cursor.close()
        conn.close()

    @classmethod
    def get_by_id(cls, booking_id):
        """
        Fetch an order and attach flight details.
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        # Get the order
        cursor.execute("SELECT * FROM Orders WHERE order_id = %s", (booking_id,))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return None

        order = cls(
            total_amount=float(result["total_amount"]),
            flight_id=result["flight_id"],
            order_status=result["order_status"],
            email_guest=result["guest_email"],
            email_registered=result["registered_email"],
            order_date=result["order_date"]
        )
        order.order_id = result["order_id"]

        # Get seats
        order.seats = cls.get_seats_for_order(order.order_id)

        data = Flight.get_by_id(order.flight_id)
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
        order.departure_datetime = flight.departure_datetime
        order.arrival_datetime = flight.get_arrival_datetime()
        order.duration = flight.get_duration_hours()
        order.origin = flight.origin
        order.destination = flight.destination

        order.load_customer_details()

        return order

    # Inside Order class
    @classmethod
    def get_by_registered_email(cls, email):
        """
        Fetch all orders made by a registered user email.
        Returns a list of Order instances.
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT *
            FROM Orders
            WHERE registered_email = %s
            ORDER BY order_date DESC
        """, (email,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        bookings = []
        for row in rows:
            order = cls(
                total_amount=float(row["total_amount"]),
                flight_id=row["flight_id"],
                order_status=row["order_status"],
                email_guest=row["guest_email"],
                email_registered=row["registered_email"],
                order_date=row["order_date"]
            )
            order.order_id = row["order_id"]
            order.seats = cls.get_seats_for_order(order.order_id)
            bookings.append(order)
        return bookings

    @classmethod
    def get_by_email_and_code(cls, email, booking_code):
        """
        Look up an order in the DB using the guest email and booking code.
        Returns an Order instance if found, else None.
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT * 
            FROM orders
            WHERE order_id = %s AND guest_email = %s
        """
        cursor.execute(query, (booking_code, email))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            return None

        # Create an Order instance from DB row
        order = cls(
            total_amount=result["total_amount"],
            flight_id=result["flight_id"],
            order_status=result["order_status"],
            email_guest=result["guest_email"],
            email_registered=result["registered_email"],
            order_date=result["order_date"]
        )
        order.order_id = result["order_id"]

        # Fetch seats for this order
        order.seats = cls.get_seats_for_order(order.order_id)

        return order

    # ====================================================
    # Helper: fetch seats for a given order
    # ====================================================
    @staticmethod
    def get_seats_for_order(order_id):
        """
        Returns a list of seat dicts for the given order_id.
        Each seat dict: { plane_id, class_type, seat_number }
        """
        conn = get_connection("FLYTAU")

        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT plane_id, class_type, seat_number
            FROM booking_seats
            WHERE order_id = %s
        """
        cursor.execute(query, (order_id,))
        seats = cursor.fetchall()
        cursor.close()
        conn.close()
        return seats

    # In Order class
    def cancel_order(self):
        """
        Cancel the order if flight is at least 36 hours in the future.
        Deduct 5% cancellation fee from total_amount.
        Returns refund amount.
        """

        if not self.order_id:
            raise ValueError("Order must be saved in DB before cancellation.")

        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        # Get flight departure datetime
        cursor.execute("SELECT departure_datetime FROM Flights WHERE flight_id = %s", (self.flight_id,))
        flight = cursor.fetchone()
        if not flight:
            cursor.close()
            conn.close()
            raise ValueError("Flight not found in DB.")

        departure_dt = flight["departure_datetime"]
        now = datetime.now()

        # Check 36-hour rule
        if departure_dt - now < timedelta(hours=36):
            cursor.close()
            conn.close()
            raise ValueError("Cannot cancel order less than 36 hours before the flight.")

        # Calculate cancellation fee (5%)
        cancellation_fee = self.total_amount * 0.05
        refund_amount = self.total_amount - cancellation_fee

        # Update order in DB
        self.order_status = "cancelled_by_customer"
        self.total_amount = refund_amount  # update total to reflect deduction
        cursor.execute("""
            UPDATE Orders
            SET order_status=%s, total_amount=%s
            WHERE order_id=%s
        """, (self.order_status, self.total_amount, self.order_id))

        # Remove seats from booking_seats
        cursor.execute("DELETE FROM Booking_Seats WHERE order_id=%s", (self.order_id,))

        conn.commit()
        cursor.close()
        conn.close()


        return refund_amount, cancellation_fee





        
