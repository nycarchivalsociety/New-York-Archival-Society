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
            data = request.json
            item.name = data.get('name')
            item.fee = data.get('fee')
            item.photo = data.get('photo')
            item.description = data.get('description_text')
            item.adopted = data.get('adopted')
            item.imgurl = data.get('imgurl')
            db.session.commit()
            return jsonify({"message": "Item updated successfully"})
        else:
            return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        db.session.rollback()
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

@auth.route('/add-item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        fee = request.form.get('fee')
        description = request.form.get('description')
        adopted = request.form.get('adopted') == 'on'  # Verificar si el checkbox 'adopted' está marcado
        donor_name = request.form.get('donorName')  # Obtener el nombre del donador (si lo hay)
        img_file = request.files.get('fileElem')  # Obtener el archivo subido

        # Inicializar 'photo' en False
        photo_available = False

        # Verificar si se cargó un archivo de imagen
        if img_file and img_file.filename != '':
            # Crear nombre de imagen modificado
            modified_name = name.lower().replace(' ', '_') + '_item'

            # Subir la imagen a Cloudinary con las transformaciones necesarias
            upload_result = cloudinary.uploader.upload(
                img_file,
                folder="New York Archival Society/Items",
                public_id=modified_name,  # Nombre de la imagen en Cloudinary
                transformation=[
                    {'width': 900, 'quality': "auto:good", 'fetch_format': 'jpg'}
                ]
            )
            imgurl = upload_result.get('secure_url')  # URL segura de la imagen subida
            # Como se subió una imagen, establecer photo_available en True
            photo_available = True
        else:
            imgurl = None
            # No se subió imagen, photo_available permanece en False

        # Crear el nuevo ítem
        new_item = Items(
            name=name,
            fee=fee,
            description=description,
            adopted=adopted,
            imgurl=imgurl,
            photo=photo_available  # Establecer el campo 'photo' adecuadamente
        )

        try:
            # Agregar el ítem a la sesión de la base de datos
            db.session.add(new_item)
            # Hacer flush de la sesión para obtener new_item.id
            db.session.flush()  # Asigna un ID a new_item sin hacer commit

            # Si el ítem fue adoptado y se proporcionó el nombre del donador, crear un nuevo donador
            if adopted and donor_name:
                new_donor = Donors(
                    donor_id=uuid.uuid4(),
                    donor_name=donor_name,
                    item_id=new_item.id  # Ahora new_item.id está disponible
                )
                db.session.add(new_donor)  # Agregar el donador a la base de datos

            # Hacer commit de la sesión
            db.session.commit()
            flash('¡Ítem y donador agregados exitosamente!', 'success')
            return redirect(url_for('auth.add_item'))  # Redirigir después de insertar correctamente
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar ítem o donador: {str(e)}', 'danger')

    return render_template('auth/items/add_item.html')


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