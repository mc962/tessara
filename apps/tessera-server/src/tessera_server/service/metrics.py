"""Prometheus metrics for Tessera."""

from prometheus_client import CollectorRegistry, Counter, Histogram

registry = CollectorRegistry()