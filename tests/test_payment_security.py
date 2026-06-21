from decimal import Decimal
import importlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

from app.routes.main import main
from app.routes.main import views
from app.services.transaction_service import TransactionError, TransactionService
from app.services.paypal_service import PayPalService


class DummyQuery:
    def __init__(self, item):
        self.item = item
        self.locked = False

    def get(self, item_id):
        return self.item

    def with_for_update(self):
        self.locked = True
        return self


@pytest.fixture
def app():
    application = Flask(__name__)
    application.config.update(TESTING=True)
    application.register_blueprint(main)
    return application


def bond(price="100.00", status="available"):
    return SimpleNamespace(
        bond_id="BOND-1",
        retail_price=Decimal(price),
        status=status,
        type="Test Bond",
    )


def completed_order(reference="BOND-1", value="105.00", currency="USD"):
    return {
        "id": "ORDER-1",
        "status": "COMPLETED",
        "payer": {
            "email_address": "buyer@example.test",
            "name": {"given_name": "Test", "surname": "Buyer"},
        },
        "purchase_units": [
            {
                "reference_id": reference,
                "amount": {"currency_code": currency, "value": value},
                "shipping": {"address": {}},
            }
        ],
    }


def patch_bond_query(monkeypatch, item):
    query = DummyQuery(item)
    monkeypatch.setattr(views, "Bond", SimpleNamespace(query=query))
    return query


def patch_historical_query(monkeypatch, item):
    query = DummyQuery(item)
    monkeypatch.setattr(views, "HistoricalRecord", SimpleNamespace(query=query))
    return query


def patch_capture_boundaries(monkeypatch, order_details, observed):
    monkeypatch.setattr(
        views.transaction_service,
        "get_transaction_by_paypal_id",
        lambda order_id: None,
    )
    monkeypatch.setattr(
        views.paypal_service,
        "get_order_details",
        lambda order_id: order_details,
    )

    transaction = SimpleNamespace(
        transaction_id="transaction-1",
        item_id="BOND-1",
        fee=Decimal("105.00"),
        pickup=False,
    )

    def create_transaction(**kwargs):
        observed["transaction"] = kwargs
        return transaction, True

    monkeypatch.setattr(
        views.transaction_service,
        "create_transaction_with_rollback",
        create_transaction,
    )

    class NotificationRecorder:
        def send_purchase_notification(self, created_transaction, payer_data):
            observed["notification"] = (created_transaction, payer_data)

    monkeypatch.setattr(
        views,
        "notification_service",
        NotificationRecorder(),
        raising=False,
    )


def test_create_order_uses_authoritative_bond_total(app, monkeypatch):
    patch_bond_query(monkeypatch, bond())
    observed = {}
    monkeypatch.setattr(
        views.paypal_service,
        "create_order",
        lambda item_id, fee, shipping_preference: observed.update(
            item_id=item_id,
            fee=fee,
            shipping_preference=shipping_preference,
        )
        or {"id": "ORDER-1"},
    )

    with app.test_client() as client:
        response = client.post(
            "/create-order",
            json={"item_id": "BOND-1"},
        )

    assert response.status_code == 200
    assert observed == {
        "item_id": "BOND-1",
        "fee": Decimal("105.00"),
        "shipping_preference": "GET_FROM_FILE",
    }


def test_create_order_disables_shipping_for_historical_record(app, monkeypatch):
    item_id = "11111111-1111-4111-8111-111111111111"
    patch_historical_query(
        monkeypatch,
        SimpleNamespace(fee=Decimal("50.00"), adopted=False),
    )
    observed = {}
    monkeypatch.setattr(
        views.paypal_service,
        "create_order",
        lambda item_id, fee, shipping_preference: observed.update(
            item_id=item_id,
            fee=fee,
            shipping_preference=shipping_preference,
        )
        or {"id": "ORDER-1"},
    )

    with app.test_client() as client:
        response = client.post("/create-order", json={"item_id": item_id})

    assert response.status_code == 200
    assert observed["shipping_preference"] == "NO_SHIPPING"


def test_paypal_order_applies_server_selected_shipping_preference(monkeypatch):
    service = PayPalService()
    observed = {}

    class Response:
        status_code = 201
        text = "created"

        @staticmethod
        def json():
            return {"id": "ORDER-1"}

    monkeypatch.setattr(service, "get_access_token", lambda: "token")
    monkeypatch.setattr(
        service,
        "_validate_config",
        lambda: {"PAYPAL_API_BASE_URL": "https://paypal.example.test"},
    )
    monkeypatch.setattr(
        service,
        "_make_request",
        lambda method, url, **kwargs: observed.update(kwargs) or Response(),
    )

    service.create_order("BOND-1", Decimal("105.00"), "GET_FROM_FILE")

    assert observed["json"]["application_context"] == {
        "shipping_preference": "GET_FROM_FILE"
    }


