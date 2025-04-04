from app.db.db import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func
import uuid

class HistoricalRecord(db.Model):
    __tablename__ = 'historical_records'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=False)
    photo = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=False)
    adopted = db.Column(db.Boolean, default=False)
    imgurl = db.Column(db.String, nullable=True)

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
    donor_name = db.Column(db.String(256), nullable=False)
    donor_email = db.Column(db.String(256), nullable=True, unique=True)
    phone = db.Column(db.String(20), nullable=True)
    
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
    retail_price = db.Column(db.Numeric, nullable=True)
    par_value = db.Column(db.String(255), nullable=True)
    issue_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    mayor = db.Column(db.String(100), nullable=True)
    comptroller = db.Column(db.String(100), nullable=True)
    size = db.Column(db.String(50), nullable=True)
    front_image = db.Column(db.String(255), nullable=True)
    back_image = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Text, default="available", nullable=False)
    type = db.Column(db.String(100), nullable=True)
    purpose_of_bond = db.Column(db.Text, nullable=True)
    vignette = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Bond {self.bond_id}>"

class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    paypal_transaction_id = db.Column(db.String(255), nullable=False)
    item_id = db.Column(db.String(255), nullable=False) # Can be either bond_id or historical_record_id
    donor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('donors.donor_id', ondelete='SET NULL'), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    fee = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(50), nullable=False, default="Completed")
    payment_method = db.Column(db.String(50), nullable=True)
    donor_email = db.Column(db.String(256), nullable=True)
    pickup = db.Column(db.Boolean, nullable=False, default=False)  # New column for in-person pickup

    def get_item(self):
        """Returns related item based on item_id format."""
        if self.is_uuid(self.item_id):
            return HistoricalRecord.query.get(self.item_id)
        return Bond.query.get(self.item_id)

    @staticmethod
    def is_uuid(value):
        """Check if value is valid UUID."""
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, AttributeError):
            return False

    def __repr__(self):
        return f"<Transaction {self.transaction_id}>"
