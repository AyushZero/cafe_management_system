# app.py
import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps # For decorators

app = Flask(__name__)
app.secret_key = os.urandom(24) # Replace with a strong, static secret key in production

# --- Database Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'cafe.db')

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        try:
            g.db = sqlite3.connect(DATABASE)
            g.db.row_factory = sqlite3.Row # Return rows as dictionary-like objects
            print("Database connection opened.")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            # Handle error appropriately, maybe flash a message or log it
            flash("Database connection error. Please try again later.", "danger")
            g.db = None # Ensure db is None if connection failed
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        print("Database connection closed.")
    if error:
        print(f"Application context teardown error: {error}")


# --- Decorators for Access Control ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') != required_role:
                flash(f'You do not have permission to access this page. Requires {required_role} role.', 'danger')
                # Redirect to appropriate dashboard or login
                if 'role' in session:
                     return redirect(url_for(f"{session['role']}_dashboard"))
                else:
                     return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        # Redirect logged-in users to their dashboard
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'employee':
            return redirect(url_for('employee_dashboard'))
        elif role == 'customer':
            return redirect(url_for('customer_dashboard'))
    return redirect(url_for('login'))

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
         return redirect(url_for('index')) # Already logged in

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        db = get_db()
        if not db: return render_template('login.html', error="Database connection failed")

        user = None
        try:
            cursor = db.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
        except sqlite3.Error as e:
            print(f"DB Error during login select: {e}")
            error = "An error occurred during login. Please try again."

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password_hash'], password):
            error = 'Incorrect password.'

        if error is None and user:
            # Store user info in session
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            # Redirect based on role
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'employee':
                return redirect(url_for('employee_dashboard'))
            elif user['role'] == 'customer':
                return redirect(url_for('customer_dashboard'))
            else:
                 # Should not happen due to DB constraint, but good practice
                 flash('Unknown user role.', 'danger')
                 return redirect(url_for('login'))
        else:
            flash(error, 'danger')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
         return redirect(url_for('index')) # Already logged in

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        error = None
        db = get_db()
        if not db: return render_template('signup.html', error="Database connection failed")


        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        else:
             # Check if username already exists
             try:
                cursor = db.execute('SELECT id FROM users WHERE username = ?', (username,))
                if cursor.fetchone() is not None:
                    error = f"Username '{username}' is already taken."
             except sqlite3.Error as e:
                 print(f"DB Error during signup check: {e}")
                 error = "An error occurred checking username availability."


        if error is None:
            # Hash password and insert new user (default role: customer)
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            try:
                cursor = db.execute(
                    'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                    (username, password_hash, 'customer')
                )
                db.commit()
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError: # Should be caught by earlier check, but for safety
                 error = f"Username '{username}' is already taken."
                 flash(error, 'danger')
            except sqlite3.Error as e:
                 print(f"DB Error during signup insert: {e}")
                 error = "An error occurred creating the account."
                 flash(error, 'danger')
                 db.rollback() # Rollback on error
        else:
             flash(error, 'danger')

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# --- Customer Routes ---

@app.route('/customer/dashboard')
@login_required
@role_required('customer')
def customer_dashboard():
    return render_template('customer/dashboard.html', username=session['username'])

