#from flask import flask: This imports the main Flask Class to create the Voting System Web Application
#render_template: This function is used to render HTML templates for the web pages.
#request: This module is used to handle incoming request data from the client (like form submissions
#redirect: function is used to redirect users to different routes within the application.
#url_for: This function is used to build URLs for specific functions dynamically.
#flash: This function is used to send one-time messages to users, often used for notifications
from flask import Flask, render_template, request, redirect, url_for, flash, session

#importing mysql.connector and Error to connect and handle MySQL database operations
import mysql.connector
from mysql.connector import Error 
from datetime import datetime

#Creating an instance of the flask class to initialize the system. Also a secret string used to encrypt session data and flash messages
app = Flask(__name__)
app.secret_key = 'cbu_voting_system'

# Add this configuration to ensure HTML files process Jinja2 syntax
app.jinja_env.add_extension('jinja2.ext.do')

#This connects to the MySQL database using the provided configuration details
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'voting_system_db' 
}

#A function that defines the database connections and uses exception handling to manage connection errors
def create_connection():
    """Create and return a database Connection."""
    try: 
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error Connecting to MySQL Database: {e}")
        return None

def init_database():
    """Initialize the database by ensuring all required tables exits.
    This function is called when the system starts."""
    connection = create_connection()
    if connection is None:
        print("Failed to create database connection")
        return

    try:
        #Creates a cursor object to exceute SQL Comands
        cursor = connection.cursor()

        # SQL query to create voters table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS voters (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            date_of_birth VARCHAR(20) NOT NULL,
            program VARCHAR(100) NOT NULL,
            student_number VARCHAR(50) UNIQUE NOT NULL,
            nrc VARCHAR(50) NOT NULL,
            gender ENUM('Male', 'Female') NOT NULL,
            email VARCHAR(100) NOT NULL,
            phone_number VARCHAR(20) NOT NULL,
            address_type ENUM('Campus', 'Off-Campus') NOT NULL,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            has_voted BOOLEAN DEFAULT FALSE
        )
        """
        cursor.execute(create_table_query)


        # SQL query to create admin table if it doesn't exist
        create_admin_table = """
        CREATE TABLE IF NOT EXISTS admin_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role ENUM('admin') DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
        """

        cursor.execute(create_admin_table)

        #Insert a default admin user if none exists
        check_admin_query = "SELECT id FROM admin_users WHERE username = 'admin'"
        cursor.execute(check_admin_query)
        existing_admin = cursor.fetchone()

        if not existing_admin:
            #Default Login Password is 'admin123'
            insert_admin_query = """
            INSERT INTO admin_users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_admin_query, ('admin', 'admin@gmail.com', 'admin123', 'admin'))
            print("Default Admin user created")
        
        connection.commit()
        print("✅ Database initialized successfully!")

    except Error as e:
        print(f"Error Initializing Database: {e}")
    finally:
        #Ensures we clean up resources by closing the connection
        if connection.is_connected():
            cursor.close()
            connection.close()

