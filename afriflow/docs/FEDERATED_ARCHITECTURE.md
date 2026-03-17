<!-- docs/FEDERATED_ARCHITECTURE.md -->

# AfriFlow Federated Country Pod Architecture

> DISCLAIMER: This project is not sanctioned by, affiliated with, or endorsed
> by Standard Bank Group, MTN Group, or any of their subsidiaries. It is a
> demonstration of concept, domain knowledge, and technical skill built by
> Thabo Kunene for portfolio and learning purposes only. All data is
> simulated. No real client, transaction, or proprietary information is used.

## Why Centralized Architecture Fails in Africa

A single data lake in Johannesburg is architecturally clean but legally and
operationally impossible across 20 African countries.

### Legal Constraints

| Country | Data Localization Requirement | Implication |
|---------|------------------------------|-------------|
| Nigeria | NDPR requires personal data of Nigerian citizens to be processed in Nigeria or with adequate safeguards | Nigerian client PII must stay in Nigerian infrastructure |
| Kenya | Data Protection Act 2019 Section 48 restricts cross border transfers without adequate protection | Kenyan client data needs local processing |
| Rwanda | Data protection law requires government approval for cross border transfers | Approval process can take months |
| Angola | Banking secrecy law is strict, central bank approval needed for data export | Raw transaction data cannot leave Angola |
| South Africa | POPIA allows cross border transfer with adequate protection (relatively permissive) | Central hub is feasible for SA data |

### Operational Constraints

| Constraint | Impact |
|------------|--------|
| Submarine cable reliability | West Africa to South Africa connectivity has experienced 3 major outages in 2 years |
| Bandwidth cost | Data transfer from DRC to South Africa costs 10 to 50 times more than intra South Africa transfer |
| Latency | Round trip from Lagos to Johannesburg is 120 to 180ms, making real time queries impractical |
| Power reliability | Nigerian data center uptime is 97% vs 99.95% in South Africa |

## Federated Architecture Design

We deploy lightweight Country Pods that process local data locally and export
only aggregated, non PII signals to the central hub in South Africa.

```
                CENTRAL HUB (Johannesburg)
                +--------------------------+
                | Aggregated Golden Record  |
                | Cross country analytics   |
                | Group level dashboards    |
                | ML model training         |
                | (No foreign country PII)  |
                +-----------+--------------+
                            |
        +-------------------+-------------------+
        |                   |                   |
 +------+------+    +------+------+    +-------+-----+
 | NIGERIA POD  |    | KENYA POD   |    | ANGOLA POD  |
 | Local Kafka  |    | Local Kafka |    | Local Kafka |
 | Local Flink  |    | Local Flink |    | Local Flink |
 | Local Delta  |    | Local Delta |    | Local Delta |
 | NG PII stays |    | KE PII stays|    | AO PII stays|
 | here         |    | here        |    | here        |
 +-------------+    +-------------+    +-------------+
```

### What Stays Local (Country Pod)

- Raw transaction data with client PII
- Client names, addresses, identification numbers
- Individual transaction records
- Cell network CDRs and SIM registration data
- Insurance policy details with personal information

### What Gets Exported (Aggregated Signals)

- Client golden ID (pseudonymized, not PII)
- Aggregated financial metrics (total CIB value, corridor volumes)
- Signal outputs (expansion detected, attrition risk score)
- Domain presence flags (has CIB: yes, has insurance: no)
- Aggregated cell metrics (SIM count, not individual SIM details)

### Country Pod Sizing

| Tier | Countries | Infrastructure | Rationale |
|------|-----------|---------------|-----------|
| Tier 1: Full Pod | Nigeria, Kenya, Ghana | Dedicated Kafka cluster, Flink, Spark, Delta Lake | High volume, strict data localization |
| Tier 2: Light Pod | Uganda, Tanzania, Mozambique, Zambia, Cote d Ivoire, Angola | Shared regional Kafka, local Flink, local storage | Moderate volume, some localization |
| Tier 3: Hub Processed | Botswana, Namibia, Lesotho, Eswatini, Malawi, Zimbabwe | Data processed at central hub with consent framework | Lower volume, permissive regulations |
| Tier 4: Correspondent | DRC, South Sudan, Ethiopia, Mauritius | Batch file transfer, weekly aggregation | Limited infrastructure, minimal data |

## Sync Protocol

Each Country Pod syncs aggregated data to the central hub using a protocol
we call Pulse.

```yaml
# config/pulse_sync.yml

sync:
  frequency: every_15_minutes
  retry_on_failure: true
  max_retry_attempts: 5
  fallback_frequency: every_6_hours
  compression: gzip
  encryption: AES_256_GCM
  authentication: mTLS

  payload:
    - entity: client_aggregate
      fields: [golden_id, domain_presence, total_value, signal_scores]
      pii_fields: []  # No PII in sync payload

    - entity: corridor_aggregate
      fields: [source_country, dest_country, volume, transaction_count]
      pii_fields: []

    - entity: signal_output
      fields: [signal_id, signal_type, client_golden_id, confidence, details]
      pii_fields: []

  connectivity_monitor:
    health_check_interval: 60_seconds
    offline_buffer_max_size: 500_MB
    auto_resync_on_reconnect: true
```

## Offline Resilience

When a Country Pod loses connectivity to the central hub, it continues to
operate independently.

| Capability | Online | Offline |
|------------|--------|---------|
| Local signal detection | Full | Full |
| Cross country signals | Full | Degraded (uses last known state) |
| RM alerts for local clients | Full | Full |
| RM alerts for cross country clients | Full | Queued until reconnect |
| Golden record updates | Real time | Buffered, synced on reconnect |
| ML model inference | Full (latest model) | Full (cached model) |

## Files in This Module

| File | Purpose |
|------|---------|
| `infrastructure/federated/pod_config.py` | Country pod configuration manager |
| `infrastructure/federated/pulse_sync.py` | Aggregated data sync protocol |
| `infrastructure/federated/offline_buffer.py` | Offline operation buffer |
| `infrastructure/federated/connectivity_monitor.py` | Network health monitoring |
| `config/country_pods/*.yml` | Per country pod configurations |
| `config/data_residency_rules.yml` | Data localization rule definitions |
| `tests/integration/test_pulse_sync.py` | Sync protocol tests |
| `tests/integration/test_offline_resilience.py` | Offline operation tests |
