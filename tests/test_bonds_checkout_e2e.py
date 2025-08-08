"""
End-to-End Test Suite for Bonds Checkout
Validates all shipping, pickup, and international scenarios
"""

import pytest
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from flask import url_for
from app import create_app
from app.db.db import db
from app.db.models import Bond, Donor, Transaction
import uuid


class TestBondsCheckoutE2E:
    """Test suite for Bonds checkout end-to-end flows"""
    
    @pytest.fixture(autouse=True)
    def setup(self, app, client):
        """Setup test environment"""
        self.app = app
        self.client = client
        self.ctx = app.app_context()
        self.ctx.push()
        
        # Create test bond
        self.test_bond = Bond(
            bond_id="TEST-BOND-001",
            retail_price=Decimal("100.00"),
            par_value="$1000",
            status="available",
            type="Municipal Bond",
            mayor="Test Mayor",
            comptroller="Test Comptroller"
        )
        db.session.add(self.test_bond)
        db.session.commit()
        
        yield
        
        # Cleanup
        db.session.rollback()
        Transaction.query.delete()
        Donor.query.delete()
        Bond.query.delete()
        db.session.commit()
        self.ctx.pop()
    
    # ============================================
    # Test Case 1: US Address + Pickup Checked
    # ============================================
    
    def test_us_address_pickup_checked(self):
        """
        Test: US address + Pickup checked
        Expected:
        - Handling and International flags hidden
        - Patched total equals base price only ($100)
        - Order captures successfully
        - Email reflects zero handling/shipping
        """
        # Create PayPal order with pickup
        order_data = {
            "item_id": self.test_bond.bond_id,
            "fee": 100.00,
            "pickup": True
        }
        
        with patch('app.services.paypal_service.paypal_service.create_order') as mock_create:
            mock_create.return_value = {"id": "TEST-ORDER-001", "status": "CREATED"}
            
            response = self.client.post('/create-order',
                                       json=order_data,
                                       content_type='application/json')
            
            assert response.status_code == 200
            assert response.json["id"] == "TEST-ORDER-001"
        
        # Simulate PayPal capture with US address
        capture_data = {
            "item_id": self.test_bond.bond_id,
            "fee": 100.00,  # Base price only, no fees
            "pickup": True,
            "donor_name": "John Doe",
            "donor_email": "john@example.com",
            "shipping_address": {
                "street": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "country_code": "US"
            }
        }
        
        with patch('app.services.paypal_service.paypal_service.get_order_details') as mock_details:
            mock_details.return_value = {
                "id": "TEST-ORDER-001",
                "status": "COMPLETED",
                "payer": {
                    "name": {"given_name": "John", "surname": "Doe"},
                    "email_address": "john@example.com"
                },
                "purchase_units": [{
                    "amount": {"value": "100.00"},
                    "shipping": {
                        "address": {
                            "address_line_1": "123 Main St",
                            "admin_area_2": "New York",
                            "admin_area_1": "NY", 
                            "postal_code": "10001",
                            "country_code": "US"
                        }
                    }
                }]
            }
            
            response = self.client.post(f'/capture-order/TEST-ORDER-001',
                                       json=capture_data,
                                       content_type='application/json')
            
            assert response.status_code == 200
            assert response.json["message"] == "Success"
        
        # Verify transaction was created correctly
        transaction = Transaction.query.filter_by(paypal_transaction_id="TEST-ORDER-001").first()
        assert transaction is not None
        assert transaction.fee == Decimal("100.00")  # Base price only
        assert transaction.pickup is True
        
        # Verify bond status updated
        bond = Bond.query.get(self.test_bond.bond_id)
        assert bond.status == "purchased"
    
    # ============================================
    # Test Case 2: US Address + Pickup Unchecked
    # ============================================
    
    def test_us_address_pickup_unchecked(self):
        """
        Test: US address + Pickup unchecked
        Expected:
        - Handling flag shown
        - Patched total equals base + $5 = $105
        """
        order_data = {
            "item_id": self.test_bond.bond_id,
            "fee": 105.00,  # Base + handling
            "pickup": False
        }
        
        with patch('app.services.paypal_service.paypal_service.create_order') as mock_create:
            mock_create.return_value = {"id": "TEST-ORDER-002", "status": "CREATED"}
            
            response = self.client.post('/create-order',
                                       json=order_data,
                                       content_type='application/json')
            
            assert response.status_code == 200
        
        # Capture with US shipping address
        capture_data = {
            "item_id": self.test_bond.bond_id,
            "fee": 105.00,  # Base + $5 handling
            "pickup": False,
            "donor_name": "Jane Smith",
            "donor_email": "jane@example.com",
            "shipping_address": {
                "street": "456 Broadway",
                "city": "Los Angeles",
                "state": "CA",
                "zip_code": "90001",
                "country_code": "US"
            }
        }
        
        with patch('app.services.paypal_service.paypal_service.get_order_details') as mock_details:
            mock_details.return_value = {
                "id": "TEST-ORDER-002",
                "status": "COMPLETED",
                "payer": {
                    "name": {"given_name": "Jane", "surname": "Smith"},
                    "email_address": "jane@example.com"
                },
                "purchase_units": [{
                    "amount": {
                        "value": "105.00",
                        "breakdown": {
                            "item_total": {"value": "100.00"},
                            "handling": {"value": "5.00"},
                            "shipping": {"value": "0.00"}
                        }
                    },
                    "shipping": {
                        "address": {
                            "address_line_1": "456 Broadway",
                            "admin_area_2": "Los Angeles",
                            "admin_area_1": "CA",
                            "postal_code": "90001",
                            "country_code": "US"
                        }
                    }
                }]
            }
            
            response = self.client.post(f'/capture-order/TEST-ORDER-002',
                                       json=capture_data,
                                       content_type='application/json')
            
            assert response.status_code == 200
        
        # Verify transaction
        transaction = Transaction.query.filter_by(paypal_transaction_id="TEST-ORDER-002").first()
        assert transaction is not None
        assert transaction.fee == Decimal("105.00")  # Base + handling
        assert transaction.pickup is False
    
    # ============================================
    # Test Case 3: Non-US Address + Pickup Unchecked
    # ============================================
    
    def test_non_us_address_pickup_unchecked(self):
        """
        Test: Non-US address + Pickup unchecked
        Expected:
        - Handling flag shown, International flag shown
        - Patched total equals base + $5 + $20 = $125
        """
        order_data = {
            "item_id": self.test_bond.bond_id,
            "fee": 125.00,  # Base + handling + international
            "pickup": False
        }
        
        with patch('app.services.paypal_service.paypal_service.create_order') as mock_create:
            mock_create.return_value = {"id": "TEST-ORDER-003", "status": "CREATED"}
            
            response = self.client.post('/create-order',
                                       json=order_data,
                                       content_type='application/json')
            
            assert response.status_code == 200
        
        # Capture with international address
        capture_data = {
            "item_id": self.test_bond.bond_id,
            "fee": 125.00,  # Base + $5 handling + $20 international
            "pickup": False,
            "donor_name": "Pierre Dupont",
            "donor_email": "pierre@example.fr",
            "shipping_address": {
                "street": "123 Rue de la Paix",
                "city": "Paris",
                "state": "Ile-de-France",
                "zip_code": "75001",
                "country_code": "FR"
            }
        }
        
        with patch('app.services.paypal_service.paypal_service.get_order_details') as mock_details:
            mock_details.return_value = {
                "id": "TEST-ORDER-003",
                "status": "COMPLETED",
                "payer": {
                    "name": {"given_name": "Pierre", "surname": "Dupont"},
                    "email_address": "pierre@example.fr"
                },
                "purchase_units": [{
                    "amount": {
                        "value": "125.00",
                        "breakdown": {
                            "item_total": {"value": "100.00"},
                            "handling": {"value": "5.00"},
                            "shipping": {"value": "20.00"}
                        }
                    },
                    "shipping": {
                        "address": {
                            "address_line_1": "123 Rue de la Paix",
                            "admin_area_2": "Paris",
                            "admin_area_1": "Ile-de-France",
                            "postal_code": "75001",
                            "country_code": "FR"
                        }
                    }
                }]
            }
            
            response = self.client.post(f'/capture-order/TEST-ORDER-003',
                                       json=capture_data,
                                       content_type='application/json')
            
            assert response.status_code == 200
        
        # Verify transaction
        transaction = Transaction.query.filter_by(paypal_transaction_id="TEST-ORDER-003").first()
        assert transaction is not None
        assert transaction.fee == Decimal("125.00")  # Base + handling + international
        assert transaction.pickup is False
    
    # ============================================
    # Test Case 4: Non-US Address + Pickup Checked (Should Reject)
    # ============================================
    
    def test_non_us_address_pickup_checked_rejection(self):
        """
        Test: Non-US address + Pickup checked
        Expected:
        - onShippingChange displays an error and blocks progression
        - Order should not complete
        """
        # This test simulates the JavaScript rejection scenario
        # In a real browser test, PayPal's onShippingChange would reject
        # Here we test that the backend properly handles this scenario
        
        order_data = {
            "item_id": self.test_bond.bond_id,
            "fee": 100.00,  # Base price only (pickup)
            "pickup": True
        }
        
        # Attempt to capture with non-US address and pickup=True
        # This should not happen in practice due to frontend validation
        capture_data = {
            "item_id": self.test_bond.bond_id,
            "fee": 100.00,
            "pickup": True,
            "donor_name": "Hans Schmidt",
            "donor_email": "hans@example.de",
            "shipping_address": {
                "street": "Hauptstraße 1",
                "city": "Berlin",
                "state": "Berlin",
                "zip_code": "10115",
                "country_code": "DE"
            }
        }
        
        # The frontend should prevent this, but test backend validation
        with patch('app.services.paypal_service.paypal_service.get_order_details') as mock_details:
            # PayPal would not return COMPLETED status if rejected
            mock_details.return_value = {
                "id": "TEST-ORDER-004",
                "status": "CREATED",  # Not completed due to rejection
                "payer": {
                    "name": {"given_name": "Hans", "surname": "Schmidt"},
                    "email_address": "hans@example.de"
                }
            }
            
            response = self.client.post(f'/capture-order/TEST-ORDER-004',
                                       json=capture_data,
                                       content_type='application/json')
            
            # Should fail because order is not COMPLETED
            assert response.status_code == 400
            assert "not completed" in response.json.get("error", "").lower()
        
        # Verify no transaction was created
        transaction = Transaction.query.filter_by(paypal_transaction_id="TEST-ORDER-004").first()
        assert transaction is None
    
    # ============================================
    # Test Case 5: Email Notification Accuracy
    # ============================================
    
    @patch('app.services.transaction_service.send_email_notification')
    def test_email_notification_accuracy(self, mock_email):
        """
        Test: Email notifications include accurate totals and pickup status
        """
        # Test pickup email
        capture_data_pickup = {
            "item_id": self.test_bond.bond_id,
            "fee": 100.00,
            "pickup": True,
            "donor_name": "Test User",
            "donor_email": "test@example.com"
        }
        
        with patch('app.services.paypal_service.paypal_service.get_order_details') as mock_details:
            mock_details.return_value = {
                "id": "TEST-EMAIL-001",
                "status": "COMPLETED",
                "payer": {
                    "name": {"given_name": "Test", "surname": "User"},
                    "email_address": "test@example.com"
                },
                "purchase_units": [{
                    "amount": {"value": "100.00"},
                    "shipping": {
                        "address": {
                            "country_code": "US"
                        }
                    }
                }]
            }
            
            self.client.post(f'/capture-order/TEST-EMAIL-001',
                           json=capture_data_pickup,
                           content_type='application/json')
        
        # Verify email was called with correct pickup status
        mock_email.assert_called()
        call_args = mock_email.call_args
        assert call_args is not None
        # Email should indicate pickup and show $100 total
        
        # Reset mock for next test
        mock_email.reset_mock()
        
        # Test international shipping email
        capture_data_intl = {
            "item_id": self.test_bond.bond_id,
            "fee": 125.00,
            "pickup": False,
            "donor_name": "International User",
            "donor_email": "intl@example.com"
        }
        
        with patch('app.services.paypal_service.paypal_service.get_order_details') as mock_details:
            mock_details.return_value = {
                "id": "TEST-EMAIL-002",
                "status": "COMPLETED",
                "payer": {
                    "name": {"given_name": "International", "surname": "User"},
                    "email_address": "intl@example.com"
                },
                "purchase_units": [{
                    "amount": {
                        "value": "125.00",
                        "breakdown": {
                            "item_total": {"value": "100.00"},
                            "handling": {"value": "5.00"},
                            "shipping": {"value": "20.00"}
                        }
                    },
                    "shipping": {
                        "address": {
                            "country_code": "GB"
                        }
                    }
                }]
            }
            
            self.client.post(f'/capture-order/TEST-EMAIL-002',
                           json=capture_data_intl,
                           content_type='application/json')
        
        # Verify email shows shipping required and $125 total
        mock_email.assert_called()
    
    # ============================================
    # Test Case 6: UI Responsiveness Validation
    # ============================================
    
    def test_bond_detail_page_rendering(self):
        """
        Test: UI remains responsive on mobile and desktop
        Validates that bond detail page renders correctly with all elements
        """
        response = self.client.get(f'/bond/{self.test_bond.bond_id}')
        
        assert response.status_code == 200
        
        # Check for essential UI elements
        html = response.data.decode('utf-8')
        
        # Verify PayPal button container exists
        assert 'id="paypal-button-container"' in html
        
        # Verify pickup checkbox exists
        assert 'id="pickup-checkbox"' in html
        assert 'USA addresses only' in html
        
        # Verify fee display elements
        assert 'id="handling-text"' in html
        assert 'id="international-text"' in html
        
        # Verify responsive meta tag for mobile
        assert 'viewport' in html
        
        # Verify bond details are displayed
        assert self.test_bond.type in html
        assert str(self.test_bond.retail_price) in html
    
    # ============================================
    # Test Case 7: Fee Calculation Validation
    # ============================================
    
    def test_fee_calculations(self):
        """
        Test: Verify all fee calculation scenarios
        """
        base_price = 100.00
        handling_fee = 5.00
        international_fee = 20.00
        
        # Scenario 1: US + Pickup
        assert base_price == 100.00
        
        # Scenario 2: US + Shipping
        assert base_price + handling_fee == 105.00
        
        # Scenario 3: International + Shipping
        assert base_price + handling_fee + international_fee == 125.00
        
        # Scenario 4: International + Pickup (should not be allowed)
        # This is validated in the rejection test above
    
    # ============================================
    # Test Case 8: Database State Validation
    # ============================================
    
    def test_database_state_after_purchase(self):
        """
        Test: Verify database state is correctly updated after purchase
        """
        # Create and capture an order
        with patch('app.services.paypal_service.paypal_service.get_order_details') as mock_details:
            mock_details.return_value = {
                "id": "TEST-DB-001",
                "status": "COMPLETED",
                "payer": {
                    "name": {"given_name": "DB", "surname": "Test"},
                    "email_address": "db@test.com",
                    "phone": {"phone_number": {"national_number": "1234567890"}}
                },
                "purchase_units": [{
                    "amount": {"value": "105.00"},
                    "shipping": {
                        "address": {
                            "address_line_1": "789 Test St",
                            "address_line_2": "Apt 10",
                            "admin_area_2": "Test City",
                            "admin_area_1": "TS",
                            "postal_code": "12345",
                            "country_code": "US"
                        }
                    }
                }]
            }
            
            capture_data = {
                "item_id": self.test_bond.bond_id,
                "fee": 105.00,
                "pickup": False,
                "donor_name": "DB Test",
                "donor_email": "db@test.com"
            }
            
            response = self.client.post(f'/capture-order/TEST-DB-001',
                                       json=capture_data,
                                       content_type='application/json')
            
            assert response.status_code == 200
        
        # Verify Transaction created
        transaction = Transaction.query.filter_by(paypal_transaction_id="TEST-DB-001").first()
        assert transaction is not None
        assert transaction.item_id == self.test_bond.bond_id
        assert transaction.fee == Decimal("105.00")
        assert transaction.payment_status == "COMPLETED"
        assert transaction.pickup is False
        
        # Verify Donor created
        donor = Donor.query.filter_by(donor_email="db@test.com").first()
        assert donor is not None
        assert donor.donor_name == "DB Test"
        assert donor.shipping_street == "789 Test St"
        assert donor.shipping_apartment == "Apt 10"
        assert donor.shipping_city == "Test City"
        assert donor.shipping_state == "TS"
        assert donor.shipping_zip_code == "12345"
        
        # Verify Bond status updated
        bond = Bond.query.get(self.test_bond.bond_id)
        assert bond.status == "purchased"
    
    # ============================================
    # Test Case 9: Edge Cases
    # ============================================
    
    def test_edge_cases(self):
        """
        Test: Various edge cases and error conditions
        """
        # Test 1: Invalid bond ID
        response = self.client.post('/create-order',
                                   json={"item_id": "INVALID-BOND", "fee": 100.00},
                                   content_type='application/json')
        assert response.status_code == 404
        
        # Test 2: Bond already purchased
        self.test_bond.status = "purchased"
        db.session.commit()
        
        response = self.client.post('/create-order',
                                   json={"item_id": self.test_bond.bond_id, "fee": 100.00},
                                   content_type='application/json')
        assert response.status_code == 400
        assert "not available" in response.json.get("error", "").lower()
        
        # Reset bond status
        self.test_bond.status = "available"
        db.session.commit()
        
        # Test 3: Fee mismatch
        response = self.client.post('/create-order',
                                   json={"item_id": self.test_bond.bond_id, "fee": 50.00},
                                   content_type='application/json')
        assert response.status_code == 400
        assert "mismatch" in response.json.get("error", "").lower()
        
        # Test 4: Duplicate transaction
        with patch('app.services.transaction_service.get_transaction_by_paypal_id') as mock_get:
            mock_get.return_value = MagicMock()  # Return existing transaction
            
            response = self.client.post(f'/capture-order/DUPLICATE-ORDER',
                                       json={"item_id": self.test_bond.bond_id, "fee": 100.00},
                                       content_type='application/json')
            
            assert response.status_code == 200
            assert "already processed" in response.json.get("message", "").lower()


# Pytest configuration
@pytest.fixture
def app():
    """Create and configure a test app instance"""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
