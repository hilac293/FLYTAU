import mysql.connector
from datetime import datetime
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




# Check expiry date in payment
def is_expiry_valid(expiry):
    """
    expiry format: MM/YY
    Returns True if expiry is in the future.
    """
    try:
        month, year = expiry.split("/")
        month = int(month)
        year = int(year)

        if month < 1 or month > 12:
            return False

        now = datetime.now()
        current_month = now.month
        current_year = now.year % 100  # last two digits

        # expired?
        if year < current_year:
            return False
        if year == current_year and month < current_month:
            return False

        return True
    except:
        return False


