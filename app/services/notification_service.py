import logging
from typing import Any, Dict, Iterable

import requests
from flask import current_app

logger = logging.getLogger(__name__)


class NotificationService:
    ENDPOINT = "https://api.emailjs.com/api/v1.0/email/send"
    TIMEOUT_SECONDS = 10

    @staticmethod
    def _recipients(value: Any) -> Iterable[str]:
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            return [str(email).strip() for email in value if str(email).strip()]
        return [email.strip() for email in str(value).split(",") if email.strip()]

    @staticmethod
    def _payer_name(payer_data: Dict[str, Any]) -> str:
        name = payer_data.get("name") or {}
        full_name = f"{name.get('given_name', '')} {name.get('surname', '')}".strip()
        return full_name or "Unknown"

    def send_purchase_notification(
        self, transaction: Any, payer_data: Dict[str, Any]
    ) -> bool:
        service_id = current_app.config.get("EMAILJS_SERVICE_ID")
        template_id = current_app.config.get(
            "EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL"
        )
        public_key = current_app.config.get("EMAILJS_API_ID")
        private_key = current_app.config.get("EMAILJS_PRIVATE_KEY")
        recipients = list(
            self._recipients(current_app.config.get("RECIPIENT_EMAILS"))
        )
        if not all((service_id, template_id, public_key)) or not recipients:
            logger.warning("Purchase notification skipped: EmailJS is not configured")
            return False

        item = transaction.get_item()
        shipping = payer_data.get("shipping_address") or {}
        item_name = getattr(item, "type", None) or getattr(item, "name", "Item")
        subject = (
            "Bond Purchase!"
            if hasattr(item, "bond_id")
            else "Historical Record Purchase!"
        )

        for recipient in recipients:
            payload = {
                "service_id": service_id,
                "template_id": template_id,
                "user_id": public_key,
                "template_params": {
                    "to_name": recipient,
                    "from_name": "NYAS SITE",
                    "subject": subject,
                    "item_name": item_name,
                    "item_id": str(transaction.item_id),
                    "item_fee": f"{transaction.fee:.2f}",
                    "donor_name": self._payer_name(payer_data),
                    "donor_email": payer_data.get("email_address", ""),
                    "donor_phone": (
                        (payer_data.get("phone") or {})
                        .get("phone_number", {})
                        .get("national_number", "Not provided")
                    ),
                    "pickup_status": (
                        "IN-PERSON PICKUP"
                        if transaction.pickup
                        else "SHIPPING REQUIRED"
                    ),
                    "street": shipping.get("address_line_1", "N/A"),
                    "apartment": shipping.get("address_line_2", "N/A"),
                    "city": shipping.get("admin_area_2", "N/A"),
                    "state": shipping.get("admin_area_1", "N/A"),
                    "zip_code": shipping.get("postal_code", "N/A"),
                },
            }
            if private_key:
                payload["accessToken"] = private_key
            response = requests.post(
                self.ENDPOINT,
                json=payload,
                timeout=self.TIMEOUT_SECONDS,
            )
            response.raise_for_status()

        return True


notification_service = NotificationService()
