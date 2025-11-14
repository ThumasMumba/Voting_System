#from flask import flask: This imports the main Flask Class to create the Voting System Web Application
#render_template: This function is used to render HTML templates for the web pages.
#request: This module is used to handle incoming request data from the client (like form submissions
#redirect: function is used to redirect users to different routes within the application.
#url_for: This function is used to build URLs for specific functions dynamically.
#flash: This function is used to send one-time messages to users, often used for notifications
from flask import Flask, render_template, request, redirect, url_for, flash, session

#importing mysql.connector and Error to connect and handle MySQL database operations
import mysql.connector
import json
import os
from mysql.connector import Error 
from datetime import datetime
from urllib.parse import urlparse

#Creating an instance of the flask class to initialize the system. Also a secret string used to encrypt session data and flash messages
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cbu_voting_system_dev_fallback')

# Add this configuration to ensure HTML files process Jinja2 syntax
app.jinja_env.add_extension('jinja2.ext.do')

#This connects to the MySQL database using the provided configuration details
def get_db_config():
    """Get database configuration from Railway environment variables"""
    # Try multiple possible database URL variables
    db_url_str = (
        os.environ.get('MYSQL_URL') or 
        os.environ.get('DATABASE_URL')
    )
    
    if db_url_str:
        db_url = urlparse(db_url_str)
        return {
            'host': db_url.hostname,
            'user': db_url.username,
            'password': db_url.password,
            'database': db_url.path[1:],
            'port': db_url.port
        }
    else:
        # Try individual MySQL variables
        if all(key in os.environ for key in ['MYSQLHOST', 'MYSQLUSER', 'MYSQLPASSWORD', 'MYSQLDATABASE']):
            return {
                'host': os.environ['MYSQLHOST'],
                'user': os.environ['MYSQLUSER'],
                'password': os.environ['MYSQLPASSWORD'],
                'database': os.environ['MYSQLDATABASE'],
                'port': int(os.environ.get('MYSQLPORT', '3306'))
            }
        else:
            # Local development fallback
            return {
                'host': 'localhost',
                'user': 'root',
                'password': '',
                'database': 'voting_system_db'
            }

# Use the function to get db_config
db_config = get_db_config()

