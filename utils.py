import mysql.connector
from flask import session


def get_connection(data_base):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database= data_base
    )
    return conn

"ליצור פונקציה חיצונית שבודקת אם קיים מטוס מתאים אם קיים ליצור אובייקט מחלקה ואם לא להעלות שגיאה"



def ensure_booking():
    """
    Ensure session['booking'] exists with default values.
    Returns the booking dictionary.
    """
    if "booking" not in session:
        session["booking"] = {
            "num_passengers": 1,  # default if not set
            "logged_in": False
        }
    return session["booking"]

