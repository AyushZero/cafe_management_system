# app.py
import sqlite3
import os
import datetime
import decimal
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'cafe.db')

SAMPLE_ITEMS = [
    {'id': 1, 'name': 'Espresso', 'price': 150.00},
    {'id': 2, 'name': 'Latte', 'price': 220.00},
    {'id': 3, 'name': 'Cappuccino', 'price': 200.00},
    # Filter Coffee is excluded as requested
    {'id': 5, 'name': 'Croissant', 'price': 180.00},
    {'id': 6, 'name': 'Muffin', 'price': 120.00},
    {'id': 7, 'name': 'Sandwich', 'price': 300.00},
    {'id': 8, 'name': 'Americano', 'price': 180.00},
    {'id': 9, 'name': 'Mocha', 'price': 250.00},
    {'id': 10, 'name': 'Hot Chocolate', 'price': 230.00},
    {'id': 11, 'name': 'Masala Chai', 'price': 100.00},
    {'id': 12, 'name': 'Iced Latte', 'price': 250.00},
    {'id': 13, 'name': 'Cold Coffee', 'price': 200.00},
    {'id': 14, 'name': 'Iced Tea', 'price': 180.00},
    {'id': 15, 'name': 'Lemonade', 'price': 150.00},
    {'id': 16, 'name': 'Milkshake', 'price': 280.00},
    {'id': 17, 'name': 'Smoothie', 'price': 350.00},
    {'id': 18, 'name': 'Panini', 'price': 350.00},
    {'id': 19, 'name': 'Burger', 'price': 400.00},
    {'id': 20, 'name': 'Pasta', 'price': 450.00},
    {'id': 21, 'name': 'Pizza Slice', 'price': 250.00},
    {'id': 22, 'name': 'Garlic Bread', 'price': 200.00},
    {'id': 23, 'name': 'French Fries', 'price': 150.00},
    {'id': 24, 'name': 'Nachos', 'price': 280.00},
    {'id': 25, 'name': 'Pastry', 'price': 200.00},
    {'id': 26, 'name': 'Cake Slice', 'price': 250.00},
    {'id': 27, 'name': 'Brownie', 'price': 220.00},
    {'id': 28, 'name': 'Cookie', 'price': 100.00},
    {'id': 29, 'name': 'Ginger Tea', 'price': 90.00},
    {'id': 30, 'name': 'Green Tea', 'price': 120.00}
]

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

@app.context_processor
def inject_current_year():
    """Inject current year into templates."""
    return {'current_year': datetime.datetime.now().year}

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

@app.route('/employee/reservations')
@login_required
@role_required('employee')
def employee_view_reservations():
    reservations = []
    db = get_db()
    if not db:
        return render_template('employee/view_reservations.html', reservations=[], error="Database connection failed")

    try:
        cursor = db.execute("""
            SELECT r.id, r.reservation_time, r.num_guests, r.status, u.username as customer_username
            FROM reservations r
            JOIN users u ON r.customer_id = u.id
            ORDER BY r.reservation_time DESC
        """)
        reservations_data = [dict(row) for row in cursor.fetchall()]

        for reservation in reservations_data:
            reservation_id = reservation['id']
            orders = []
            order_cursor = db.execute("""
                SELECT o.id as order_id, o.order_time, o.total_amount, u.username as employee_username
                FROM orders o
                JOIN users u ON o.employee_id = u.id
                WHERE o.reservation_id = ?
                ORDER BY o.order_time
            """, (reservation_id,))
            orders_data = [dict(row) for row in order_cursor.fetchall()]

            for order in orders_data:
                order_id = order['order_id']
                items_cursor = db.execute("""
                    SELECT item_name, quantity, price_per_item
                    FROM order_items
                    WHERE order_id = ?
                """, (order_id,))
                order['items'] = [dict(item_row) for item_row in items_cursor.fetchall()]
                orders.append(order)

            reservation['orders'] = orders
            reservations.append(reservation)

    except sqlite3.Error as e:
        print(f"DB Error fetching reservations with orders for employee: {e}")
        flash("Could not fetch reservation list with order details.", "danger")

    return render_template('employee/view_reservations.html', reservations=reservations)

@app.route('/employee/customers')
@login_required
@role_required('employee')
def employee_view_customers():
    customers = []
    db = get_db()
    if not db: return render_template('employee/view_customers.html', customers=[], error="Database connection failed")

    try:
        cursor = db.execute("""
            SELECT id, username, loyalty_points, created_at
            FROM users
            WHERE role = 'customer'
            ORDER BY username ASC
        """)
        customers = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"DB Error fetching customers for employee: {e}")
        flash("Could not fetch customer list.", "danger")

    return render_template('employee/view_customers.html', customers=customers)