#A function that defines the database connections and uses exception handling to manage connection errors
def create_connection():
    """Create and return a database Connection."""
    try:
        # Get fresh config each time (in case env vars change)
        current_config = get_db_config()
        connection = mysql.connector.connect(**current_config)
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
            school_id INT,  
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
            program TEXT,
            academic_year TEXT,
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

        # SQL query to create schools table if it doesn't exist
        create_schools_table = """
        CREATE TABLE IF NOT EXISTS schools (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            code VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_schools_table)

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

        # FIXED: SQL Query that creates the programs table - removed extra comma
        create_programs_table = """
        CREATE TABLE IF NOT EXISTS programs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            school_id INT,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50) NOT NULL UNIQUE,
            duration_years INT DEFAULT 4,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (school_id) REFERENCES schools(id)
        )
        """
        cursor.execute(create_programs_table)

        # SQL query to create academic_years table if it doesn't exist
        create_academic_years_table = """
        CREATE TABLE IF NOT EXISTS academic_years (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            code VARCHAR(50) NOT NULL UNIQUE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_academic_years_table)

        # Insert default schools if they dont exist
        check_schools_query = "SELECT COUNT(*) as count FROM schools"
        cursor.execute(check_schools_query)
        schools_count = cursor.fetchone()[0]

        if schools_count == 0:
            default_schools = [
                ('School of Mathematics and Natural Sciences', 'SMNS', 'School of Mathematics and Natural Sciences'),
                ('School of Information Communications Technology', 'SICT', 'School of Information Communication Technology'),
                ('School of Business', 'SB', 'School of Business'),
                ('School of Medicine', 'SOM', 'School of Medicine'),
                ('School of Humanities and Social Sciences', 'SHSS', 'School of Humanities and Social Sciences')
            ]
            
            insert_school_query = "INSERT INTO schools (name, code, description) VALUES (%s, %s, %s)"
            for school in default_schools:
                cursor.execute(insert_school_query, school)

        # Insert default programs if they don't exist
        check_programs_query = "SELECT COUNT(*) as count FROM programs"
        cursor.execute(check_programs_query)
        programs_count = cursor.fetchone()[0]

        if programs_count == 0:
            # Get school IDs
            cursor.execute("SELECT id, name FROM schools")
            schools = cursor.fetchall()
            school_map = {school[1]: school[0] for school in schools}
            
            default_programs = [
                ('Computer Science', 'CS', school_map['School of Information Communications Technology'], 4),
                ('Computer Engineering', 'CE', school_map['School of Information Communications Technology'], 5),
                ('Software Engineering', 'SE', school_map['School of Information Communications Technology'], 4),
                ('Information Technology', 'IT', school_map['School of Information Communications Technology'], 4),
                ('Data Science', 'DS', school_map['School of Mathematics and Natural Sciences'], 4),
                ('Bioinformatics', 'BIO', school_map['School of Mathematics and Natural Sciences'], 4),
                ('Business Administration', 'BA', school_map['School of Business'], 4),
                ('Medicine', 'MED', school_map['School of Medicine'], 6),
                ('Psychology', 'PSY', school_map['School of Humanities and Social Sciences'], 4)
            ]
            
            insert_program_query = "INSERT INTO programs (name, code, school_id, duration_years) VALUES (%s, %s, %s, %s)"
            for program in default_programs:
                cursor.execute(insert_program_query, program)

        # Insert default academic years if they don't exist
        check_academic_years_query = "SELECT COUNT(*) as count FROM academic_years"
        cursor.execute(check_academic_years_query)
        academic_years_count = cursor.fetchone()[0]

        if academic_years_count == 0:
            default_academic_years = [
                ('First Year', 'Y1'),
                ('Second Year', 'Y2'),
                ('Third Year', 'Y3'),
                ('Fourth Year', 'Y4'),
                ('Fifth Year', 'Y5'),
                ('Sixth Year', 'Y6')
            ]
            
            insert_academic_year_query = "INSERT INTO academic_years (name, code) VALUES (%s, %s)"
            for academic_year in default_academic_years:
                cursor.execute(insert_academic_year_query, academic_year)

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
                ('Student Union President 2024', 'Student Union Election for President', 'Student Union', 'CBU', '["all"]', '["all"]', '2024-03-01 08:00:00', '2024-03-05 17:00:00', 'active', 1),
                ('Class Representatives 2024', 'Class Representative Elections', 'Class Representative', 'School of Engineering', '["1"]', '["2"]', '2024-03-10 08:00:00', '2024-03-15 17:00:00', 'upcoming', 1)
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
        connection.rollback()
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
#Initializes database when the flask app starts
init_database()

