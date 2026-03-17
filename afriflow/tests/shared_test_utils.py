"""
Shared testing utilities and mock data generators for AfriFlow.

This module provides consistent test fixtures, mock data generators,
and assertion helpers that can be reused across all domains.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Iterator
from dataclasses import dataclass, field


@dataclass
class MockClient:
    """Mock client data structure for testing."""
    client_id: str
    golden_id: str
    name: str
    tier: str
    home_country: str
    relationship_manager: str
    domains_active: List[str]
    total_relationship_value_zar: float
    risk_category: str
    incorporation_date: str
    industry: str


@dataclass
class MockPayment:
    """Mock payment data structure for testing."""
    payment_id: str
    debtor_client_id: str
    creditor_client_id: str
    amount: float
    currency: str
    corridor: str
    payment_type: str
    business_date: str
    purpose: str
    urgency: str


@dataclass
class MockCurrencyEvent:
    """Mock currency event data structure for testing."""
    event_id: str
    currency: str
    event_type: str
    severity: str
    rate_change_pct: float
    detected_at: datetime
    is_official_announcement: bool
    source: str


@dataclass
class MockSIM:
    """Mock SIM activation data structure for testing."""
    sim_id: str
    client_id: str
    activation_date: str
    country: str
    city: str
    data_usage_mb: int
    voice_minutes: int
    sms_count: int
    tariff_plan: str


@dataclass
class MockInsurancePolicy:
    """Mock insurance policy data structure for testing."""
    policy_id: str
    client_id: str
    policy_type: str
    coverage_amount: float
    premium_amount: float
    currency: str
    start_date: str
    end_date: str
    country: str
    risk_level: str


@dataclass
class MockFXTrade:
    """Mock FX trade data structure for testing."""
    trade_id: str
    client_id: str
    currency_pair: str
    trade_type: str
    direction: str
    notional_usd: float
    rate: float
    value_date: str
    country: str
    traded_at: datetime


class MockDataGenerator:
    """Centralized mock data generator for all domains."""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
    
    def generate_client(self, **kwargs) -> MockClient:
        """Generate a mock client."""
        client_id = kwargs.get("client_id", f"CLIENT-{random.randint(1000, 9999)}")
        
        return MockClient(
            client_id=client_id,
            golden_id=kwargs.get("golden_id", f"GOLDEN-{client_id}"),
            name=kwargs.get("name", f"Test Corporation {random.randint(1, 100)}"),
            tier=kwargs.get("tier", random.choice(["Platinum", "Gold", "Silver", "Bronze"])),
            home_country=kwargs.get("home_country", random.choice(["ZA", "NG", "KE", "GH", "TZ"])),
            relationship_manager=kwargs.get("rm", f"RM-{random.randint(1, 50)}"),
            domains_active=kwargs.get("domains", random.sample(["cib", "forex", "cell", "insurance", "pbb"], k=random.randint(1, 3))),
            total_relationship_value_zar=kwargs.get("relationship_value", random.uniform(1_000_000, 1_000_000_000)),
            risk_category=kwargs.get("risk", random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])),
            incorporation_date=kwargs.get("incorporation_date", (datetime.now(timezone.utc) - timedelta(days=random.randint(365, 3650))).strftime("%Y-%m-%d")),
            industry=kwargs.get("industry", random.choice(["Mining", "Agriculture", "Manufacturing", "Services", "Technology", "Financial"]))
        )
    
    def generate_payment(self, **kwargs) -> MockPayment:
        """Generate a mock payment."""
        debtor_id = kwargs.get("debtor_client_id", f"CLIENT-{random.randint(1000, 9999)}")
        creditor_id = kwargs.get("creditor_client_id", f"CLIENT-{random.randint(1000, 9999)}")
        
        # Generate corridor
        countries = ["ZA", "NG", "KE", "GH", "TZ", "UG", "ZM", "MZ", "AO", "RW"]
        debtor_country = kwargs.get("debtor_country", random.choice(countries))
        creditor_country = kwargs.get("creditor_country", random.choice([c for c in countries if c != debtor_country]))
        corridor = f"{debtor_country}-{creditor_country}"
        
        # Generate currency based on corridor
        corridor_currencies = {
            "ZA": "ZAR", "NG": "NGN", "KE": "KES", "GH": "GHS", "TZ": "TZS",
            "UG": "UGX", "ZM": "ZMW", "MZ": "MZN", "AO": "AOA", "RW": "RWF"
        }
        currency = kwargs.get("currency", corridor_currencies.get(debtor_country, "USD"))
        
        return MockPayment(
            payment_id=kwargs.get("payment_id", f"PAY-{uuid.uuid4().hex[:8].upper()}"),
            debtor_client_id=debtor_id,
            creditor_client_id=creditor_id,
            amount=kwargs.get("amount", random.uniform(10_000, 10_000_000)),
            currency=currency,
            corridor=corridor,
            payment_type=kwargs.get("payment_type", random.choice(["SUPPLIER", "TRADE", "PAYROLL", "DIVIDEND", "TAX"])),
            business_date=kwargs.get("business_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            purpose=kwargs.get("purpose", f"Payment for {random.choice(['goods', 'services', 'supplies', 'equipment'])}"),
            urgency=kwargs.get("urgency", random.choice(["NORMAL", "URGENT", "CRITICAL"]))
        )
    
    def generate_currency_event(self, **kwargs) -> MockCurrencyEvent:
        """Generate a mock currency event."""
        currency = kwargs.get("currency", random.choice(["NGN", "ZAR", "KES", "GHS", "ZMW"]))
        
        return MockCurrencyEvent(
            event_id=kwargs.get("event_id", f"FXE-{currency}-{uuid.uuid4().hex[:6].upper()}"),
            currency=currency,
            event_type=kwargs.get("event_type", random.choice(["DEVALUATION", "INTERVENTION", "VOLATILITY_SPIKE", "REGIME_CHANGE"])),
            severity=kwargs.get("severity", random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])),
            rate_change_pct=kwargs.get("rate_change_pct", random.uniform(-20, 30)),
            detected_at=kwargs.get("detected_at", datetime.now(timezone.utc)),
            is_official_announcement=kwargs.get("is_official_announcement", random.choice([True, False])),
            source=kwargs.get("source", random.choice(["CENTRAL_BANK", "MARKET_DATA", "NEWS_FEED", "ALGORITHM"]))
        )
    
    def generate_sim_activation(self, **kwargs) -> MockSIM:
        """Generate a mock SIM activation."""
        client_id = kwargs.get("client_id", f"CLIENT-{random.randint(1000, 9999)}")
        
        countries = ["ZA", "NG", "KE", "GH", "TZ", "UG", "ZM", "MZ", "RW"]
        country = kwargs.get("country", random.choice(countries))
        
        cities = {
            "ZA": ["Johannesburg", "Cape Town", "Durban"],
            "NG": ["Lagos", "Abuja", "Port Harcourt"],
            "KE": ["Nairobi", "Mombasa", "Kisumu"],
            "GH": ["Accra", "Kumasi", "Takoradi"],
            "TZ": ["Dar es Salaam", "Arusha", "Mwanza"],
            "UG": ["Kampala", "Entebbe", "Jinja"],
            "ZM": ["Lusaka", "Ndola", "Kitwe"],
            "MZ": ["Maputo", "Beira", "Nampula"],
            "RW": ["Kigali", "Butare", "Gisenyi"]
        }
        
        return MockSIM(
            sim_id=kwargs.get("sim_id", f"SIM-{uuid.uuid4().hex[:8].upper()}"),
            client_id=client_id,
            activation_date=kwargs.get("activation_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            country=country,
            city=kwargs.get("city", random.choice(cities.get(country, ["Unknown"]))),
            data_usage_mb=kwargs.get("data_usage_mb", random.randint(100, 50000)),
            voice_minutes=kwargs.get("voice_minutes", random.randint(0, 10000)),
            sms_count=kwargs.get("sms_count", random.randint(0, 1000)),
            tariff_plan=kwargs.get("tariff_plan", random.choice(["Enterprise", "Business", "Standard", "Premium"]))
        )
    
    def generate_insurance_policy(self, **kwargs) -> MockInsurancePolicy:
        """Generate a mock insurance policy."""
        client_id = kwargs.get("client_id", f"CLIENT-{random.randint(1000, 9999)}")
        
        policy_types = ["PROPERTY", "LIABILITY", "MARINE", "CREDIT", "LIFE", "HEALTH"]
        currencies = ["ZAR", "USD", "EUR", "GBP"]
        countries = ["ZA", "NG", "KE", "GH", "TZ"]
        
        start_date = kwargs.get("start_date", datetime.now(timezone.utc))
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        
        duration_years = kwargs.get("duration_years", random.choice([1, 3, 5, 10]))
        end_date = start_date + timedelta(days=365 * duration_years)
        
        coverage_amount = kwargs.get("coverage_amount", random.uniform(100_000, 100_000_000))
        premium_rate = random.uniform(0.001, 0.05)  # 0.1% to 5%
        premium_amount = coverage_amount * premium_rate
        
        return MockInsurancePolicy(
            policy_id=kwargs.get("policy_id", f"POL-{uuid.uuid4().hex[:8].upper()}"),
            client_id=client_id,
            policy_type=kwargs.get("policy_type", random.choice(policy_types)),
            coverage_amount=coverage_amount,
            premium_amount=premium_amount,
            currency=kwargs.get("currency", random.choice(currencies)),
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            country=kwargs.get("country", random.choice(countries)),
            risk_level=kwargs.get("risk_level", random.choice(["LOW", "MEDIUM", "HIGH"]))
        )
    
    def generate_fx_trade(self, **kwargs) -> MockFXTrade:
        """Generate a mock FX trade."""
        client_id = kwargs.get("client_id", f"CLIENT-{random.randint(1000, 9999)}")
        
        pairs = ["USD/ZAR", "USD/NGN", "USD/KES", "USD/GHS", "USD/ZMW", "USD/TZS"]
        pair = kwargs.get("currency_pair", random.choice(pairs))
        
        countries = {
            "USD/ZAR": "South Africa", "USD/NGN": "Nigeria", "USD/KES": "Kenya",
            "USD/GHS": "Ghana", "USD/ZMW": "Zambia", "USD/TZS": "Tanzania"
        }
        
        return MockFXTrade(
            trade_id=kwargs.get("trade_id", f"TRADE-{uuid.uuid4().hex[:8].upper()}"),
            client_id=client_id,
            currency_pair=pair,
            trade_type=kwargs.get("trade_type", random.choice(["spot", "forward", "ndf"])),
            direction=kwargs.get("direction", random.choice(["buy_usd", "sell_usd"])),
            notional_usd=kwargs.get("notional_usd", random.uniform(50_000, 5_000_000)),
            rate=kwargs.get("rate", random.uniform(10, 2000)),
            value_date=kwargs.get("value_date", (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")),
            country=kwargs.get("country", countries.get(pair, "Unknown")),
            traded_at=kwargs.get("traded_at", datetime.now(timezone.utc))
        )
    
    def generate_timestamp(self, days_ago: int = 0, hours_ago: int = 0, minutes_ago: int = 0) -> datetime:
        """Generate a timestamp relative to now."""
        return datetime.now(timezone.utc) - timedelta(
            days=days_ago, hours=hours_ago, minutes=minutes_ago
        )
    
    def generate_time_series(self, days: int = 30, frequency: str = "daily") -> List[datetime]:
        """Generate a time series of timestamps."""
        now = datetime.now(timezone.utc)
        
        if frequency == "daily":
            return [now - timedelta(days=i) for i in range(days)]
        elif frequency == "hourly":
            return [now - timedelta(hours=i) for i in range(days * 24)]
        elif frequency == "minutely":
            return [now - timedelta(minutes=i) for i in range(days * 24 * 60)]
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")


class AssertionHelpers:
    """Reusable assertion helpers for testing."""
    
    @staticmethod
    def assert_valid_timestamp(timestamp: str, max_age_days: int = 365) -> None:
        """Assert that a timestamp is valid and not too old."""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = (now - dt).days
            assert age >= 0, f"Timestamp is in the future: {timestamp}"
            assert age <= max_age_days, f"Timestamp is too old: {timestamp} (age: {age} days)"
        except ValueError as e:
            raise AssertionError(f"Invalid timestamp format: {timestamp}") from e
    
    @staticmethod
    def assert_valid_currency(currency: str) -> None:
        """Assert that a currency code is valid."""
        valid_currencies = {
            "ZAR", "USD", "EUR", "GBP", "NGN", "KES", "GHS", "TZS", "UGX", 
            "ZMW", "MZN", "AOA", "XOF", "XAF", "RWF", "ETB", "MWK", "BWP", "NAD"
        }
        assert currency in valid_currencies, f"Invalid currency: {currency}"
    
    @staticmethod
    def assert_valid_country(country: str) -> None:
        """Assert that a country code is valid."""
        valid_countries = {
            "ZA", "NG", "KE", "GH", "TZ", "UG", "ZM", "MZ", "AO", "RW", 
            "ET", "MW", "BW", "NA", "CD", "SS", "CF", "CG", "GA", "GQ"
        }
        assert country in valid_countries, f"Invalid country: {country}"
    
    @staticmethod
    def assert_valid_corridor(corridor: str) -> None:
        """Assert that a payment corridor is valid."""
        parts = corridor.split("-")
        assert len(parts) == 2, f"Invalid corridor format: {corridor}"
        
        for country in parts:
            AssertionHelpers.assert_valid_country(country)
    
    @staticmethod
    def assert_valid_amount(amount: float, min_amount: float = 0.01, max_amount: float = 1e12) -> None:
        """Assert that an amount is valid."""
        assert isinstance(amount, (int, float)), f"Amount must be numeric: {amount}"
        assert amount >= min_amount, f"Amount too small: {amount} (min: {min_amount})"
        assert amount <= max_amount, f"Amount too large: {amount} (max: {max_amount})"
    
    @staticmethod
    def assert_valid_rate(rate: float) -> None:
        """Assert that an FX rate is valid."""
        assert isinstance(rate, (int, float)), f"Rate must be numeric: {rate}"
        assert rate > 0, f"Rate must be positive: {rate}"
        assert rate < 1e6, f"Rate unreasonably high: {rate}"
    
    @staticmethod
    def assert_valid_uuid(uuid_str: str) -> None:
        """Assert that a string is a valid UUID."""
        try:
            uuid.UUID(uuid_str)
        except ValueError as e:
            raise AssertionError(f"Invalid UUID: {uuid_str}") from e
    
    @staticmethod
    def assert_valid_trade_type(trade_type: str) -> None:
        """Assert that a trade type is valid."""
        valid_types = {"spot", "forward", "swap", "option", "ndf"}
        assert trade_type in valid_types, f"Invalid trade type: {trade_type}"
    
    @staticmethod
    def assert_valid_direction(direction: str) -> None:
        """Assert that a trade direction is valid."""
        valid_directions = {"buy_usd", "sell_usd"}
        assert direction in valid_directions, f"Invalid direction: {direction}"
    
    @staticmethod
    def assert_utc_timezone(dt: datetime) -> None:
        """Assert that a datetime has UTC timezone."""
        assert dt.tzinfo is not None, f"Datetime must be timezone-aware: {dt}"
        assert dt.tzinfo == timezone.utc, f"Datetime must be in UTC: {dt}"


# Global instances for convenience
mock_generator = MockDataGenerator()
assertions = AssertionHelpers()


def generate_test_client(**kwargs) -> MockClient:
    """Convenience function to generate a test client."""
    return mock_generator.generate_client(**kwargs)


def generate_test_payment(**kwargs) -> MockPayment:
    """Convenience function to generate a test payment."""
    return mock_generator.generate_payment(**kwargs)


def generate_test_currency_event(**kwargs) -> MockCurrencyEvent:
    """Convenience function to generate a test currency event."""
    return mock_generator.generate_currency_event(**kwargs)


def generate_test_sim_activation(**kwargs) -> MockSIM:
    """Convenience function to generate a test SIM activation."""
    return mock_generator.generate_sim_activation(**kwargs)


def generate_test_insurance_policy(**kwargs) -> MockInsurancePolicy:
    """Convenience function to generate a test insurance policy."""
    return mock_generator.generate_insurance_policy(**kwargs)


def generate_test_fx_trade(**kwargs) -> MockFXTrade:
    """Convenience function to generate a test FX trade."""
    return mock_generator.generate_fx_trade(**kwargs)


def generate_utc_timestamp(**kwargs) -> datetime:
    """Generate a UTC timestamp for testing."""
    days_ago = kwargs.get("days_ago", 0)
    hours_ago = kwargs.get("hours_ago", 0)
    minutes_ago = kwargs.get("minutes_ago", 0)
    
    return datetime.now(timezone.utc) - timedelta(
        days=days_ago, hours=hours_ago, minutes=minutes_ago
    )