@pytest.mark.parametrize(
    ("order", "expected_error"),
    [
        (completed_order(reference="OTHER"), "reference"),
        (completed_order(value="0.01"), "amount"),
        (completed_order(currency="EUR"), "currency"),
        (
            {
                **completed_order(),
                "purchase_units": completed_order()["purchase_units"] * 2,
            },
            "purchase unit",
        ),
    ],
)
def test_capture_rejects_unbound_paypal_order(
    app, monkeypatch, order, expected_error
):
    patch_bond_query(monkeypatch, bond())
    observed = {}
    patch_capture_boundaries(monkeypatch, order, observed)

    with app.test_client() as client:
        response = client.post(
            "/capture-order/ORDER-1",
            json={"item_id": "BOND-1", "pickup": False},
        )

    assert response.status_code == 400
    assert expected_error in response.get_json()["error"].lower()
    assert "transaction" not in observed
    assert "notification" not in observed


def test_capture_uses_authoritative_fee_and_notifies_after_commit(
    app, monkeypatch
):
    patch_bond_query(monkeypatch, bond())
    observed = {}
    patch_capture_boundaries(monkeypatch, completed_order(), observed)

    with app.test_client() as client:
        response = client.post(
            "/capture-order/ORDER-1",
            json={"item_id": "BOND-1", "fee": 0.01, "pickup": False},
        )

    assert response.status_code == 200
    assert observed["transaction"]["fee"] == Decimal("105.00")
    assert observed["notification"][0].transaction_id == "transaction-1"


@pytest.mark.parametrize(
    ("model_name", "item"),
    [
        ("historical", SimpleNamespace(adopted=True)),
        ("bond", bond(status="purchased")),
    ],
)
def test_item_claim_rejects_already_sold_inventory(
    monkeypatch, model_name, item
):
    if model_name == "historical":
        query = DummyQuery(item)
        module = importlib.import_module("app.services.transaction_service")
        monkeypatch.setattr(
            module, "HistoricalRecord", SimpleNamespace(query=query)
        )
        item_id = "11111111-1111-4111-8111-111111111111"
    else:
        query = DummyQuery(item)
        module = importlib.import_module("app.services.transaction_service")
        monkeypatch.setattr(module, "Bond", SimpleNamespace(query=query))
        item_id = "BOND-1"

    with pytest.raises(TransactionError, match="not available"):
        TransactionService._update_item_status(item_id)

    assert query.locked is True


def test_payment_templates_do_not_expose_emailjs_purchase_credentials():
    root = Path(__file__).resolve().parents[1]
    templates = [
        root
        / "app/templates/Adopt_New_Yorks_Past/components/items/view_item.html",
        root / "app/templates/Bonds/bond_details.html",
    ]

    for template in templates:
        contents = template.read_text(encoding="utf-8")
        assert "EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL" not in contents
        assert "sendPurchaseNotification" not in contents
        assert "emailjs.send" not in contents
        assert 'url: "/create-order"' in contents
        assert "actions.order.create" not in contents

    bond_template = templates[1].read_text(encoding="utf-8")
    assert "pickup: isPickup" in bond_template


def test_notification_service_sends_purchase_data_from_server(app, monkeypatch):
    module_name = "app.services.notification_service"
    assert importlib.util.find_spec(module_name) is not None
    module = importlib.import_module(module_name)
    sent = []

    class Response:
        status_code = 200
        text = "OK"

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(
        module.requests,
        "post",
        lambda url, **kwargs: sent.append((url, kwargs)) or Response(),
    )
    item = bond()
    transaction = SimpleNamespace(
        get_item=lambda: item,
        item_id="BOND-1",
        fee=Decimal("105.00"),
        pickup=False,
    )
    payer = {
        "email_address": "buyer@example.test",
        "name": {"given_name": "Test", "surname": "Buyer"},
        "shipping_address": {"address_line_1": "1 Main St"},
    }

    app.config.update(
        EMAILJS_SERVICE_ID="service",
        EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL="payment-template",
        EMAILJS_API_ID="public-key",
        EMAILJS_PRIVATE_KEY="private-key",
        RECIPIENT_EMAILS="ops@example.test",
    )
    with app.app_context():
        assert module.notification_service.send_purchase_notification(
            transaction, payer
        ) is True

    assert sent[0][0] == "https://api.emailjs.com/api/v1.0/email/send"
    payload = sent[0][1]["json"]
    assert payload["template_id"] == "payment-template"
    assert payload["accessToken"] == "private-key"
    assert payload["template_params"]["item_id"] == "BOND-1"
    assert payload["template_params"]["donor_email"] == "buyer@example.test"
