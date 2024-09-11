from app.db.db import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Items(db.Model):
    __tablename__ = 'items'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    fee = db.Column(db.Integer, nullable=False)
    photo = db.Column(db.Boolean, default=False)
    desc = db.Column(db.Text, nullable=False)
    adopted = db.Column(db.Boolean, default=False)
    imgurl = db.Column("imgurl", db.String, nullable=True) 

    # Define the relationship to Donors
    donors = db.relationship('Donors', backref='item', lazy=True)

    def __repr__(self):
        return f"<Items {self.name}>"

class Donors(db.Model):
    __tablename__ = 'donors'

    donor_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    donor_name = db.Column(db.String(256), nullable=False)
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey('items.id'), nullable=False)

    def __repr__(self):
        return f"<Donors {self.donor_name}>"
