# Talking Points Engine

Generates concise talking points from multi-format inputs for client briefings.

## Usage

```python
from afriflow.integration.client_briefing.talking_points_engine import TalkingPointsEngine, TalkingPointsConfig

cfg = TalkingPointsConfig(
    max_topics=8,
    max_points=5,
    timeout_seconds=2.0,
    output_format="json",
)
engine = TalkingPointsEngine(cfg)

result = engine.process("Expansion in Kenya with forex risk and working capital needs")
print(result)  # JSON with points and quality metrics
```

### Supported Inputs
- Plain text string
- JSON file path containing `text` or `texts`
- CSV file path with a `text` column

### Output Formats
- `json`: `{"points": [{"text": "...", "relevance": ..., "conciseness": ..., "uniqueness": ...}] }`
- `markdown`: bullet list with inline metrics
- `text`: numbered lines

## Quality Metrics
- Relevance: topic appears in input tokens
- Conciseness: word count below configured threshold
- Uniqueness: no duplicate points

## Configuration
- `model_path`: optional model artifact path
- `timeout_seconds`: processing time budget
- `simulate_latency_ms`: artificial delay for testing
- Logging: path, level, rotating file settings

## Batch Processing

```python
outs = engine.batch_process([{"text": "Topic one"}, {"text": "Topic two"}], output_format="markdown")
```

## Error Handling
- `ModelLoadError` for model loading failures
- `EmptyInputError` for missing/empty inputs
- `ProcessingTimeoutError` for exceeded time budget

## Notes
- No secrets in inputs; sanitize notebooks and scripts upstream
- Keep output format aligned with consumer expectations