@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_view_users():
    users = []
    db = get_db()
    if not db: return render_template('admin/view_users.html', users=[], error="Database connection failed")

    try:
        cursor = db.execute("SELECT id, username, role, created_at FROM users ORDER BY role, username")
        users = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"DB Error fetching users for admin: {e}")
        flash("Could not fetch user list.", "danger")

    return render_template('admin/view_users.html', users=users)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_user(user_id):
    db = get_db()
    if not db:
         flash("Database connection failed.", "danger")
         return redirect(url_for('admin_view_users'))

    # IMPORTANT: Add checks to prevent critical deletions
    if user_id == session.get('user_id'):
         flash("You cannot delete your own account.", "danger")
         return redirect(url_for('admin_view_users'))

    # Check if user is the *only* admin (prevent locking out)
    cursor = db.execute("SELECT COUNT(*) as admin_count FROM users WHERE role = 'admin'")
    admin_count = cursor.fetchone()['admin_count']
    cursor = db.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user_to_delete = cursor.fetchone()

    if user_to_delete and user_to_delete['role'] == 'admin' and admin_count <= 1:
         flash("Cannot delete the only admin account.", "danger")
         return redirect(url_for('admin_view_users'))

    # Add more checks? Deleting users with existing orders/reservations can cause issues
    # For now, proceed with caution. Consider 'deactivating' instead of deleting in a real app.
    try:
        # Check for related records (simple check example)
        cursor = db.execute("SELECT COUNT(*) FROM reservations WHERE customer_id = ?", (user_id,))
        if cursor.fetchone()[0] > 0:
             flash(f"Cannot delete user ID {user_id}. They have existing reservations. Delete reservations first.", "warning")
             return redirect(url_for('admin_view_users'))

        cursor = db.execute("SELECT COUNT(*) FROM orders WHERE employee_id = ?", (user_id,))
        if cursor.fetchone()[0] > 0:
            flash(f"Cannot delete user ID {user_id}. They have existing orders recorded.", "warning")
            return redirect(url_for('admin_view_users'))

        # Proceed with deletion if checks pass
        cursor = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        if cursor.rowcount > 0:
             flash(f"User ID {user_id} deleted successfully.", "success")
        else:
             flash(f"User ID {user_id} not found.", "warning")

    except sqlite3.IntegrityError as e:
         db.rollback()
         print(f"DB IntegrityError deleting user {user_id}: {e}")
         flash(f"Could not delete user ID {user_id}. They might be linked to other records (e.g., orders, reservations).", "danger")
    except sqlite3.Error as e:
         db.rollback()
         print(f"DB Error deleting user {user_id}: {e}")
         flash(f"An error occurred while deleting user ID {user_id}.", "danger")

    return redirect(url_for('admin_view_users'))


@app.route('/admin/reservations')
@login_required
@role_required('admin')
def admin_view_reservations():
    reservations = []
    db = get_db()
    if not db:
        return render_template('admin/view_reservations.html', reservations=[], error="Database connection failed")

    try:
        cursor = db.execute("""
            SELECT r.id, r.reservation_time, r.num_guests, r.status, u.username as customer_username
            FROM reservations r
            JOIN users u ON r.customer_id = u.id
            ORDER BY r.reservation_time DESC
        """)
        reservations_data = [dict(row) for row in cursor.fetchall()]

        for reservation in reservations_data:
            reservation_id = reservation['id']
            orders = []
            order_cursor = db.execute("""
                SELECT o.id as order_id, o.order_time, o.total_amount, u.username as employee_username
                FROM orders o
                JOIN users u ON o.employee_id = u.id
                WHERE o.reservation_id = ?
                ORDER BY o.order_time
            """, (reservation_id,))
            orders_data = [dict(row) for row in order_cursor.fetchall()]

            for order in orders_data:
                order_id = order['order_id']
                items_cursor = db.execute("""
                    SELECT item_name, quantity, price_per_item
                    FROM order_items
                    WHERE order_id = ?
                """, (order_id,))
                order['items'] = [dict(row) for row in items_cursor.fetchall()]
                orders.append(order)

            reservation['orders'] = orders
            reservations.append(reservation)

    except sqlite3.Error as e:
        print(f"DB Error fetching reservations with orders for admin: {e}")
        flash("Could not fetch reservation list with order details.", "danger")

    return render_template('admin/view_reservations.html', reservations=reservations)

