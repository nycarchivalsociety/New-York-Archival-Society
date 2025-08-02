from app.db.db import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func, Index, text
from sqlalchemy.orm import validates
import uuid
from decimal import Decimal
import re

class HistoricalRecord(db.Model):
    __tablename__ = 'historical_records'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = db.Column(db.String(256), nullable=False, index=True)
    fee = db.Column(db.Numeric(10, 2), nullable=False)
    photo = db.Column(db.Boolean, default=False, nullable=False)
    description = db.Column(db.Text, nullable=False)
    adopted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    imgurl = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Add database constraints and indexes
    __table_args__ = (
        Index('idx_historical_records_adopted_name', 'adopted', 'name'),
        Index('idx_historical_records_fee', 'fee'),
        db.CheckConstraint('fee > 0', name='check_positive_fee'),
        db.CheckConstraint('char_length(name) > 0', name='check_name_not_empty'),
    )

    # Update relationship with explicit join condition
    donors = db.relationship(
        'DonorItem',
        back_populates='item',
        cascade="all, delete-orphan",
        primaryjoin="HistoricalRecord.id == DonorItem.item_id"
    )

    def __repr__(self):
        return f"<HistoricalRecord {self.name}>"

class Donor(db.Model):
    __tablename__ = 'donors'

    donor_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    donor_name = db.Column(db.String(256), nullable=False, index=True)
    donor_email = db.Column(db.String(256), nullable=True, unique=True, index=True)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Shipping address fields
    shipping_street = db.Column(db.String(255), nullable=True)
    shipping_apartment = db.Column(db.String(255), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=True)
    shipping_state = db.Column(db.String(100), nullable=True)
    shipping_zip_code = db.Column(db.String(20), nullable=True)
    
    items = db.relationship('DonorItem', back_populates='donor', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Donor {self.donor_name}>"

class DonorItem(db.Model):
    __tablename__ = 'donor_item'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    donor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('donors.donor_id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('historical_records.id', ondelete='CASCADE'), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=False)

    donor = db.relationship('Donor', back_populates='items')
    item = db.relationship('HistoricalRecord', back_populates='donors')

    def __repr__(self):
        return f"<DonorItem Donor: {self.donor_id}, Item: {self.item_id}>"

class Bond(db.Model):
    __tablename__ = 'bonds'

    bond_id = db.Column(db.String(255), primary_key=True, unique=True, nullable=False)
    retail_price = db.Column(db.Numeric(12, 2), nullable=True)
    par_value = db.Column(db.String(255), nullable=True)
    issue_date = db.Column(db.Date, nullable=True, index=True)
    due_date = db.Column(db.Date, nullable=True)
    mayor = db.Column(db.String(100), nullable=True)
    comptroller = db.Column(db.String(100), nullable=True)
    size = db.Column(db.String(50), nullable=True)
    front_image = db.Column(db.String(500), nullable=True)
    back_image = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default="available", nullable=False, index=True)
    type = db.Column(db.String(100), nullable=True, index=True)
    purpose_of_bond = db.Column(db.Text, nullable=True)
    vignette = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Add database constraints and indexes
    __table_args__ = (
        Index('idx_bonds_status_type', 'status', 'type'),
        Index('idx_bonds_issue_date', 'issue_date'),
        db.CheckConstraint("status IN ('available', 'purchased', 'reserved')", name='check_valid_status'),
        db.CheckConstraint('retail_price > 0', name='check_positive_retail_price'),
    )

    def __repr__(self):
        return f"<Bond {self.bond_id}>"

class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    paypal_transaction_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    item_id = db.Column(db.String(255), nullable=False, index=True) # Can be either bond_id or historical_record_id
    donor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('donors.donor_id', ondelete='SET NULL'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    fee = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default="COMPLETED", index=True)
    payment_method = db.Column(db.String(50), nullable=True, default="PayPal")
    donor_email = db.Column(db.String(256), nullable=True, index=True)
    pickup = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Add database constraints and indexes
    __table_args__ = (
        Index('idx_transactions_timestamp_status', 'timestamp', 'payment_status'),
        Index('idx_transactions_donor_timestamp', 'donor_id', 'timestamp'),
        db.CheckConstraint("payment_status IN ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED')", name='check_valid_payment_status'),
        db.CheckConstraint('fee > 0', name='check_positive_transaction_fee'),
    )

    def get_item(self):
        """Returns related item based on item_id format."""
        if self.is_uuid(self.item_id):
            return HistoricalRecord.query.get(self.item_id)
        return Bond.query.get(self.item_id)

    @validates('fee')
    def validate_fee(self, key, fee):
        """Validate transaction fee is positive."""
        if fee is not None and fee <= 0:
            raise ValueError("Transaction fee must be positive")
        return fee
    
    @validates('donor_email')
    def validate_email(self, key, email):
        """Validate email format."""
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError("Invalid email format")
        return email
    
    @staticmethod
    def is_uuid(value):
        """Check if value is valid UUID."""
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, AttributeError, TypeError):
            return False

    def __repr__(self):
        return f"<Transaction {self.transaction_id}>"
