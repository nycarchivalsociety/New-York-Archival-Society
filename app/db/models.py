from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.db import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Items(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    fee = db.Column(db.Integer, nullable=False)
    photo = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=False)
    adopted = db.Column(db.Boolean, default=False)
    imgurl = db.Column(db.String, nullable=True) 

    # Define the relationship to Donors
    donors = db.relationship('Donors', backref='item', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Items {self.name}>"


class Donors(db.Model):
    __tablename__ = 'donors'

    donor_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    donor_name = db.Column(db.String(256), nullable=False)
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self):
        return f"<Donors {self.donor_name}>"


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='standard')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check the hashed password."""
        return check_password_hash(self.password_hash, password)

    # Override Flask-Login required methods
    @property
    def is_active(self):
        """Return True if the user is active."""
        return True

    @property
    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return True

    @property
    def is_anonymous(self):
        """Return False, as anonymous users are not allowed."""
        return False

    def get_id(self):
        """Override to return the UUID as a string."""
        return str(self.id)

    def __repr__(self):
        return f'<User {self.username}>'

# SQL statements to create tables
create_tables_sql = """
BEGIN;

CREATE TABLE IF NOT EXISTS donors (
    donor_id UUID PRIMARY KEY,
    donor_name VARCHAR(255),
    donor_lastname VARCHAR(255),
    donor_email VARCHAR(255),
    donor_phone VARCHAR(255),
    created_at TIMESTAMPTZ,
    donated_amount FLOAT4,
    donor_zip_code INT
);

CREATE TABLE IF NOT EXISTS items (
    item_id UUID PRIMARY KEY,
    item_name VARCHAR(255),
    item_description VARCHAR(255),
    created_at TIMESTAMPTZ,
    photo BOOLEAN,
    item_img_url VARCHAR(255),
    fee FLOAT4,
    adopted BOOLEAN,
    adoption_date TIMESTAMPTZ,
    total_donated_minus_remaining FLOAT4,
    remaining_balance FLOAT4,
    item_img_alt VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS item_donors (
    item_id UUID REFERENCES items(item_id),
    donor_id UUID REFERENCES donors(donor_id),
    adoption_date TIMESTAMPTZ,
    PRIMARY KEY (item_id, donor_id)
);

COMMIT;
"""
