# init_db.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

# Define the path for the database relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'cafe.db')

def init_db():
    print(f"Initializing database at: {DATABASE}")
    # Delete existing database file if it exists to start fresh
    if os.path.exists(DATABASE):
        print("Removing existing database...")
        os.remove(DATABASE)

    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        print("Database connection established.")

        # Create users table
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('customer', 'employee', 'admin')),
            loyalty_points INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        print("Created 'users' table.")

        # Create reservations table
        cursor.execute('''
        CREATE TABLE reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            reservation_time DATETIME NOT NULL,
            num_guests INTEGER NOT NULL,
            status TEXT DEFAULT 'confirmed', -- e.g., confirmed, completed, cancelled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users(id)
        );
        ''')
        print("Created 'reservations' table.")

        # Create orders table
        cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER, -- Can be NULL if it's a walk-in order not tied to a reservation
            employee_id INTEGER NOT NULL, -- Who took the order
            order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL,
            -- For simplicity, we store total amount. A real system would have an order_items table.
            FOREIGN KEY (reservation_id) REFERENCES reservations(id),
            FOREIGN KEY (employee_id) REFERENCES users(id)
        );
        ''')
        print("Created 'orders' table.")

        # Create order_items table (NEW)
        cursor.execute('''
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_item REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE -- Delete items if order is deleted
        );
        ''')
        print("Created 'order_items' table.")

        # --- Seed Data (Optional but helpful for testing) ---

        # Add a default admin user
        admin_pass_hash = generate_password_hash('adminpass', method='pbkdf2:sha256')
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                       ('admin', admin_pass_hash, 'admin'))
        print("Added default admin user (admin/adminpass).")

        # Add a default employee user
        emp_pass_hash = generate_password_hash('emppass', method='pbkdf2:sha256')
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                       ('employee1', emp_pass_hash, 'employee'))
        print("Added default employee user (employee1/emppass).")

        # Add a default customer user
        cust_pass_hash = generate_password_hash('custpass', method='pbkdf2:sha256')
        cursor.execute("INSERT INTO users (username, password_hash, role, loyalty_points) VALUES (?, ?, ?, ?)",
                       ('customer1', cust_pass_hash, 'customer', 50))
        print("Added default customer user (customer1/custpass).")


        conn.commit()
        print("Database initialized and seeded successfully.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    init_db()