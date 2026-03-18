"""
@file __init__.py
@description Cross-domain signals sub-package initialisation for AfriFlow.

             This package contains independent signal engines that each detect
             a specific category of intelligence by combining data from two or
             more of the five domains (CIB, Forex, Insurance, Cell, PBB).

             Modules in this package:
               - expansion_signal          : Geographic market expansion detection
               - competitive_leakage_signal: Wallet-share leakage to competitors
               - currency_event_propagator : FX event cross-domain impact cascade
               - data_shadow_model         : Intelligence from meaningful data absences
               - hedge_gap_signal          : Unhedged FX exposure detection
               - relationship_risk_signal  : Attrition and churn risk detection
               - seasonal_calendar         : African agricultural seasonal adjustments
               - supply_chain_risk_signal  : Supply-chain disruption signals
               - total_relationship_value  : Unified TRV calculator across domains
               - workforce_signal          : Workforce growth/contraction signals
@author Thabo Kunene
@created 2026-03-18
"""