# helper functions to fetch data from database
def get_schools_from_db():
    """Fetch all active schools from the database"""
    connection = create_connection()
    if connection is None:
        print("❌ Database connection failed in get_schools_from_db")
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name, code FROM schools WHERE is_active = TRUE ORDER BY name")
        schools = cursor.fetchall()
        print(f"✅ Found {len(schools)} schools: {schools}")
        return schools
    except Error as e:
        print(f"Error fetching schools: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_programs_from_db(school_id=None):
    """Fetch programs from the database, optionally filtered by school"""
    connection = create_connection()
    if connection is None:
        print("❌ Database connection failed in get_programs_from_db")
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        if school_id:
            cursor.execute("""
                SELECT p.id, p.name, p.code, s.name as school_name 
                FROM programs p 
                JOIN schools s ON p.school_id = s.id 
                WHERE p.is_active = TRUE AND p.school_id = %s 
                ORDER BY p.name
            """, (school_id,))
        else:
            cursor.execute("""
                SELECT p.id, p.name, p.code, s.name as school_name 
                FROM programs p 
                JOIN schools s ON p.school_id = s.id 
                WHERE p.is_active = TRUE 
                ORDER BY s.name, p.name
            """)
        programs = cursor.fetchall()
        print(f"✅ Found {len(programs)} programs: {programs}")
        return programs
    except Error as e:
        print(f"Error fetching programs: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_academic_years_from_db():
    """Fetch all active academic years from the database"""
    connection = create_connection()
    if connection is None:
        print("❌ Database connection failed in get_academic_years_from_db")
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name, code FROM academic_years WHERE is_active = TRUE ORDER BY code")
        academic_years = cursor.fetchall()
        print(f"✅ Found {len(academic_years)} academic years: {academic_years}")
        return academic_years
    except Error as e:
        print(f"Error fetching academic years: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Candidates Management Routes
@app.route('/admin/candidates')
def manage_candidates():
    """
    Display all candidates with filtering capabilities
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

        # Get filter parameters
        election_filter = request.args.get('election', 'all')
        status_filter = request.args.get('status', 'all')
        search_query = request.args.get('search', '')

        # Base query for candidates
        query = """
        SELECT c.*, 
               e.name as election_name,
               e.election_type,
               v.first_name, 
               v.last_name,
               v.program,
               v.academic_year,
               v.date_of_birth,
               v.nrc,
               v.gender,
               v.email
        FROM candidates c
        LEFT JOIN elections e ON c.election_id = e.id
        LEFT JOIN voters v ON c.student_number = v.student_number
        """

        # Build WHERE conditions based on filters
        conditions = []
        params = []

        # Election filter condition
        if election_filter != 'all':
            conditions.append("c.election_id = %s")
            params.append(election_filter)

        # Status filter condition
        if status_filter != 'all':
            conditions.append("c.is_approved = %s")
            params.append(1 if status_filter == 'approved' else 0)

        # Search conditions
        if search_query:
            conditions.append("(v.first_name LIKE %s OR v.last_name LIKE %s OR v.student_number LIKE %s OR c.position LIKE %s)")
            params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

        # WHERE clause if any conditions are there
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY c.created_at DESC"
        
        cursor.execute(query, tuple(params))
        candidates = cursor.fetchall()

        # Get all elections for filter dropdown
        cursor.execute("SELECT id, name FROM elections ORDER BY name")
        elections = cursor.fetchall()

        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_candidates,
                SUM(CASE WHEN is_approved = TRUE THEN 1 ELSE 0 END) as approved_candidates,
                SUM(CASE WHEN is_approved = FALSE THEN 1 ELSE 0 END) as pending_candidates
            FROM candidates
        """)
        stats = cursor.fetchone()

        return render_template('manage_candidates.html', 
                               candidates=candidates,
                               elections=elections,
                               stats=stats,
                               current_election=election_filter,
                               current_status=status_filter,
                               search_query=search_query)

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/admin/candidates/create', methods=['GET', 'POST'])
def create_candidate():
    """
    Create a new candidate
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))
    
    connection = create_connection()
    if connection is None:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('manage_candidates'))

    try:
        cursor = connection.cursor(dictionary=True)

        # Get elections for dropdown
        cursor.execute("SELECT id, name, election_type FROM elections ORDER BY name")
        elections = cursor.fetchall()

        # Get positions for selected election (will be populated via AJAX)
        positions = []

        if request.method == 'POST':
            # Get form data
            election_id = request.form['election_id']
            student_number = request.form['student_number']
            position = request.form['position']
            manifesto = request.form.get('manifesto', '')
            
            # Validate required fields
            if not all([election_id, student_number, position]):
                flash('Please fill in all required fields.', 'error')
                return render_template('create_candidate.html', 
                                     elections=elections, 
                                     positions=positions)

            # Check if student exists
            cursor.execute("SELECT * FROM voters WHERE student_number = %s", (student_number,))
            student = cursor.fetchone()

            if not student:
                flash('No student found with that student number.', 'error')
                return render_template('create_candidate.html', 
                                     elections=elections, 
                                     positions=positions)

            # Check if candidate already exists for this election and position
            cursor.execute("""
                SELECT id FROM candidates 
                WHERE election_id = %s AND student_number = %s
            """, (election_id, student_number))
            existing_candidate = cursor.fetchone()

            if existing_candidate:
                flash('This student is already a candidate in this election.', 'error')
                return render_template('create_candidate.html', 
                                     elections=elections, 
                                     positions=positions)

            # Handle file upload
            photo_url = ''
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo and photo.filename != '':
                    # Secure filename and save
                    import os
                    from werkzeug.utils import secure_filename
                    
                    # Create uploads directory if it doesn't exist
                    upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'candidates')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Generate unique filename
                    filename = secure_filename(f"{student_number}_{photo.filename}")
                    photo_path = os.path.join(upload_dir, filename)
                    photo.save(photo_path)
                    
                    # Store relative path for web access
                    photo_url = f"uploads/candidates/{filename}"

            # Insert candidate into database
            insert_query = """
            INSERT INTO candidates (election_id, student_number, position, manifesto, photo_url, is_approved)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, 
                         (election_id, student_number, position, manifesto, photo_url, True))
            
            connection.commit()
            flash('Candidate created successfully!', 'success')
            return redirect(url_for('manage_candidates'))

        # GET request - show the form
        return render_template('create_candidate.html', 
                             elections=elections, 
                             positions=positions)

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('manage_candidates'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/admin/get-positions/<int:election_id>')
def get_positions_by_election(election_id):
    """
    AJAX endpoint to get positions for a specific election
    """
    connection = create_connection()
    if connection is None:
        return json.dumps([])
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, position_name FROM positions WHERE election_id = %s ORDER BY position_name", (election_id,))
        positions = cursor.fetchall()
        return json.dumps(positions)
    except Error as e:
        print(f"Error fetching positions: {e}")
        return json.dumps([])
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/admin/get-student/<student_number>')
def get_student_info(student_number):
    """
    AJAX endpoint to get student information by student number
    """
    connection = create_connection()
    if connection is None:
        return json.dumps({})
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT first_name, last_name, program, academic_year, date_of_birth, nrc, gender, email
            FROM voters WHERE student_number = %s
        """, (student_number,))
        student = cursor.fetchone()
        return json.dumps(student if student else {})
    except Error as e:
        print(f"Error fetching student: {e}")
        return json.dumps({})
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/admin/candidates/<int:candidate_id>/toggle_approval', methods=['POST'])
def toggle_candidate_approval(candidate_id):
    """
    Toggle candidate approval status
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))

    connection = create_connection()
    if connection is None:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('manage_candidates'))

    try:
        cursor = connection.cursor(dictionary=True)

        # Check if candidate exists
        cursor.execute("SELECT id, is_approved FROM candidates WHERE id = %s", (candidate_id,))
        candidate = cursor.fetchone()

        if not candidate:
            flash('Candidate not found.', 'error')
            return redirect(url_for('manage_candidates'))

        # Toggle approval status
        new_status = not candidate['is_approved']
        update_query = "UPDATE candidates SET is_approved = %s WHERE id = %s"
        cursor.execute(update_query, (new_status, candidate_id))
        connection.commit()

        status_text = "approved" if new_status else "pending"
        flash(f'Candidate status updated to {status_text}.', 'success')

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('manage_candidates'))

