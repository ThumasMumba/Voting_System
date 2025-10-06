#from flask import flask: This imports the main Flask Class to create the Voting System Web Application
#render_template: This function is used to render HTML templates for the web pages.
#request: This module is used to handle incoming request data from the client (like form submissions
#redirect: function is used to redirect users to different routes within the application.
#url_for: This function is used to build URLs for specific functions dynamically.
#flash: This function is used to send one-time messages to users, often used for notifications
from flask import Flask, render_template, request, redirect, url_for, flash

#importing mysql.connector and Error to connect and handle MySQL database operations
import mysql.connector
from mysql.connector import Error 

#Creating an instance of the flask class to initialize the system. Also a secret string used to encrypt session data and flash messages
app = Flask(__name__)
app.secret_key = 'cbu_voting_system'

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
    
@app.route('/admin/voters')
def admin_voters():
    """
    Displays all registered voters to the admin
    Only accessible by admin users
    """

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

        return render_template('admin_voters.html', voters=voters)  
    except Error as e:
        return f"Database error: {str(e)}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if  __name__ == '__main__':
    app.run(debug=True)