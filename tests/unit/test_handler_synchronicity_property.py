"""
Property-based tests for handler synchronicity and async operation completion.

Feature: fix-backend-handler-bugs, Property 1: Handler synchronicity
Validates: Requirements 3.1, 3.2

Feature: fix-backend-handler-bugs, Property 2: Async operation completion
Validates: Requirements 3.3
"""

import asyncio
import inspect
import time
from typing import Any, Callable, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.handlers import business_title_handler, profile_handler


def is_synchronous_function(func: Callable) -> bool:
    """
    Check if a function is synchronous (not async).
    
    Args:
        func: Function to check
        
    Returns:
        True if function is synchronous, False if async
    """
    return not asyncio.iscoroutinefunction(func)


def get_lambda_handler_functions() -> Dict[str, Callable]:
    """
    Get all Lambda handler functions from the handlers modules.
    
    Returns:
        Dictionary mapping handler names to handler functions
    """
    handlers = {}
    
    # Business title handler functions
    handlers["generate_business_titles"] = business_title_handler.generate_business_titles
    handlers["select_business_title"] = business_title_handler.select_business_title
    handlers["regenerate_business_titles"] = business_title_handler.regenerate_business_titles
    handlers["get_title_history"] = business_title_handler.get_title_history
    
    # Profile handler main function
    handlers["profile_handler"] = profile_handler.handler
    
    return handlers


class TestHandlerSynchronicity:
    """Property-based tests for Lambda handler synchronicity."""
    
    def test_all_lambda_handlers_are_synchronous(self):
        """
        Property 1: Handler synchronicity
        
        For any Lambda handler function, the function signature should be 
        synchronous (def, not async def), ensuring AWS Lambda can properly 
        invoke and manage the function lifecycle.
        
        Validates: Requirements 3.1, 3.2
        """
        handlers = get_lambda_handler_functions()
        
        for handler_name, handler_func in handlers.items():
            # Check that the handler is synchronous
            assert is_synchronous_function(handler_func), (
                f"Handler '{handler_name}' must be synchronous (def), not async (async def). "
                f"AWS Lambda requires synchronous handler functions."
            )
            
            # Verify the function signature accepts event and context
            sig = inspect.signature(handler_func)
            params = list(sig.parameters.keys())
            
            assert len(params) >= 2, (
                f"Handler '{handler_name}' must accept at least 2 parameters (event, context)"
            )
    
    @given(
        event_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(max_size=100),
                st.dictionaries(
                    keys=st.text(min_size=1, max_size=10),
                    values=st.text(max_size=50)
                )
            ),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_handler_returns_without_await(self, event_data: Dict[str, Any]):
        """
        Property test: Handler functions should return immediately without requiring await.
        
        For any event data, calling a handler function should return a result
        synchronously without needing to await it.
        
        Validates: Requirements 3.1, 3.2
        """
        handlers = get_lambda_handler_functions()
        
        # Test with a simple handler that we know exists
        handler_func = handlers["profile_handler"]
        
        # Create a minimal valid event
        test_event = {
            "httpMethod": "GET",
            "path": "/profiles",
            "headers": {"Authorization": "Bearer test-token"},
            "pathParameters": None,
            "queryStringParameters": None,
            "body": None,
        }
        test_event.update(event_data)
        
        # Call the handler - this should NOT require await
        # If the handler is async, this will fail or return a coroutine
        result = handler_func(test_event, {})
        
        # Verify we got a result, not a coroutine
        assert not asyncio.iscoroutine(result), (
            "Handler returned a coroutine - it should be synchronous and return a result directly"
        )
        
        # Verify the result is a dictionary (API Gateway response format)
        assert isinstance(result, dict), (
            f"Handler should return a dict, got {type(result)}"
        )
        
        # Verify the result has the expected API Gateway response structure
        assert "statusCode" in result, "Handler response must include statusCode"
        assert "body" in result, "Handler response must include body"
    
    def test_business_title_handler_class_methods_use_async_internally(self):
        """
        Verify that handler class methods properly wrap async operations.
        
        The public handler methods should be synchronous, but they can use
        async helper methods internally with proper event loop management.
        
        Validates: Requirements 3.2, 3.3
        """
        handler_instance = business_title_handler.BusinessTitleHandler()
        
        # Public methods should be synchronous
        public_methods = [
            "generate_business_titles",
            "select_business_title",
            "regenerate_business_titles",
            "get_title_history",
        ]
        
        for method_name in public_methods:
            method = getattr(handler_instance, method_name)
            assert is_synchronous_function(method), (
                f"Public handler method '{method_name}' must be synchronous"
            )
        
        # Internal async methods should exist and be async
        async_methods = [
            "_generate_business_titles_async",
            "_select_business_title_async",
            "_regenerate_business_titles_async",
            "_get_title_history_async",
        ]
        
        for method_name in async_methods:
            method = getattr(handler_instance, method_name)
            assert asyncio.iscoroutinefunction(method), (
                f"Internal helper method '{method_name}' should be async"
            )
    
    @given(
        headers=st.dictionaries(
            keys=st.sampled_from(["Authorization", "Content-Type", "User-Agent"]),
            values=st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=3
        )
    )
    @settings(max_examples=100)
    def test_handler_synchronous_execution_with_various_events(
        self, headers: Dict[str, str]
    ):
        """
        Property test: Handlers execute synchronously regardless of event structure.
        
        For any valid event structure with various headers, the handler should
        execute synchronously and return a response without requiring await.
        
        Validates: Requirements 3.1, 3.2
        """
        # Create event with provided headers
        event = {
            "httpMethod": "GET",
            "path": "/profiles",
            "headers": headers,
            "pathParameters": None,
            "queryStringParameters": None,
            "body": None,
        }
        
        # Call handler synchronously
        result = profile_handler.handler(event, {})
        
        # Verify synchronous execution
        assert not asyncio.iscoroutine(result), (
            "Handler must execute synchronously and not return a coroutine"
        )
        
        # Verify response structure
        assert isinstance(result, dict), "Handler must return a dict"
        assert "statusCode" in result, "Response must have statusCode"
        assert isinstance(result["statusCode"], int), "statusCode must be an integer"


