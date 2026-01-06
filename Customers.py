from werkzeug.security import check_password_hash

from utils import get_connection
from datetime import datetime, date

class Customer:
    def __init__(self, first_name, last_name, email, phones=None):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phones = phones if phones else []

    # --- Update first name and save to DB ---
    def update_first_name(self, new_first_name):
        self.first_name = new_first_name
        self.save_to_db()  # Save changes to database

    # --- Update last name and save to DB ---
    def update_last_name(self, new_last_name):
        self.last_name = new_last_name
        self.save_to_db()  # Save changes to database

    # --- Update email and save to DB ---
    def update_email(self, new_email):
        old_email = self.email
        self.email = new_email
        self.update_email_in_db(old_email)  # Handle DB update

    # --- Add a phone number ---
    def add_phone(self, phone):
        if phone not in self.phones:
            self.phones.append(phone)
            self.save_to_db()

    # --- Remove a phone number ---
    def remove_phone(self, phone):
        if phone in self.phones:
            self.phones.remove(phone)
            self.save_to_db()




class Guest(Customer):
    def save_to_db(self):
        """
        Insert or update Guest in FLYTAU DB and update phones.
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        # Insert or update guest info
        cursor.execute("""
            INSERT INTO guests (email, first_name, last_name)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE first_name=%s, last_name=%s
        """, (self.email, self.first_name, self.last_name,
              self.first_name, self.last_name))

        # Update phones
        cursor.execute("DELETE FROM guest_phones WHERE email = %s", (self.email,))
        for phone in self.phones:
            cursor.execute("INSERT INTO guest_phones (email, phone_number) VALUES (%s, %s)",
                           (self.email, phone))

        conn.commit()
        cursor.close()
        conn.close()


    def update_email_in_db(self, old_email):
        """
        Update email in Guests and Guest_Phones tables
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        cursor.execute("UPDATE guests SET email = %s WHERE email = %s", (self.email, old_email))
        cursor.execute("UPDATE guest_phones SET email = %s WHERE email = %s", (self.email, old_email))

        conn.commit()
        cursor.close()
        conn.close()



class Registered(Customer):
    def __init__(self, first_name, last_name, email, passport_number,
                 birth_date=None, registration_date=None, password=None, phones=None):
        super().__init__(first_name, last_name, email, phones)
        self.passport_number = passport_number
        self.birth_date = birth_date
        self.registration_date = registration_date
        self.password = password
        self.phones = phones or []

    def save_to_db(self):
        """
        Insert or update registered user in FLYTAU DB and update phones.
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        query = """
            INSERT INTO registered
            (passport_number, first_name, last_name, email, birth_date, registration_date, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE first_name=%s, last_name=%s, email=%s,
            birth_date=%s, registration_date=%s, password=%s
        """

        params = (
            self.passport_number, self.first_name, self.last_name, self.email,
            self.birth_date, self.registration_date, self.password,  # VALUES
            self.first_name, self.last_name, self.email,
            self.birth_date, self.registration_date, self.password  # ON DUPLICATE KEY UPDATE
        )

        print("SQL Query:", query)
        print("Parameters:", params)

        # cursor.execute(query, params)

        try:
            cursor.execute(query, params)
        except Exception as e:
            print("SQL execution error:", e)
            raise

        # Update phones
        cursor.execute("DELETE FROM registered_phones WHERE passport_number = %s", (self.passport_number,))
        for phone in self.phones:
            cursor.execute("INSERT INTO registered_phones (passport_number, phone_number) VALUES (%s, %s)",
                           (self.passport_number, phone))

        conn.commit()
        cursor.close()
        conn.close()

    @classmethod
    def find_by_email(cls, email):
        """
        Find a registered user in the database by email.
        Returns:
            - Registered object if user exists
            - None if no user is found
        """
        # 1️⃣ Connect to database
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)  # use dictionary for easier access

        # 2️⃣ Fetch user basic information from 'registered' table
        cursor.execute(
            "SELECT * FROM registered WHERE email = %s",
            (email,)
        )
        user_row = cursor.fetchone()

        # 3️⃣ If user not found, close connection and return None
        if not user_row:
            cursor.close()
            conn.close()
            return None

        passport_number = user_row["passport_number"]

        # 4️⃣ Fetch user's phone numbers from 'registered_phones' table
        cursor.execute(
            "SELECT phone_number FROM registered_phones WHERE passport_number = %s",
            (passport_number,)
        )
        phones_rows = cursor.fetchall()
        phones = [row["phone_number"] for row in phones_rows]  # convert to list

        # 5️⃣ Close database connection
        cursor.close()
        conn.close()

        # 6️⃣ Create and return a Registered object
        return cls(
            first_name=user_row["first_name"],
            last_name=user_row["last_name"],
            email=user_row["email"],
            passport_number=user_row["passport_number"],
            birth_date=user_row["birth_date"],
            registration_date=user_row["registration_date"],
            password=user_row["password"],
            phones=phones
        )

    def update_email_in_db(self, old_email):
        """
        Update email in registered table
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        cursor.execute("UPDATE registered SET email = %s WHERE email = %s", (self.email, old_email))

        conn.commit()
        cursor.close()
        conn.close()



    # --- Check if the input password matches the hashed password ---
    def check_password(self, input_password):
        """
        Check if the input_password matches the hashed password stored in the DB.
        """
        if not self.password:
            return False
        return check_password_hash(self.password, input_password)

    # --- Update password in the database ---
    def update_password(self, new_password):
        """
        Hash the new password and update it in the database.
        """
        # 1️⃣ Hash the new password
        hashed_password = generate_password_hash(new_password)
        self.password = hashed_password

        # 2️⃣ Connect to DB and update
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE registered SET password = %s WHERE passport_number = %s",
            (self.password, self.passport_number)
        )
        conn.commit()
        cursor.close()
        conn.close()

    # --- Fetch order history for this registered customer ---
    def get_order_history(self, status=None):
        conn = get_connection("FLYTAU")
        cursor = conn.cursor(dictionary=True)

        if status:
            cursor.execute("""
                SELECT *
                FROM Orders
                WHERE email_registered = %s AND order_status = %s
                ORDER BY order_date DESC
            """, (self.email, status))
        else:
            cursor.execute("""
                SELECT *
                FROM Orders
                WHERE email_registered = %s
                ORDER BY order_date DESC
            """, (self.email,))

        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return orders

    # --- Fill order object with user's personal details (optional, for code side) ---
    def auto_fill_details_for_order(self, order):
        order.first_name = self.first_name
        order.last_name = self.last_name
        order.email = self.email
        order.phones = list(self.phones)
        