@app.route('/admin/delete_reservation/<int:res_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_reservation(res_id):
    db = get_db()
    if not db:
         flash("Database connection failed.", "danger")
         return redirect(url_for('admin_view_reservations'))

    try:
        # Optional: Delete associated orders first if needed, or handle via CASCADE/SET NULL in DB schema
        cursor = db.execute("DELETE FROM orders WHERE reservation_id = ?", (res_id,)) # Example: remove linked orders
        print(f"Deleted {cursor.rowcount} orders linked to reservation {res_id}")

        cursor = db.execute("DELETE FROM reservations WHERE id = ?", (res_id,))
        db.commit()
        if cursor.rowcount > 0:
             flash(f"Reservation ID {res_id} deleted successfully.", "success")
        else:
             flash(f"Reservation ID {res_id} not found.", "warning")

    except sqlite3.Error as e:
         db.rollback()
         print(f"DB Error deleting reservation {res_id}: {e}")
         flash(f"An error occurred while deleting reservation ID {res_id}.", "danger")

    return redirect(url_for('admin_view_reservations'))

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
    if not db:
        return render_template('customer/view_orders.html', orders=[], reservation=None, error="Database connection failed")

    try:
        # Verify the reservation belongs to the logged-in customer
        cursor = db.execute('SELECT * FROM reservations WHERE id = ? AND customer_id = ?', (res_id, customer_id))
        reservation_row = cursor.fetchone()
        if reservation_row:
            reservation_details = dict(reservation_row)
            orders_data = db.execute("""
                SELECT o.id as order_id, o.order_time, o.total_amount, u.username as employee_username
                FROM orders o
                JOIN users u ON o.employee_id = u.id
                WHERE o.reservation_id = ?
                ORDER BY o.order_time
            """, (res_id,)).fetchall()

            orders = []
            for order_row in orders_data:
                order = dict(order_row)
                items_cursor = db.execute("""
                    SELECT item_name, quantity, price_per_item
                    FROM order_items
                    WHERE order_id = ?
                """, (order['order_id'],))
                order['items'] = [dict(item_row) for item_row in items_cursor.fetchall()]
                orders.append(order)
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

@app.route('/employee/order/add/<int:reservation_id>', methods=['GET'])
@login_required
@role_required('employee')
def employee_add_order(reservation_id):
    """Displays the page to add items to an order for a specific reservation."""
    db = get_db()
    if not db:
        flash("Database connection failed.", "danger")
        return redirect(url_for('employee_view_reservations'))

    reservation = None
    order_details = None
    order_items = []
    current_total = decimal.Decimal('0.00')

    try:
        # Fetch reservation details
        cursor = db.execute("""
            SELECT r.id, r.reservation_time, r.num_guests, r.status, u.username as customer_username
            FROM reservations r
            JOIN users u ON r.customer_id = u.id
            WHERE r.id = ?
        """, (reservation_id,))
        reservation = cursor.fetchone()

        if not reservation:
            flash("Reservation not found.", "warning")
            return redirect(url_for('employee_view_reservations'))

        # Find if an order already exists for this reservation
        # For simplicity, we assume one order per reservation initiated by an employee for now.
        cursor = db.execute("""
            SELECT id, total_amount FROM orders WHERE reservation_id = ? ORDER BY order_time DESC LIMIT 1
        """, (reservation_id,))
        order_details = cursor.fetchone()

        if order_details:
            # Fetch existing items for this order
            items_cursor = db.execute("""
                SELECT item_name, quantity, price_per_item
                FROM order_items
                WHERE order_id = ?
            """, (order_details['id'],))
            order_items = [dict(row) for row in items_cursor.fetchall()]
            current_total = decimal.Decimal(str(order_details['total_amount'])) # Use Decimal for currency


    except sqlite3.Error as e:
        print(f"DB Error fetching reservation/order details for adding items: {e}")
        flash("Could not load order details.", "danger")
        return redirect(url_for('employee_view_reservations'))

    # Ensure reservation is passed as a dictionary-like object
    reservation_dict = dict(reservation) if reservation else None

    return render_template(
        'employee/add_order.html',
        reservation=reservation_dict,
        menu_items=SAMPLE_ITEMS, # Pass sample items from app.py
        current_order_items=order_items,
        current_total=current_total,
        order_id=order_details['id'] if order_details else None
    )

@app.route('/employee/order/add_item/<int:reservation_id>', methods=['POST'])
@login_required
@role_required('employee')
def employee_add_item(reservation_id):
    """Handles adding a selected item to the order and updates loyalty points."""
    db = get_db()
    employee_id = session['user_id']
    if not db:
        flash("Database connection failed.", "danger")
        return redirect(url_for('employee_add_order', reservation_id=reservation_id))

    item_id_str = request.form.get('item_id')
    quantity_str = request.form.get('quantity', '1') # Default quantity to 1

    if not item_id_str:
        flash("No item selected.", "warning")
        return redirect(url_for('employee_add_order', reservation_id=reservation_id))

    try:
        item_id = int(item_id_str)
        quantity = int(quantity_str)
        if quantity <= 0:
            flash("Quantity must be positive.", "warning")
            return redirect(url_for('employee_add_order', reservation_id=reservation_id))

        selected_item = next((item for item in SAMPLE_ITEMS if item['id'] == item_id), None)

        if not selected_item:
            flash("Selected item not found.", "danger")
            return redirect(url_for('employee_add_order', reservation_id=reservation_id))

        item_name = selected_item['name']
        # Use Decimal for accurate price calculations
        price_per_item = decimal.Decimal(str(selected_item['price']))
        item_subtotal = price_per_item * quantity

        # --- Transaction: Find/Create Order, Add Item, Update Total, Update Loyalty ---
        order_id = None
        customer_id = None

        try:
            # Get customer_id from reservation
            cursor = db.execute("SELECT customer_id FROM reservations WHERE id = ?", (reservation_id,))
            reservation_data = cursor.fetchone()
            if not reservation_data:
                 flash("Could not find reservation to link order.", "danger")
                 # No rollback needed here as nothing is committed yet
                 return redirect(url_for('employee_view_reservations'))
            customer_id = reservation_data['customer_id']


            # Check if an order exists
            cursor = db.execute("SELECT id FROM orders WHERE reservation_id = ? LIMIT 1", (reservation_id,))
            existing_order = cursor.fetchone()

            if existing_order:
                order_id = existing_order['id']
            else:
                # Create a new order if none exists
                cursor = db.execute(
                    "INSERT INTO orders (reservation_id, employee_id, total_amount) VALUES (?, ?, ?)",
                    (reservation_id, employee_id, '0.00') # Initial total is 0
                )
                order_id = cursor.lastrowid
                print(f"Created new order ID {order_id} for reservation {reservation_id}")

            # Add the item to order_items
            cursor = db.execute(
                "INSERT INTO order_items (order_id, item_name, quantity, price_per_item) VALUES (?, ?, ?, ?)",
                (order_id, item_name, quantity, str(price_per_item)) # Store price as string/real
            )
            print(f"Added {quantity} x {item_name} to order {order_id}")

            # Recalculate the total for the order
            cursor = db.execute(
                "SELECT SUM(quantity * price_per_item) as total FROM order_items WHERE order_id = ?",
                 (order_id,)
            )
            result = cursor.fetchone()
            # Ensure new_total is Decimal
            new_total = decimal.Decimal(str(result['total'])) if result and result['total'] is not None else decimal.Decimal('0.00')

            # Update the total_amount in the orders table
            db.execute("UPDATE orders SET total_amount = ? WHERE id = ?", (str(new_total), order_id))
            print(f"Updated order {order_id} total to {new_total}")

            # --- Loyalty Points Logic ---
            if customer_id:
                # Calculate points for the item(s) just added (e.g., 1 point per dollar, rounded down)
                points_to_add = int(item_subtotal)
                if points_to_add > 0:
                    db.execute(
                        "UPDATE users SET loyalty_points = loyalty_points + ? WHERE id = ?",
                        (points_to_add, customer_id)
                    )
                    print(f"Awarded {points_to_add} loyalty points to customer {customer_id}")
            # --- End Loyalty Points Logic ---

            db.commit() # Commit all changes (item add, total update, loyalty update)
            flash(f"{quantity} x {item_name} added. {points_to_add if customer_id and points_to_add > 0 else 0} loyalty points awarded.", "success")

        except sqlite3.Error as e:
            db.rollback() # Rollback on any DB error during the transaction
            print(f"DB Error adding item/updating points: {e}")
            flash("Error adding item to order or updating points.", "danger")
        except Exception as e:
            db.rollback()
            print(f"Generic Error adding item/updating points: {e}")
            flash("An unexpected error occurred.", "danger")


    except ValueError:
        flash("Invalid item ID or quantity.", "danger")
    except Exception as e:
        # Catch potential errors before DB connection if needed
        print(f"Error processing add item form: {e}")
        flash("An error occurred processing the request.", "danger")

    return redirect(url_for('employee_add_order', reservation_id=reservation_id))

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