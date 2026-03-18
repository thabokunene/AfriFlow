"""
@file talking_points_engine.py
@description Lexical talking-points engine for AfriFlow client briefings.

             Given raw text (or a list of texts, a JSON file, or a CSV file),
             the engine extracts the most frequent non-stop-word topics and
             converts each into a concise, deduplicated talking point.  Quality
             is measured along three dimensions — relevance, conciseness, and
             uniqueness — and only points that pass all three thresholds are
             emitted.

             Output can be rendered as structured JSON (default), Markdown, or
             plain numbered text.

             DISCLAIMER: This project is not sanctioned by, affiliated with, or
             endorsed by Standard Bank Group, MTN Group, or any of their
             subsidiaries. It is a demonstration of concept, domain knowledge,
             and technical skill built by Thabo Kunene for portfolio and
             learning purposes only.
@author Thabo Kunene
@created 2026-03-18
"""

# Python 3.10+ union-type annotations without importing Union explicitly
from __future__ import annotations

# Standard-library imports
import csv                              # For reading CSV input files
import json                             # For reading JSON input files
import logging                          # Structured logging throughout the engine
import os                               # File-existence checks and path operations
import re                               # Tokenisation via regex word extraction
import time                             # Latency simulation and timeout enforcement
from collections import Counter         # Frequency counting for topic extraction
from dataclasses import dataclass       # Lightweight config and result containers
from functools import lru_cache         # Cache repeated extract_key_topics calls
from logging.handlers import RotatingFileHandler  # File-based log rotation
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Custom exceptions — raised instead of bare Exception for precise handling
# ---------------------------------------------------------------------------

class ModelLoadError(Exception):
    """Raised when the NLP model fails to load."""


class EmptyInputError(Exception):
    """Raised when input text is empty or missing."""


class ProcessingTimeoutError(Exception):
    """Raised when processing exceeds the configured timeout."""


# ---------------------------------------------------------------------------
# Configuration dataclass — all engine tunables in one place
# ---------------------------------------------------------------------------

@dataclass
class TalkingPointsConfig:
    """Configuration for TalkingPointsEngine."""

    # Path to an external NLP model; None means use the built-in lexical model
    model_path: Optional[str] = None
    # Maximum number of distinct topics to extract per input text
    max_topics: int = 8
    # Maximum number of talking points to emit per input text
    max_points: int = 6
    # Maximum word count for a single talking point (conciseness threshold)
    max_point_words: int = 24
    # Hard wall on total processing time in seconds
    timeout_seconds: float = 2.0
    # Optional path for a rotating log file; None means console-only
    log_path: Optional[str] = None
    # Python logging level (e.g. logging.INFO)
    log_level: int = logging.INFO
    # Maximum log file size before rotation kicks in
    log_max_bytes: int = 512_000
    # Number of rotated log files to retain
    log_backup_count: int = 3
    # Default output format: "json" | "markdown" | "text"
    output_format: str = "json"
    # Optional artificial latency in milliseconds (useful for load testing)
    simulate_latency_ms: int = 0
    # Minimum uniqueness score (0–1) a candidate point must reach
    min_uniqueness_ratio: float = 0.6
    # Minimum relevance score (0–1) a candidate point must reach
    min_relevance_ratio: float = 0.5


# ---------------------------------------------------------------------------
# Result dataclass — one per emitted talking point
# ---------------------------------------------------------------------------

@dataclass
class TalkingPoint:
    """A single talking point with quality metrics."""

    # The generated talking-point string
    text: str
    # How well the point relates to the dominant topics (0–1)
    relevance: float
    # Inverse of word count relative to max_point_words (0–1)
    conciseness: float
    # How distinct this point is from all previously emitted points (0–1)
    uniqueness: float


# ---------------------------------------------------------------------------
# Engine class
# ---------------------------------------------------------------------------

