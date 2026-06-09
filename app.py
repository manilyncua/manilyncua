from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

app = Flask(__name__)
app.secret_key = "your_secret_key"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="sb_ordinance_db"
)

cursor = db.cursor()


def get_documents(query=None):
    sql = "SELECT * FROM documents"
    params = []

    if query:
        term = f"%{query}%"
        sql += """
            WHERE control_no LIKE %s
               OR title LIKE %s
               OR document_type LIKE %s
               OR originating_office LIKE %s
               OR date_received LIKE %s
               OR status LIKE %s
        """
        params = [term, term, term, term, term, term]

    sql += " ORDER BY id DESC"
    cursor.execute(sql, params)
    return cursor.fetchall()


def filter_documents_by_period(documents, period):
    if not period or period not in ('daily', 'weekly', 'monthly'):
        return documents

    from datetime import datetime, date, timedelta

    today = date.today()

    if period == 'daily':
        start = today
        end = today
    elif period == 'weekly':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    else:
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)

    filtered = []
    for doc in documents:
        received_on = doc[4]
        if not received_on:
            continue

        try:
            if isinstance(received_on, datetime):
                doc_date = received_on.date()
            else:
                doc_date = datetime.strptime(str(received_on), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue

        if start <= doc_date <= end:
            filtered.append(doc)

    return filtered


# Landing Page
@app.route('/landing')
def landing():
    return render_template('landing.html')

# Dashboard
@app.route('/')
def index():

    if 'user_id' not in session:
        return redirect('/landing')

    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM documents WHERE status='Archived'"
    )
    archived_docs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM documents WHERE status='Received'"
    )
    received_docs = cursor.fetchone()[0]

    cursor.execute(
       "SELECT COUNT(*) FROM documents WHERE status='Approved'"
    )
    approved_docs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM documents WHERE released_to IS NOT NULL"
    )
    released_docs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM documents WHERE status='Under Review'"
    )
    under_review_docs = cursor.fetchone()[0]
    
    from datetime import datetime
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    return render_template(
        'index.html',
        total_docs=total_docs,
        archived_docs=archived_docs,
        received_docs=received_docs,
        approved_docs=approved_docs,
        released_docs=released_docs,
        under_review_docs=under_review_docs,
        current_time=current_time
    )
# Documents Management Page
@app.route('/documents')
def documents():
    if 'user_id' not in session:
        return redirect('/login')

    query = request.args.get('q', '').strip()
    documents_list = get_documents(query)

    return render_template('documents.html', documents=documents_list, query=query)

