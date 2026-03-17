from datetime import timezone

from afriflow.domains.cib.processing.flink.flow_drift_detector import FlowDriftDetector


def test_detect_drift_timestamp_timezone_aware():
    det = FlowDriftDetector(threshold_percentage=0.0, window_size=4)
    # Add 4 observations to ensure detection path runs
    for v in (100.0, 100.0, 150.0, 150.0):
        det.add_observation("CLIENT-1", "ZA-NG", v)
    alert = det.detect_drift("CLIENT-1", "ZA-NG")
    assert alert is not None
    assert alert.detected_at.tzinfo is not None
    assert alert.detected_at.tzinfo == timezone.utc
