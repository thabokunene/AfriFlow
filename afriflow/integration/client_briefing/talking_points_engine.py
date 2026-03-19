"""
@file talking_points_engine.py
@description Lexical talking-points engine for AfriFlow client briefings.
             Extracts key topics from raw text and converts them into concise,
             deduplicated talking points. Measured along relevance, conciseness,
             and uniqueness dimensions. Supports JSON, Markdown, and plain text
             output formats.
@author Thabo Kunene
@created 2026-03-19
"""

# Talking Points Engine
#
# Lexical engine that extracts key topics from raw text inputs and
# converts them into structured, high-quality talking points for RMs.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard-library imports for file processing, logging, and data handling
import csv
import json
import logging
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ModelLoadError(Exception):
    """Raised when the NLP model fails to load."""
    pass


class EmptyInputError(Exception):
    """Raised when input text is empty or missing."""
    pass


class ProcessingTimeoutError(Exception):
    """Raised when processing exceeds the configured timeout."""
    pass


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class TalkingPointsConfig:
    """
    Configuration for TalkingPointsEngine.

    :param model_path: Path to external model; None uses built-in lexical model
    :param max_topics: Max distinct topics to extract
    :param max_points: Max talking points to emit
    :param max_point_words: Conciseness threshold (max words per point)
    :param timeout_seconds: Hard wall on processing time
    :param log_path: Path for rotating log file; None uses console
    :param log_level: Python logging level
    :param log_max_bytes: Max log file size before rotation
    :param log_backup_count: Number of rotated log files to retain
    :param output_format: "json", "markdown", or "text"
    :param simulate_latency_ms: Artificial latency for load testing
    :param min_uniqueness_ratio: Threshold for point uniqueness (0-1)
    :param min_relevance_ratio: Threshold for point relevance (0-1)
    """

    model_path: Optional[str] = None
    max_topics: int = 8
    max_points: int = 6
    max_point_words: int = 24
    timeout_seconds: float = 2.0
    log_path: Optional[str] = None
    log_level: int = logging.INFO
    log_max_bytes: int = 512_000
    log_backup_count: int = 3
    output_format: str = "json"
    simulate_latency_ms: int = 0
    min_uniqueness_ratio: float = 0.6
    min_relevance_ratio: float = 0.5


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class TalkingPoint:
    """
    A single generated talking point with quality metrics.

    :param text: The talking point string
    :param relevance: Topic relationship score (0-1)
    :param conciseness: Word count efficiency score (0-1)
    :param uniqueness: Distinctness score (0-1)
    """

    text: str
    relevance: float
    conciseness: float
    uniqueness: float


# ---------------------------------------------------------------------------
# Engine class
# ---------------------------------------------------------------------------

class TalkingPointsEngine:
    """
    Engine responsible for generating high-quality talking points from text.
    """

    def __init__(self, config: Optional[TalkingPointsConfig] = None) -> None:
        """
        Initialise the engine with optional configuration.

        :param config: Configuration instance; defaults to production settings
        """
        # Load configuration or use defaults
        self.config = config or TalkingPointsConfig()
        # Initialize logging for observability
        self.logger = self._setup_logger()
        # Load the processing model (lexical or external)
        self.model = self._load_model(self.config.model_path)

    def _setup_logger(self) -> logging.Logger:
        """
        Configure and return a module-scoped logger.

        :return: Configured logging.Logger instance.
        """
        # Create a logger specific to this engine component
        logger = logging.getLogger("afriflow.integration.talking_points_engine")
        logger.setLevel(self.config.log_level)

        # Attach rotating file handler if a log path is configured
        if self.config.log_path:
            handler = RotatingFileHandler(
                self.config.log_path,
                maxBytes=self.config.log_max_bytes,
                backupCount=self.config.log_backup_count,
            )
            fmt = logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
            handler.setFormatter(fmt)
            # Ensure only one handler is attached to the logger
            if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
                logger.addHandler(handler)
        return logger

    def _load_model(self, path: Optional[str]) -> Any:
        """
        Load the NLP model from disk, or return a lexical stub.

        :param path: Path to the model artifact
        :return: A model descriptor dictionary.
        :raises ModelLoadError: If the model cannot be loaded.
        """
        start = time.time()
        try:
            if path:
                # Check for file existence before loading
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Model path not found: {path}")
            # Stub for actual model loading logic
            return {"name": "lexical", "version": "1.0"}
        except Exception as e:
            # Record failure in logs before raising custom exception
            self.logger.error("Model load failure: %s", e)
            raise ModelLoadError(str(e))
        finally:
            # Monitor load performance
            self.logger.debug("Model load took %.3fs", time.time() - start)

    def process(
        self,
        input_data: Union[str, Dict[str, Any], List[str]],
        output_format: Optional[str] = None,
    ) -> Union[Dict[str, Any], str]:
        """
        Process input data and generate formatted talking points.

        :param input_data: Raw text, list of texts, or path to JSON/CSV file
        :param output_format: Optional override for the output format
        :return: Formatted output (dict or string).
        :raises EmptyInputError: If no text is available to process.
        :raises ProcessingTimeoutError: If execution exceeds timeout.
        """
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
