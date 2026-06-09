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

# Check if user exists
cursor.execute("SELECT * FROM users WHERE username='mjm'")
user = cursor.fetchone()

if user:
    print("✓ User 'mjm' found:")
    print(f"  ID: {user[0]}")
    print(f"  Fullname: {user[1]}")
    print(f"  Username: {user[2]}")
    print(f"  Password Hash: {user[3][:20]}...")
    print(f"  Role: {user[4]}")
    
    # Update with new hash
    print("\nUpdating password hash...")
    new_hash = generate_password_hash('mjm112233')
    cursor.execute("UPDATE users SET password=%s WHERE username='mjm'", (new_hash,))
    db.commit()
    print("✓ Password updated successfully!")
    
else:
    print("✗ User 'mjm' NOT found in database")
    print("\nCreating new user...")
    hashed_password = generate_password_hash('mjm112233')
    cursor.execute(
        "INSERT INTO users (fullname, username, password, role) VALUES (%s, %s, %s, %s)",
        ("MJM Staff", "mjm", hashed_password, "Staff")
    )
    db.commit()
    print("✓ User 'mjm' created successfully!")
    print("  Username: mjm")
    print("  Password: mjm112233")
    print("  Role: Staff")

cursor.close()
db.close()