#Initializes database when the flask app starts
init_database()

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles voter login
    GET: Displays the login form
    POST: Processes the login form submission
    """

    #Check if the form submission is a POST Request
    if request.method == 'POST':
        #Get login credentials from the form
        email = request.form['email-address']
        student_number = request.form['SIN']

        #Check if the fields are not empty
        if not email or not student_number:
            flash('Please enter both email student number.', 'error')
            return redirect(url_for('login'))

        connection = create_connection()
        if connection is None:
            flash('Database connection error. Please try again later.', 'error')
            return redirect(url_for('login'))

        try:
            cursor = connection.cursor(dictionary=True)

            #SQL Query to verify student credentials
            login_query = """
            SELECT id, first_name, last_name, student_number, email, program, has_voted 
            FROM voters
            WHERE email = %s AND student_number = %s
            """

            #Execute the query with email and student_number
            cursor.execute(login_query, (email, student_number))

            #Get the student record
            student = cursor.fetchone()

            #Check if student exists
            if student:
                session['student_id'] = student['id']
                session['first_name'] = student['first_name']
                session['last_name'] = student['last_name']
                session['student_number'] = student['student_number']
                session['email'] = student['email']
                session['program'] = student['program']
                session['has_voted'] = student['has_voted']

                flash('Login successful! You can now vote.', 'success')
                return redirect(url_for('student_dasboard'))
            else:
                flash('No voter found with that student number.', 'error')
                return redirect(url_for('login'))

        except Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return redirect(url_for('login'))
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    #GET request, show the login form
    return render_template('login.html')

#Student Dashboard Route
@app.route('/student/dasboard')
def student_dasboard():
    """
    Displays the student voting dashboard
    Shows student information and voting options
    """

    if 'student_id' not in session:
        flash('Please login to access the voting dashboard.', 'error')
        return redirect(url_for('login'))
    
    student_data = {
        'first_name': session['first_name'],
        'last_name': session['last_name'],
        'student_number': session['student_number'],
        'email': session['email'],
        'program': session['program'],
        'has_voted': session['has_voted']
    }

    return render_template('student_dashboard.html', student=student_data)


#Registration Route
@app.route('/', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles voter registration
    GET: Displays the registration form
    POST: Processes the form submission and saves it to the database
    """

    #check if the form submission is a POST Request
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        program = request.form['program']
        student_number = request.form['student_number']
        nrc = request.form['nrc']
        gender = request.form['gender']
        email = request.form['email']
        phone_number = request.form['phone_number']
        address_type = request.form['address_type']

        #Cheack if important fields are not empty
        if not all([first_name, last_name, student_number, email]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('register'))
        
        #get a database connection
        connection = create_connection()
        if connection is None:
            flash('Database connection error. Please try again later.', 'error')
            return redirect(url_for('register'))
        
        try: 
            cursor = connection.cursor()

            #SQL Query to check if student number already exists
            check_query = "SELECT id FROM voters WHERE student_number = %s"

            #Execute the query with the student_number as parameter
            cursor.execute(check_query, (student_number,))

            existing_voter = cursor.fetchone()

            #If a voter is with this student number show error message
            if existing_voter:
                flash('A voter with this student number already exists.', 'error')
                return redirect(url_for('register'))
            
            #SQL Query  to insert new voter into the database
            insert_query = """
            INSERT INTO voters
            (first_name, last_name, date_of_birth, program, student_number,
            nrc, gender, email, phone_number, address_type) VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            #Excetion of the insert query
            cursor.execute(insert_query, 
                           (first_name, last_name, date_of_birth, program,
                            student_number, nrc, gender, email, phone_number,
                            address_type))
            
            connection.commit()

            #Show success message to user
            flash('Registration successful! You can now login to vote when the election opens.', 'success')

        except Error as e:
            flash(f'Database error: {str(e)}', 'error')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

        return redirect(url_for('register'))    
    
    # For GET requests, show the registration form
    return render_template('register.html')

#Admin dashboard Route    
@app.route('/admin/dashboard')
def admin_dashboard():
    """
    Displays all registered voters to the admin
    Only accessible by admin users
    """

     # Check if admin is logged in
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page.', 'error')
        return redirect(url_for('admin_login'))

    connection = create_connection()
    if connection is None:
        return "Database connection error", 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
                        SELECT id, first_name, last_name, student_number, program,
                        gender, email, phone_number, address_type, registration_date, has_voted
                        FROM voters
                        ORDER BY registration_date DESC
                        """)
        voters = cursor.fetchall()

        return render_template('admin_dashboard.html', voters=voters)  
    except Error as e:
        return f"Database error: {str(e)}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

#Admin login Route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Handles admin login
    GET: Displays the admin login form
    POST: Processes the admin login form submission
    """

    # Clear any existing flash messages on GET request
    if request.method == 'GET':
        session.pop('_flashes', None)
    
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        # Get login credentials from the form
        email = request.form.get('email-address')
        password = request.form.get('password')

        print(f"Login attempt - Email: {email}, Password: {password}")  # Debug print

        # Check if the fields are not empty
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('admin_login.html')
        
        connection = create_connection()
        if connection is None:
            flash('Database connection error. Please try again later.', 'error')
            return render_template('admin_login.html')
        
        try:
            cursor = connection.cursor(dictionary=True)

            # SQL Query to verify admin credentials
            login_query = """
            SELECT id, username, email, role 
            FROM admin_users
            WHERE email = %s AND password = %s AND is_active = TRUE
            """

            # Execute the query with email and password
            cursor.execute(login_query, (email, password))

            # Get the admin record
            admin_user = cursor.fetchone()

            print(f"Admin user found: {admin_user}")  # Debug print

            # Check if admin exists
            if admin_user:
                session['admin_logged_in'] = True
                session['admin_id'] = admin_user['id']
                session['admin_username'] = admin_user['username']
                session['admin_email'] = admin_user['email']
                session['admin_role'] = admin_user['role']

                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials. Please check your email and password.', 'error')
                return render_template('admin_login.html')
            
        except Error as e:
            print(f"Database error: {e}")  # Debug print
            flash(f'Database error: {str(e)}', 'error')
            return render_template('admin_login.html')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    # GET request - show the login form
    return render_template('admin_login.html')

@app.route('/admin/debug')
def admin_debug():
    """Debug route to check admin user"""
    connection = create_connection()
    if connection is None:
        return "Database connection failed"
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin_users")
        admin_users = cursor.fetchall()
        return f"Admin users: {admin_users}"
    except Error as e:
        return f"Error: {e}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if  __name__ == '__main__':
    app.run(debug=True)