@app.route('/admin/candidates/<int:candidate_id>/delete', methods=['POST'])
def delete_candidate(candidate_id):
    """
    Delete a candidate
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))

    connection = create_connection()
    if connection is None:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('manage_candidates'))

    try:
        cursor = connection.cursor()

        # Check if candidate exists
        cursor.execute("SELECT id FROM candidates WHERE id = %s", (candidate_id,))
        candidate = cursor.fetchone()

        if not candidate:
            flash('Candidate not found.', 'error')
            return redirect(url_for('manage_candidates'))

        # Delete candidate
        delete_query = "DELETE FROM candidates WHERE id = %s"
        cursor.execute(delete_query, (candidate_id,))
        connection.commit()

        flash('Candidate deleted successfully!', 'success')

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('manage_candidates'))

@app.route('/admin/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
def edit_candidate(candidate_id):
    """
    Edit an existing candidate
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))

    connection = create_connection()
    if connection is None:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('manage_candidates'))

    try:
        cursor = connection.cursor(dictionary=True)

        # Get candidate data
        cursor.execute("""
            SELECT c.*, 
                   e.name as election_name,
                   v.first_name, 
                   v.last_name,
                   v.program,
                   v.academic_year,
                   v.date_of_birth,
                   v.nrc,
                   v.gender,
                   v.email
            FROM candidates c
            LEFT JOIN elections e ON c.election_id = e.id
            LEFT JOIN voters v ON c.student_number = v.student_number
            WHERE c.id = %s
        """, (candidate_id,))
        candidate = cursor.fetchone()

        if not candidate:
            flash('Candidate not found.', 'error')
            return redirect(url_for('manage_candidates'))

        # Get elections and positions
        cursor.execute("SELECT id, name FROM elections ORDER BY name")
        elections = cursor.fetchall()

        cursor.execute("SELECT id, position_name FROM positions WHERE election_id = %s ORDER BY position_name", (candidate['election_id'],))
        positions = cursor.fetchall()

        if request.method == 'POST':
            # Get form data
            election_id = request.form['election_id']
            position = request.form['position']
            manifesto = request.form.get('manifesto', '')
            is_approved = 'is_approved' in request.form

            # Validate required fields
            if not all([election_id, position]):
                flash('Please fill in all required fields.', 'error')
                return render_template('edit_candidate.html', 
                                     candidate=candidate,
                                     elections=elections,
                                     positions=positions)

            # Handle file upload
            photo_url = candidate['photo_url']
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo and photo.filename != '':
                    # Secure filename and save
                    import os
                    from werkzeug.utils import secure_filename
                    
                    # Create uploads directory if it doesn't exist
                    upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'candidates')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Generate unique filename
                    filename = secure_filename(f"{candidate['student_number']}_{photo.filename}")
                    photo_path = os.path.join(upload_dir, filename)
                    photo.save(photo_path)
                    
                    # Store relative path for web access
                    photo_url = f"uploads/candidates/{filename}"

            # Update candidate
            update_query = """
            UPDATE candidates 
            SET election_id = %s, position = %s, manifesto = %s, photo_url = %s, is_approved = %s
            WHERE id = %s
            """
            cursor.execute(update_query, 
                         (election_id, position, manifesto, photo_url, is_approved, candidate_id))
            
            connection.commit()
            flash('Candidate updated successfully!', 'success')
            return redirect(url_for('manage_candidates'))

        # GET request - show the form
        return render_template('edit_candidate.html', 
                             candidate=candidate,
                             elections=elections,
                             positions=positions)

    except Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('manage_candidates'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


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

     # For GET requests, show the registration form with schools and academic years
    if request.method == 'GET':
        # Fetch schools and academic years from database
        schools = get_schools_from_db()
        academic_years = get_academic_years_from_db()
        
        return render_template('register.html', 
                              schools=schools, 
                              academic_years=academic_years)

    #check if the form submission is a POST Request
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        school_id = request.form['school']
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
                (first_name, last_name, date_of_birth, school_id, program, academic_year, student_number,
                nrc, gender, email, phone_number, address_type) VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

            #Excetion of the insert query
            cursor.execute(insert_query, 
               (first_name, last_name, date_of_birth, school_id, program, academic_year,
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
    
   # This route fetches programs by school
@app.route('/get-programs/<int:school_id>')
def get_programs(school_id):
    """AJAX endpoint to get programs by school"""
    programs = get_programs_from_db(school_id)
    return json.dumps(programs)

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
    
    # Fetch data from database for the form
    schools = get_schools_from_db()
    programs = get_programs_from_db()
    academic_years = get_academic_years_from_db()

    # Handling form submission
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        election_type = request.form['election_type']
        school_id = request.form.get('school', '')

        
        program_selections = request.form.getlist('program')
        if 'all' in program_selections:
            program = 'all'
        else:
            program = json.dumps(program_selections) if program_selections else ''


        academic_year_selections = request.form.getlist('academic_year')
        if 'all' in academic_year_selections:
            academic_year = 'all'
        else:
            # Store selected academic year IDs as JSON string
            academic_year = json.dumps(academic_year_selections) if academic_year_selections else ''


        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']

        # Validate required fields
        if not all([name, election_type, start_date, end_date]):
            flash('Please fill in all required fields.', 'error')
            return render_template('create_election.html',
                                   schools=schools,
                                   programs=programs,
                                   academic_years=academic_years)
        
        # Validate date logic
        if start_date >= end_date:
            flash('End date must be after start date.', 'error')
            return render_template('create_election.html', 
                                 schools=schools, 
                                 programs=programs, 
                                 academic_years=academic_years)

        connection = create_connection()
        if connection is None:
            flash('Database connection error. Please try again later.', 'error')
            return redirect(url_for('manage_elections'))

        try:
            cursor = connection.cursor()

            # Get school name if school_id is provided
            school_name = ''
            if school_id:
                cursor.execute("SELECT name FROM schools WHERE id = %s", (school_id,))
                school_result = cursor.fetchone()
                if school_result:
                    school_name = school_result[0]

            # SQL Query to insert new election
            insert_query = """
            INSERT INTO elections
            (name, description, election_type, school, program, academic_year, start_date, end_date, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(insert_query,
                           (name, description, election_type, school_name, program, academic_year,
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
            return render_template('create_election.html', 
                                 schools=schools, 
                                 programs=programs, 
                                 academic_years=academic_years)
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    # GET request - show the create election form
    return render_template('create_election.html',
                         schools=schools,
                         programs=programs,
                         academic_years=academic_years)


#Get programs by school in AJAX
@app.route('/admin/get-programs/<int:school_id>')
def get_programs_by_school(school_id):
    """AJAX endpoint to get programs by school"""
    programs = get_programs_from_db(school_id)
    return json.dumps(programs)


#Editing an election
@app.route('/admin/elections/<int:election_id>/edit', methods=['GET', 'POST'])
def edit_election(election_id):
    """
    Edit an existing election
    """
    if 'admin_logged_in' not in session:
        flash('Please login as admin to access this page', 'error')
        return redirect(url_for('admin_login'))
    
     # Fetch data from database for the form
    schools = get_schools_from_db()
    programs = get_programs_from_db()
    academic_years = get_academic_years_from_db()

    connection = create_connection()
    if connection is None:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('manage_elections'))

    try:
        cursor = connection.cursor(dictionary=True)

     # Fetch existing election data
        cursor.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
        election = cursor.fetchone()

        # Check if election exists
        if not election:
            flash('Election not found.', 'error')
            return redirect(url_for('manage_elections'))

        #Handle form submission
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            election_type = request.form['election_type']
            school_id = request.form.get('school', '')
             # Handle multiple program selection
            program_selections = request.form.getlist('program')
            if 'all' in program_selections:
                program = 'all'
            else:
                program = json.dumps(program_selections) if program_selections else ''
            
            # Handle multiple academic year selection
            academic_year_selections = request.form.getlist('academic_year')
            if 'all' in academic_year_selections:
                academic_year = 'all'
            else:
                academic_year = json.dumps(academic_year_selections) if academic_year_selections else ''
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            status = request.form['status']

            #Validate required fields
            if not all([name, election_type, start_date, end_date]):
                flash('Please fill in all required fields.', 'error')
                return render_template('edit_election.html', 
                                     election=election, 
                                     schools=schools, 
                                     programs=programs, 
                                     academic_years=academic_years)
           
            # Get school name if school_id is provided
            school_name = ''
            if school_id:
                cursor.execute("SELECT name FROM schools WHERE id = %s", (school_id,))
                school_result = cursor.fetchone()
                if school_result:
                    school_name = school_result['name']

            #SQL Query to update election
            update_query = """
             UPDATE elections
            SET name = %s, description = %s, election_type = %s, school = %s,
                program = %s, academic_year = %s, start_date = %s, end_date = %s, status = %s
            WHERE id = %s
            """
            cursor.execute(update_query,
                           (name, description, election_type, school_name, program, academic_year,
                            start_date, end_date, status, election_id))
            connection.commit()
       
        flash('Election updated successfully!', 'success')
        return redirect(url_for('manage_elections'))

        # GET request - parse existing data for the for
        if election['program'] and election['program'] != 'all':
            try:
                election['program_list'] = json.loads(election['program'])
            except:
                election['program_list'] = [election['program']]
        else:
            election['program_list'] = ['all'] if election['program'] == 'all' else []
        
        if election['academic_year'] and election['academic_year'] != 'all':
            try:
                election['academic_year_list'] = json.loads(election['academic_year'])
            except:
                election['academic_year_list'] = [election['academic_year']]
        else:
            election['academic_year_list'] = ['all'] if election['academic_year'] == 'all' else []
        
        return render_template('edit_election.html', 
                             election=election, 
                             schools=schools, 
                             programs=programs, 
                             academic_years=academic_years)

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

# For Railway production deployment
if __name__ == '__main__':
    # Check if we're in production (Railway sets PORT environment variable)
    if os.environ.get('RAILWAY_ENV') or os.environ.get('PORT'):
        # Railway will use gunicorn, so no need to run app directly
        pass
    else:
        # Local development
        app.run(debug=True)