# Cafe Management System

A simple, local web application built with Flask and SQLite to manage basic cafe operations like user roles (Admin, Employee, Customer), reservations, and orders.

## Features

* **User Roles:**
    * **Customer:** Can sign up, log in, make reservations, view past reservations, and view associated orders & loyalty points.
    * **Employee:** Can log in, add new customer accounts, add reservations for customers, and create orders (optionally linked to reservations).
    * **Admin:** Can log in and add new employee accounts.
* **Authentication:** Secure login/signup using password hashing.
* **Reservations:** Customers can book tables, and employees can manage reservations.
* **Orders:** Employees can create orders, optionally linking them to reservations. Basic loyalty points are awarded upon order completion if linked to a reservation.
* **Database:** Uses SQLite for simple, file-based data storage.
* **Local Deployment:** Runs entirely on your local machine using Flask's development server.

## Technology Stack

* **Backend:** Python, Flask
* **Database:** SQLite3
* **Frontend:** HTML, CSS
* **Environment Management:** venv

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd cafe_management_system
    ```
    *(Replace `<your-repository-url>` with the actual URL of your GitHub repository)*

2.  **Create and Activate Virtual Environment:**
    * **Windows (cmd/powershell):**
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
    * **Linux/macOS:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the Database:**
    *(This creates the `cafe.db` file and sets up the necessary tables and default users)*
    ```bash
    python init_db.py
    ```

## Running the Application

1.  **Ensure your virtual environment is activated.**
2.  **Run the Flask app:**
    ```bash
    python app.py
    ```
3.  Open your web browser and navigate to: `http://127.0.0.1:5000` or `http://localhost:5000`

## Usage

* **Sign Up:** New users can sign up via the "Sign Up" link (they are created as 'customer' role).
* **Log In:** Use the login form. Default credentials (created by `init_db.py`):
    * **Admin:** `admin` / `adminpass`
    * **Employee:** `employee1` / `emppass`
    * **Customer:** `customer1` / `custpass`
* Navigate through the dashboard specific to your user role to access available features.

---

*Project created on April 15, 2025, in Chennai, Tamil Nadu, India.*