# Add Document
@app.route('/add', methods=['GET', 'POST'])
def add_document():
    if request.method == 'POST':
        # Generate automatic control number
        cursor.execute("SELECT control_no FROM documents ORDER BY id DESC LIMIT 1")
        last_control = cursor.fetchone()
        
        new_num = 1
        if last_control and last_control[0]:
            try:
                # Try to extract number from 'DOC-###' format
                parts = last_control[0].split('-')
                if len(parts) >= 2:
                    last_num = int(parts[-1])
                    new_num = last_num + 1
            except (ValueError, IndexError):
                # If format is different, just count all docs + 1
                cursor.execute("SELECT COUNT(*) FROM documents")
                new_num = cursor.fetchone()[0] + 1
        
        control_no = f"DOC-{new_num:03d}"
        
        title = request.form['title']
        document_type = request.form['document_type']
        date_received = request.form['date_received']
        originating_office = request.form['originating_office']
        status = request.form['status']
        remarks = request.form['remarks']

        sql = """
        INSERT INTO documents
        (control_no, title, document_type, date_received,
        originating_office, status, remarks)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            control_no,
            title,
            document_type,
            date_received,
            originating_office,
            status,
            remarks
        )

        cursor.execute(sql, values)
        db.commit()

        return redirect('/')

    return render_template('add.html')

# Delete Document
@app.route('/delete/<int:id>')
def delete_document(id):
    cursor.execute("DELETE FROM documents WHERE id=%s", (id,))
    db.commit()
    return redirect('/')

# Update Status
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_document(id):
    if request.method == 'POST':
        status = request.form['status']
        remarks = request.form['remarks']

        cursor.execute("""
            UPDATE documents
            SET status=%s, remarks=%s
            WHERE id=%s
        """, (status, remarks, id))

        db.commit()
        return redirect('/documents')

    cursor.execute("SELECT * FROM documents WHERE id=%s", (id,))
    document = cursor.fetchone()

    return render_template('update.html', document=document)

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        print("DEBUG USER:", user)  # <-- IMPORTANT DEBUG

        # Accept both plain text and hashed passwords
        password_match = False
        if user:
            stored_password = user[3]
            # Check if it's a hashed password (starts with 'scrypt:' or '$2')
            if stored_password.startswith('scrypt:') or stored_password.startswith('$2'):
                # Try hashed password check
                try:
                    password_match = check_password_hash(stored_password, password)
                except:
                    password_match = False
            else:
                # Plain text password
                password_match = (stored_password == password)

        if user and password_match:

            session['user_id'] = user[0]
            session['fullname'] = user[1]
            session['role'] = user[4]

            return redirect('/')

        return "Invalid Login"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/landing')
    
@app.route('/archives')
def archives():

    if 'user_id' not in session:
        return redirect('/login')

    cursor.execute("""
        SELECT * FROM documents
        WHERE status = 'Archived'
        ORDER BY id DESC
    """)

    archived_docs = cursor.fetchall()

    return render_template(
        'archives.html',
        documents=archived_docs
    )
@app.route('/archive/<int:id>')
def archive_document(id):

    if 'user_id' not in session:
        return redirect('/login')

    cursor.execute("""
        UPDATE documents
        SET status='Archived'
        WHERE id=%s
    """, (id,))

    db.commit()

    return redirect('/')

@app.route('/reports')
def reports():

    if 'user_id' not in session:
        return redirect('/login')

    query = request.args.get('q', '').strip()
    period = request.args.get('period', '').strip().lower()
    status = request.args.get('status', '').strip().lower()
    document_type = request.args.get('document_type', '').strip().lower()

    documents = get_documents(query)
    documents = filter_documents_by_period(documents, period)

    if status:
        documents = [doc for doc in documents if doc[6].lower() == status]

    if document_type:
        documents = [doc for doc in documents if doc[3].lower() == document_type]
    
    from datetime import datetime
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    report_title = 'Document Reports'
    if period == 'daily':
        report_title = 'Daily Document Report'
    elif period == 'weekly':
        report_title = 'Weekly Document Report'
    elif period == 'monthly':
        report_title = 'Monthly Document Report'

    return render_template(
        'reports.html',
        documents=documents,
        current_time=current_time,
        query=query,
        period=period,
        status=status,
        document_type=document_type,
        report_title=report_title
    )

# Analytics Routes
@app.route('/analytics/<category>')
def analytics(category):
    
    if 'user_id' not in session:
        return redirect('/login')

    query = request.args.get('q', '').strip()
    category_name = category.lower()
    documents = []
    page_title = ""
    
    if category_name == 'total':
        documents = get_documents(query)
        page_title = "All Documents"
    
    elif category_name == 'approved':
        documents = [doc for doc in get_documents(query) if doc[6] == 'Approved']
        page_title = "Approved Documents"
    
    elif category_name == 'released':
        documents = [doc for doc in get_documents(query) if doc[10] is not None]
        page_title = "Released Documents"
    
    elif category_name == 'archived':
        documents = [doc for doc in get_documents(query) if doc[6] == 'Archived']
        page_title = "Archived Documents"
    
    elif category_name == 'under-review':
        documents = [doc for doc in get_documents(query) if doc[6] == 'Under Review']
        page_title = "Documents Under Review"
    
    elif category_name == 'received':
        documents = [doc for doc in get_documents(query) if doc[6] == 'Received']
        page_title = "Received Documents"
    
    from datetime import datetime
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    return render_template(
        'analytics.html',
        documents=documents,
        page_title=page_title,
        current_time=current_time,
        category=category_name,
        query=query
    )
    
@app.route('/users')
def users():

    if 'user_id' not in session:
        return redirect('/login')

    if session.get('role') != 'Admin':
        return "Access Denied"

    cursor.execute("SELECT * FROM users")
    all_users = cursor.fetchall()

    return render_template('users.html', users=all_users)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():

    if 'user_id' not in session:
        return redirect('/login')

    if session.get('role') != 'Admin':
        return "Access Denied"

    if request.method == 'POST':

        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users (fullname, username, password, role)
            VALUES (%s, %s, %s, %s)
        """, (fullname, username, hashed_password, role))

        db.commit()

        return redirect('/users')

    return render_template('add_user.html')

@app.route('/delete_user/<int:id>')
def delete_user(id):

    if session.get('role') != 'Admin':
        return "Access Denied"

    cursor.execute("DELETE FROM users WHERE id=%s", (id,))
    db.commit()

    return redirect('/users')

@app.route('/release/<int:id>', methods=['GET', 'POST'])
def release(id):

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        released_to = request.form['released_to']
        received_by = request.form['received_by']
        date_released = request.form['date_released']

        cursor.execute("""
            UPDATE documents
            SET released_to=%s,
                received_by=%s,
                date_released=%s
            WHERE id=%s
        """, (released_to, received_by, date_released, id))

        db.commit()

        return redirect('/')

    cursor.execute("SELECT * FROM documents WHERE id=%s", (id,))
    doc = cursor.fetchone()

    return render_template("release.html", doc=doc)
        
if __name__ == '__main__':
    # Debug: Check if user exists
    # cursor.execute("SELECT * FROM users WHERE username='mjm'")
    # user = cursor.fetchone()
    # print("User mjm:", user)
    # If user exists but password is plain text, you can hash it:
    # hashed = generate_password_hash('mjm112233')
    # cursor.execute("UPDATE users SET password=%s WHERE username='mjm'", (hashed,))
    # db.commit()
    
    app.run(debug=True)