class TalkingPointsEngine:
    """Generates concise, high-quality talking points from input text."""

    def __init__(self, config: Optional[TalkingPointsConfig] = None) -> None:
        """
        Initialise the engine with optional configuration.

        :param config: TalkingPointsConfig instance; defaults to sensible
                       production values if not provided
        """
        # Fall back to defaults if no config is supplied
        self.config = config or TalkingPointsConfig()
        # Set up the logger first so model-load errors can be recorded
        self.logger = self._setup_logger()
        # Load (or mock-load) the NLP model
        self.model = self._load_model(self.config.model_path)

    def _setup_logger(self) -> logging.Logger:
        """
        Configure and return a module-scoped logger.

        If log_path is set in config, a RotatingFileHandler is attached;
        otherwise logging falls through to the root handler (usually stdout).

        :return: Configured logging.Logger instance
        """
        logger = logging.getLogger("afriflow.integration.talking_points_engine")
        logger.setLevel(self.config.log_level)
        if self.config.log_path:
            # Use rotating handler to avoid unbounded log file growth
            handler = RotatingFileHandler(
                self.config.log_path,
                maxBytes=self.config.log_max_bytes,
                backupCount=self.config.log_backup_count,
            )
            fmt = logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
            handler.setFormatter(fmt)
            # Guard against adding the same handler twice during hot-reload
            if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
                logger.addHandler(handler)
        return logger

    def _load_model(self, path: Optional[str]) -> Any:
        """
        Load the NLP model from disk, or return a lexical stub.

        In this implementation the "model" is a simple lexical frequency
        analyser. A future version can swap in a real embedding model by
        pointing model_path at its artefact directory.

        :param path: Filesystem path to the model artefact, or None
        :return: A model descriptor dict
        :raises ModelLoadError: If path is provided but does not exist
        """
        start = time.time()
        try:
            if path:
                # Validate the path before attempting to load
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Model path not found: {path}")
            # Return a lightweight descriptor; real models would be loaded here
            return {"name": "lexical", "version": "1.0"}
        except Exception as e:
            self.logger.error("Model load failure: %s", e)
            raise ModelLoadError(str(e))
        finally:
            # Always log load duration for performance monitoring
            self.logger.debug("Model load took %.3fs", time.time() - start)

    def process(
        self,
        input_data: Union[str, Dict[str, Any], List[str]],
        output_format: Optional[str] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Process input and generate formatted talking points.

        :param input_data: Raw input — a plain string, a dict with "text" or
                           "texts" keys, a list of strings, or a file path
                           ending in .json / .csv
        :param output_format: Override config.output_format for this call only
        :return: Formatted output (dict for "json", str for "markdown"/"text")
        :raises EmptyInputError: If no usable text can be extracted
        :raises ProcessingTimeoutError: If wall-clock time exceeds timeout_seconds
        """
        start = time.time()
        # Honour artificial latency if configured (useful in benchmarking)
        if self.config.simulate_latency_ms > 0:
            time.sleep(self.config.simulate_latency_ms / 1000.0)

        # Normalise input to a flat list of non-empty strings
        text_items = self._normalize_input(input_data)
        if not text_items:
            raise EmptyInputError("No input text provided")

        all_points: List[TalkingPoint] = []
        for text in text_items:
            # Extract the most salient topics from this text fragment
            topics = self.extract_key_topics(text)
            # Convert topics into scored TalkingPoint objects
            points = self.generate_points(text, topics)
            all_points.extend(points)
            # Enforce hard timeout after processing each text item
            if time.time() - start > self.config.timeout_seconds:
                raise ProcessingTimeoutError("Processing timed out")

        # Render the collected points in the requested format
        formatted = self._format_output(all_points, output_format or self.config.output_format)
        return formatted

    def batch_process(
        self, inputs: Sequence[Union[str, Dict[str, Any]]], output_format: Optional[str] = None
    ) -> List[Union[Dict[str, Any], str]]:
        """
        Process multiple inputs and return a list of formatted outputs.

        :param inputs: Ordered sequence of inputs, each formatted as accepted
                       by process()
        :param output_format: Format override applied to every item in the batch
        :return: List of formatted outputs in the same order as inputs
        """
        outputs: List[Union[Dict[str, Any], str]] = []
        for item in inputs:
            # Delegate to process() so timeout and format logic are centralised
            outputs.append(self.process(item, output_format))
        return outputs

    def _normalize_input(self, input_data: Union[str, Dict[str, Any], List[str]]) -> List[str]:
        """
        Normalise heterogeneous input into a flat list of text strings.

        Supported input types:
        - str: plain text, or a file path ending in .json / .csv
        - dict: must contain "text" (str) or "texts" (list of str)
        - list: items are cast to str and stripped

        :param input_data: Raw input in any supported form
        :return: Flat list of non-empty stripped strings
        """
        if isinstance(input_data, str):
            s = input_data.strip()
            # If the string looks like a JSON file path, load and recurse
            if s.endswith(".json") and os.path.exists(s):
                with open(s, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._normalize_input(data)
            # If it looks like a CSV file path, delegate to the CSV reader
            if s.endswith(".csv") and os.path.exists(s):
                return self._read_csv_texts(s)
            # Otherwise treat the string itself as the input text
            return [s] if s else []

        if isinstance(input_data, dict):
            # Single-text dict: {"text": "..."}
            if "text" in input_data and isinstance(input_data["text"], str):
                return [input_data["text"].strip()] if input_data["text"].strip() else []
            # Multi-text dict: {"texts": ["...", "..."]}
            if "texts" in input_data and isinstance(input_data["texts"], list):
                return [str(t).strip() for t in input_data["texts"] if str(t).strip()]
            # Unrecognised dict structure — return empty to trigger EmptyInputError
            return []

        if isinstance(input_data, list):
            # Cast each element to string and discard blanks
            return [str(t).strip() for t in input_data if str(t).strip()]

        # Unsupported type — return empty
        return []

    def _read_csv_texts(self, path: str) -> List[str]:
        """
        Read text values from a CSV file.

        Prefers a column named "text"; falls back to the first column if
        "text" is not present.

        :param path: Absolute or relative path to the CSV file
        :return: List of non-empty text strings from the selected column
        """
        rows: List[str] = []
        with open(path, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            # Prefer explicit "text" column; otherwise use first available column
            col = "text" if "text" in r.fieldnames else (r.fieldnames[0] if r.fieldnames else None)
            if not col:
                return []  # No usable column found
            for row in r:
                v = str(row.get(col, "")).strip()
                if v:
                    rows.append(v)
        return rows

    @lru_cache(maxsize=128)
    def extract_key_topics(self, text: str) -> List[str]:
        """
        Extract key topics from text using lexical frequency analysis.

        The method tokenises the text, removes common English stop-words,
        counts the remaining tokens, and returns the top-N by frequency.

        Caching is applied via lru_cache because the same text block may
        be submitted multiple times during batch processing.

        :param text: Raw input text string
        :return: List of up to max_topics lower-case topic words, most
                 frequent first
        """
        # Tokenise: extract runs of alphanumeric/underscore/hyphen characters
        tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text)]
        # Remove common English stop-words that carry no topical signal
        stops = {
            "the",
            "and",
            "of",
            "to",
            "in",
            "for",
            "on",
            "at",
            "a",
            "an",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "it",
            "this",
            "that",
            "from",
        }
        # Also filter out very short tokens (2 chars or fewer) as noise
        tokens = [t for t in tokens if t not in stops and len(t) > 2]
        counts = Counter(tokens)
        # Return only the most frequent tokens up to the configured cap
        top = [w for w, _ in counts.most_common(self.config.max_topics)]
        return top

    def generate_points(self, text: str, topics: List[str]) -> List[TalkingPoint]:
        """
        Generate concise, unique talking points from extracted topics.

        For each topic a candidate talking point is constructed as
        "<Topic capitalised> focus and next steps". The candidate is
        then scored on relevance, conciseness, and uniqueness before
        being accepted or rejected.

        :param text: The original input text (used to compute relevance)
        :param topics: Ordered list of key topics from extract_key_topics()
        :return: List of accepted TalkingPoint objects, up to max_points
        """
        points: List[TalkingPoint] = []
        seen: set = set()  # Deduplicate candidates before scoring
        # Build a set of unique words for fast relevance lookup
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text)]
        unique_words = set(words)

        for topic in topics:
            # Simple template: real implementations would use an LLM here
            base = f"{topic.capitalize()} focus and next steps"
            # Skip exact duplicates before incurring scoring cost
            if base in seen:
                continue
            seen.add(base)

            relevance = self._compute_relevance(topic, unique_words)
            conciseness = self._compute_conciseness(base)
            uniqueness = self._compute_uniqueness(base, points)

            # Only emit points that clear all three quality thresholds
            if self._passes_quality(relevance, conciseness, uniqueness):
                points.append(TalkingPoint(text=base, relevance=relevance, conciseness=conciseness, uniqueness=uniqueness))

            # Stop once we have reached the configured maximum
            if len(points) >= self.config.max_points:
                break

        return points

    def _compute_relevance(self, topic: str, unique_words: set) -> float:
        """
        Compute relevance score for a topic.

        A topic is fully relevant (1.0) if it appears in the source text;
        otherwise it receives the minimum threshold as a floor.

        :param topic: Single lower-case topic word
        :param unique_words: Set of all unique lower-case words in the source text
        :return: Relevance score in [min_relevance_ratio, 1.0]
        """
        return 1.0 if topic in unique_words else self.config.min_relevance_ratio

    def _compute_conciseness(self, text: str) -> float:
        """
        Compute conciseness score for a candidate talking point.

        Points at or under max_point_words score 1.0; longer points are
        penalised proportionally.

        :param text: The candidate talking-point string
        :return: Conciseness score in [0.0, 1.0]
        """
        words = text.split()
        return 1.0 if len(words) <= self.config.max_point_words else max(0.0, self.config.max_point_words / max(1, len(words)))

    def _compute_uniqueness(self, candidate: str, points: List[TalkingPoint]) -> float:
        """
        Compute uniqueness score relative to already-accepted points.

        Exact case-insensitive duplicates reduce uniqueness to near-zero;
        the first candidate always scores 1.0.

        :param candidate: The candidate talking-point string
        :param points: List of already-accepted TalkingPoint objects
        :return: Uniqueness score in [0.0, 1.0]
        """
        if not points:
            return 1.0  # First candidate is always maximally unique
        overlap = sum(1 for p in points if p.text.lower() == candidate.lower())
        return 1.0 - (overlap / (len(points) + 1))

    def _passes_quality(self, relevance: float, conciseness: float, uniqueness: float) -> bool:
        """
        Determine whether a candidate passes all quality gates.

        :param relevance: Score from _compute_relevance()
        :param conciseness: Score from _compute_conciseness()
        :param uniqueness: Score from _compute_uniqueness()
        :return: True if the candidate meets all thresholds, False otherwise
        """
        # Reject if the topic is not meaningfully present in the source text
        if relevance < self.config.min_relevance_ratio:
            return False
        # Reject if the point would be too verbose for an RM to read quickly
        if conciseness < 0.5:
            return False
        # Reject near-duplicate points to avoid redundant briefing content
        if uniqueness < self.config.min_uniqueness_ratio:
            return False
        return True

    def _format_output(self, points: List[TalkingPoint], fmt: str) -> Union[Dict[str, Any], str]:
        """
        Render the accepted talking points in the requested format.

        :param points: List of accepted TalkingPoint objects
        :param fmt: One of "json", "markdown", or "text"; unknown values
                    fall back to "json"
        :return: Dict for "json", str for all other formats
        """
        if fmt == "json":
            # Structured dict suitable for API responses and downstream parsing
            return {
                "points": [
                    {
                        "text": p.text,
                        "relevance": round(p.relevance, 3),
                        "conciseness": round(p.conciseness, 3),
                        "uniqueness": round(p.uniqueness, 3),
                    }
                    for p in points
                ]
            }
        if fmt == "markdown":
            # Bulleted list with inline quality metrics for documentation use
            lines = []
            for p in points:
                lines.append(f"- {p.text} (rel={p.relevance:.2f}, conc={p.conciseness:.2f}, uniq={p.uniqueness:.2f})")
            return "\n".join(lines) + ("\n" if lines else "")
        if fmt == "text":
            # Numbered plain-text list for terminal output or email bodies
            lines = [f"{i+1}. {p.text}" for i, p in enumerate(points)]
            return "\n".join(lines) + ("\n" if lines else "")
        # Unknown format — fall back to JSON to avoid silent failures
        return self._format_output(points, "json")
