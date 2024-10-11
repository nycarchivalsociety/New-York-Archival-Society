# app/db/models.py

from app.db.db import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func
import uuid

class Items(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=False)  # Define fee here
    photo = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=False)
    adopted = db.Column(db.Boolean, default=False)
    imgurl = db.Column(db.String, nullable=True)

    donors = db.relationship('Donors', backref='item', lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship('Transactions', backref='item', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Items {self.name}>"

class Donors(db.Model):
    __tablename__ = 'donors'

    donor_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    donor_name = db.Column(db.String(256), nullable=False)
    donor_email = db.Column(db.String(256), nullable=True)  # Set nullable=True
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=True)
    
    transactions = db.relationship('Transactions', backref='donor', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Donors {self.donor_name}>"

class Transactions(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    paypal_transaction_id = db.Column(db.String(255), nullable=False)  # New field to store PayPal transaction ID
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('items.id', ondelete='SET NULL'), nullable=False)
    donor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('donors.donor_id', ondelete='SET NULL'), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(50), nullable=False, default="Completed")
    payment_method = db.Column(db.String(50), nullable=True)  # Ensure sufficient length
    donor_email = db.Column(db.String(256), nullable=True)

    def __init__(self, paypal_transaction_id, item_id, donor_id, fee=None, **kwargs):
        super().__init__(**kwargs)
        self.paypal_transaction_id = paypal_transaction_id
        self.item_id = item_id
        self.donor_id = donor_id
        
        item = Items.query.get(item_id)
        donor = Donors.query.get(donor_id)
        self.fee = fee or donor.fee or item.fee

    def __repr__(self):
        return f"<Transactions {self.transaction_id}>"