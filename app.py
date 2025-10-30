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
            academic_year VARCHAR(20) NOT NULL,
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

        #SQL query to create elections table stores election information and status
        create_elections_table = """
    CREATE TABLE IF NOT EXISTS elections (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        election_type ENUM('Student Union', 'Class Representative', 'Association') NOT NULL,
        school VARCHAR(100),
        program VARCHAR(100),
        academic_year VARCHAR(20),
        start_date DATETIME NOT NULL,
        end_date DATETIME NOT NULL,
        status ENUM('draft', 'upcoming', 'active', 'completed', 'cancelled') DEFAULT 'draft',
        created_by INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES admin_users(id)
        )"""

        cursor.execute(create_elections_table)

         # SQL query to create votes table if it doesn't exist
        create_votes_table = """
        CREATE TABLE IF NOT EXISTS votes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            election_id INT,
            voter_id INT,
            candidate_id INT,
            voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address VARCHAR(45),
            FOREIGN KEY (election_id) REFERENCES elections(id),
            FOREIGN KEY (voter_id) REFERENCES voters(id)
        )
        """
        cursor.execute(create_votes_table)

        # SQL query to create positions table if it doesn't exist
        create_positions_table = """
        CREATE TABLE IF NOT EXISTS positions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            election_id INT NOT NULL,
            position_name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (election_id) REFERENCES elections(id)
        )
        """ 
        cursor.execute(create_positions_table)

        # SQL query to create candidates table if it doesn't exist
        create_candidates_table = """
        CREATE TABLE IF NOT EXISTS candidates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            election_id INT NOT NULL,
            student_number VARCHAR(50) NOT NULL,
            position VARCHAR(100) NOT NULL,
            manifesto TEXT,
            photo_url VARCHAR(255),
            is_approved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (election_id) REFERENCES elections(id),
            FOREIGN KEY (student_number) REFERENCES voters(student_number)
        )
        """
        cursor.execute(create_candidates_table)

        # Check if default admin user already exists
        check_admin_query = "SELECT id FROM admin_users WHERE username = 'admin'"
        cursor.execute(check_admin_query)
        existing_admin = cursor.fetchone()

        # Insert default admin user if no admin exists
        if not existing_admin:
            insert_admin_query = """
            INSERT INTO admin_users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_admin_query, ('admin', 'admin@gmail.com', 'admin123', 'admin'))
            print("Default Admin user created")
        
        # Insert sample election data for testing
        check_elections_query = "SELECT COUNT(*) as count FROM elections"
        cursor.execute(check_elections_query)
        election_count = cursor.fetchone()[0]

        if election_count == 0:
            # Insert sample elections
            sample_elections = [
                ('Student Union President 2024', 'Student Union Election for President', 'Student Union', 'CBU', 'All Programs', 'All Years', '2024-03-01 08:00:00', '2024-03-05 17:00:00', 'active', 1),
                ('Class Representatives 2024', 'Class Representative Elections', 'Class Representative', 'School of Engineering', 'Computer Science', 'Second Year', '2024-03-10 08:00:00', '2024-03-15 17:00:00', 'upcoming', 1)
            ]
            
            insert_election_query = """
            INSERT INTO elections (name, description, election_type, school, program, academic_year, start_date, end_date, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            for election in sample_elections:
                cursor.execute(insert_election_query, election)
                election_id = cursor.lastrowid
                
                # Create default positions for sample elections
                election_type = election[2]  # election_type is at index 2
                if election_type == 'Student Union':
                    default_positions = ['President', 'Academics Minister', 'Prime Minister']
                    for position_name in default_positions:
                        position_query = "INSERT INTO positions (election_id, position_name) VALUES (%s, %s)"
                        cursor.execute(position_query, (election_id, position_name))
                        print(f"Created position '{position_name}' for Student Union election")
                
                elif election_type == 'Class Representative':
                    default_positions = ['Male Class Representative', 'Female Class Representative']
                    for position_name in default_positions:
                        position_query = "INSERT INTO positions (election_id, position_name) VALUES (%s, %s)"
                        cursor.execute(position_query, (election_id, position_name))
                        print(f"Created position '{position_name}' for Class Representative election")
            
        
        connection.commit()
        print("✅ Database initialized successfully!")

    except Error as e:
        print(f"Error Initializing Database: {e}")
    finally:
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
@app.route('/student/dashboard')
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
        academic_year = request.form['academic_year']
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
                (first_name, last_name, date_of_birth, program, academic_year, student_number,
                nrc, gender, email, phone_number, address_type) VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

            #Excetion of the insert query
            cursor.execute(insert_query, 
               (first_name, last_name, date_of_birth, program, academic_year,
                student_number, nrc, gender, email, phone_number, address_type))
            
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

        # Get total number of registered voters
        cursor.execute("SELECT COUNT(*) as count FROM voters")
        total_voters_result = cursor.fetchone()
        total_voters = total_voters_result['count'] if total_voters_result else 0 

        # Get number of voters who have voted
        cursor.execute("SELECT COUNT(*) as count FROM voters WHERE has_voted = TRUE")
        voted_count_result = cursor.fetchone()
        voted_count = voted_count_result['count'] if voted_count_result else 0

        # Get number of pending votes
        pending_count = total_voters - voted_count

        # Get number of active elections
        cursor.execute("SELECT COUNT(*) as count FROM elections WHERE status='active'")
        active_elections_result = cursor.fetchone()
        active_elections = active_elections_result['count'] if active_elections_result else 0

        # Get recent voter registration
        cursor.execute("""
        SELECT first_name, last_name, student_number, program, email,
                       registration_date, has_voted
        FROM voters
        ORDER BY registration_date DESC
        LIMIT 5
        """)
        recent_voters = cursor.fetchall()

        # Get active elections with vote counts
        elections = []
        try:
            # Check if the votes table exists
            cursor.execute("SHOW TABLES LIKE 'votes'")
            votes_table_exists = cursor.fetchone()

            if votes_table_exists:
                cursor.execute("""
                SELECT e.*, COUNT(v.id) as votes_cast
                FROM elections e
                LEFT JOIN votes v ON e.id = v.election_id
                WHERE e.status = 'active'
                GROUP BY e.id
                ORDER BY e.start_date DESC
                LIMIT 3
                """)
            else:
                cursor.execute("""
                SELECT e.*, 0 as votes_cast
                FROM elections e
                WHERE e.status = 'active'
                ORDER BY e.start_date DESC
                LIMIT 3
                """)
            elections = cursor.fetchall()  # Fixed typo: was 'featchall'

        except Error as e:
            print(f"Error fetching elections: {e}")
            # If there's an error, just get basic election data
            cursor.execute("""
            SELECT e.*, 0 as votes_cast
            FROM elections e
            WHERE e.status = 'active'
            ORDER BY e.start_date DESC
            LIMIT 3
            """)
            elections = cursor.fetchall()

        # Statistics 
        stats = {
            'total_voters': total_voters,
            'voted_count': voted_count,
            'pending_count': pending_count,
            'active_elections': active_elections
        }

        return render_template('admin_dashboard.html', 
                               stats=stats,
                               recent_voters=recent_voters,
                               elections=elections)  
        
    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
        print(f"Database error in admin_dashboard: {e}")
        # Return empty data if database error occurs
        return render_template('admin_dashboard.html',
                             stats={'total_voters': 0, 'voted_count': 0, 'pending_count': 0, 'active_elections': 0},
                             recent_voters=[],
                             elections=[])
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

#logout route
@app.route('/admin/logout')
def admin_logout():
    """
    Handles admin logout and redirects user to admin login page
    """
    # Remove all admin-related session data
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    session.pop('admin_email', None)
    session.pop('admin_role', None)
    
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

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
    return redirect(url_for('admin_dashboard'))

#Voters
@app.route('/admin/voters')
def manage_voters():
    """Placeholder for manage voters page"""
    flash('Voter management feature coming soon!', 'info')
    return redirect(url_for('admin_dashboard'))

#Election Results
@app.route('/admin/results')
def view_results():
    """Placeholder for view results page"""
    flash('Results feature coming soon!', 'info')
    return redirect(url_for('admin_dashboard'))

#Admin Settings
@app.route('/admin/settings')
def system_settings():
    """Placeholder for system settings page"""
    flash('System settings feature coming soon!', 'info')
    return redirect(url_for('admin_dashboard'))

#Election Management
@app.route('/admin/elections')
def manage_elections():
    """
    Display all elections with filtering and search apabilities
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page.', 'error')
        return redirect(url_for('admin_login'))
    
    connection = create_connection()
    if connection is None:
        flash('Database connection error', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        cursor = connection.cursor(dictionary=True)

        #Get filter parameters
        status_filter = request.args.get('status', 'all')
        election_type = request.args.get('type', 'all')
        search_query = request.args.get('search', '')

        #Base Query
        query = """
        SELECT e.*,
                COUNT(DISTINCT c.id) as candidate_count,
                COUNT(DISTINCT v.id) as vote_count,
                a.username as created_by_name
        FROM elections e
        LEFT JOIN candidates c ON e.id = c.election_id
        LEFT JOIN votes v ON e.id = v.election_id
        LEFT JOIN admin_users a ON e.created_by = a.id
        """

        #Builds Where conditions based on filters
        conditions = []
        params = []

        #Status Filter condition
        if status_filter != 'all':
            conditions.append("e.status = %s")
            params.append(status_filter)

        #Election type filter condition
        if election_type != 'all':
            conditions.append("e.election_type = %s")
            params.append(election_type)

        #Search conditions 
        if search_query:
            conditions.append("(e.name LIKE %s OR e.description LIKE %s)")
            params.extend([f'%{search_query}%', f'%{search_query}%'])

        #Where clause if any conditions are there
        if conditions:
            query += " WHERE " + " AND ".join(conditions)   
        query += " GROUP BY e.id ORDER BY e.created_at DESC"    
        cursor.execute(query, tuple(params))
        elections = cursor.fetchall()

        cursor.execute("""
            SELECT 
                COUNT(*) as total_elections,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_elections,
                SUM(CASE WHEN status = 'upcoming' THEN 1 ELSE 0 END) as upcoming_elections,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_elections
                FROM elections
        """)

        stats = cursor.fetchone()

        return render_template('manage_elections.html', 
                               elections=elections,
                               stats=stats,
                               current_status=status_filter,
                               current_type=election_type,
                               search_query=search_query)

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

#Create Elections
@app.route('/admin/elections/create', methods=['GET', 'POST'])
def create_election():
    """
    Create a new election
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))

    # Handling form submission
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        election_type = request.form['election_type']
        school = request.form.get('school', '')
        program = request.form.get('program', '')
        academic_year = request.form.get('academic_year', '')
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']

        # Validate required fields
        if not all([name, election_type, start_date, end_date]):
            flash('Please fill in all required fields.', 'error')
            return render_template('create_election.html')

        connection = create_connection()
        if connection is None:
            flash('Database connection error. Please try again later.', 'error')
            return redirect(url_for('manage_elections'))

        try:
            cursor = connection.cursor()

            # SQL Query to insert new election
            insert_query = """
            INSERT INTO elections
            (name, description, election_type, school, program, academic_year, start_date, end_date, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(insert_query,
                           (name, description, election_type, school, program, academic_year,
                            start_date, end_date, status, session['admin_id']))
            
            # Get the newly created election ID
            election_id = cursor.lastrowid
            
            # Create default positions based on election type
            if election_type == 'Student Union':
                default_positions = ['President', 'Academics Minister', 'Prime Minister']
            elif election_type == 'Class Representative':
                default_positions = ['Male Class Representative', 'Female Class Representative']
            else:  # Association elections - no default positions
                default_positions = []
            
            # Insert default positions
            for position_name in default_positions:
                position_query = "INSERT INTO positions (election_id, position_name) VALUES (%s, %s)"
                cursor.execute(position_query, (election_id, position_name))

            connection.commit()

            flash('Election created successfully with default positions!', 'success')
            return redirect(url_for('manage_elections'))

        except Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return render_template('create_election.html')
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    # GET request - show the create election form
    return render_template('create_election.html')

#Editing an election
@app.route('/admin/elections/<int:election_id>/edit', methods=['GET', 'POST'])
def edit_election(election_id):
    """
    Edit an existing election
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))

    connection = create_connection()
    if connection is None:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('manage_elections'))

    try:
        cursor = connection.cursor(dictionary=True)


        #Handle form submission
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            election_type = request.form['election_type']
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            status = request.form['status']

            #Validate required fields
            if not all([name, election_type, start_date, end_date]):
                flash('Please fill in all required fields.', 'error')
                return render_template('edit_election.html', election=election)

            #SQL Query to update election
            update_query = """
            UPDATE elections
            SET name = %s, description = %s, election_type = %s,
                start_date = %s, end_date = %s, status = %s
            WHERE id = %s
            """
            cursor.execute(update_query,
                           (name, description, election_type,
                            start_date, end_date, status, election_id))
            connection.commit()
       # Fetchs existing election data
        cursor.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
        election = cursor.fetchone()

   #Check if an election exists
        if not election:
            flash('Election not found.', 'error')
            return redirect(url_for('manage_elections'))

    #GET request - show the edit election form with existing data
            return render_template('edit_election.html', election=election)
    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('manage_elections'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

#Delete election route
@app.route('/admin/elections/<int:election_id>/delete', methods=['POST'])
def delete_election(election_id):
    """
    Delete an election
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))

    connection = create_connection()
    if connection is None:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('manage_elections'))

    try:
        cursor = connection.cursor()

        #Check if election exists
        cursor.execute("SELECT id FROM elections WHERE id = %s", (election_id,))
        election = cursor.fetchone()

        if not election:
            flash('Election not found.', 'error')
            return redirect(url_for('manage_elections'))

        #SQL Query to delete election
        delete_query = "DELETE FROM elections WHERE id = %s"
        cursor.execute(delete_query, (election_id,))
        connection.commit()

        flash('Election deleted successfully!', 'success')

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('manage_elections'))

    #Toggle status
@app.route('/admin/elections/<int:election_id>/toggle_status', methods=['POST'])
def toggle_election_status(election_id):
    """
    Toggle the status of an election between active and inactive
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))

    connection = create_connection()
    if connection is None:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('manage_elections'))

    try:
        cursor = connection.cursor(dictionary=True)

        #Check if election exists
        cursor.execute("SELECT status FROM elections WHERE id = %s", (election_id,))
        election = cursor.fetchone()

        if not election:
            flash('Election not found.', 'error')
            return redirect(url_for('manage_elections'))

        #Determine new status
        new_status = 'draft' if election['status'] == 'active' else 'active'

        #SQL Query to update election status
        update_query = "UPDATE elections SET status = %s WHERE id = %s"
        cursor.execute(update_query, (new_status, election_id))
        connection.commit()

        flash(f'Election status updated to {new_status}.', 'success')

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('manage_elections'))

#Manage Positions Route
@app.route('/admin/elections/<int:election_id>/positions', methods=['GET', 'POST'])
def manage_positions(election_id):
    """
    Manage positions for an election
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))

    connection = create_connection()
    if connection is None:
        flash('Database connection error', 'error')
        return redirect(url_for('manage_elections'))

    try:
        cursor = connection.cursor(dictionary=True)

        # Get election details
        cursor.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
        election = cursor.fetchone()

        if not election:
            flash('Election not found', 'error')
            return redirect(url_for('manage_elections'))

        if request.method == 'POST':
            position_name = request.form['position_name']
            
            if position_name:
                insert_query = "INSERT INTO positions (election_id, position_name) VALUES (%s, %s)"
                cursor.execute(insert_query, (election_id, position_name))
                connection.commit()
                flash('Position added successfully!', 'success')

        # Get existing positions
        cursor.execute("SELECT * FROM positions WHERE election_id = %s ORDER BY id", (election_id,))
        positions = cursor.fetchall()

        return render_template('manage_positions.html', 
                             election=election, 
                             positions=positions)

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('manage_elections'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if  __name__ == '__main__':
    app.run(debug=True)