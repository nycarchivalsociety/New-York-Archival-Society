from flask import request, session, redirect, url_for, render_template, flash
from uuid import UUID
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg2
import psycopg2.extras
from . import login
from datetime import datetime
import uuid  # Import the uuid module
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="dpg-co2a6e8l6cac739j2mh0-a.ohio-postgres.render.com",
            port="5432",
            database="nyas_db",
            user="nyas_db_user",
            password="QQ9HfLAqRJq6mZRTx6gZF5uZ4jgvXba3",
            sslmode="require"
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None


@login.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login.login_view'))


@login.route('/register')
def register():
    # Render the login form template
    return render_template('login/register.html')

@login.route('/login')
def login_view():
    # Render the login form template
    return render_template('login/index.html')




@login.route('/donations')
def donations():
    # Ensure user is logged in
    if 'user_id' not in session:
        # Redirect to login page if user is not in session
        return redirect(url_for('login.login_view'))

    # Get user_id from the session
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # Fetch all donations related to the logged-in user
        cur.execute("""
            SELECT i.item_name, i.item_description, i.item_image_url, 
                   d.donated_amount, d.donation_date
            FROM item_donors d
            INNER JOIN items i ON i.item_id = d.item_id
            WHERE d.donor_id = %s;
        """, (user_id,))
        donations_info = cur.fetchall()
    except psycopg2.Error as e:
        # Handle database error
        flash(f"Database error: {e.pgerror}", 'error')
        donations_info = None
    finally:
        cur.close()
        conn.close()

    # Render the donations page with the donation data
    return render_template('login/donations.html', donations=donations_info)




@login.route('/register_form', methods=['GET', 'POST'], endpoint='login_register')
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)  # Hash the password
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Check if the username or email already exists
        cur.execute('SELECT * FROM users WHERE username = %s OR email = %s;', (username, email,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('Username or Email already exists. Please choose another one.')
            return redirect(url_for('login.register'))

        # Generate a new UUID for the user_id
        new_user_id = str(uuid.uuid4())
        
        # Proceed with inserting the new user since the username and email are unique
        cur.execute('INSERT INTO users (user_id, username, email, hashed_password, created_at) VALUES (%s, %s, %s, %s, %s);', 
                    (new_user_id, username, email, hashed_password, datetime.now()))
        conn.commit()
        cur.close()
        conn.close()
        
        # Redirect to the login page after successful registration
        return redirect(url_for('login.login_form'))
    else:
        # If it's a GET request, render the registration page
        return render_template('login/register.html')


@login.route('/login_form', methods=['GET', 'POST'])
def login_form():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM users WHERE email = %s;', (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        # Check the hashed password
        if user and check_password_hash(user['hashed_password'], password):
             session['user_id'] = user['user_id']
             session['username'] = user['username']  # Store the username in session instead of the user's email
             return redirect(url_for('main.index')) 
        else:
            flash('Invalid email or password')
            return redirect(url_for('login.login_view'))
    else:
        return render_template('main/index.html')

    
    