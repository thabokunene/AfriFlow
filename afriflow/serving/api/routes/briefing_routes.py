"""
Briefing Routes — pre-meeting RM briefing endpoint.

The briefing endpoint is the most latency-sensitive in the API.
It is called when the RM opens their mobile app 30 minutes before
a client meeting. Target P99 latency: < 800ms.

Cache strategy: briefings are pre-computed nightly via the
daily_unified_golden_record DAG and served from the feature store.
On-demand refresh is supported but incurs full pipeline cost.
"""

from afriflow.serving.api.app import BriefingRoutes

__all__ = ["BriefingRoutes"]
