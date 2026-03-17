<!-- docs/SIM_DEFLATION.md -->

# AfriFlow SIM to Employee Deflation Model

> DISCLAIMER: This project is not sanctioned by, affiliated with, or endorsed
> by Standard Bank Group, MTN Group, or any of their subsidiaries. It is a
> demonstration of concept, domain knowledge, and technical skill built by
> Thabo Kunene for portfolio and learning purposes only. All data is
> simulated. No real client, transaction, or proprietary information is used.

## The Problem

In South Korea, one person equals one phone number equals one verifiable
identity. Kakao Bank can trust that SIM count equals user count.

In Africa, this assumption is dangerously wrong. A single employee in Nigeria
commonly carries 2 to 4 SIM cards across MTN, Airtel, Glo, and 9mobile. A
corporate SIM registered to the company may be used by an employee's family
member. SIM registration data under RICA (South Africa) or similar frameworks
in other countries is often incomplete.

If we use raw SIM count as a proxy for employee count, we will systematically
overestimate workforce size by 50% to 180% depending on the market. This
destroys RM trust the first time we send an alert saying "your client has
2,800 employees in Lagos" when the actual number is 1,000.

## Deflation Factors by Country

We maintain country level deflation factors derived from survey data,
industry benchmarks, and calibration against known client employee counts.

| Country | Avg SIMs per Person | Corporate SIM Sharing Rate | Deflation Factor | Confidence |
|---------|--------------------|---------------------------|------------------|------------|
| South Africa | 1.3 | 5% | 0.73 | High |
| Nigeria | 2.8 | 15% | 0.31 | Medium |
| Kenya | 2.1 | 10% | 0.43 | High |
| Ghana | 1.9 | 12% | 0.46 | Medium |
| Tanzania | 2.4 | 8% | 0.39 | Medium |
| Uganda | 2.2 | 10% | 0.41 | Medium |
| DRC | 1.9 | 20% | 0.42 | Low |
| Mozambique | 1.7 | 15% | 0.50 | Medium |
| Zambia | 1.6 | 8% | 0.57 | Medium |
| Angola | 1.5 | 10% | 0.61 | Low |
| Cote d Ivoire | 2.0 | 12% | 0.44 | Low |
| Botswana | 1.4 | 5% | 0.68 | High |
| Namibia | 1.3 | 5% | 0.73 | High |

### How to Read the Deflation Factor

If MTN reports 1,000 corporate SIMs for a client in Nigeria, we estimate
the actual employee count as:

```
estimated_employees = sim_count * deflation_factor
estimated_employees = 1000 * 0.31
estimated_employees = 310
```

### Calibration Method

We calibrate deflation factors using clients where we have both cell SIM
data and PBB payroll data. The payroll gives us the actual employee count,
and we compare it against the SIM count to derive the country level factor.

```
calibration_factor = actual_payroll_employees / reported_sim_count
```

We recalibrate quarterly as the multi SIM culture evolves (it is slowly
declining in some markets as smartphone penetration increases).

## Sector Adjustments

Some sectors have higher or lower SIM per employee ratios.

| Sector | Adjustment | Rationale |
|--------|-----------|-----------|
| Mining | 0.8x base factor | Remote sites, company issued SIMs dominate |
| Retail | 1.2x base factor | High turnover staff, personal SIMs common |
| Financial services | 0.9x base factor | Compliance driven, fewer personal SIMs |
| Agriculture | 1.5x base factor | Seasonal workers, shared SIMs |
| Construction | 1.3x base factor | Temporary workers, SIM sharing |
| Telecommunications | 0.7x base factor | Employees get company SIMs as perk |

## Confidence Intervals

We never report a single employee count estimate. We report a range.

```python
# Example output from the deflation model

{
    "client_id": "GLD-A1B2C3D4E5F6",
    "country": "NG",
    "raw_sim_count": 1000,
    "deflation_factor": 0.31,
    "sector_adjustment": 1.2,  # retail
    "estimated_employees": {
        "point_estimate": 372,
        "lower_bound": 280,
        "upper_bound": 465,
        "confidence_level": "medium"
    }
}
```

## Files in This Module

| File | Purpose |
|------|---------|
| `integration/sim_deflation/deflator.py` | Core deflation calculation engine |
| `integration/sim_deflation/calibrator.py` | Calibration against PBB payroll data |
| `config/sim_deflation_factors.yml` | Country and sector deflation factors |
| `tests/unit/test_sim_deflation.py` | Unit tests for deflation logic |
