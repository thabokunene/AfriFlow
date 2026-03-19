"""
@file payment_generator.py
@description Generator for synthetic CIB cross-border corporate payments, simulating complex international trade flows.
@author Thabo Kunene
@created 2026-03-19
"""

"""
CIB Payment Generator.

We generate synthetic cross-border corporate payment
transactions for the CIB domain. This simulator is
used for testing and demonstration purposes.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# UUID for generating unique transaction and record identifiers
import uuid
# Random library for stochastic event generation based on market profiles
import random
# Datetime utilities for timestamping generated events and simulating cycles
from datetime import datetime, timedelta, timezone
# Type hinting for defining strong collection and functional contracts
from typing import Dict, List, Optional, Any
# Standard logging for operational observability and security auditing
import logging

# Faker library for generating realistic synthetic company names and addresses
from faker import Faker

# Registry of African countries and their metadata for geographic attribution
from afriflow.domains.shared.african_countries import AFRICAN_COUNTRIES
# Mapping of country codes to their respective primary currencies
from afriflow.domains.shared.currency_map import COUNTRY_TO_CURRENCY

# Initialize module-level logger for the CIB payment simulator
logger = logging.getLogger(__name__)

# Global Faker instance for generating realistic data
fake = Faker()


class PaymentGenerator:
    """
    Generates synthetic cross-border corporate payment transactions for the CIB domain.

    Attributes:
        clients: Pre-generated list of major corporate client names in Africa.
        seed: Random seed for ensuring reproducibility of generated datasets.
    """

    # Safety limit to prevent infinite loops during random country selection.
    MAX_COUNTRY_ATTEMPTS = 100

    def __init__(self, seed: Optional[int] = None) -> None:
        """
        Initializes the payment generator with an optional random seed.

        :param seed: Optional integer for deterministic data generation.
        """
        # Seed both Faker and the random module for consistent output across runs.
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
            logger.info(f"PaymentGenerator seeded with {seed}")

        # Registry of prominent African corporate entities to simulate realistic client portfolios.
        self.clients: List[str] = [
            "Dangote Cement",
            "MTN Group",
            "Safaricom",
            "Shoprite Holdings",
            "Standard Bank",
            "FirstRand",
            "Absa Group",
            "Nedbank",
            "Zenith Bank",
            "Guaranty Trust Bank",
            "Access Bank",
            "KCB Group",
            "Equity Group",
            "Co-operative Bank",
            "Vodacom",
            "Airtel Africa",
            "Coca-Cola Beverages Africa",
        ]

        logger.info(
            f"PaymentGenerator initialized with "
            f"{len(self.clients)} corporate clients"
        )

    def _fuzzy_name(self, name: str) -> str:
        """
        Introduces realistic data quality issues (typos, case variations) into entity names.
        Useful for testing fuzzy matching and entity resolution algorithms.

        :param name: The original, clean company name.
        :return: A variation of the name with simulated data quality issues.
        """
        # Choose a random variation type to apply.
        action = random.choice(["none", "typo", "suffix", "case"])

        if action == "none":
            return name
        elif action == "typo":
            # Simulate a character swap typo.
            if len(name) > 3:
                idx = random.randint(0, len(name) - 2)
                # Swap two adjacent characters.
                chars = list(name)
                chars[idx], chars[idx+1] = chars[idx+1], chars[idx]
                return "".join(chars)
            return name
        elif action == "suffix":
            # Add or change the corporate legal suffix.
            suffixes = ["Ltd", "Limited", "PLC", "Group", "Holdings"]
            base_name = name.split(" ")[0]
            return f"{base_name} {random.choice(suffixes)}"
        elif action == "case":
            # Simulate inconsistent casing from source systems.
            return name.upper() if random.random() > 0.5 else name.lower()
        return name

    def _select_beneficiary_country(
        self,
        sender_country: str
    ) -> str:
        """
        Select a different country for beneficiary.

        Args:
            sender_country: Sender's country code

        Returns:
            Beneficiary country code (different from sender)

        Raises:
            RuntimeError: If unable to find different country
        """
        countries = list(AFRICAN_COUNTRIES.keys())

        if len(countries) < 2:
            raise RuntimeError(
                "Need at least 2 countries for cross-border payments"
            )

        # Try random selection with limit to prevent infinite loop
        for attempt in range(self.MAX_COUNTRY_ATTEMPTS):
            beneficiary = random.choice(countries)
            if beneficiary != sender_country:
                return beneficiary

        # Fallback: select first different country
        for country in countries:
            if country != sender_country:
                return country

        raise RuntimeError(
            f"Unable to find different country from {sender_country}"
        )

    def generate_single_payment(self) -> Dict[str, Any]:
        """
        Generate a single synthetic payment transaction.

        Returns:
            Payment transaction dictionary

        Raises:
            RuntimeError: If payment generation fails
        """
        try:
            sender_country = random.choice(
                list(AFRICAN_COUNTRIES.keys())
            )

            # Ensure cross-border (with safety limit)
            beneficiary_country = self._select_beneficiary_country(
                sender_country
            )

            # Select currency
            currency_options = [
                COUNTRY_TO_CURRENCY.get(sender_country, "USD"),
                COUNTRY_TO_CURRENCY.get(beneficiary_country, "USD"),
                "USD",
                "EUR",
            ]
            currency = random.choice(currency_options)

            # Generate amount (realistic corporate payment range)
            amount = round(random.uniform(1000, 5_000_000), 2)

            # Determine sender/beneficiary (one is likely a corporate client)
            is_sender_corp = random.choice([True, False])

            if is_sender_corp:
                sender = self._fuzzy_name(
                    random.choice(self.clients)
                )
                beneficiary = fake.company()
            else:
                sender = fake.company()
                beneficiary = self._fuzzy_name(
                    random.choice(self.clients)
                )

            # Generate timestamp (within last ~7 days)
            timestamp = datetime.now(timezone.utc) - timedelta(
                minutes=random.randint(0, 10_000)
            )

            payment = {
                "transaction_id": str(uuid.uuid4()),
                "timestamp": timestamp.isoformat(),
                "amount": amount,
                "currency": currency,
                "sender_name": sender,
                "sender_country": sender_country,
                "beneficiary_name": beneficiary,
                "beneficiary_country": beneficiary_country,
                "status": random.choices(
                    ["COMPLETED", "PENDING", "FAILED"],
                    weights=[90, 8, 2]
                )[0],
                "purpose_code": random.choice(
                    ["CORT", "INTC", "DIVI", "SALA", "TREA"]
                ),
                "corridor": f"{sender_country}-{beneficiary_country}",
            }

            logger.debug(
                f"Generated payment: {payment['transaction_id'][:8]}... "
                f"{sender_country} -> {beneficiary_country} "
                f"{amount} {currency}"
            )

            return payment

        except Exception as e:
            logger.error(f"Failed to generate payment: {e}")
            raise RuntimeError(
                f"Payment generation failed: {e}"
            ) from e

    def generate_batch(
        self,
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Generate a batch of payment transactions.

        Args:
            count: Number of payments to generate

        Returns:
            List of payment transaction dictionaries
        """
        if count <= 0:
            logger.warning(f"Invalid batch count: {count}")
            return []

        logger.info(f"Generating batch of {count} payments")

        payments = [
            self.generate_single_payment()
            for _ in range(count)
        ]

        logger.info(f"Generated {len(payments)} payments")
        return payments


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    gen = PaymentGenerator(seed=42)
    payments = gen.generate_batch(5)

    print(json.dumps(payments, indent=2))
