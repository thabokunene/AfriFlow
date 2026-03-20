"""
Unit tests for Lekgotla Moderation

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from afriflow.lekgotla.moderation import Moderator

@pytest.fixture
def moderator():
    return Moderator(client_golden_names=["Dangote Group", "Safaricom"])

def test_pii_detection_account_number(moderator):
    content = "My account number is 1234567890. Please check it."
    result = moderator.scan_content(content)
    assert result.approved is False
    assert "account_number" in result.pii_detected
    assert result.held_for_review is True

def test_pii_detection_phone_number(moderator):
    content = "Call me at +27 12 345 6789 to discuss."
    result = moderator.scan_content(content)
    assert result.approved is False
    assert "phone_number" in result.pii_detected

def test_pii_detection_email(moderator):
    content = "Email me at thabo@example.com."
    result = moderator.scan_content(content)
    assert result.approved is False
    assert "email" in result.pii_detected

def test_client_name_detection(moderator):
    content = "We are working with Dangote Group in Nigeria."
    result = moderator.scan_content(content)
    assert result.approved is False
    assert any("Dangote Group" in r for r in result.reasons)

def test_proprietary_pricing_detection(moderator):
    content = "The internal use only markup for this corridor is 50bps."
    result = moderator.scan_content(content)
    assert result.approved is False
    assert "Proprietary pricing detected" in result.reasons

def test_clean_content_passes(moderator):
    content = "Let's discuss the new trade finance policy for cocoa exporters."
    result = moderator.scan_content(content)
    assert result.approved is True
    assert len(result.pii_detected) == 0