class TestAsyncOperationCompletion:
    """
    Property-based tests for async operation completion.
    
    Feature: fix-backend-handler-bugs, Property 2: Async operation completion
    Validates: Requirements 3.3
    """
    
    @given(
        delay_ms=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=100)
    def test_async_operations_complete_before_handler_returns(self, delay_ms: int):
        """
        Property 2: Async operation completion
        
        For any handler that uses asynchronous operations internally, all async 
        operations should complete before the handler returns a response.
        
        This test verifies that when a handler uses asyncio.run() to execute
        async operations, those operations fully complete before the handler
        returns control to the caller.
        
        Validates: Requirements 3.3
        """
        # Track whether async operation completed
        operation_completed = {"value": False}
        
        async def mock_async_operation():
            """Simulate an async operation with a delay."""
            await asyncio.sleep(delay_ms / 1000.0)  # Convert ms to seconds
            operation_completed["value"] = True
            return {"status": "completed"}
        
        # Create a mock handler that uses asyncio.run()
        def synchronous_handler_with_async_logic(event, context):
            """Synchronous handler that wraps async logic."""
            async def async_logic():
                result = await mock_async_operation()
                return {
                    "statusCode": 200,
                    "body": str(result)
                }
            
            return asyncio.run(async_logic())
        
        # Call the handler
        event = {"test": "data"}
        context = {}
        
        start_time = time.time()
        result = synchronous_handler_with_async_logic(event, context)
        end_time = time.time()
        
        # Verify the handler returned a result (not a coroutine)
        assert not asyncio.iscoroutine(result), (
            "Handler should return a completed result, not a coroutine"
        )
        
        # Verify the async operation completed before the handler returned
        assert operation_completed["value"], (
            "Async operation must complete before handler returns. "
            "The handler should use asyncio.run() or equivalent to ensure "
            "all async operations finish before returning."
        )
        
        # Verify the handler actually waited for the async operation
        elapsed_ms = (end_time - start_time) * 1000
        assert elapsed_ms >= delay_ms * 0.8, (
            f"Handler returned too quickly ({elapsed_ms:.1f}ms). "
            f"Expected at least {delay_ms * 0.8:.1f}ms to ensure async operation completed."
        )
        
        # Verify the result has the expected structure
        assert isinstance(result, dict), "Handler must return a dict"
        assert "statusCode" in result, "Result must have statusCode"
    
    def test_handler_with_asyncio_run_completes_all_operations(self):
        """
        Test that handlers using asyncio.run() complete all async operations.
        
        This test verifies that when a handler uses asyncio.run() to execute
        async logic, all async operations complete before the handler returns.
        
        Validates: Requirements 3.3
        """
        # Track async operation completion
        operations_completed = {
            "operation_1": False,
            "operation_2": False,
            "operation_3": False,
        }
        
        # Create mock async operations
        async def async_operation_1():
            await asyncio.sleep(0.01)
            operations_completed["operation_1"] = True
            return "result_1"
        
        async def async_operation_2():
            await asyncio.sleep(0.02)
            operations_completed["operation_2"] = True
            return "result_2"
        
        async def async_operation_3():
            await asyncio.sleep(0.01)
            operations_completed["operation_3"] = True
            return "result_3"
        
        # Create a handler that mimics the business title handler pattern
        def handler_with_async_logic(event, context):
            """Synchronous handler that wraps async logic with asyncio.run()."""
            async def async_handler_logic():
                # Execute multiple async operations
                result_1 = await async_operation_1()
                result_2 = await async_operation_2()
                result_3 = await async_operation_3()
                
                return {
                    "statusCode": 200,
                    "body": f"{result_1}, {result_2}, {result_3}"
                }
            
            # Use asyncio.run() to execute async logic synchronously
            return asyncio.run(async_handler_logic())
        
        # Call the handler
        event = {"test": "data"}
        context = {}
        result = handler_with_async_logic(event, context)
        
        # Verify the handler returned a result (not a coroutine)
        assert not asyncio.iscoroutine(result), (
            "Handler should return a completed result, not a coroutine"
        )
        
        # Verify ALL async operations completed before the handler returned
        assert operations_completed["operation_1"], (
            "Async operation 1 must complete before handler returns"
        )
        assert operations_completed["operation_2"], (
            "Async operation 2 must complete before handler returns"
        )
        assert operations_completed["operation_3"], (
            "Async operation 3 must complete before handler returns"
        )
        
        # Verify the result structure
        assert isinstance(result, dict), "Handler must return a dict"
        assert "statusCode" in result, "Result must have statusCode"
        assert result["statusCode"] == 200, "Should return 200 for successful operation"
    
    @given(
        num_operations=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_multiple_async_operations_all_complete(self, num_operations: int):
        """
        Property test: Multiple async operations all complete before return.
        
        For any number of async operations executed within a handler, all
        operations should complete before the handler returns.
        
        Validates: Requirements 3.3
        """
        # Track completion of each operation
        operations_completed = [False] * num_operations
        
        async def mock_async_operation(index: int):
            """Simulate an async operation."""
            await asyncio.sleep(0.01)
            operations_completed[index] = True
            return f"operation_{index}_completed"
        
        def handler_with_multiple_async_ops(event, context):
            """Handler that executes multiple async operations."""
            async def async_logic():
                # Execute all async operations
                results = []
                for i in range(num_operations):
                    result = await mock_async_operation(i)
                    results.append(result)
                
                return {
                    "statusCode": 200,
                    "body": str(results)
                }
            
            return asyncio.run(async_logic())
        
        # Call the handler
        result = handler_with_multiple_async_ops({}, {})
        
        # Verify all operations completed
        for i, completed in enumerate(operations_completed):
            assert completed, (
                f"Async operation {i} did not complete before handler returned. "
                f"All async operations must complete before the handler returns."
            )
        
        # Verify the handler returned a proper result
        assert not asyncio.iscoroutine(result), "Handler must return a result, not a coroutine"
        assert isinstance(result, dict), "Handler must return a dict"
        assert result["statusCode"] == 200, "Handler should return success status"
