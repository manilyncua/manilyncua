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

# Check if admin user exists
cursor.execute("SELECT * FROM users WHERE username='admin'")
user = cursor.fetchone()

if user:
    print("✓ User 'admin' found:")
    print(f"  ID: {user[0]}")
    print(f"  Fullname: {user[1]}")
    print(f"  Username: {user[2]}")
    print(f"  Password: {user[3][:30]}...")
    print(f"  Role: {user[4]}")
    
    # Update with new password (plain text to match the login logic)
    print("\nUpdating password...")
    cursor.execute("UPDATE users SET password=%s WHERE username='admin'", ('admincua111',))
    db.commit()
    print("✓ Password updated successfully!")
    print("  Username: admin")
    print("  Password: admincua111")
    
else:
    print("✗ User 'admin' NOT found in database")
    print("\nCreating new admin user...")
    cursor.execute(
        "INSERT INTO users (fullname, username, password, role) VALUES (%s, %s, %s, %s)",
        ("Administrator", "admin", "admincua111", "Admin")
    )
    db.commit()
    print("✓ Admin user created successfully!")
    print("  Username: admin")
    print("  Password: admincua111")
    print("  Role: Admin")

cursor.close()
db.close()
