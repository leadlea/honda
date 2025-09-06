"""
Base repository class for DynamoDB operations
"""
import logging
import os
from typing import Any, Dict, List, Optional, Type, TypeVar

import boto3
from botocore.exceptions import ClientError

from src.utils.encryption import pii_protection_service
from src.utils.performance import (
    ConnectionPool,
    DynamoDBOptimizer,
    performance_monitor,
    performance_timer,
)

# Type variable for model classes
T = TypeVar("T")

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common DynamoDB operations"""

    def __init__(self, table_name: str):
        """Initialize repository with table name and optimized connections"""
        self.table_name = table_name
        self.region = os.environ.get("REGION", "us-west-2")
        # Use connection pool for better performance
        self.dynamodb = ConnectionPool.get_resource("dynamodb", self.region)
        self.table = self.dynamodb.Table(table_name)
        self.optimizer = DynamoDBOptimizer()

    def get_item(
        self, key: Dict[str, Any], unprotect_pii: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get a single item by key with optional PII unprotection"""
        try:
            response = self.table.get_item(Key=key)
            item = response.get("Item")

            # Unprotect PII data after retrieval
            if item and unprotect_pii:
                item = pii_protection_service.unprotect_pii_data(item)

            return item
        except ClientError as e:
            logger.error(f"Error getting item from {self.table_name}: {e}")
            raise

    def put_item(self, item: Dict[str, Any], protect_pii: bool = True) -> bool:
        """Put an item into the table with optional PII protection"""
        try:
            # Protect PII data before storing
            if protect_pii:
                item = pii_protection_service.protect_pii_data(item)

            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"Error putting item to {self.table_name}: {e}")
            raise

    def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Update an item in the table"""
        try:
            kwargs = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_attribute_values,
                "ReturnValues": "UPDATED_NEW",
            }

            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            self.table.update_item(**kwargs)
            return True
        except ClientError as e:
            logger.error(f"Error updating item in {self.table_name}: {e}")
            raise

    def delete_item(self, key: Dict[str, Any]) -> bool:
        """Delete an item from the table"""
        try:
            self.table.delete_item(Key=key)
            return True
        except ClientError as e:
            logger.error(f"Error deleting item from {self.table_name}: {e}")
            raise

    @performance_timer("dynamodb_query")
    def query(
        self,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
        filter_expression: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query items from the table with performance optimization"""
        try:
            # Use optimizer to build query parameters
            kwargs = self.optimizer.build_optimized_query(
                self.table_name,
                key_condition_expression,
                filter_expression,
                index_name,
                limit,
                scan_index_forward,
            )

            kwargs["ExpressionAttributeValues"] = expression_attribute_values

            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            response = self.table.query(**kwargs)
            items = response.get("Items", [])

            # Record performance metrics
            performance_monitor.record_metric(
                f"dynamodb_query_items_returned_{self.table_name}", len(items), "count"
            )

            return items
        except ClientError as e:
            logger.error(f"Error querying {self.table_name}: {e}")
            raise

    def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Scan items from the table"""
        try:
            kwargs = {}

            if filter_expression:
                kwargs["FilterExpression"] = filter_expression

            if expression_attribute_values:
                kwargs["ExpressionAttributeValues"] = expression_attribute_values

            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            if limit:
                kwargs["Limit"] = limit

            response = self.table.scan(**kwargs)
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Error scanning {self.table_name}: {e}")
            raise

    def batch_get_items(self, keys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get multiple items by keys"""
        try:
            response = self.dynamodb.batch_get_item(
                RequestItems={self.table_name: {"Keys": keys}}
            )
            return response.get("Responses", {}).get(self.table_name, [])
        except ClientError as e:
            logger.error(f"Error batch getting items from {self.table_name}: {e}")
            raise

    @performance_timer("dynamodb_batch_write")
    def batch_write_items(
        self,
        items: List[Dict[str, Any]],
        delete_keys: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Batch write items to the table with optimization"""
        try:
            request_items = []

            # Add put requests with PII protection
            for item in items:
                protected_item = pii_protection_service.protect_pii_data(item)
                request_items.append({"PutRequest": {"Item": protected_item}})

            # Add delete requests
            if delete_keys:
                for key in delete_keys:
                    request_items.append({"DeleteRequest": {"Key": key}})

            # Use optimizer to split into optimal batches
            optimized_batches = self.optimizer.optimize_batch_operations(request_items)

            for batch in optimized_batches:
                self.dynamodb.batch_write_item(RequestItems={self.table_name: batch})

            # Record performance metrics
            performance_monitor.record_metric(
                f"dynamodb_batch_write_items_{self.table_name}",
                len(request_items),
                "count",
            )

            return True
        except ClientError as e:
            logger.error(f"Error batch writing items to {self.table_name}: {e}")
            raise

    def item_exists(self, key: Dict[str, Any]) -> bool:
        """Check if an item exists in the table"""
        item = self.get_item(key)
        return item is not None

    def get_item_for_public(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get item with PII anonymized for public display"""
        try:
            response = self.table.get_item(Key=key)
            item = response.get("Item")

            if item:
                # First unprotect to get original data
                item = pii_protection_service.unprotect_pii_data(item)
                # Then anonymize for public display
                item = pii_protection_service.anonymize_for_public(item)

            return item
        except ClientError as e:
            logger.error(f"Error getting public item from {self.table_name}: {e}")
            raise

    def get_table_info(self) -> Dict[str, Any]:
        """Get table information"""
        try:
            response = self.table.meta.client.describe_table(TableName=self.table_name)
            return response["Table"]
        except ClientError as e:
            logger.error(f"Error getting table info for {self.table_name}: {e}")
            raise
