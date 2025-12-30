from utils import get_connection  

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
            INSERT INTO Guests (email, first_name, last_name)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE first_name=%s, last_name=%s
        """, (self.email, self.first_name, self.last_name,
              self.first_name, self.last_name))

        # Update phones
        cursor.execute("DELETE FROM Guest_Phones WHERE email = %s", (self.email,))
        for phone in self.phones:
            cursor.execute("INSERT INTO Guest_Phones (email, phone_number) VALUES (%s, %s)",
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

        cursor.execute("UPDATE Guests SET email = %s WHERE email = %s", (self.email, old_email))
        cursor.execute("UPDATE Guest_Phones SET email = %s WHERE email = %s", (self.email, old_email))

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

    def save_to_db(self):
        """
        Insert or update Registered user in FLYTAU DB and update phones.
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Registered
            (passport_number, first_name, last_name, email, birth_date, registration_date, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE first_name=%s, last_name=%s, email=%s,
            birth_date=%s, registration_date=%s, password=%s
        """, (self.passport_number, self.first_name, self.last_name, self.email,
              self.birth_date, self.registration_date, self.password,
              self.first_name, self.last_name, self.email,
              self.birth_date, self.registration_date, self.password))

        # Update phones
        cursor.execute("DELETE FROM Registered_Phones WHERE passport_number = %s", (self.passport_number,))
        for phone in self.phones:
            cursor.execute("INSERT INTO Registered_Phones (passport_number, phone_number) VALUES (%s, %s)",
                           (self.passport_number, phone))

        conn.commit()
        cursor.close()
        conn.close()

    def update_email_in_db(self, old_email):
        """
        Update email in Registered table
        """
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()

        cursor.execute("UPDATE Registered SET email = %s WHERE email = %s", (self.email, old_email))

        conn.commit()
        cursor.close()
        conn.close()


    def check_password(self, input_password):
        return self.password == input_password
        

    def update_password(self, new_password):
        self.password = new_password
        conn = get_connection("FLYTAU")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Registered SET password = %s WHERE passport_number = %s",
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
        
