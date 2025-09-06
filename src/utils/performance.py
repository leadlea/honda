"""
Performance optimization utilities for Lambda functions and DynamoDB operations.
Includes caching, connection pooling, and query optimization.
"""

import json
import logging
import threading
import time
from datetime import datetime
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, List, Optional

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor and log performance metrics."""

    def __init__(self):
        self.metrics = {}
        self.lock = threading.Lock()

    def record_metric(self, name: str, value: float, unit: str = "ms"):
        """Record a performance metric."""
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = []

            self.metrics[name].append(
                {
                    "value": value,
                    "unit": unit,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            # Keep only last 100 measurements
            if len(self.metrics[name]) > 100:
                self.metrics[name] = self.metrics[name][-100:]

    def get_average(self, name: str) -> Optional[float]:
        """Get average value for a metric."""
        with self.lock:
            if name not in self.metrics or not self.metrics[name]:
                return None

            values = [m["value"] for m in self.metrics[name]]
            return sum(values) / len(values)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        with self.lock:
            summary = {}
            for name, measurements in self.metrics.items():
                if measurements:
                    values = [m["value"] for m in measurements]
                    summary[name] = {
                        "count": len(values),
                        "average": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "latest": values[-1],
                        "unit": measurements[-1]["unit"],
                    }
            return summary


# Global performance monitor
performance_monitor = PerformanceMonitor()


def performance_timer(metric_name: str):
    """Decorator to time function execution."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                performance_monitor.record_metric(metric_name, duration_ms)
                logger.debug(f"{metric_name}: {duration_ms:.2f}ms")

        return wrapper

    return decorator


class ConnectionPool:
    """Connection pool for AWS services to reduce cold start impact."""

    _instances = {}
    _lock = threading.Lock()

    @classmethod
    def get_client(cls, service_name: str, region: str = "us-west-2") -> Any:
        """Get cached AWS service client."""
        key = f"{service_name}_{region}"

        if key not in cls._instances:
            with cls._lock:
                if key not in cls._instances:
                    # Optimized configuration for better performance
                    config = Config(
                        region_name=region,
                        retries={"max_attempts": 3, "mode": "adaptive"},
                        max_pool_connections=50,
                        connect_timeout=5,
                        read_timeout=10,
                    )

                    cls._instances[key] = boto3.client(service_name, config=config)
                    logger.debug(f"Created new {service_name} client for {region}")

        return cls._instances[key]

    @classmethod
    def get_resource(cls, service_name: str, region: str = "us-west-2") -> Any:
        """Get cached AWS service resource."""
        key = f"{service_name}_resource_{region}"

        if key not in cls._instances:
            with cls._lock:
                if key not in cls._instances:
                    config = Config(
                        region_name=region,
                        retries={"max_attempts": 3, "mode": "adaptive"},
                        max_pool_connections=50,
                    )

                    cls._instances[key] = boto3.resource(service_name, config=config)
                    logger.debug(f"Created new {service_name} resource for {region}")

        return cls._instances[key]


class DynamoDBOptimizer:
    """DynamoDB query optimization utilities."""

    @staticmethod
    def build_optimized_query(
        table_name: str,
        key_condition: str,
        filter_expression: Optional[str] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_forward: bool = True,
    ) -> Dict[str, Any]:
        """Build optimized DynamoDB query parameters."""
        query_params = {
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": scan_forward,
        }

        if filter_expression:
            query_params["FilterExpression"] = filter_expression

        if index_name:
            query_params["IndexName"] = index_name

        if limit:
            # Use smaller page sizes for better performance
            query_params["Limit"] = min(limit, 100)

        return query_params

    @staticmethod
    def optimize_batch_operations(
        items: List[Dict[str, Any]], batch_size: int = 25
    ) -> List[List[Dict[str, Any]]]:
        """Optimize batch operations by splitting into optimal chunks."""
        # DynamoDB batch operations are limited to 25 items
        optimized_batches = []

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            optimized_batches.append(batch)

        return optimized_batches

    @staticmethod
    def calculate_read_capacity(
        item_size_kb: float, reads_per_second: float, consistency: str = "eventual"
    ) -> int:
        """Calculate optimal read capacity units."""
        # Each RCU provides 1 strongly consistent read or 2 eventually consistent reads
        # for items up to 4KB

        rcu_per_item = max(1, item_size_kb / 4)

        if consistency == "strong":
            total_rcu = reads_per_second * rcu_per_item
        else:  # eventual consistency
            total_rcu = (reads_per_second * rcu_per_item) / 2

        # Add 20% buffer for spikes
        return int(total_rcu * 1.2)

    @staticmethod
    def calculate_write_capacity(item_size_kb: float, writes_per_second: float) -> int:
        """Calculate optimal write capacity units."""
        # Each WCU provides 1 write per second for items up to 1KB
        wcu_per_item = max(1, item_size_kb)
        total_wcu = writes_per_second * wcu_per_item

        # Add 20% buffer for spikes
        return int(total_wcu * 1.2)


