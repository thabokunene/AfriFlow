import pytest
from afriflow.domains.cib.simulator.payment_generator import PaymentGenerator

@pytest.fixture
def generator():
    return PaymentGenerator(seed=42)

def test_payment_structure(generator):
    payment = generator.generate_single_payment()
    assert isinstance(payment, dict)
    required_keys = [
        "transaction_id", "timestamp", "amount", "currency",
        "sender_name", "sender_country", "beneficiary_name",
        "beneficiary_country", "status", "purpose_code", "corridor"
    ]
    for key in required_keys:
        assert key in payment

def test_currency_logic(generator):
    payment = generator.generate_single_payment()
    assert len(payment["currency"]) == 3
    # Currency should be sender's, beneficiary's, or a major one
    assert payment["currency"] in ["USD", "EUR", "ZAR", "NGN", "KES", "EGP", "GHS", "RWF", "MAD", "ETB", "XOF", "TZS", "UGX", "ZMW", "ZWL", "MZN", "AOA", "GBP", "CNY"]

def test_cross_border_logic(generator):
    for _ in range(10):
        payment = generator.generate_single_payment()
        assert payment["sender_country"] != payment["beneficiary_country"]
