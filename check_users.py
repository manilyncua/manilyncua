import mysql.connector
from werkzeug.security import generate_password_hash

# Connect to database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="sb_ordinance_db"
)

cursor = db.cursor()

# Check all users
print("=== ALL USERS IN DATABASE ===\n")
cursor.execute("SELECT id, fullname, username, password, role FROM users")
all_users = cursor.fetchall()

if all_users:
    for user in all_users:
        print(f"ID: {user[0]}")
        print(f"  Fullname: {user[1]}")
        print(f"  Username: {user[2]}")
        print(f"  Password (stored): {user[3][:30]}...")
        print(f"  Role: {user[4]}")
        print()
else:
    print("No users found!")

cursor.close()
db.close()
