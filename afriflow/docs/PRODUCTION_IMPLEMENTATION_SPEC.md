<!--
@file PRODUCTION_IMPLEMENTATION_SPEC.md
@description Implementation specifications for simulators, diagrams, NBA, deployment, and risk
@author Thabo Kunene
@created 2026-03-17
-->
# AfriFlow Production Implementation Specification


 
**Classification:** Internal  

---

## Table of Contents

1. [Domain Simulators Implementation Roadmap](#1-domain-simulators-implementation-roadmap)
2. [Diagram Generators Technical Specifications](#2-diagram-generators-technical-specifications)
3. [ML Models (NBA) Phase 2 Integration Plan](#3-ml-models-nba-phase-2-integration-plan)
4. [Enhanced Deployment Checklist](#4-enhanced-deployment-checklist)
5. [Post-Deployment Monitoring and Feedback Framework](#5-post-deployment-monitoring-and-feedback-framework)
6. [Risk Mitigation Strategies](#6-risk-mitigation-strategies)

---

## 1. Domain Simulators Implementation Roadmap

### 1.1 Overview

Domain simulators are critical for generating realistic test data that mirrors production patterns across all five domains (CIB, Forex, Insurance, Cell, PBB). These simulators enable continuous testing, validation, and demonstration capabilities without requiring access to production data.

### 1.2 Architecture Requirements

#### 1.2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOMAIN SIMULATOR PLATFORM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    CIB       │  │    FOREX     │  │  INSURANCE   │  │    CELL      │    │
│  │  Simulator   │  │  Simulator   │  │  Simulator   │  │  Simulator   │    │
│  │              │  │              │  │              │  │              │    │
│  │ - Payments   │  │ - FX Trades  │  │ - Policies   │  │ - SIM Usage  │    │
│  │ - Cash Mgmt  │  │ - Hedging    │  │ - Claims     │  │ - MoMo       │    │
│  │ - Trade Fin  │  │ - Forwards   │  │ - Premiums   │  │ - USSD       │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┴────────┬────────┴─────────────────┘             │
│                                    │                                         │
│                          ┌─────────▼─────────┐                              │
│                          │  PBB Simulator    │                              │
│                          │                   │                              │
│                          │ - Accounts        │                              │
│                          │ - Payroll         │                              │
│                          │ - Deposits        │                              │
│                          └─────────┬─────────┘                              │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         │                          │                          │             │
│         ▼                          ▼                          ▼             │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐         │
│  │   Schema    │          │   Event     │          │   Quality   │         │
│  │  Validator  │          │  Generator  │          │  Enforcer   │         │
│  └──────┬──────┘          └──────┬──────┘          └──────┬──────┘         │
│         │                        │                        │                 │
│         └────────────────────────┼────────────────────────┘                 │
│                                  │                                          │
│                         ┌────────▼────────┐                                │
│                         │  Kafka Producer │                                │
│                         │     Gateway     │                                │
│                         └────────┬────────┘                                │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   Apache Kafka (Raw Topics)  │
                    │                              │
                    │ - cib.payments.raw           │
                    │ - forex.trades.raw           │
                    │ - insurance.policies.raw     │
                    │ - cell.usage.raw             │
                    │ - pbb.accounts.raw           │
                    └──────────────────────────────┘
```

#### 1.2.2 Component Specifications

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| Domain Simulators | Generate domain-specific events | Python 3.11+ with asyncio |
| Schema Validator | Ensure Avro schema compliance | fastavro + Schema Registry client |
| Event Generator | Create realistic event sequences | Faker + custom probability distributions |
| Quality Enforcer | Apply data quality rules | Great Expectations integration |
| Kafka Producer Gateway | Publish events to Kafka | confluent-kafka with async support |
| Configuration Manager | Manage simulator parameters | Pydantic settings with YAML overrides |

### 1.3 Technology Stack Recommendations

#### 1.3.1 Core Technologies

```yaml
Runtime:
  Language: Python 3.11+
  Async Framework: asyncio + aiohttp
  Type Checking: mypy --strict

Data Generation:
  Synthetic Data: Faker 19.0+
  Probability Distributions: numpy 1.24+
  Time Series Patterns: pandas 2.0+

Schema Management:
  Avro Processing: fastavro 1.8+
  Schema Registry: confluent-schema-registry 7.4+
  Validation: pydantic 2.0+

Messaging:
  Kafka Client: confluent-kafka 2.0+
  Serialization: Avro + JSON fallback
  Compression: snappy

Configuration:
  Settings Management: pydantic-settings 2.0+
  Secret Management: HashiCorp Vault integration
  Feature Flags: LaunchDarkly SDK

Testing:
  Unit Testing: pytest 7.4+
  Property-Based: hypothesis 6.88+
  Integration: pytest-kafka
  Load Testing: locust 2.20+
```

#### 1.3.2 Infrastructure Dependencies

```yaml
Required Services:
  - Apache Kafka 3.4+ (3 brokers minimum)
  - Schema Registry 7.4+
  - Redis 7.0+ (for rate limiting and state)
  - PostgreSQL 15+ (for simulator state persistence)

Optional Services:
  - Grafana (for simulator metrics visualization)
  - Prometheus (for metrics collection)
  - Jaeger (for distributed tracing)
```

### 1.4 Integration Points with Existing Systems

#### 1.4.1 Kafka Integration

```python
# afriflow/simulators/integration/kafka_producer.py
from typing import Dict, Any, Optional
from confluent_kafka import Producer
from afriflow.config.settings import KafkaSettings

class SimulatorKafkaProducer:
    """
    Kafka producer optimized for domain simulators.
    
    Features:
    - Automatic schema registration
    - Idempotent publishing with correlation IDs
    - Backpressure handling
    - Delivery confirmation with retries
    """
    
    def __init__(
        self,
        settings: KafkaSettings,
        schema_registry_url: str
    ):
        self.settings = settings
        self.schema_registry = schema_registry_url
        self.producer = Producer({
            'bootstrap.servers': settings.bootstrap_servers,
            'acks': 'all',
            'retries': 5,
            'enable.idempotence': True,
            'compression.type': 'snappy'
        })
    
    async def publish(
        self,
        topic: str,
        event: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> str:
        """Publish event with delivery confirmation."""
        # Implementation details...
        pass
```

#### 1.4.2 Schema Registry Integration

| Domain | Schema Subject | Compatibility | Version Strategy |
|--------|---------------|---------------|------------------|
| CIB | cib.payment | BACKWARD | Semantic versioning |
| CIB | cib.trade_finance | BACKWARD | Semantic versioning |
| Forex | forex.trade | BACKWARD | Semantic versioning |
| Forex | forex.rate_tick | BACKWARD | Semantic versioning |
| Insurance | insurance.policy | BACKWARD | Semantic versioning |
| Insurance | insurance.claim | BACKWARD | Semantic versioning |
| Cell | cell.usage | BACKWARD | Semantic versioning |
| Cell | cell.momo | BACKWARD | Semantic versioning |
| PBB | pbb.account | BACKWARD | Semantic versioning |
| PBB | pbb.payroll | BACKWARD | Semantic versioning |

#### 1.4.3 Configuration Integration

```yaml
# afriflow/config/simulator_config.yaml
simulators:
  cib:
    enabled: true
    events_per_minute: 100
    schema_version: "2.0"
    patterns:
      payments:
        peak_hours: [9, 10, 11, 14, 15, 16]
        weekend_reduction: 0.3
        month_end_spike: 1.5
      trade_finance:
        business_days_only: true
        avg_daily_volume: 50
  
  forex:
    enabled: true
    events_per_minute: 200
    schema_version: "1.5"
    patterns:
      trades:
        market_hours: [8, 17]  # JSE hours
        volatility_clustering: true
      rate_ticks:
        frequency_seconds: 5
        major_pairs: ["USDZAR", "EURZAR", "GBSZAR"]
  
  insurance:
    enabled: true
    events_per_minute: 50
    schema_version: "1.2"
    patterns:
      policies:
        new_business_ratio: 0.3
        renewal_ratio: 0.7
      claims:
        frequency_by_type:
          short_term: 0.6
          long_term: 0.4
  
  cell:
    enabled: true
    events_per_minute: 500
    schema_version: "1.8"
    patterns:
      usage:
        peak_evening: [18, 22]
        data_vs_voice_ratio: 3.5
      momo:
        transaction_peak: [12, 13, 17]
        avg_transaction_value: 250
  
  pbb:
    enabled: true
    events_per_minute: 75
    schema_version: "1.3"
    patterns:
      accounts:
        new_accounts_daily: 150
        closure_rate: 0.02
      payroll:
        month_end_concentration: 0.8
        avg_salary_by_segment:
          mass: 15000
          affluent: 45000
          private_banking: 150000
```

### 1.5 Development Timeline with Milestones

#### Phase 1: Foundation (Weeks 1-3)

| Week | Deliverables | Success Criteria |
|------|-------------|------------------|
| 1 | - Project scaffolding<br>- Base simulator class<br>- Kafka producer gateway | - All modules importable<br>- Basic event publishing works<br>- Schema validation passes |
| 2 | - CIB simulator (payments)<br>- CIB simulator (trade finance)<br>- Unit tests | - 100 events/minute sustained<br>- Schema compliance verified<br>- Test coverage >90% |
| 3 | - Forex simulator<br>- Integration tests<br>- Performance benchmarks | - 200 events/minute sustained<br>- End-to-end latency <100ms<br>- Zero data loss in 24h run |

#### Phase 2: Core Domains (Weeks 4-6)

| Week | Deliverables | Success Criteria |
|------|-------------|------------------|
| 4 | - Insurance simulator (policies)<br>- Insurance simulator (claims)<br>- Data quality enforcer | - Policy lifecycle simulation<br>- Claims pattern accuracy<br>- DQ rules enforced |
| 5 | - Cell simulator (usage, MoMo)<br>- USSD session simulator<br>- Load testing suite | - 500 events/minute sustained<br>- Realistic session patterns<br>- Load test passes 1000 events/sec |
| 6 | - PBB simulator (accounts)<br>- PBB simulator (payroll)<br>- Cross-domain correlation | - Account lifecycle simulation<br>- Payroll cycle accuracy<br>- Cross-entity consistency |

#### Phase 3: Enhancement (Weeks 7-9)

| Week | Deliverables | Success Criteria |
|------|-------------|------------------|
| 7 | - Seasonal pattern injection<br>- Anomaly injection framework<br>- Monitoring dashboard | - Seasonal adjustments accurate<br>- Anomalies detectable<br>- Grafana dashboard operational |
| 8 | - State persistence layer<br>- Replay capability<br>- Configuration UI | - State survives restarts<br>- Historical replay works<br>- UI functional |
| 9 | - Documentation<br>- Runbooks<br>- Training materials | - All docs complete<br>- Runbooks tested<br>- Training delivered |

#### Phase 4: Validation (Weeks 10-12)

| Week | Deliverables | Success Criteria |
|------|-------------|------------------|
| 10 | - UAT with business users<br>- Pattern accuracy validation<br>- Performance optimization | - Business sign-off<br>- Pattern accuracy >95%<br>- Performance targets met |
| 11 | - Chaos engineering tests<br>- Disaster recovery test<br>- Security audit | - System survives failures<br>- DR test passes RTO/RPO<br>- Security findings resolved |
| 12 | - Production deployment<br>- Handover to operations<br>- Project closure | - Simulators running in prod<br>- Ops team trained<br>- Lessons learned documented |

### 1.6 Resource Allocation Needs

#### 1.6.1 Team Composition

| Role | FTE | Duration | Responsibilities |
|------|-----|----------|------------------|
| Senior Python Developer | 2 | 12 weeks | Core simulator development, Kafka integration |
| Data Engineer | 1 | 8 weeks | Schema design, data quality rules |
| DevOps Engineer | 0.5 | 6 weeks | Infrastructure, CI/CD, monitoring |
| QA Engineer | 1 | 8 weeks | Test automation, load testing |
| Technical Writer | 0.5 | 4 weeks | Documentation, runbooks |
| Product Owner | 0.2 | 12 weeks | Requirements, UAT coordination |

#### 1.6.2 Infrastructure Requirements

```yaml
Development Environment:
  Compute: 4 vCPU, 16GB RAM per developer
  Storage: 100GB SSD per environment
  Kafka Cluster: 3 brokers, 8GB RAM each

Testing Environment:
  Compute: 8 vCPU, 32GB RAM
  Storage: 500GB SSD
  Kafka Cluster: 3 brokers, 16GB RAM each

Production Environment:
  Compute: 16 vCPU, 64GB RAM (auto-scaling)
  Storage: 1TB SSD (hot) + 5TB (cold)
  Kafka Cluster: 5 brokers, 32GB RAM each
  Redis Cluster: 3 nodes, 8GB RAM each
  PostgreSQL: 4 vCPU, 16GB RAM, 200GB storage
```

### 1.7 Testing Strategies

#### 1.7.1 Unit Testing

```python
# afriflow/simulators/tests/unit/test_cib_simulator.py
import pytest
from hypothesis import given, strategies as st
from afriflow.simulators.cib import CIBPaymentSimulator
from afriflow.simulators.schema_validator import SchemaValidator

class TestCIBPaymentSimulator:
    
    @pytest.fixture
    def simulator(self, config):
        return CIBPaymentSimulator(config)
    
    def test_generate_payment_event(self, simulator):
        """Verify payment event structure and required fields."""
        event = simulator.generate_payment_event()
        
        assert "payment_id" in event
        assert "amount" in event
        assert "currency" in event
        assert "timestamp" in event
        assert event["schema_version"] == "2.0"
    
    @given(
        amount=st.floats(min_value=0.01, max_value=1_000_000),
        currency=st.sampled_from(["ZAR", "USD", "EUR", "GBP"])
    )
    def test_payment_event_schema_compliance(
        self, simulator, amount, currency
    ):
        """Property-based test for schema compliance."""
        event = simulator.generate_payment_event(
            amount=amount, currency=currency
        )
        
        validator = SchemaValidator("cib.payment.v2")
        assert validator.validate(event) is True
    
    def test_peak_hour_pattern(self, simulator):
        """Verify increased event generation during peak hours."""
        peak_events = simulator.generate_batch(hour=10, count=100)
        off_peak_events = simulator.generate_batch(hour=3, count=100)
        
        # Peak hours should have more valid transactions
        assert len(peak_events) >= len(off_peak_events) * 0.9
```

#### 1.7.2 Integration Testing

```python
# afriflow/simulators/tests/integration/test_kafka_integration.py
import pytest
import asyncio
from afriflow.simulators.integration import SimulatorKafkaProducer
from afriflow.simulators.cib import CIBPaymentSimulator

@pytest.mark.kafka
class TestKafkaIntegration:
    
    @pytest.fixture
    async def producer(self, kafka_settings):
        p = SimulatorKafkaProducer(kafka_settings)
        await p.connect()
        yield p
        await p.disconnect()
    
    async def test_end_to_end_event_publish(
        self, producer, simulator, kafka_consumer
    ):
        """Verify events are published and consumable."""
        event = simulator.generate_payment_event()
        correlation_id = await producer.publish(
            topic="cib.payments.raw",
            event=event
        )
        
        # Consume and verify
        consumed = await kafka_consumer.consume_one(
            topic="cib.payments.raw",
            timeout_ms=5000
        )
        
        assert consumed is not None
        assert consumed.value["payment_id"] == event["payment_id"]
        assert consumed.headers["correlation_id"] == correlation_id
    
    async def test_backpressure_handling(self, producer, simulator):
        """Verify system handles backpressure gracefully."""
        # Simulate slow consumer
        events = [simulator.generate_payment_event() for _ in range(1000)]
        
        # Should not raise, should queue or reject gracefully
        results = await asyncio.gather(
            *[producer.publish("cib.payments.raw", e) for e in events],
            return_exceptions=True
        )
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count >= 950  # 95% success rate minimum
```

#### 1.7.3 Load Testing

```python
# afriflow/simulators/tests/load/test_simulator_performance.py
from locust import HttpUser, task, between
import time

class SimulatorLoadTest(HttpUser):
    wait_time = between(0.01, 0.1)
    
    @task(3)
    def publish_payment_event(self):
        """Simulate high-frequency payment event publishing."""
        start_time = time.time()
        
        response = self.client.post(
            "/api/v1/simulators/cib/payments",
            json={"count": 10}
        )
        
        elapsed = time.time() - start_time
        
        # Performance assertions
        assert response.status_code == 200
        assert elapsed < 0.5  # 500ms p95 latency target
    
    @task(1)
    def get_simulator_metrics(self):
        """Monitor simulator health during load."""
        response = self.client.get("/api/v1/simulators/metrics")
        assert response.status_code == 200
```

#### 1.7.4 Accuracy Validation

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Event schema compliance | 100% | Schema Registry validation |
| Pattern accuracy | >95% | Statistical comparison with production |
| Distribution fidelity | >90% | Kolmogorov-Smirnov test |
| Temporal consistency | >98% | Autocorrelation analysis |
| Cross-entity correlation | >85% | Correlation coefficient comparison |

---

## 2. Diagram Generators Technical Specifications

### 2.1 Overview

Automated diagram generation provides visual representation of system architecture, data flows, entity relationships, and operational metrics. These diagrams are generated dynamically from live system data and configuration.

### 2.2 Required Data Sources

#### 2.2.1 Primary Data Sources

| Source | Type | Content | Refresh Rate |
|--------|------|---------|--------------|
| Kafka Topics | Streaming | Topic topology, partition info, consumer groups | Real-time |
| Schema Registry | API | Avro schemas, version history, compatibility | On-change |
| Delta Lake | Query | Table lineage, schema evolution, statistics | Hourly |
| dbt Catalog | API | Model dependencies, column lineage, tests | On-build |
| Kubernetes API | API | Pod topology, service mesh, resource allocation | Real-time |
| Airflow | API | DAG definitions, task dependencies, execution history | Real-time |

#### 2.2.2 Data Source Integration

```python
# afriflow/diagrams/data_sources.py
from typing import Dict, List, Any
from abc import ABC, abstractmethod

class DiagramDataSource(ABC):
    """Abstract base class for diagram data sources."""
    
    @abstractmethod
    async def fetch(self) -> Dict[str, Any]:
        """Fetch data from the source."""
        pass
    
    @abstractmethod
    def get_cache_ttl(self) -> int:
        """Return cache TTL in seconds."""
        pass

class KafkaTopologySource(DiagramDataSource):
    """Fetch Kafka topology information."""
    
    def __init__(self, admin_client: KafkaAdminClient):
        self.admin_client = admin_client
    
    async def fetch(self) -> Dict[str, Any]:
        topics = self.admin_client.list_topics()
        consumer_groups = self.admin_client.list_consumer_groups()
        
        return {
            "topics": [
                {
                    "name": topic.name,
                    "partitions": topic.num_partitions,
                    "replication_factor": topic.replication_factor,
                    "config": topic.config
                }
                for topic in topics
            ],
            "consumer_groups": [
                {
                    "group_id": cg.group_id,
                    "topics": cg.topics,
                    "members": cg.members,
                    "lag": cg.total_lag
                }
                for cg in consumer_groups
            ]
        }
    
    def get_cache_ttl(self) -> int:
        return 60  # 1 minute cache

class DbtLineageSource(DiagramDataSource):
    """Fetch dbt model lineage."""
    
    def __init__(self, dbt_cloud_api: DbtCloudClient):
        self.dbt_cloud_api = dbt_cloud_api
    
    async def fetch(self) -> Dict[str, Any]:
        models = await self.dbt_cloud_api.get_models()
        
        return {
            "models": [
                {
                    "name": model.name,
                    "schema": model.schema,
                    "depends_on": model.depends_on.nodes,
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.data_type,
                            "tests": col.tests
                        }
                        for col in model.columns
                    ]
                }
                for model in models
            ]
        }
    
    def get_cache_ttl(self) -> int:
        return 3600  # 1 hour cache
```

### 2.3 Visualization Frameworks

#### 2.3.1 Recommended Stack

| Purpose | Framework | Rationale |
|---------|-----------|-----------|
| Graph Layout | Graphviz + pygraphviz | Industry standard for graph visualization |
| Interactive Diagrams | D3.js + React | Rich interactivity, web-native |
| Static Diagrams | Mermaid.js | Markdown-compatible, easy embedding |
| Architecture Diagrams | Structurizr | C4 model support, code-to-diagram |
| Flow Diagrams | Apache ECharts | High performance, rich animations |

#### 2.3.2 Implementation Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIAGRAM GENERATION ENGINE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Data      │  │   Data      │  │   Data      │             │
│  │  Sources    │  │  Sources    │  │  Sources    │             │
│  │  (Kafka)    │  │  (dbt)      │  │  (K8s)      │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│                 ┌────────▼────────┐                            │
│                 │  Data Aggregator │                            │
│                 │  & Normalizer   │                            │
│                 └────────┬────────┘                            │
│                          │                                      │
│         ┌────────────────┼────────────────┐                    │
│         │                │                │                    │
│         ▼                ▼                ▼                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Graph     │  │    Flow     │  │  Architecture│            │
│  │  Generator  │  │  Generator  │  │  Generator  │            │
│  │             │  │             │  │             │            │
│  │ - Entity    │  │ - Pipeline  │  │ - C4 Model  │            │
│  │   Graph     │  │   Flow      │  │ - Component │            │
│  │ - Lineage   │  │ - Data Flow │  │   Diagram   │            │
│  │   Graph     │  │ - Event     │  │ - Deployment│            │
│  │             │  │   Flow      │  │   Diagram   │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│                 ┌────────▼────────┐                            │
│                 │  Render Engine  │                            │
│                 │                 │                            │
│                 │ - SVG           │                            │
│                 │ - PNG           │                            │
│                 │ - PDF           │                            │
│                 │ - Interactive   │                            │
│                 └────────┬────────┘                            │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   REST API    │  │  CLI Tool     │  │  Scheduled    │
│   Endpoints   │  │               │  │  Export       │
└───────────────┘  └───────────────┘  └───────────────┘
```

### 2.4 Output Formats

#### 2.4.1 Supported Formats

| Format | Use Case | Generation Method |
|--------|----------|-------------------|
| SVG | Web embedding, documentation | Graphviz SVG output |
| PNG | Presentations, reports | Cairo/SVG rasterization |
| PDF | Formal documentation, printing | ReportLab integration |
| Interactive HTML | Dashboards, exploration | D3.js + React |
| Mermaid MD | Markdown docs, wikis | Template rendering |
| DOT/Graphviz | Further processing | Direct Graphviz output |
| JSON | Programmatic consumption | Internal representation |

#### 2.4.2 Format Specifications

```python
# afriflow/diagrams/renderers.py
from typing import Dict, Any, Literal
from abc import ABC, abstractmethod
import io

DiagramFormat = Literal["svg", "png", "pdf", "html", "mermaid", "dot", "json"]

class DiagramRenderer(ABC):
    """Abstract base class for diagram renderers."""
    
    @abstractmethod
    def render(self, graph: Dict[str, Any]) -> bytes:
        """Render the graph to the target format."""
        pass
    
    @property
    @abstractmethod
    def format(self) -> DiagramFormat:
        """Return the output format."""
        pass

class SVGRenderer(DiagramRenderer):
    """Render diagrams to SVG format."""
    
    def __init__(self, width: int = 1200, height: int = 800):
        self.width = width
        self.height = height
    
    def render(self, graph: Dict[str, Any]) -> bytes:
        import graphviz
        
        dot = graphviz.Digraph(
            format='svg',
            graph_attr={
                'rankdir': 'TB',
                'splines': 'ortho',
                'nodesep': '0.5',
                'ranksep': '0.75'
            }
        )
        
        # Build graph from normalized representation
        for node in graph['nodes']:
            dot.node(
                node['id'],
                node['label'],
                shape=node.get('shape', 'box'),
                style=node.get('style', 'filled'),
                fillcolor=node.get('color', '#ffffff')
            )
        
        for edge in graph['edges']:
            dot.edge(
                edge['source'],
                edge['target'],
                label=edge.get('label', ''),
                style=edge.get('style', 'solid')
            )
        
        return dot.pipe()
    
    @property
    def format(self) -> DiagramFormat:
        return "svg"

class InteractiveHTMLRenderer(DiagramRenderer):
    """Render interactive diagrams using D3.js."""
    
    TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            .node rect {{ fill: #fff; stroke: #333; stroke-width: 2px; }}
            .edge path {{ stroke: #999; stroke-width: 2px; fill: none; }}
            .node text {{ font: 12px sans-serif; }}
        </style>
    </head>
    <body>
        <svg id="diagram" width="{width}" height="{height}"></svg>
        <script>
            const graph = {graph_data};
            // D3.js rendering logic
        </script>
    </body>
    </html>
    """
    
    def __init__(self, width: int = 1400, height: int = 900):
        self.width = width
        self.height = height
    
    def render(self, graph: Dict[str, Any]) -> bytes:
        import json
        
        html = self.TEMPLATE.format(
            title=graph.get('title', 'AfriFlow Diagram'),
            width=self.width,
            height=self.height,
            graph_data=json.dumps(graph)
        )
        
        return html.encode('utf-8')
    
    @property
    def format(self) -> DiagramFormat:
        return "html"
```

### 2.5 Customization Options

#### 2.5.1 Styling Configuration

```yaml
# afriflow/config/diagram_styles.yaml
styles:
  nodes:
    kafka_topic:
      shape: cylinder
      color: "#FF6B6B"
      border_color: "#C92A2A"
      font_color: "#ffffff"
    
    flink_job:
      shape: ellipse
      color: "#4ECDC4"
      border_color: "#087F5B"
      font_color: "#ffffff"
    
    delta_table:
      shape: folder
      color: "#45B7D1"
      border_color: "#1864AB"
      font_color: "#ffffff"
    
    dbt_model:
      shape: box
      color: "#96CEB4"
      border_color: "#2D6A4F"
      font_color: "#1B4332"
    
    api_endpoint:
      shape: hexagon
      color: "#DDA0DD"
      border_color: "#8B5CF6"
      font_color: "#ffffff"
  
  edges:
    data_flow:
      style: solid
      color: "#666666"
      width: 2
      arrowhead: normal
    
    schema_evolution:
      style: dashed
      color: "#999999"
      width: 1
      arrowhead: normal
    
    alert_path:
      style: dotted
      color: "#FF0000"
      width: 2
      arrowhead: normal
  
  layouts:
    architecture:
      direction: TB  # Top to bottom
      node_spacing: 50
      rank_spacing: 75
    
    lineage:
      direction: LR  # Left to right
      node_spacing: 40
      rank_spacing: 60
    
    flow:
      direction: LR
      node_spacing: 30
      rank_spacing: 50
```

#### 2.5.2 Filter and Focus Options

```python
# afriflow/diagrams/filters.py
from typing import List, Optional, Callable
from dataclasses import dataclass

@dataclass
class DiagramFilter:
    """Filter configuration for diagram generation."""
    
    # Domain filter
    domains: Optional[List[str]] = None  # ["cib", "forex", "insurance"]
    
    # Layer filter
    layers: Optional[List[str]] = None  # ["bronze", "silver", "gold"]
    
    # Country filter
    countries: Optional[List[str]] = None  # ["ZA", "NG", "KE"]
    
    # Depth limit for lineage diagrams
    max_depth: Optional[int] = None
    
    # Custom node/edge filters
    node_filter: Optional[Callable[[dict], bool]] = None
    edge_filter: Optional[Callable[[dict], bool]] = None
    
    def apply(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters to the graph."""
        filtered_nodes = []
        node_ids = set()
        
        for node in graph['nodes']:
            if self._should_include_node(node):
                filtered_nodes.append(node)
                node_ids.add(node['id'])
        
        filtered_edges = [
            edge for edge in graph['edges']
            if edge['source'] in node_ids and edge['target'] in node_ids
        ]
        
        return {
            **graph,
            'nodes': filtered_nodes,
            'edges': filtered_edges
        }
    
    def _should_include_node(self, node: dict) -> bool:
        """Check if node passes all filters."""
        if self.domains and node.get('domain') not in self.domains:
            return False
        if self.layers and node.get('layer') not in self.layers:
            return False
        if self.countries and node.get('country') not in self.countries:
            return False
        if self.node_filter and not self.node_filter(node):
            return False
        return True
```

### 2.6 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Diagram generation latency | <2 seconds p95 | From request to response |
| Concurrent generation | 50 diagrams/sec | Sustained throughput |
| Cache hit ratio | >80% | For repeated requests |
| Memory usage | <500MB per instance | Peak memory |
| Diagram size | <5MB per diagram | Output file size |
| API availability | 99.9% | Uptime SLA |

### 2.7 Integration Methodology

#### 2.7.1 API Integration

```python
# afriflow/diagrams/api/routes.py
from fastapi import APIRouter, Query, Response
from typing import Optional, List

router = APIRouter(prefix="/api/v1/diagrams", tags=["diagrams"])

@router.get("/architecture")
async def get_architecture_diagram(
    format: str = Query("svg", regex="^(svg|png|pdf|html)$"),
    include_countries: Optional[List[str]] = Query(None),
    detail_level: str = Query("high", regex="^(low|medium|high)$")
) -> Response:
    """Generate architecture diagram."""
    generator = ArchitectureDiagramGenerator()
    graph = await generator.generate(
        countries=include_countries,
        detail_level=detail_level
    )
    
    renderer = get_renderer(format)
    content = renderer.render(graph)
    
    return Response(
        content=content,
        media_type=get_media_type(format)
    )

@router.get("/lineage/{model_name}")
async def get_lineage_diagram(
    model_name: str,
    format: str = Query("svg"),
    max_depth: int = Query(5, ge=1, le=10),
    include_tests: bool = Query(False)
) -> Response:
    """Generate data lineage diagram for a specific model."""
    generator = LineageDiagramGenerator()
    graph = await generator.generate(
        model_name=model_name,
        max_depth=max_depth,
        include_tests=include_tests
    )
    
    renderer = get_renderer(format)
    content = renderer.render(graph)
    
    return Response(
        content=content,
        media_type=get_media_type(format)
    )

@router.get("/pipeline/{pipeline_name}")
async def get_pipeline_flow_diagram(
    pipeline_name: str,
    format: str = Query("svg"),
    include_metrics: bool = Query(False)
) -> Response:
    """Generate pipeline flow diagram."""
    generator = PipelineFlowDiagramGenerator()
    graph = await generator.generate(
        pipeline_name=pipeline_name,
        include_metrics=include_metrics
    )
    
    renderer = get_renderer(format)
    content = renderer.render(graph)
    
    return Response(
        content=content,
        media_type=get_media_type(format)
    )
```

#### 2.7.2 CLI Integration

```python
# afriflow/diagrams/cli.py
import typer
from pathlib import Path

app = typer.Typer(help="AfriFlow Diagram Generator")

@app.command()
def architecture(
    output: Path = typer.Option(..., "-o", "--output"),
    format: str = typer.Option("svg", "-f", "--format"),
    countries: List[str] = typer.Option(None, "-c", "--country")
):
    """Generate architecture diagram."""
    generator = ArchitectureDiagramGenerator()
    graph = asyncio.run(generator.generate(countries=countries))
    
    renderer = get_renderer(format)
    content = renderer.render(graph)
    
    output.write_bytes(content)
    typer.echo(f"Diagram written to {output}")

@app.command()
def lineage(
    model: str = typer.Argument(...),
    output: Path = typer.Option(..., "-o", "--output"),
    format: str = typer.Option("svg", "-f", "--format"),
    max_depth: int = typer.Option(5, "-d", "--depth")
):
    """Generate lineage diagram for a model."""
    generator = LineageDiagramGenerator()
    graph = asyncio.run(generator.generate(model, max_depth=max_depth))
    
    renderer = get_renderer(format)
    content = renderer.render(graph)
    
    output.write_bytes(content)
    typer.echo(f"Diagram written to {output}")

@app.command()
def export_all(
    output_dir: Path = typer.Option(..., "-o", "--output"),
    format: str = typer.Option("svg", "-f", "--format")
):
    """Export all standard diagrams."""
    exporter = BulkDiagramExporter(output_dir)
    asyncio.run(exporter.export_all(format=format))
    typer.echo(f"All diagrams exported to {output_dir}")
```

---

## 3. ML Models (NBA) Phase 2 Integration Plan

### 3.1 Overview

The Next Best Action (NBA) ML models provide intelligent recommendations for Relationship Managers by analyzing cross-domain signals, client behavior patterns, and business objectives. This section details the Phase 2 integration plan.

### 3.2 Data Requirements

#### 3.2.1 Feature Data Sources

| Category | Source | Features | Refresh Rate |
|----------|--------|----------|--------------|
| Client Profile | Gold Layer | Client segment, tenure, relationship strength | Daily |
| Transaction Behavior | Silver Layer | Transaction frequency, avg value, channel preference | Hourly |
| Product Holdings | Gold Layer | Current products, utilization, profitability | Daily |
| Cross-Domain Signals | Signal Engine | Expansion signals, risk signals, engagement score | Real-time |
| Interaction History | CRM | Last contact, channel, outcome, sentiment | Daily |
| Market Context | External | FX rates, interest rates, economic indicators | Hourly |
| Campaign History | Marketing | Past campaigns, responses, conversions | Daily |

#### 3.2.2 Feature Store Schema

```python
# afriflow/ml/features.py
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ClientFeatures:
    """Feature vector for NBA model."""
    
    # Client identity
    client_id: str
    snapshot_date: datetime
    
    # Demographic features
    segment: str  # mass, affluent, private_banking
    tenure_months: int
    country: str
    industry: str
    
    # Behavioral features
    transaction_frequency_30d: float
    transaction_frequency_90d: float
    avg_transaction_value: float
    digital_channel_ratio: float
    
    # Product features
    product_count: int
    product_utilization_score: float
    cross_sell_ratio: float
    profitability_score: float
    
    # Signal features
    expansion_signal_score: float
    risk_signal_score: float
    engagement_score: float
    
    # Interaction features
    days_since_last_contact: int
    last_interaction_outcome: str
    preferred_contact_channel: str
    
    # Contextual features
    fx_exposure: float
    interest_rate_sensitivity: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for model input."""
        return {
            "client_id": self.client_id,
            **{k: v for k, v in self.__dict__.items() if k != "client_id"}
        }

class FeaturePipeline:
    """Extract and transform features for NBA model."""
    
    def __init__(
        self,
        feature_store: FeastClient,
        delta_lake: DeltaLakeClient
    ):
        self.feature_store = feature_store
        self.delta_lake = delta_lake
    
    async def get_client_features(
        self,
        client_ids: List[str],
        snapshot_date: datetime
    ) -> List[ClientFeatures]:
        """Fetch features for batch of clients."""
        
        # Fetch from feature store
        features = await self.feature_store.get_online_features(
            features=[
                "client_profile:segment",
                "client_profile:tenure_months",
                "behavioral:transaction_frequency_30d",
                "behavioral:avg_transaction_value",
                "products:product_count",
                "signals:expansion_signal_score",
                "signals:engagement_score"
            ],
            entities={"client_id": client_ids}
        )
        
        return [
            ClientFeatures(
                client_id=client_id,
                snapshot_date=snapshot_date,
                **feature_row
            )
            for client_id, feature_row in zip(client_ids, features)
        ]
```

### 3.3 Model Training Pipeline

#### 3.3.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      NBA MODEL TRAINING PIPELINE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐                                                   │
│  │   Airflow    │  Trigger: Daily 02:00 SAST                       │
│  │   DAG        │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 1: Data Extraction                                       │  │
│  │ - Extract features from Feature Store                         │  │
│  │ - Extract labels from outcome tables                          │  │
│  │ - Apply data quality checks                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 2: Feature Engineering                                   │  │
│  │ - Handle missing values                                       │  │
│  │ - Encode categorical variables                                │  │
│  │ - Scale numerical features                                    │  │
│  │ - Create interaction features                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 3: Model Training                                        │  │
│  │ - Train LightGBM classifier                                   │  │
│  │ - Hyperparameter tuning (Optuna)                              │  │
│  │ - Cross-validation (5-fold)                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 4: Model Evaluation                                      │  │
│  │ - Calculate metrics (AUC, precision, recall, F1)              │  │
│  │ - Compare with champion model                                 │  │
│  │ - Generate explanation reports (SHAP)                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 5: Model Registration                                    │  │
│  │ - Register to MLflow                                          │  │
│  │ - Tag with version, metrics, parameters                       │  │
│  │ - If better than champion, mark as staging                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Step 6: Model Deployment (if staging)                         │  │
│  │ - Deploy to serving infrastructure                            │  │
│  │ - Canary deployment (5% traffic)                              │  │
│  │ - Monitor performance                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 Training Implementation

```python
# afriflow/ml/training/train.py
from typing import Dict, Any, Tuple
import lightgbm as lgbm
import optuna
from sklearn.model_selection import cross_val_score
import mlflow
from mlflow.tracking import MlflowClient

class NBATrainer:
    """Train Next Best Action models."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mlflow_client = MlflowClient()
    
    def train(
        self,
        train_data: pd.DataFrame,
        val_data: pd.DataFrame
    ) -> Tuple[lgbm.Booster, Dict[str, float]]:
        """Train model with hyperparameter tuning."""
        
        with mlflow.start_run(run_name="nba_training"):
            # Log parameters
            mlflow.log_params(self.config)
            
            # Hyperparameter optimization
            study = optuna.create_study(direction="maximize")
            study.optimize(
                lambda trial: self._objective(trial, train_data, val_data),
                n_trials=50,
                timeout=3600
            )
            
            best_params = study.best_params
            
            # Train final model with best parameters
            model = self._train_model(train_data, val_data, best_params)
            
            # Evaluate
            metrics = self._evaluate(model, val_data)
            
            # Log to MLflow
            mlflow.log_metrics(metrics)
            mlflow.log_params(best_params)
            mlflow.lightgbm.log_model(model, "model")
            
            return model, metrics
    
    def _objective(
        self,
        trial: optuna.Trial,
        train_data: pd.DataFrame,
        val_data: pd.DataFrame
    ) -> float:
        """Optuna objective function."""
        
        params = {
            "objective": "binary",
            "metric": "auc",
            "boosting_type": "gbdt",
            "num_leaves": trial.suggest_int("num_leaves", 20, 100),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.6, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.6, 1.0),
            "bagging_freq": trial.suggest_int("bagging_freq", 1, 10),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 100),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 1.0),
        }
        
        model = self._train_model(train_data, val_data, params)
        metrics = self._evaluate(model, val_data)
        
        return metrics["auc"]
    
    def _train_model(
        self,
        train_data: pd.DataFrame,
        val_data: pd.DataFrame,
        params: Dict[str, Any]
    ) -> lgbm.Booster:
        """Train LightGBM model."""
        
        train_dataset = lgbm.Dataset(
            train_data[self.feature_columns],
            label=train_data["label"]
        )
        val_dataset = lgbm.Dataset(
            val_data[self.feature_columns],
            label=val_data["label"],
            reference=train_dataset
        )
        
        model = lgbm.train(
            params,
            train_dataset,
            num_boost_round=1000,
            valid_sets=[val_dataset],
            early_stopping_rounds=50,
            verbose_eval=100
        )
        
        return model
    
    def _evaluate(
        self,
        model: lgbm.Booster,
        val_data: pd.DataFrame
    ) -> Dict[str, float]:
        """Evaluate model performance."""
        
        predictions = model.predict(val_data[self.feature_columns])
        
        return {
            "auc": roc_auc_score(val_data["label"], predictions),
            "precision": precision_score(val_data["label"], predictions > 0.5),
            "recall": recall_score(val_data["label"], predictions > 0.5),
            "f1": f1_score(val_data["label"], predictions > 0.5),
            "log_loss": log_loss(val_data["label"], predictions)
        }
```

### 3.4 API Specifications

#### 3.4.1 Prediction API

```python
# afriflow/ml/serving/api.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import numpy as np

app = FastAPI(title="AfriFlow NBA API", version="1.0.0")

class NBARequest(BaseModel):
    """Request schema for NBA predictions."""
    
    client_ids: List[str] = Field(
        ...,
        min_items=1,
        max_items=1000,
        description="List of client IDs to score"
    )
    
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional context (campaign_id, channel, etc.)"
    )
    
    top_n: int = Field(
        3,
        ge=1,
        le=10,
        description="Number of recommendations to return per client"
    )

class NBARecommendation(BaseModel):
    """Single NBA recommendation."""
    
    action_id: str
    action_type: str
    action_name: str
    description: str
    score: float
    confidence: float
    rationale: List[str]
    expected_value: float
    channel: str
    priority: int

class NBAResponse(BaseModel):
    """Response schema for NBA predictions."""
    
    client_id: str
    recommendations: List[NBARecommendation]
    model_version: str
    scored_at: datetime

@app.post("/api/v1/nba/predict", response_model=List[NBAResponse])
async def predict_nba(
    request: NBARequest,
    model_service: ModelService = Depends()
) -> List[NBAResponse]:
    """
    Get Next Best Action recommendations for clients.
    
    Returns personalized recommendations ranked by expected value.
    """
    try:
        recommendations = await model_service.predict(
            client_ids=request.client_ids,
            context=request.context,
            top_n=request.top_n
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/nba/actions")
async def list_actions() -> Dict[str, Any]:
    """List all available NBA actions with metadata."""
    return {
        "actions": [
            {
                "action_id": "cross_sell_forex",
                "action_type": "cross_sell",
                "action_name": "Cross-sell Forex Account",
                "description": "Recommend opening a forex trading account",
                "target_segment": ["affluent", "private_banking"],
                "channels": ["rm_call", "email", "app_notification"],
                "expected_conversion_rate": 0.15,
                "expected_value": 5000
            },
            # ... more actions
        ]
    }

@app.get("/api/v1/nba/model/info")
async def get_model_info() -> Dict[str, Any]:
    """Get current model information."""
    return {
        "model_name": "nba_classifier",
        "model_version": "2.3.1",
        "trained_at": "2026-03-16T02:00:00Z",
        "deployed_at": "2026-03-16T08:00:00Z",
        "metrics": {
            "auc": 0.847,
            "precision": 0.723,
            "recall": 0.681,
            "f1": 0.701
        },
        "feature_count": 47
    }
```

### 3.5 Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Model AUC | >0.82 | Cross-validation on holdout set |
| Precision@3 | >0.70 | Top 3 recommendations accuracy |
| Recall | >0.65 | Coverage of actual conversions |
| Inference latency (p95) | <100ms | API response time |
| Throughput | >1000 req/sec | Sustained API load |
| Model training time | <30 minutes | End-to-end pipeline |
| Feature freshness | <1 hour | Time since last update |

### 3.6 Expected ROI Metrics

| Metric | Baseline | Target | Measurement Period |
|--------|----------|--------|-------------------|
| Cross-sell conversion rate | 8% | 12% | Quarterly |
| Revenue per RM | R2.5M | R3.2M | Quarterly |
| Client engagement score | 65 | 75 | Monthly |
| Product penetration | 2.3 | 2.8 | Quarterly |
| RM productivity | 15 actions/day | 22 actions/day | Monthly |
| Campaign ROI | 3.2x | 4.5x | Quarterly |

**Projected Annual Impact:**
- Additional revenue: R45M
- RM efficiency gain: R12M
- Reduced churn: R8M
- **Total: R65M**

### 3.7 Deployment Strategy

#### 3.7.1 Step-by-Step Deployment

```yaml
# Phase 1: Infrastructure Setup (Week 1-2)
Week 1:
  - Deploy MLflow tracking server
  - Deploy Feast feature store
  - Configure model registry
  - Set up GPU compute nodes (optional)

Week 2:
  - Deploy model serving infrastructure (Seldon Core / KServe)
  - Configure API gateway
  - Set up monitoring dashboards
  - Implement CI/CD for ML pipelines

# Phase 2: Model Development (Week 3-6)
Week 3-4:
  - Historical data extraction
  - Feature engineering
  - Baseline model training
  - Initial evaluation

Week 5-6:
  - Hyperparameter optimization
  - Model explainability analysis
  - A/B test design
  - Documentation

# Phase 3: Staging Deployment (Week 7-8)
Week 7:
  - Deploy to staging environment
  - Integration testing
  - Performance testing
  - Security review

Week 8:
  - Business validation
  - RM feedback sessions
  - Model refinement
  - Go/no-go decision

# Phase 4: Production Rollout (Week 9-12)
Week 9:
  - Canary deployment (5% traffic)
  - Monitor metrics
  - Collect feedback

Week 10:
  - Expand to 25% traffic
  - Compare with baseline
  - Address issues

Week 11:
  - Expand to 50% traffic
  - Full performance validation
  - RM training completion

Week 12:
  - Full rollout (100%)
  - Decommission legacy system
  - Project closure
```

#### 3.7.2 Rollback Procedures

```python
# afriflow/ml/deployment/rollback.py
from typing import Optional
import mlflow
from kubernetes import client as k8s_client

class ModelRollbackManager:
    """Manage model rollback procedures."""
    
    def __init__(
        self,
        mlflow_tracking_uri: str,
        k8s_namespace: str
    ):
        self.mlflow_client = mlflow.tracking.MlflowClient(
            mlflow_tracking_uri
        )
        self.k8s_namespace = k8s_namespace
    
    def rollback(
        self,
        model_name: str,
        target_version: Optional[str] = None,
        reason: str = ""
    ) -> bool:
        """
        Rollback to previous model version.
        
        Args:
            model_name: Name of the model to rollback
            target_version: Specific version to rollback to (default: previous)
            reason: Reason for rollback
        
        Returns:
            True if rollback successful
        """
        # Get current model version
        current_run = self._get_current_model_run(model_name)
        
        # Determine target version
        if target_version is None:
            target_run = self._get_previous_model_run(model_name)
        else:
            target_run = self._get_model_run(model_name, target_version)
        
        if target_run is None:
            raise ValueError(f"No target version found for {model_name}")
        
        # Update model registry
        self.mlflow_client.transition_model_version_stage(
            name=model_name,
            version=target_run.info.run_id,
            stage="Production",
            archive_existing_versions=True
        )
        
        # Update Kubernetes deployment
        self._update_kubernetes_deployment(model_name, target_run)
        
        # Log rollback event
        self._log_rollback_event(current_run, target_run, reason)
        
        # Notify stakeholders
        self._notify_stakeholders(model_name, current_run, target_run, reason)
        
        return True
    
    def automatic_rollback(
        self,
        model_name: str,
        metrics_threshold: Dict[str, float]
    ) -> bool:
        """
        Perform automatic rollback if metrics degrade beyond threshold.
        
        Triggered by monitoring system.
        """
        current_metrics = self._get_current_model_metrics(model_name)
        
        for metric, threshold in metrics_threshold.items():
            if current_metrics.get(metric, 0) < threshold:
                return self.rollback(
                    model_name,
                    reason=f"Metric {metric} ({current_metrics[metric]}) "
                           f"below threshold ({threshold})"
                )
        
        return False
    
    def _update_kubernetes_deployment(
        self,
        model_name: str,
        model_run: mlflow.entities.Run
    ):
        """Update Kubernetes deployment to use target model version."""
        apps_v1 = k8s_client.AppsV1Api()
        
        deployment_name = f"{model_name}-serving"
        
        # Get current deployment
        deployment = apps_v1.read_namespaced_deployment(
            name=deployment_name,
            namespace=self.k8s_namespace
        )
        
        # Update model version in container env
        for container in deployment.spec.template.spec.containers:
            for env in container.env:
                if env.name == "MODEL_VERSION":
                    env.value = model_run.info.run_id
        
        # Apply updated deployment
        apps_v1.patch_namespaced_deployment(
            name=deployment_name,
            namespace=self.k8s_namespace,
            body=deployment
        )
```

---

## 4. Enhanced Deployment Checklist

### 4.1 Pre-Deployment Checklist

#### 4.1.1 Environment Validation Procedures

| Item | Validation Step | Command/Tool | Success Criteria | Owner |
|------|----------------|--------------|------------------|-------|
| Infrastructure | Verify Kubernetes cluster | `kubectl cluster-info` | Cluster accessible, all nodes Ready | Platform Team |
| Infrastructure | Verify namespace exists | `kubectl get namespace afriflow` | Namespace exists | Platform Team |
| Infrastructure | Verify resource quotas | `kubectl describe quota -n afriflow` | Quotas configured | Platform Team |
| Networking | Verify ingress configuration | `kubectl get ingress -n afriflow` | Ingress rules configured | Platform Team |
| Networking | Verify TLS certificates | `openssl s_client -connect <domain>:443` | Valid cert, not expiring <30 days | Security Team |
| Networking | Verify DNS resolution | `nslookup <domain>` | Correct IP resolution | Platform Team |
| Storage | Verify PVC availability | `kubectl get pvc -n afriflow` | All PVCs Bound | Platform Team |
| Storage | Verify database connectivity | `psql -h <host> -U <user> -d afriflow` | Connection successful | DBA Team |
| Storage | Verify Kafka connectivity | `kafka-topics --bootstrap-server <broker> --list` | Topics listed | Platform Team |
| Secrets | Verify secrets exist | `kubectl get secrets -n afriflow` | All required secrets present | Security Team |
| Secrets | Verify secret rotation | Check secret creation timestamps | No secrets >90 days old | Security Team |
| Compute | Verify node capacity | `kubectl top nodes` | CPU <70%, Memory <80% | Platform Team |
| Compute | Verify HPA configuration | `kubectl get hpa -n afriflow` | HPA configured for all services | Platform Team |

#### 4.1.2 Database Migration Scripts with Rollback Plans

```sql
-- afriflow/migrations/V2026.03.17__initial_schema.sql
-- Migration: Initial AfriFlow Schema
-- Author: DBA Team
-- Date: 2026-03-17

-- Start transaction
BEGIN;

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create client profiles table
CREATE TABLE IF NOT EXISTS client_profiles (
    client_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    id_number VARCHAR(20) UNIQUE,
    date_of_birth DATE,
    country_code CHAR(2) NOT NULL,
    segment VARCHAR(50) NOT NULL,
    onboarded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for segment queries
CREATE INDEX idx_client_profiles_segment ON client_profiles(segment);
CREATE INDEX idx_client_profiles_country ON client_profiles(country_code);

-- Create product holdings table
CREATE TABLE IF NOT EXISTS product_holdings (
    holding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES client_profiles(client_id),
    product_type VARCHAR(50) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    opened_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_product_holdings_client ON product_holdings(client_id);
CREATE INDEX idx_product_holdings_type ON product_holdings(product_type);

-- Create signal events table
CREATE TABLE IF NOT EXISTS signal_events (
    signal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES client_profiles(client_id),
    signal_type VARCHAR(50) NOT NULL,
    signal_subtype VARCHAR(50),
    score DECIMAL(5,4) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100),
    outcome VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signal_events_client ON signal_events(client_id);
CREATE INDEX idx_signal_events_type ON signal_events(signal_type);
CREATE INDEX idx_signal_events_detected ON signal_events(detected_at);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_table ON audit_log(table_name);
CREATE INDEX idx_audit_log_record ON audit_log(record_id);

-- Create function for updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_client_profiles_updated_at
    BEFORE UPDATE ON client_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO afriflow_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO afriflow_app;

-- Commit transaction
COMMIT;

-- ROLLBACK SCRIPT
-- afriflow/migrations/V2026.03.17__ROLLBACK.sql

BEGIN;

-- Drop triggers
DROP TRIGGER IF EXISTS update_client_profiles_updated_at ON client_profiles;

-- Drop function
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS signal_events CASCADE;
DROP TABLE IF EXISTS product_holdings CASCADE;
DROP TABLE IF EXISTS client_profiles CASCADE;

-- Drop extension
DROP EXTENSION IF EXISTS "uuid-ossp";

COMMIT;
```

#### 4.1.3 API Endpoint Testing Protocols

| Endpoint | Test Type | Request | Expected Response | Success Criteria |
|----------|-----------|---------|-------------------|------------------|
| `/health` | Health Check | GET | 200 OK, `{"status": "healthy"}` | Response time <100ms |
| `/api/v1/clients/{id}` | Functional | GET | 200 OK, client data | Valid JSON schema |
| `/api/v1/clients/{id}` | Not Found | GET (invalid ID) | 404 Not Found | Error message present |
| `/api/v1/signals` | Functional | POST | 201 Created, signal ID | Signal persisted |
| `/api/v1/signals` | Validation | POST (invalid data) | 400 Bad Request | Validation errors returned |
| `/api/v1/nba/predict` | Functional | POST | 200 OK, recommendations | Recommendations valid |
| `/api/v1/nba/predict` | Load | POST (1000 concurrent) | 200 OK, p95 <500ms | Error rate <1% |
| `/api/v1/nba/predict` | Auth | POST (no token) | 401 Unauthorized | Auth error returned |

```python
# afriflow/tests/deployment/test_api_endpoints.py
import pytest
import httpx
from typing import Dict, Any

class TestAPIEndpoints:
    
    BASE_URL = "https://api.afriflow.example.com"
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.get_test_token()}"}
    
    def test_health_endpoint(self):
        """Verify health endpoint returns healthy status."""
        response = httpx.get(f"{self.BASE_URL}/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.elapsed.total_seconds() < 0.1
    
    def test_client_endpoint_authenticated(
        self, auth_headers: Dict[str, str]
    ):
        """Verify client endpoint with valid auth."""
        response = httpx.get(
            f"{self.BASE_URL}/api/v1/clients/test-client-id",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "client_id" in response.json()
        assert "segment" in response.json()
    
    def test_client_endpoint_unauthenticated(self):
        """Verify client endpoint rejects unauthenticated requests."""
        response = httpx.get(
            f"{self.BASE_URL}/api/v1/clients/test-client-id"
        )
        
        assert response.status_code == 401
    
    @pytest.mark.load_test
    async def test_nba_predict_load(self, auth_headers: Dict[str, str]):
        """Verify NBA endpoint under load."""
        async with httpx.AsyncClient() as client:
            tasks = [
                client.post(
                    f"{self.BASE_URL}/api/v1/nba/predict",
                    json={"client_ids": [f"client-{i}" for i in range(10)]},
                    headers=auth_headers
                )
                for _ in range(100)
            ]
            
            responses = await asyncio.gather(*tasks)
            
            success_count = sum(
                1 for r in responses if r.status_code == 200
            )
            assert success_count >= 95  # 95% success rate
```

#### 4.1.4 Load Testing Thresholds

| Scenario | Concurrent Users | Target RPS | Max Latency (p95) | Max Error Rate |
|----------|-----------------|------------|-------------------|----------------|
| Normal Load | 100 | 500 | 200ms | 0.1% |
| Peak Load | 500 | 2000 | 500ms | 0.5% |
| Stress Test | 1000 | 4000 | 1000ms | 1.0% |
| Breakpoint | 2000+ | Until failure | - | Until >5% |

```yaml
# afriflow/tests/load/locustfile.py
from locust import HttpUser, task, between
import json

class AfriFlowLoadTest(HttpUser):
    wait_time = between(0.5, 2)
    
    @task(5)
    def get_client(self):
        self.client.get("/api/v1/clients/test-client-id")
    
    @task(3)
    def get_signals(self):
        self.client.get("/api/v1/signals?client_id=test-client-id")
    
    @task(2)
    def predict_nba(self):
        self.client.post(
            "/api/v1/nba/predict",
            json={"client_ids": ["test-client-id"]},
            headers=self.auth_headers
        )
    
    @task(1)
    def create_signal(self):
        self.client.post(
            "/api/v1/signals",
            json={
                "client_id": "test-client-id",
                "signal_type": "expansion",
                "score": 0.85
            },
            headers=self.auth_headers
        )
```

#### 4.1.5 Security Vulnerability Scanning Requirements

| Scan Type | Tool | Frequency | Threshold | Owner |
|-----------|------|-----------|-----------|-------|
| Dependency Scan | Snyk / Dependabot | Daily | No critical/high vulnerabilities | Security Team |
| Container Scan | Trivy / Clair | Each build | No critical vulnerabilities | Platform Team |
| SAST | SonarQube / Semgrep | Each commit | No critical/high issues | Dev Team |
| DAST | OWASP ZAP / Burp | Weekly | No critical/high issues | Security Team |
| IaC Scan | Checkov / Terrascan | Each commit | No high severity issues | Platform Team |
| Secret Scan | GitLeaks / TruffleHog | Each commit | No secrets detected | Dev Team |

```yaml
# .github/workflows/security-scan.yml
name: Security Scanning

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Snyk
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
  
  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build image
        run: docker build -t afriflow:latest .
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'afriflow:latest'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
  
  sast-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/owasp-top-ten
```

#### 4.1.6 Configuration Management Steps

| Step | Action | Validation | Rollback |
|------|--------|------------|----------|
| 1 | Export current config | `kubectl get configmap -n afriflow -o yaml > backup.yaml` | Apply backup YAML |
| 2 | Update ConfigMap | `kubectl apply -f new-config.yaml` | Reapply previous version |
| 3 | Validate config syntax | Run config validation script | N/A |
| 4 | Rolling restart | `kubectl rollout restart deployment` | `kubectl rollout undo` |
| 5 | Verify application health | Health check endpoints | Trigger rollback |
| 6 | Update documentation | Config registry | Restore previous docs |

### 4.2 Deployment Checklist

#### 4.2.1 Stakeholder Notification Procedures

| Phase | Stakeholders | Method | Timing | Content |
|-------|-------------|--------|--------|---------|
| T-7 Days | All stakeholders | Email | 7 days before | Deployment schedule, expected impact |
| T-3 Days | Business users | Email + Teams | 3 days before | Feature summary, training reminder |
| T-1 Day | Operations team | Teams channel | 1 day before | Final checklist, runbook review |
| T-1 Hour | All stakeholders | Teams broadcast | 1 hour before | Deployment starting, status page link |
| T-0 | Operations team | War room | Deployment start | Go confirmation |
| T+30 min | Stakeholders | Teams broadcast | 30 min after | Initial status (success/issues) |
| T+2 Hours | All stakeholders | Email | 2 hours after | Deployment summary, known issues |
| T+24 Hours | Business users | Email | Next day | Usage instructions, support contacts |

#### 4.2.2 Go-Live Criteria with Measurable Success Factors

| Criterion | Metric | Target | Measurement Method |
|-----------|--------|--------|-------------------|
| System Health | Pod readiness | 100% pods Ready | Kubernetes |
| System Health | Error rate | <0.1% | Monitoring dashboard |
| System Health | Latency (p95) | <500ms | APM tool |
| Data Quality | Pipeline success rate | >99% | Airflow DAG runs |
| Data Quality | Schema compliance | 100% | Schema Registry |
| Data Quality | Data freshness | <1 hour lag | Freshness monitor |
| Performance | API throughput | >500 RPS | Load test results |
| Performance | Database connections | <80% capacity | DB monitoring |
| Security | Vulnerability scan | No critical/high | Security scan results |
| Business | Smoke tests | 100% pass | Manual test suite |
| Business | User acceptance | Sign-off received | UAT completion |

### 4.3 Emergency Response Protocols

#### 4.3.1 Escalation Paths

```
Level 1: On-Call Engineer
├── Response Time: 15 minutes
├── Authority: Restart services, rollback deployments
├── Contact: +27-XXX-XXX-XXXX (PagerDuty)
└── Escalate to: Level 2 if not resolved in 30 minutes

Level 2: Team Lead / Senior Engineer
├── Response Time: 30 minutes
├── Authority: Full rollback, infrastructure changes
├── Contact: +27-XXX-XXX-XXXX (PagerDuty)
└── Escalate to: Level 3 if not resolved in 1 hour

Level 3: Platform Manager / Director
├── Response Time: 1 hour
├── Authority: Business communication, external escalation
├── Contact: +27-XXX-XXX-XXXX (Phone)
└── Escalate to: Executive team if business impact

Level 4: Executive Team
├── Response Time: 2 hours
├── Authority: Strategic decisions, external communication
└── Contact: Executive escalation list
```

#### 4.3.2 Incident Response Procedures

| Incident Type | Detection | Immediate Response | Escalation | Recovery |
|--------------|-----------|-------------------|------------|----------|
| Service Outage | Health check failure | Restart pods, check logs | Level 2 if >15 min | Rollback if needed |
| Data Corruption | DQ alert, user report | Stop pipelines, assess scope | Level 2 immediately | Restore from backup |
| Security Breach | Security alert, anomaly | Isolate affected systems | Level 3 immediately | Security team lead |
| Performance Degradation | Latency alert | Scale up, check resources | Level 2 if >30 min | Optimize/rollback |
| Integration Failure | Pipeline failure | Check external systems | Level 2 if >1 hour | Coordinate with vendor |

---

## 5. Post-Deployment Monitoring and Feedback Framework

### 5.1 KPIs and SLAs for System Performance

#### 5.1.1 Key Performance Indicators

| Category | KPI | Target | Measurement Frequency | Owner |
|----------|-----|--------|----------------------|-------|
| Availability | System uptime | 99.9% | Daily | Platform Team |
| Availability | API availability | 99.95% | Hourly | Platform Team |
| Performance | API latency (p95) | <500ms | Real-time | Platform Team |
| Performance | API latency (p99) | <1000ms | Real-time | Platform Team |
| Performance | Throughput | >1000 RPS | Real-time | Platform Team |
| Data | Pipeline success rate | >99% | Per run | Data Engineering |
| Data | Data freshness | <1 hour | Hourly | Data Engineering |
| Data | Data quality score | >95% | Daily | Data Engineering |
| Business | Signal detection accuracy | >90% | Weekly | Analytics Team |
| Business | False positive rate | <10% | Weekly | Analytics Team |
| Business | RM adoption rate | >50% | Monthly | Business Team |
| Business | Revenue attribution | Trackable | Monthly | Finance Team |

#### 5.1.2 Service Level Agreements

| Service | SLA | Remedy |
|---------|-----|--------|
| API Availability | 99.9% monthly | Service credit for downtime |
| Data Freshness | <2 hours lag | Priority investigation |
| Incident Response | 15 minutes (P1) | Escalation review |
| Bug Resolution | 4 hours (P1), 24 hours (P2) | Sprint priority |
| Support Response | 4 business hours | SLA tracking |

### 5.2 Real-Time Monitoring Dashboards Requirements

#### 5.2.1 Dashboard Specifications

| Dashboard | Audience | Refresh Rate | Key Metrics |
|-----------|----------|--------------|-------------|
| System Health | Operations | Real-time (5s) | Pod status, CPU/Memory, Error rates |
| Pipeline Health | Data Engineering | 1 minute | DAG status, lag, throughput |
| Data Quality | Data Stewardship | 5 minutes | DQ scores, anomalies, trends |
| Business Metrics | Business Users | 15 minutes | Signals, conversions, revenue |
| Executive Summary | Leadership | Hourly | KPI summary, alerts, trends |

#### 5.2.2 Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "AfriFlow System Health",
    "refresh": "5s",
    "panels": [
      {
        "title": "Pod Status",
        "type": "stat",
        "targets": [
          {
            "expr": "kube_pod_status_phase{namespace=\"afriflow\", phase=\"Running\"}",
            "legendFormat": "{{pod}}"
          }
        ],
        "thresholds": [
          {"value": 0, "color": "red"},
          {"value": 1, "color": "green"}
        ]
      },
      {
        "title": "API Latency (p95)",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job=\"afriflow-api\"}[5m]))",
            "legendFormat": "p95"
          }
        ],
        "thresholds": [
          {"value": 0.5, "color": "yellow"},
          {"value": 1.0, "color": "red"}
        ]
      },
      {
        "title": "Error Rate",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(http_requests_total{job=\"afriflow-api\", status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ],
        "thresholds": [
          {"value": 0.01, "color": "yellow"},
          {"value": 0.05, "color": "red"}
        ]
      }
    ]
  }
}
```

### 5.3 Alerting Thresholds and Notification Mechanisms

#### 5.3.1 Alert Configuration

| Alert | Condition | Severity | Notification | Escalation |
|-------|-----------|----------|--------------|------------|
| Service Down | Pod not Ready >2 min | P1 | PagerDuty + SMS | 15 min |
| High Error Rate | >1% for 5 min | P1 | PagerDuty + SMS | 15 min |
| High Latency | p95 >1s for 10 min | P2 | PagerDuty | 30 min |
| Pipeline Failure | DAG failed | P2 | Email + Teams | 1 hour |
| Data Staleness | No data >2 hours | P2 | Email + Teams | 1 hour |
| Low DQ Score | <90% for any domain | P3 | Email | 4 hours |
| Disk Usage | >80% | P3 | Email | 4 hours |
| Certificate Expiry | <30 days | P3 | Email | 1 day |

#### 5.3.2 Alertmanager Configuration

```yaml
# alertmanager/config.yml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@afriflow.example.com'

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
    - match:
        severity: warning
      receiver: 'teams-warnings'

receivers:
  - name: 'default'
    email_configs:
      - to: 'platform-team@example.com'
        send_resolved: true

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '<pagerduty-service-key>'
        severity: critical
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'

  - name: 'teams-warnings'
    webhook_configs:
      - url: '<teams-webhook-url>'
        send_resolved: true
```

### 5.4 User Adoption Metrics Tracking Methodology

| Metric | Definition | Target | Collection Method |
|--------|------------|--------|-------------------|
| Daily Active Users | Unique users per day | >60% of RMs | Authentication logs |
| Weekly Active Users | Unique users per week | >80% of RMs | Authentication logs |
| Feature Usage | Actions per feature | Track all | Event tracking |
| Session Duration | Average session length | >10 minutes | Session analytics |
| Return Rate | Users returning next day | >70% | Cohort analysis |
| Task Completion | Successful workflows | >90% | Funnel analysis |
| Support Tickets | Tickets per 100 users | <5 | Support system |

### 5.5 Feedback Collection Tools and Processes

#### 5.5.1 Feedback Channels

| Channel | Purpose | Frequency | Owner |
|---------|---------|-----------|-------|
| In-App Feedback | Quick ratings, comments | Continuous | Product Team |
| User Surveys | Detailed feedback | Monthly | Product Team |
| RM Focus Groups | Deep dive sessions | Quarterly | Business Team |
| Support Tickets | Issue tracking | Continuous | Support Team |
| Usage Analytics | Behavioral insights | Continuous | Analytics Team |

#### 5.5.2 Feedback Processing Pipeline

```
User Feedback
      │
      ▼
┌─────────────────┐
│ Collection      │
│ - In-app form   │
│ - Survey        │
│ - Support ticket│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Categorization  │
│ - Bug           │
│ - Enhancement   │
│ - Question      │
│ - Praise        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Prioritization  │
│ - Impact score  │
│ - Effort score  │
│ - RICE framework│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Assignment      │
│ - Sprint backlog│
│ - Backlog       │
│ - Knowledge base│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Resolution      │
│ - Fix           │
│ - Build         │
│ - Respond       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Follow-up       │
│ - User notified │
│ - Satisfaction  │
│ - Closed loop   │
└─────────────────┘
```

### 5.6 Performance Benchmarking Criteria

| Benchmark | Baseline | Target | Stretch | Measurement |
|-----------|----------|--------|---------|-------------|
| API Latency (p95) | 500ms | 300ms | 200ms | Monthly load test |
| Throughput | 1000 RPS | 2000 RPS | 5000 RPS | Monthly load test |
| Pipeline Duration | 30 min | 20 min | 15 min | Weekly analysis |
| Data Freshness | 1 hour | 30 min | 15 min | Continuous |
| Model Accuracy | 82% AUC | 85% AUC | 88% AUC | Per model version |

### 5.7 Incident Response Procedures

#### 5.7.1 Incident Severity Classification

| Severity | Definition | Response Time | Resolution Time | Communication |
|----------|------------|---------------|-----------------|---------------|
| P1 - Critical | Complete outage, data loss | 15 minutes | 4 hours | Executive + All stakeholders |
| P2 - High | Major degradation, no workaround | 30 minutes | 8 hours | Management + Affected users |
| P3 - Medium | Partial degradation, workaround exists | 2 hours | 24 hours | Affected users |
| P4 - Low | Minor issue, no user impact | 4 hours | 1 week | Internal team |

#### 5.7.2 Incident Response Workflow

```
Incident Detected
       │
       ▼
┌──────────────┐
│ Triage       │
│ - Severity   │
│ - Impact     │
│ - Scope      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Mobilize     │
│ - On-call    │
│ - Subject    │
│   experts    │
│ - War room   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Diagnose     │
│ - Logs       │
│ - Metrics    │
│ - Traces     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Mitigate     │
│ - Workaround │
│ - Rollback   │
│ - Fix        │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Resolve      │
│ - Verify     │
│ - Monitor    │
│ - Close      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Post-Mortem  │
│ - Timeline   │
│ - Root cause │
│ - Actions    │
└──────────────┘
```

### 5.8 Continuous Improvement Loop

#### 5.8.1 Monthly Review Cycle

| Week | Activity | Participants | Output |
|------|----------|--------------|--------|
| Week 1 | Metrics review | Platform Team, Analytics | Performance report |
| Week 2 | User feedback review | Product Team, Business | Feedback summary |
| Week 3 | Incident review | All teams | Post-mortem actions |
| Week 4 | Planning | Leadership, Team Leads | Next month priorities |

#### 5.8.2 Improvement Tracking

| Metric | Current | Target | Owner | Due Date |
|--------|---------|--------|-------|----------|
| System uptime | 99.85% | 99.9% | Platform Team | 2026-04-30 |
| API latency | 450ms | 300ms | Platform Team | 2026-04-30 |
| Pipeline success | 98.5% | 99.5% | Data Engineering | 2026-04-30 |
| User satisfaction | 4.2/5 | 4.5/5 | Product Team | 2026-04-30 |

---

## 6. Risk Mitigation Strategies

### 6.1 Entity Resolution Errors

| Aspect | Details |
|--------|---------|
| **Detection Mechanisms** | - Precision/recall monitoring dashboard<br>- Manual review queue sampling<br>- Cross-domain inconsistency alerts<br>- Client complaint tracking |
| **Immediate Response** | 1. Flag affected records<br>2. Queue for manual review<br>3. Notify data steward<br>4. Log incident |
| **Long-Term Prevention** | - Continuous model retraining<br>- Feature engineering improvements<br>- Human-in-the-loop verification<br>- Regular accuracy audits |
| **Contingency Plan** | Activate manual review queue for all new matches. Revert to previous model version if accuracy drops >5%. |
| **Activation Criteria** | Precision <85% OR Recall <80% OR False merge rate >2% |
| **Responsible Team** | Data Engineering + Data Stewardship |
| **Communication Protocol** | Alert data steward immediately. Notify business users if impact >100 clients. |
| **Recovery Time Objective** | 4 hours for detection, 24 hours for resolution |
| **Post-Incident Analysis** | Root cause analysis within 48 hours. Model retraining plan within 1 week. |

### 6.2 Data Quality Issues

| Aspect | Details |
|--------|---------|
| **Detection Mechanisms** | - Great Expectations validation at ingestion<br>- Statistical anomaly detection<br>- Schema compliance checks<br>- Freshness monitoring |
| **Immediate Response** | 1. Circuit breaker activation<br>2. Route to quarantine table<br>3. Alert data engineering<br>4. Notify source system |
| **Long-Term Prevention** | - Source system validation improvements<br>- Data contract enforcement<br>- Automated DQ rule generation<br>- Regular DQ audits |
| **Contingency Plan** | Use last-known-good data with staleness indicator. Switch to backup data source if available. |
| **Activation Criteria** | DQ score <90% OR Missing data >20% OR Schema violations detected |
| **Responsible Team** | Data Engineering + Domain Data Owners |
| **Communication Protocol** | Alert data engineering on-call. Notify domain owners within 1 hour. |
| **Recovery Time Objective** | 2 hours for detection, 8 hours for resolution |
| **Post-Incident Analysis** | DQ incident report within 24 hours. Prevention plan within 1 week. |

### 6.3 System Downtime

| Aspect | Details |
|--------|---------|
| **Detection Mechanisms** | - Health check endpoints<br>- Synthetic monitoring<br>- Kubernetes pod status<br>- External uptime monitoring |
| **Immediate Response** | 1. Page on-call engineer<br>2. Check pod status and logs<br>3. Attempt pod restart<br>4. Escalate if not resolved |
| **Long-Term Prevention** | - Multi-AZ deployment<br>- Auto-scaling configuration<br>- Resource quota management<br>- Regular chaos engineering |
| **Contingency Plan** | Failover to DR environment. Enable read-only mode with cached data. |
| **Activation Criteria** | Service unavailable >2 minutes OR Error rate >50% |
| **Responsible Team** | Platform Operations + SRE |
| **Communication Protocol** | PagerDuty alert to on-call. Status page update within 15 minutes. Stakeholder notification for P1. |
| **Recovery Time Objective** | 15 minutes for detection, 1 hour for resolution |
| **Post-Incident Analysis** | Post-mortem within 48 hours. Action items tracked to completion. |

### 6.4 Performance Degradation

| Aspect | Details |
|--------|---------|
| **Detection Mechanisms** | - Latency monitoring (p95, p99)<br>- Throughput tracking<br>- Resource utilization alerts<br>- Slow query logging |
| **Immediate Response** | 1. Scale up resources<br>2. Identify bottleneck<br>3. Kill long-running queries<br>4. Enable caching |
| **Long-Term Prevention** | - Query optimization<br>- Index tuning<br>- Connection pooling<br>- Regular load testing |
| **Contingency Plan** | Enable request throttling. Disable non-critical features. Switch to degraded mode. |
| **Activation Criteria** | p95 latency >1s for 10 min OR Throughput <50% of baseline |
| **Responsible Team** | Platform Engineering + Database Team |
| **Communication Protocol** | Alert platform team. Notify business if impact >30 minutes. |
| **Recovery Time Objective** | 10 minutes for detection, 2 hours for resolution |
| **Post-Incident Analysis** | Performance analysis report. Optimization plan within 1 week. |

### 6.5 Security Breaches

| Aspect | Details |
|--------|---------|
| **Detection Mechanisms** | - SIEM integration<br>- Anomaly detection<br>- Access log monitoring<br>- Vulnerability scanning |
| **Immediate Response** | 1. Isolate affected systems<br>2. Revoke compromised credentials<br>3. Preserve evidence<br>4. Engage security team |
| **Long-Term Prevention** | - Regular penetration testing<br>- Security training<br>- Zero-trust architecture<br>- Continuous vulnerability scanning |
| **Contingency Plan** | Activate incident response plan. Engage external security consultants if needed. |
| **Activation Criteria** | Confirmed unauthorized access OR Data exfiltration detected OR Critical vulnerability exploited |
| **Responsible Team** | Security Team + Legal + Compliance |
| **Communication Protocol** | Immediate escalation to CISO. Legal review before external communication. Regulatory notification if required. |
| **Recovery Time Objective** | Immediate detection, 4 hours for containment |
| **Post-Incident Analysis** | Full forensic analysis. Security enhancement plan. Regulatory reporting if required. |

### 6.6 Integration Failures

| Aspect | Details |
|--------|---------|
| **Detection Mechanisms** | - Pipeline failure alerts<br>- Data freshness monitoring<br>- Consumer lag tracking<br>- External API health checks |
| **Immediate Response** | 1. Check external system status<br>2. Review error logs<br>3. Retry failed batches<br>4. Engage vendor support |
| **Long-Term Prevention** | - Contract testing<br>- Version compatibility checks<br>- Fallback mechanisms<br>- Regular integration testing |
| **Contingency Plan** | Use cached data. Switch to manual ingestion. Enable offline mode. |
| **Activation Criteria** | Pipeline failure >1 hour OR Data lag >4 hours OR External API unavailable |
| **Responsible Team** | Integration Team + Vendor Management |
| **Communication Protocol** | Alert integration team. Notify vendor. Business notification if impact >4 hours. |
| **Recovery Time Objective** | 30 minutes for detection, 4 hours for resolution |
| **Post-Incident Analysis** | Integration incident report. Vendor review. Prevention plan. |

---

## Appendix A: Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-17 | Technical Architecture Team | Initial release |

## Appendix B: Related Documents

- [PRODUCTION_READINESS.md](../PRODUCTION_READINESS.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [FEDERATED_ARCHITECTURE.md](FEDERATED_ARCHITECTURE.md)
- [SECURITY_REVIEW_CHECKLIST.md](../docs/security/SECURITY_REVIEW_CHECKLIST.md)

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| NBA | Next Best Action |
| DQ | Data Quality |
| RPO | Recovery Point Objective |
| RTO | Recovery Time Objective |
| SRE | Site Reliability Engineering |
| SIEM | Security Information and Event Management |

---

*Document End*