@app.route('/customer/reserve', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def make_reservation():
    if request.method == 'POST':
        reservation_time = request.form['reservation_time']
        num_guests = request.form['num_guests']
        customer_id = session['user_id']
        error = None
        db = get_db()
        if not db: return render_template('customer/make_reservation.html', error="Database connection failed")

        if not reservation_time or not num_guests:
            error = "Please fill in all fields."
        elif int(num_guests) <= 0:
            error = "Number of guests must be positive."
        # Add more validation for date/time format if needed

        if error is None:
            try:
                cursor = db.execute(
                    'INSERT INTO reservations (customer_id, reservation_time, num_guests) VALUES (?, ?, ?)',
                    (customer_id, reservation_time, num_guests)
                )
                db.commit()
                flash('Reservation made successfully!', 'success')
                return redirect(url_for('customer_view_reservations'))
            except sqlite3.Error as e:
                print(f"DB Error during reservation insert: {e}")
                error = "An error occurred making the reservation."
                flash(error, 'danger')
                db.rollback()
        else:
             flash(error, 'danger')

    return render_template('customer/make_reservation.html')

@app.route('/customer/reservations')
@login_required
@role_required('customer')
def customer_view_reservations():
    reservations = []
    loyalty_points = 0
    db = get_db()
    if not db: return render_template('customer/view_reservations.html', reservations=[], loyalty_points=0, error="Database connection failed")

    customer_id = session['user_id']
    try:
        # Fetch reservations
        cursor = db.execute(
            'SELECT id, reservation_time, num_guests, status FROM reservations WHERE customer_id = ? ORDER BY reservation_time DESC',
            (customer_id,)
        )
        reservations = cursor.fetchall()

        # Fetch loyalty points
        cursor = db.execute('SELECT loyalty_points FROM users WHERE id = ?', (customer_id,))
        user_data = cursor.fetchone()
        if user_data:
             loyalty_points = user_data['loyalty_points']

    except sqlite3.Error as e:
        print(f"DB Error fetching reservations/loyalty: {e}")
        flash("Could not fetch reservation history.", "danger")

    return render_template('customer/view_reservations.html', reservations=reservations, loyalty_points=loyalty_points)


@app.route('/customer/reservation/<int:res_id>/orders')
@login_required
@role_required('customer')
def customer_view_orders(res_id):
    orders = []
    reservation_details = None
    db = get_db()
    customer_id = session['user_id']
    if not db: return render_template('customer/view_orders.html', orders=[], reservation=None, error="Database connection failed")

    try:
        # Verify the reservation belongs to the logged-in customer
        cursor = db.execute('SELECT * FROM reservations WHERE id = ? AND customer_id = ?', (res_id, customer_id))
        reservation_details = cursor.fetchone()

        if reservation_details:
            # Fetch orders associated with this reservation
            cursor = db.execute(
                '''SELECT o.id, o.order_time, o.total_amount, e.username as employee_username
                   FROM orders o
                   JOIN users e ON o.employee_id = e.id
                   WHERE o.reservation_id = ?
                   ORDER BY o.order_time DESC''',
                (res_id,)
            )
            orders = cursor.fetchall()
        else:
             flash("Reservation not found or access denied.", "warning")
             return redirect(url_for('customer_view_reservations'))

    except sqlite3.Error as e:
        print(f"DB Error fetching orders for reservation {res_id}: {e}")
        flash("Could not fetch order history for this reservation.", "danger")

    return render_template('customer/view_orders.html', orders=orders, reservation=reservation_details)


# --- Employee Routes ---

@app.route('/employee/dashboard')
@login_required
@role_required('employee')
def employee_dashboard():
    return render_template('employee/dashboard.html', username=session['username'])

@app.route('/employee/add_customer', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def employee_add_customer():
    # This is essentially the same as signup, but initiated by an employee
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Optional: Add more fields like phone, email if needed
        error = None
        db = get_db()
        if not db: return render_template('employee/add_customer.html', error="Database connection failed")

        if not username or not password:
            error = 'Username and password are required.'
        else:
             try:
                cursor = db.execute('SELECT id FROM users WHERE username = ?', (username,))
                if cursor.fetchone() is not None:
                    error = f"Username '{username}' is already taken."
             except sqlite3.Error as e:
                print(f"DB Error checking username (emp add cust): {e}")
                error = "Error checking username availability."

        if error is None:
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            try:
                cursor = db.execute(
                    'INSERT INTO users (username, password_hash, role, loyalty_points) VALUES (?, ?, ?, ?)',
                    (username, password_hash, 'customer', 0) # New customers start with 0 points
                )
                db.commit()
                flash(f'Customer account "{username}" created successfully!', 'success')
                # Redirect back to employee dashboard or stay on page? Redirect for now.
                return redirect(url_for('employee_dashboard'))
            except sqlite3.IntegrityError:
                 error = f"Username '{username}' is already taken."
                 flash(error, 'danger')
            except sqlite3.Error as e:
                print(f"DB Error inserting customer (emp add cust): {e}")
                error = "An error occurred creating the customer account."
                flash(error, 'danger')
                db.rollback()
        else:
            flash(error, 'danger')

    return render_template('employee/add_customer.html')


@app.route('/employee/add_reservation', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def employee_add_reservation():
    customers = []
    db = get_db()
    if not db: return render_template('employee/add_reservation.html', customers=[], error="Database connection failed")

    # Get list of customers to populate a dropdown/selection
    try:
        cursor = db.execute("SELECT id, username FROM users WHERE role = 'customer' ORDER BY username")
        customers = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"DB Error fetching customers for emp reservation: {e}")
        flash("Could not load customer list.", "warning")


    if request.method == 'POST':
        customer_id = request.form['customer_id']
        reservation_time = request.form['reservation_time']
        num_guests = request.form['num_guests']
        error = None

        if not customer_id or not reservation_time or not num_guests:
            error = "Please select a customer and fill in all fields."
        elif int(num_guests) <= 0:
            error = "Number of guests must be positive."
        # Add more validation

        if error is None:
            try:
                cursor = db.execute(
                    'INSERT INTO reservations (customer_id, reservation_time, num_guests) VALUES (?, ?, ?)',
                    (customer_id, reservation_time, num_guests)
                )
                db.commit()
                flash('Reservation added successfully for customer!', 'success')
                return redirect(url_for('employee_dashboard')) # Or maybe a page showing all reservations?
            except sqlite3.Error as e:
                print(f"DB Error employee adding reservation: {e}")
                error = "An error occurred adding the reservation."
                flash(error, 'danger')
                db.rollback()
        else:
            flash(error, 'danger')

    # Pass customers list again in case of POST error redisplay
    return render_template('employee/add_reservation.html', customers=customers)


@app.route('/employee/create_order', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def employee_create_order():
    reservations = [] # Active/recent reservations
    db = get_db()
    if not db: return render_template('employee/create_order.html', reservations=[], error="Database connection failed")

    # Get list of recent/active reservations to potentially link order to
    # Limiting to recent ones might be practical
    try:
        # Select reservations from today or future, or maybe just recent ones
        cursor = db.execute("""
            SELECT r.id, r.reservation_time, r.num_guests, u.username as customer_username
            FROM reservations r
            JOIN users u ON r.customer_id = u.id
            WHERE r.status = 'confirmed' -- or filter by date
            ORDER BY r.reservation_time DESC
            LIMIT 20
        """)
        reservations = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"DB Error fetching reservations for order creation: {e}")
        flash("Could not load recent reservations.", "warning")

    if request.method == 'POST':
        reservation_id = request.form.get('reservation_id') # Use .get for optional field
        total_amount = request.form['total_amount']
        employee_id = session['user_id']
        error = None

        # Basic validation
        if not total_amount:
             error = "Total amount is required."
        else:
             try:
                 total_amount_float = float(total_amount)
                 if total_amount_float <= 0:
                     error = "Total amount must be positive."
             except ValueError:
                 error = "Invalid total amount."

        # Handle optional reservation_id (make sure it's an integer if provided)
        db_reservation_id = None
        if reservation_id and reservation_id != 'None' and reservation_id != '':
             try:
                 db_reservation_id = int(reservation_id)
             except ValueError:
                 error = "Invalid reservation selected."
        else:
             db_reservation_id = None # Explicitly set to None for walk-ins/no selection


        if error is None:
             try:
                 # Insert the order
                 cursor = db.execute(
                     'INSERT INTO orders (reservation_id, employee_id, total_amount) VALUES (?, ?, ?)',
                     (db_reservation_id, employee_id, total_amount_float)
                 )
                 order_id = cursor.lastrowid # Get the ID of the order just inserted

                 # Update loyalty points if linked to a customer via reservation
                 if db_reservation_id:
                      cursor = db.execute('SELECT customer_id FROM reservations WHERE id = ?', (db_reservation_id,))
                      res_data = cursor.fetchone()
                      if res_data:
                           customer_id_for_points = res_data['customer_id']
                           # Add points (e.g., 1 point per dollar/unit currency)
                           points_to_add = int(total_amount_float) # Example logic
                           cursor = db.execute(
                               'UPDATE users SET loyalty_points = loyalty_points + ? WHERE id = ?',
                               (points_to_add, customer_id_for_points)
                           )
                           print(f"Added {points_to_add} loyalty points to customer {customer_id_for_points}")

                 # Mark reservation as completed maybe? (Optional step)
                 # if db_reservation_id:
                 #     cursor = db.execute("UPDATE reservations SET status='completed' WHERE id = ?", (db_reservation_id,))


                 db.commit()
                 flash(f'Order #{order_id} created successfully!', 'success')
                 return redirect(url_for('employee_dashboard'))
             except sqlite3.Error as e:
                 print(f"DB Error creating order: {e}")
                 error = "An error occurred creating the order."
                 flash(error, 'danger')
                 db.rollback()
        else:
             flash(error, 'danger')


    return render_template('employee/create_order.html', reservations=reservations)


# --- Admin Routes ---

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    return render_template('admin/dashboard.html', username=session['username'])

@app.route('/admin/add_employee', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_employee():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        error = None
        db = get_db()
        if not db: return render_template('admin/add_employee.html', error="Database connection failed")

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        else:
            # Check if username already exists
            try:
                cursor = db.execute('SELECT id FROM users WHERE username = ?', (username,))
                if cursor.fetchone() is not None:
                    error = f"Username '{username}' is already taken."
            except sqlite3.Error as e:
                print(f"DB Error checking username (admin add emp): {e}")
                error = "Error checking username availability."

        if error is None:
            # Hash password and insert new user with 'employee' role
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            try:
                cursor = db.execute(
                    'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                    (username, password_hash, 'employee')
                )
                db.commit()
                flash(f'Employee account "{username}" created successfully!', 'success')
                return redirect(url_for('admin_dashboard')) # Redirect back to admin dashboard
            except sqlite3.IntegrityError:
                 error = f"Username '{username}' is already taken."
                 flash(error, 'danger')
            except sqlite3.Error as e:
                 print(f"DB Error inserting employee (admin add emp): {e}")
                 error = "An error occurred creating the employee account."
                 flash(error, 'danger')
                 db.rollback()
        else:
             flash(error, 'danger')

    return render_template('admin/add_employee.html')


# --- Main Execution ---
if __name__ == '__main__':
    # Check if the database exists, if not, initialize it.
    if not os.path.exists(DATABASE):
        print("Database not found, initializing...")
        # We need to import and run the init_db function here
        # This requires careful handling if init_db.py imports things from app.py
        # A better approach is often a separate flask command `flask init-db`
        # For simplicity here, let's assume init_db.py was run manually first.
        # Or you could include the init logic within app.py guarded by a check.
        from init_db import init_db as initialize_database
        initialize_database() # Make sure init_db.py is runnable as a module

    app.run(debug=True) # debug=True enables auto-reloading and detailed errors