import mysql.connector
def get_connection(data_base):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database= data_base
    )
    return conn

"ליצור פונקציה חיצונית שבודקת אם קיים מטוס מתאים אם קיים ליצור אובייקט מחלקה ואם לא להעלות שגיאה"

