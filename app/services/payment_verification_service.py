from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict

from app.db.models import Bond
from app.utils.validators import ValidationError


USD = "USD"
BOND_HANDLING_FEE = Decimal("5.00")
CENT = Decimal("0.01")


class PaymentVerificationService:
    @staticmethod
    def money(value: Any) -> Decimal:
        try:
            return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("Invalid payment amount") from None

    def get_total(self, item: Any) -> Decimal:
        if isinstance(item, Bond) or hasattr(item, "retail_price"):
            if item.retail_price is None:
                raise ValidationError("Bond price is not configured")
            return self.money(item.retail_price) + BOND_HANDLING_FEE
        return self.money(item.fee)

    def verify_order(
        self,
        order_details: Dict[str, Any],
        item_id: str,
        expected_total: Decimal,
    ) -> None:
        if order_details.get("status") != "COMPLETED":
            raise ValidationError("Order not completed")

        purchase_units = order_details.get("purchase_units")
        if not isinstance(purchase_units, list) or len(purchase_units) != 1:
            raise ValidationError("Order must contain exactly one purchase unit")

        purchase_unit = purchase_units[0]
        if str(purchase_unit.get("reference_id")) != str(item_id):
            raise ValidationError("PayPal order reference does not match item")

        amount = purchase_unit.get("amount")
        if not isinstance(amount, dict):
            raise ValidationError("PayPal order amount is missing")
        if amount.get("currency_code") != USD:
            raise ValidationError("PayPal order currency must be USD")
        if self.money(amount.get("value")) != self.money(expected_total):
            raise ValidationError("PayPal order amount does not match item price")


payment_verification_service = PaymentVerificationService()

