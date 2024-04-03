from flask import Flask, jsonify, request, render_template, current_app as app, session
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv
import os
from . import items

# Load environment variables
load_dotenv()

# Database connection parameters
DATABASE_URL = os.getenv('DATABASE_URL')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')

conn = psycopg2.connect(DATABASE_URL)

# Establish a connection to the database
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

@items.route('/items', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # SQL query to select all items and order by 'adopted' status and 'created_at' timestamp
    cur.execute("""
SELECT items.*, COALESCE(json_agg(json_build_object('donor_name', donors.donor_name, 'donor_lastname', donors.donor_lastname)) FILTER (WHERE donors.donor_id IS NOT NULL), '[]') AS donors
FROM items
LEFT JOIN item_donors ON items.item_id = item_donors.item_id
LEFT JOIN donors ON item_donors.donor_id = donors.donor_id
GROUP BY items.item_id
ORDER BY items.adopted ASC, items.created_at DESC;
""")

    items_list = cur.fetchall()

    conn.close()
    
    return render_template('items/index.html', items=items_list)



@items.route('/item/<uuid:item_id>', methods=['GET'])
def view_item(item_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Convert UUID to string before executing the query
    cur.execute("SELECT * FROM items WHERE item_id = %s;", (str(item_id),))
    item = cur.fetchone()

    if not item:
        return render_template('error/404NotFound.html'), 404

    # Fetch donor details for the item
    cur.execute("""
    SELECT donors.donor_name, donors.donor_lastname
    FROM item_donors
    JOIN donors ON item_donors.donor_id = donors.donor_id
    WHERE item_donors.item_id = %s;
    """, (str(item_id),))  # Convert UUID to string
    donors = cur.fetchall()

    conn.close()

    # Render the template with the item and list of donors
    return render_template('items/view_item.html', item=item, donors=donors, PAYPAL_CLIENT_ID=PAYPAL_CLIENT_ID)



@items.route('/submit_donation', methods=['POST'])
def submit_donation():
    # Ensure the user is logged in and get the user_id from the session
    user_id = session.get('user_id')
    if not user_id:
        print("User not logged in")  # Server-side log for debugging
        return jsonify({'error': 'User must be logged in to make a donation'}), 401

    donation_data = request.get_json()
    print("Donation Data Received:", donation_data)  # Server-side log for debugging

    if not donation_data:
        print("No data provided")  # Server-side log for debugging
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['firstName', 'lastName', 'email', 'phone', 'zipCode', 'item_id']
    if not all(field in donation_data for field in required_fields):
        print("Missing required data fields")  # Server-side log for debugging
        return jsonify({'error': 'Missing required data fields'}), 400

    item_id = donation_data['item_id']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        conn.autocommit = False

        # Update the adopted status of the item to true
        cur.execute("""
            UPDATE items
            SET adopted = true
            WHERE item_id = %s;
        """, (item_id,))

        # Insert the donor into the donors table, if they don't already exist
        cur.execute("""
            INSERT INTO donors (donor_id, donor_name, donor_lastname, donor_email, donor_phone, created_at, donor_zip_code)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            ON CONFLICT (donor_id) DO NOTHING;
        """, (user_id, donation_data['firstName'], donation_data['lastName'], donation_data['email'], donation_data['phone'], donation_data['zipCode']))

        # Insert the donation record into the item_donors table
        cur.execute("""
            INSERT INTO item_donors (item_id, donor_id, donation_date)
            VALUES (%s, %s, CURRENT_TIMESTAMP);
        """, (item_id, user_id))

        conn.commit()
        return jsonify({"success": True}), 200
    except psycopg2.Error as e:
        conn.rollback()
        print("Database Error:", e.pgerror)  # Server-side log for debugging
        return jsonify({'error': 'Database error', 'details': str(e.pgerror)}), 500
    finally:
        cur.close()
        conn.close()
