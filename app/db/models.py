from app.db.db import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func
import uuid

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=False)  # Fee is required for each item
    photo = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=False)
    adopted = db.Column(db.Boolean, default=False)
    imgurl = db.Column(db.String, nullable=True)

    # Establish many-to-many relationship with Donor through DonorItem
    donors = db.relationship('DonorItem', back_populates='item', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item {self.name}>"

class Donor(db.Model):
    __tablename__ = 'donors'

    donor_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    donor_name = db.Column(db.String(256), nullable=False)
    donor_email = db.Column(db.String(256), nullable=True, unique=True)  # Now nullable

    # Establish many-to-many relationship with Item through DonorItem
    items = db.relationship('DonorItem', back_populates='donor', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Donor {self.donor_name}>"

class DonorItem(db.Model):
    __tablename__ = 'donor_item'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    donor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('donors.donor_id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=False)  # Fee is now required

    # Relationships to Donor and Item
    donor = db.relationship('Donor', back_populates='items')
    item = db.relationship('Item', back_populates='donors')

    def __repr__(self):
        return f"<DonorItem Donor: {self.donor_id}, Item: {self.item_id}>"

class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    paypal_transaction_id = db.Column(db.String(255), nullable=False)  # To store PayPal transaction ID
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('items.id', ondelete='SET NULL'), nullable=False)
    donor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('donors.donor_id', ondelete='SET NULL'), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(50), nullable=False, default="Completed")
    payment_method = db.Column(db.String(50), nullable=True)  # Ensure sufficient length
    donor_email = db.Column(db.String(256), nullable=True)  # Optional: Remove if redundant

    def __repr__(self):
        return f"<Transaction {self.transaction_id}>"
