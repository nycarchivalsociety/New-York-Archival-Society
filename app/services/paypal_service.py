# app/services/paypal_service.py

import requests
import logging
from typing import Optional, Dict, Any
from flask import current_app
from datetime import datetime, timedelta
from functools import wraps
import time

logger = logging.getLogger(__name__)

class PayPalAPIError(Exception):
    """Custom exception for PayPal API errors"""
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class PayPalService:
    """Service class for handling PayPal API operations with security and caching"""
    
    def __init__(self):
        self._token_cache = None
        self._token_expires_at = None
        self._max_retries = 3
        self._timeout = 30  # seconds
    
    def _validate_config(self) -> Dict[str, str]:
        """Validate and retrieve PayPal configuration"""
        required_configs = [
            'PAYPAL_CLIENT_ID',
            'PAYPAL_CLIENT_SECRET_KEY', 
            'PAYPAL_API_BASE_URL'
        ]
        
        config = {}
        missing_configs = []
        
        for key in required_configs:
            value = current_app.config.get(key)
            if not value:
                missing_configs.append(key)
            else:
                config[key] = value
        
        if missing_configs:
            raise PayPalAPIError(
                f"Missing PayPal configuration: {', '.join(missing_configs)}"
            )
        
        return config
    
    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid"""
        if not self._token_cache or not self._token_expires_at:
            return False
        
        # Add 5 minute buffer before expiration
        buffer_time = datetime.now() + timedelta(minutes=5)
        return buffer_time < self._token_expires_at
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic and proper error handling"""
        kwargs.setdefault('timeout', self._timeout)
        
        for attempt in range(self._max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                
                # Don't retry on client errors (4xx)
                if 400 <= response.status_code < 500:
                    break
                    
                # Retry on server errors (5xx) or connection issues
                if response.status_code >= 500 and attempt < self._max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"PayPal API request failed (attempt {attempt + 1}), "
                        f"retrying in {wait_time}s. Status: {response.status_code}"
                    )
                    time.sleep(wait_time)
                    continue
                    
                break
                
            except requests.exceptions.RequestException as e:
                if attempt < self._max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"PayPal API request exception (attempt {attempt + 1}), "
                        f"retrying in {wait_time}s. Error: {str(e)}"
                    )
                    time.sleep(wait_time)
                    continue
                raise PayPalAPIError(f"PayPal API request failed: {str(e)}")
        
        return response
    
    def get_access_token(self) -> str:
        """
        Get PayPal access token with caching and proper error handling
        
        Returns:
            str: Valid PayPal access token
            
        Raises:
            PayPalAPIError: If unable to retrieve access token
        """
        # Return cached token if still valid
        if self._is_token_valid():
            return self._token_cache
        
        try:
            config = self._validate_config()
            
            logger.info("Requesting new PayPal access token")
            
            response = self._make_request(
                'POST',
                f"{config['PAYPAL_API_BASE_URL']}/v1/oauth2/token",
                headers={
                    'Accept': 'application/json',
                    'Accept-Language': 'en_US'
                },
                data={'grant_type': 'client_credentials'},
                auth=(config['PAYPAL_CLIENT_ID'], config['PAYPAL_CLIENT_SECRET_KEY'])
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Failed to retrieve PayPal access token. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                raise PayPalAPIError(
                    "Failed to retrieve PayPal access token",
                    status_code=response.status_code,
                    response_data=response.json() if response.text else None
                )
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
            
            if not access_token:
                raise PayPalAPIError("No access token in PayPal response")
            
            # Cache token with expiration
            self._token_cache = access_token
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("PayPal access token retrieved successfully")
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error retrieving PayPal token: {str(e)}")
            raise PayPalAPIError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving PayPal token: {str(e)}")
            raise PayPalAPIError(f"Unexpected error: {str(e)}")
    
    def create_order(self, item_id: str, fee: float) -> Dict[str, Any]:
        """
        Create PayPal order with proper validation
        
        Args:
            item_id: Unique identifier for the item
            fee: Purchase amount
            
        Returns:
            Dict containing PayPal order response
            
        Raises:
            PayPalAPIError: If order creation fails
        """
        if not item_id or not fee:
            raise PayPalAPIError("Missing required parameters: item_id or fee")
        
        if fee <= 0:
            raise PayPalAPIError("Fee must be positive")
        
        try:
            access_token = self.get_access_token()
            config = self._validate_config()
            
            order_payload = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'reference_id': str(item_id),
                    'amount': {
                        'currency_code': 'USD',
                        'value': f"{fee:.2f}"
                    }
                }]
            }
            
            logger.info(f"Creating PayPal order for item {item_id}, amount ${fee:.2f}")
            
            response = self._make_request(
                'POST',
                f"{config['PAYPAL_API_BASE_URL']}/v2/checkout/orders",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                },
                json=order_payload
            )
            
            if response.status_code not in [200, 201]:
                logger.error(
                    f"Failed to create PayPal order. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                raise PayPalAPIError(
                    "Failed to create PayPal order",
                    status_code=response.status_code,
                    response_data=response.json() if response.text else None
                )
            
            order_data = response.json()
            logger.info(f"PayPal order created successfully: {order_data.get('id')}")
            return order_data
            
        except PayPalAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating PayPal order: {str(e)}")
            raise PayPalAPIError(f"Unexpected error: {str(e)}")
    
    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Get PayPal order details
        
        Args:
            order_id: PayPal order ID
            
        Returns:
            Dict containing order details
            
        Raises:
            PayPalAPIError: If unable to retrieve order details
        """
        if not order_id:
            raise PayPalAPIError("Order ID is required")
        
        try:
            access_token = self.get_access_token()
            config = self._validate_config()
            
            logger.info(f"Retrieving PayPal order details for {order_id}")
            
            response = self._make_request(
                'GET',
                f"{config['PAYPAL_API_BASE_URL']}/v2/checkout/orders/{order_id}",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                }
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Failed to get PayPal order details. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                raise PayPalAPIError(
                    "Failed to get order details",
                    status_code=response.status_code,
                    response_data=response.json() if response.text else None
                )
            
            order_data = response.json()
            logger.info(f"PayPal order details retrieved for {order_id}")
            return order_data
            
        except PayPalAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting order details: {str(e)}")
            raise PayPalAPIError(f"Unexpected error: {str(e)}")

# Global service instance
paypal_service = PayPalService()