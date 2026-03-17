"""
Seasonal Factor Calibration

We recalibrate seasonal factors from historical CIB
payment data to improve accuracy over time.

Disclaimer: This is not a sanctioned Standard Bank Group
project. It is a demonstration of concept, domain
knowledge, and skill by Thabo Kunene. All data is
simulated.
"""

from collections import defaultdict
from typing import Dict, List
import statistics


class SeasonalCalibrator:
    """
    We calibrate seasonal factors by analyzing 3 years
    of historical payment data grouped by client
    industry and country.

    The calibration process:
    1. Group payments by country, industry, month
    2. Calculate average monthly volume
    3. Normalize to produce seasonal factors
    4. Compare with existing factors
    5. Update where deviation exceeds threshold
    """

    DEVIATION_THRESHOLD = 0.15

    def __init__(self):
        self.monthly_volumes: Dict[
            str, Dict[str, Dict[int, List[float]]]
        ] = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(list)
            )
        )

    def ingest_historical_payment(
        self, payment: Dict
    ):
        """
        We ingest a historical payment record for
        calibration.
        """

        country = payment["country_code"]
        industry = payment["industry"]
        month = payment["month"]
        volume = payment["volume"]

        self.monthly_volumes[country][industry][
            month
        ].append(volume)

    def calibrate(self) -> Dict:
        """
        We compute calibrated seasonal factors from
        historical data.

        Returns a dictionary structured identically
        to the african_calendar.json seasonal_factors
        section.
        """

        calibrated = {}

        for country, industries in (
            self.monthly_volumes.items()
        ):
            calibrated[country] = {}

            for industry, months in industries.items():
                monthly_averages = {}
                for month in range(1, 13):
                    values = months.get(month, [])
                    if values:
                        monthly_averages[month] = (
                            statistics.mean(values)
                        )
                    else:
                        monthly_averages[month] = 0.0

                overall_avg = statistics.mean(
                    v for v in monthly_averages.values()
                    if v > 0
                ) if any(
                    v > 0
                    for v in monthly_averages.values()
                ) else 1.0

                factors = {}
                for month, avg in (
                    monthly_averages.items()
                ):
                    if overall_avg > 0 and avg > 0:
                        factors[str(month)] = round(
                            avg / overall_avg, 2
                        )
                    else:
                        factors[str(month)] = 1.0

                calibrated[country][industry] = factors

        return calibrated

    def compare_with_existing(
        self,
        existing_factors: Dict,
        calibrated_factors: Dict
    ) -> List[Dict]:
        """
        We compare calibrated factors with existing
        factors and flag significant deviations.
        """

        deviations = []

        for country in calibrated_factors:
            for industry in calibrated_factors[country]:
                for month in (
                    calibrated_factors[country][industry]
                ):
                    new_val = (
                        calibrated_factors
                        [country][industry][month]
                    )
                    existing_country = (
                        existing_factors.get(country, {})
                    )
                    existing_industry = (
                        existing_country.get(
                            industry, {}
                        )
                    )
                    old_val = existing_industry.get(
                        month, 1.0
                    )

                    if old_val > 0:
                        deviation = (
                            abs(new_val - old_val)
                            / old_val
                        )
                    else:
                        deviation = 1.0

                    if (
                        deviation
                        > self.DEVIATION_THRESHOLD
                    ):
                        deviations.append({
                            "country": country,
                            "industry": industry,
                            "month": month,
                            "old_factor": old_val,
                            "new_factor": new_val,
                            "deviation_pct": round(
                                deviation * 100, 1
                            ),
                            "recommendation": (
                                "UPDATE"
                                if deviation > 0.25
                                else "REVIEW"
                            )
                        })

        return sorted(
            deviations,
            key=lambda d: d["deviation_pct"],
            reverse=True
        )