class BedrockOptimizer:
    """Bedrock API optimization utilities."""

    def __init__(self):
        self.response_cache = {}
        self.cache_ttl = 300  # 5 minutes

    @lru_cache(maxsize=100)
    def get_cached_response(self, prompt_hash: str, model_id: str) -> Optional[str]:
        """Get cached Bedrock response if available."""
        cache_key = f"{model_id}_{prompt_hash}"

        if cache_key in self.response_cache:
            cached_item = self.response_cache[cache_key]

            # Check if cache is still valid
            if time.time() - cached_item["timestamp"] < self.cache_ttl:
                logger.debug(f"Cache hit for Bedrock request: {cache_key}")
                return cached_item["response"]
            else:
                # Remove expired cache entry
                del self.response_cache[cache_key]

        return None

    def cache_response(self, prompt_hash: str, model_id: str, response: str):
        """Cache Bedrock response."""
        cache_key = f"{model_id}_{prompt_hash}"

        self.response_cache[cache_key] = {
            "response": response,
            "timestamp": time.time(),
        }

        # Limit cache size
        if len(self.response_cache) > 1000:
            # Remove oldest entries
            sorted_items = sorted(
                self.response_cache.items(), key=lambda x: x[1]["timestamp"]
            )

            # Keep only newest 800 entries
            self.response_cache = dict(sorted_items[-800:])

    @staticmethod
    def optimize_prompt(prompt: str, max_tokens: int = 4000) -> str:
        """Optimize prompt for better Bedrock performance."""
        # Remove excessive whitespace
        optimized = " ".join(prompt.split())

        # Truncate if too long (rough token estimation: 1 token ≈ 4 characters)
        max_chars = max_tokens * 4
        if len(optimized) > max_chars:
            optimized = optimized[:max_chars] + "..."
            logger.warning(f"Prompt truncated to {max_chars} characters")

        return optimized

    @staticmethod
    def get_optimal_inference_params(use_case: str) -> Dict[str, Any]:
        """Get optimal inference parameters for different use cases."""
        params = {
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9,
            "stop_sequences": [],
        }

        if use_case == "questionnaire_generation":
            params.update({"max_tokens": 2000, "temperature": 0.8, "top_p": 0.9})
        elif use_case == "matching_analysis":
            params.update({"max_tokens": 1500, "temperature": 0.5, "top_p": 0.8})
        elif use_case == "business_title_generation":
            params.update({"max_tokens": 100, "temperature": 0.6, "top_p": 0.7})
        elif use_case == "search_ranking":
            params.update({"max_tokens": 500, "temperature": 0.3, "top_p": 0.7})

        return params


class LambdaColdStartOptimizer:
    """Utilities to reduce Lambda cold start impact."""

    @staticmethod
    def warm_up_connections():
        """Pre-warm connections during Lambda initialization."""
        try:
            # Pre-create AWS service clients
            ConnectionPool.get_client("dynamodb")
            ConnectionPool.get_client("bedrock-runtime")
            ConnectionPool.get_resource("dynamodb")

            logger.info("AWS connections pre-warmed")
        except Exception as e:
            logger.warning(f"Failed to pre-warm connections: {e}")

    @staticmethod
    def preload_modules():
        """Preload commonly used modules."""
        try:
            # Import heavy modules during initialization
            pass

            logger.info("Common modules preloaded")
        except Exception as e:
            logger.warning(f"Failed to preload modules: {e}")

    @staticmethod
    def initialize_global_objects():
        """Initialize global objects that can be reused across invocations."""
        try:
            # Initialize performance monitor
            global performance_monitor
            if not hasattr(performance_monitor, "initialized"):
                performance_monitor.initialized = True
                logger.info("Global objects initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize global objects: {e}")


class MemoryOptimizer:
    """Memory usage optimization utilities."""

    @staticmethod
    def optimize_json_parsing(data: str) -> Dict[str, Any]:
        """Optimize JSON parsing for large payloads."""
        try:
            # Use faster JSON parsing for large payloads
            if len(data) > 10000:  # 10KB threshold
                import orjson

                return orjson.loads(data)
            else:
                return json.loads(data)
        except ImportError:
            # Fallback to standard JSON
            return json.loads(data)

    @staticmethod
    def optimize_response_size(
        data: Dict[str, Any], max_size_kb: int = 6000
    ) -> Dict[str, Any]:
        """Optimize response size to stay within Lambda limits."""
        response_str = json.dumps(data)

        if len(response_str) > max_size_kb * 1024:
            logger.warning(f"Response size ({len(response_str)} bytes) exceeds limit")

            # Try to reduce response size
            if "items" in data and isinstance(data["items"], list):
                # Reduce number of items
                original_count = len(data["items"])
                data["items"] = data["items"][:50]  # Limit to 50 items
                data["truncated"] = True
                data["original_count"] = original_count

                logger.info(
                    f"Response truncated from {original_count} to {len(data['items'])} items"
                )

        return data


# Global instances
bedrock_optimizer = BedrockOptimizer()
cold_start_optimizer = LambdaColdStartOptimizer()


def optimize_lambda_handler(func: Callable) -> Callable:
    """Decorator to optimize Lambda handler performance."""

    @wraps(func)
    def wrapper(event, context):
        # Record handler execution time
        start_time = time.time()

        try:
            # Optimize event parsing
            if isinstance(event.get("body"), str):
                event["body"] = MemoryOptimizer.optimize_json_parsing(event["body"])

            # Execute handler
            result = func(event, context)

            # Optimize response size
            if isinstance(result, dict) and "body" in result:
                if isinstance(result["body"], str):
                    body_data = json.loads(result["body"])
                    optimized_body = MemoryOptimizer.optimize_response_size(body_data)
                    result["body"] = json.dumps(optimized_body)

            return result

        finally:
            # Record performance metrics
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            performance_monitor.record_metric("lambda_handler_duration", duration_ms)

            # Log performance summary periodically
            if hasattr(context, "aws_request_id"):
                logger.debug(
                    f"Handler completed in {duration_ms:.2f}ms - {context.aws_request_id}"
                )

    return wrapper


# Initialize optimizations during module import
try:
    cold_start_optimizer.warm_up_connections()
    cold_start_optimizer.preload_modules()
    cold_start_optimizer.initialize_global_objects()
except Exception as e:
    logger.warning(f"Optimization initialization failed: {e}")
