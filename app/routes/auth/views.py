from flask import render_template, Blueprint, redirect, url_for, request, flash, jsonify
from flask_login import login_user, login_required, logout_user
from werkzeug.security import check_password_hash
from app.db.models import User, Items, Donors
from app.db.db import db  # Correct import of the SQLAlchemy instance
import cloudinary
import cloudinary.uploader
import cloudinary.api
import uuid  # Import UUID generation
from . import auth

# Cloudinary Configuration
cloudinary.config(
  cloud_name='dakw2jqjp',  
  api_key='774531617983771',  
  api_secret='3semSLqOIyE-j8GK7Zpy7a7uRWc'  
)

@auth.route('/api/items/<item_id>', methods=['GET'])
@login_required
def get_item(item_id):
    item = Items.query.get(item_id)
    if item:
        item_data = {
            "id": str(item.id),
            "name": item.name,
            "fee": item.fee,
            "photo": item.photo,
            "description_text": item.description,
            "adopted": item.adopted,
            "imgurl": item.imgurl
        }
        return jsonify(item_data)
    else:
        return jsonify({"error": "Item not found"}), 404

@auth.route('/api/items/<item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    try:
        item = Items.query.get(item_id)
        if item:
            # Get data from the form
            name = request.form.get('name')
            fee = request.form.get('fee')
            description = request.form.get('description_text')
            adopted = request.form.get('adopted') == 'true'
            photo_available = request.form.get('photo') == 'true'
            donor_name = request.form.get('donor_name')  # Optional donor's name

            # Handle image if available
            imgurl = item.imgurl  # Keep existing image URL by default
            if photo_available:
                if 'image' in request.files:
                    img_file = request.files['image']
                    if img_file and img_file.filename != '':
                        modified_name = name.lower().replace(' ', '_') + '_item'

                        # Upload the image to Cloudinary
                        upload_result = cloudinary.uploader.upload(
                            img_file,
                            folder="New York Archival Society/Items",
                            public_id=modified_name,
                            transformation=[
                                {'width': 900, 'quality': "auto:good", 'fetch_format': 'jpg'}
                            ]
                        )
                        imgurl = upload_result.get('secure_url')
            else:
                imgurl = None  # No image available

            # Update item fields
            item.name = name
            item.fee = fee
            item.photo = photo_available
            item.description = description
            item.adopted = adopted
            item.imgurl = imgurl

            # Handle donor records based on adopted status
            if adopted:
                # If the item is adopted and donor's name is provided, create/update a donor record
                if donor_name:
                    # Delete existing donor records for the item to avoid duplicates
                    Donors.query.filter_by(item_id=item.id).delete()
                    db.session.commit()

                    new_donor = Donors(
                        donor_name=donor_name,
                        item_id=item.id  # Associate donor with the item
                    )
                    db.session.add(new_donor)
            else:
                # If adopted is False, delete donor records related to the item
                Donors.query.filter_by(item_id=item.id).delete()

            # Commit all changes to the database
            db.session.commit()
            return jsonify({"message": "Item updated successfully"})
        else:
            return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating item: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth.route('/api/items/<item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    try:
        item = Items.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"message": "Item deleted successfully"})
        else:
            return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting item: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth.route('/api/items', methods=['GET'])
@login_required
def get_items():
    items = Items.query.order_by(Items.name).all()  # Ensure consistent alphabetical ordering
    items_data = [
        {
            "id": str(item.id),
            "name": item.name,
            "fee": item.fee,
            "photo": item.photo,
            "description_text": item.description,
            "adopted": item.adopted,
            "imgurl": item.imgurl
        }
        for item in items
    ]
    return jsonify(items_data)

@auth.route('/api/items', methods=['POST'])
@login_required
def add_item_api():
    try:
        # Get form data
        name = request.form.get('name')
        fee = request.form.get('fee')
        description = request.form.get('description_text')
        adopted = request.form.get('adopted') == 'true'  # Convert to boolean
        photo_available = request.form.get('photo') == 'true'  # Convert to boolean
        donor_name = request.form.get('donor_name')  # New field for donor's name

        imgurl = None  # Initialize image URL

        # Handle image upload if photo is available
        if photo_available:
            img_file = request.files.get('image')
            if img_file and img_file.filename != '':
                modified_name = name.lower().replace(' ', '_') + '_item'

                # Upload image to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    img_file,
                    folder="New York Archival Society/Items",
                    public_id=modified_name,
                    transformation=[
                        {'width': 900, 'quality': "auto:good", 'fetch_format': 'jpg'}
                    ]
                )
                imgurl = upload_result.get('secure_url')
            else:
                imgurl = None
        else:
            imgurl = None

        # Create the new item
        new_item = Items(
            name=name,
            fee=fee,
            description=description,
            adopted=adopted,
            imgurl=imgurl,
            photo=photo_available
        )

        # Add the new item to the session and flush to get its ID
        db.session.add(new_item)
        db.session.flush()  # Flush to get new_item.id before commit

        # If the item is adopted and donor's name is provided, create a donor record
        if adopted and donor_name:
            new_donor = Donors(
                donor_name=donor_name,
                item_id=new_item.id  # Associate donor with the new item
            )
            db.session.add(new_donor)

        # Commit all changes to the database
        db.session.commit()

        return jsonify({"message": "Item added successfully"}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding item: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# Donor API Routes
# ----------------------------

@auth.route('/api/donors', methods=['GET'])
@login_required
def get_donors():
    donors = Donors.query.all()
    donors_data = [
        {
            "donor_id": str(donor.donor_id),
            "donor_name": donor.donor_name,
            "item_id": str(donor.item_id)
        }
        for donor in donors
    ]
    return jsonify(donors_data), 200

# ----------------------------
# Authentication Routes
# ----------------------------

@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/dashboard')
@login_required
def dashboard():
    return render_template('auth/dashboard/dashboard.html')

@auth.route('/view-donors')
@login_required
def view_donors():
    return render_template('auth/donors/view_donors.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('auth.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login/login.html')