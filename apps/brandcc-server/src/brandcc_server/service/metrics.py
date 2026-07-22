"""Prometheus metrics for BrandCC."""

from prometheus_client import CollectorRegistry, Counter, Histogram

registry = CollectorRegistry()