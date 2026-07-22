"""Prometheus metrics for Tessara."""

from prometheus_client import CollectorRegistry, Counter, Histogram

registry = CollectorRegistry()