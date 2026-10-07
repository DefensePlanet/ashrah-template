"""
Normalizer for API test output.

Parses API test failures (pytest with requests library) and extracts
structured error information about endpoint failures.
"""

import re
import json
from typing import Dict, List, Any
from ..feedback_schema import ValidationFeedback, ErrorInfo, SeverityLevel


class ApiTestNormalizer:
    """Parse and normalize API test output (pytest + requests)."""

    # Pytest test failure patterns
    TEST_FAILURE_PATTERN = re.compile(
        r'^(?P<file>[^\s]+)::(?P<test>\S+)\s+FAILED'
    )

    # HTTP error patterns
    STATUS_CODE_PATTERN = re.compile(
        r'(?:AssertionError|assert)\s+(?P<actual>\d+)\s*(?:!=|==)\s*(?P<expected>\d+)'
    )

    ENDPOINT_PATTERN = re.compile(
        r'(?:GET|POST|PUT|DELETE|PATCH)\s+(?P<endpoint>/[^\s]+)'
    )

    # Common API error categories
    ERROR_CATEGORIES = {
        '400': 'bad_request',
        '401': 'unauthorized',
        '403': 'forbidden',
        '404': 'not_found',
        '405': 'method_not_allowed',
        '422': 'validation_error',
        '500': 'internal_server_error',
        '502': 'bad_gateway',
        '503': 'service_unavailable',
        'timeout': 'timeout',
        'connection': 'connection_error',
    }

    def normalize(self, validation_output: Dict[str, Any]) -> ValidationFeedback:
        """
        Normalize pytest API test output into structured feedback.

        Args:
            validation_output: Dict with 'stdout', 'stderr', 'exit_code'

        Returns:
            ValidationFeedback with parsed API test failures
        """
        stdout = validation_output.get('stdout', '')
        stderr = validation_output.get('stderr', '')
        exit_code = validation_output.get('exit_code', 0)

        # Combine output
        output = stdout + '\n' + stderr

        errors = []
        warnings = []

        # Parse test failures
        failures = self._extract_test_failures(output)

        for failure in failures:
            error_info = ErrorInfo(
                type=self._categorize_error(failure),
                message=failure['message'],
                file=failure.get('file', ''),
                line=failure.get('line', 0),
                severity=self._determine_severity(failure),
                suggestion=self._generate_suggestion(failure),
                metadata={
                    'test_name': failure.get('test', ''),
                    'endpoint': failure.get('endpoint', ''),
                    'expected_status': failure.get('expected_status'),
                    'actual_status': failure.get('actual_status'),
                    'error_type': failure.get('error_type')
                }
            )

            if error_info.severity == SeverityLevel.ERROR:
                errors.append(error_info)
            else:
                warnings.append(error_info)

        success = exit_code == 0 and len(errors) == 0

        # Extract test summary
        summary = self._extract_test_summary(output)

        return ValidationFeedback(
            tool_name='pytest_api',
            success=success,
            errors=errors,
            warnings=warnings,
            metadata={
                'exit_code': exit_code,
                'total_tests': summary.get('total', 0),
                'passed': summary.get('passed', 0),
                'failed': summary.get('failed', 0),
                'errors': summary.get('errors', 0)
            }
        )

    def _extract_test_failures(self, output: str) -> List[Dict[str, Any]]:
        """Extract test failure details from pytest output."""
        failures = []
        lines = output.splitlines()

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for FAILED test
            match = self.TEST_FAILURE_PATTERN.search(line)
            if match:
                failure = {
                    'file': match.group('file'),
                    'test': match.group('test'),
                    'message': line.strip()
                }

                # Look ahead for error details
                j = i + 1
                context = []
                while j < len(lines) and j < i + 30:  # Look 30 lines ahead
                    context.append(lines[j])
                    j += 1

                context_str = '\n'.join(context)

                # Extract status code error
                status_match = self.STATUS_CODE_PATTERN.search(context_str)
                if status_match:
                    failure['expected_status'] = int(status_match.group('expected'))
                    failure['actual_status'] = int(status_match.group('actual'))
                    failure['error_type'] = 'status_code_mismatch'

                # Extract endpoint
                endpoint_match = self.ENDPOINT_PATTERN.search(context_str)
                if endpoint_match:
                    failure['endpoint'] = endpoint_match.group('endpoint')

                # Check for common error types
                if 'ConnectionError' in context_str:
                    failure['error_type'] = 'connection_error'
                elif 'Timeout' in context_str:
                    failure['error_type'] = 'timeout'
                elif 'JSONDecodeError' in context_str:
                    failure['error_type'] = 'json_parse_error'
                elif 'ValidationError' in context_str:
                    failure['error_type'] = 'validation_error'

                failures.append(failure)

            i += 1

        return failures

    def _extract_test_summary(self, output: str) -> Dict[str, int]:
        """Extract test summary from pytest output."""
        summary = {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0}

        # Look for pytest summary line
        # e.g., "= 5 failed, 10 passed in 2.30s ="
        summary_pattern = re.compile(
            r'(?P<failed>\d+)\s+failed.*?(?P<passed>\d+)\s+passed'
        )

        match = summary_pattern.search(output)
        if match:
            summary['failed'] = int(match.group('failed'))
            summary['passed'] = int(match.group('passed'))
            summary['total'] = summary['failed'] + summary['passed']

        return summary

    def _categorize_error(self, failure: Dict[str, Any]) -> str:
        """Categorize error based on failure details."""
        error_type = failure.get('error_type')

        if error_type:
            return error_type

        # Categorize by status code
        status = str(failure.get('actual_status', ''))
        for code_prefix, category in self.ERROR_CATEGORIES.items():
            if status.startswith(code_prefix):
                return category

        return 'unknown_api_error'

    def _determine_severity(self, failure: Dict[str, Any]) -> SeverityLevel:
        """Determine severity based on failure type."""
        error_type = failure.get('error_type', '')
        actual_status = failure.get('actual_status')

        # Critical errors that block functionality
        critical_errors = ['connection_error', 'timeout', 'internal_server_error']
        critical_statuses = [500, 502, 503]

        if error_type in critical_errors or actual_status in critical_statuses:
            return SeverityLevel.ERROR

        # Client errors are usually less critical
        if actual_status and 400 <= actual_status < 500:
            return SeverityLevel.WARNING

        return SeverityLevel.ERROR

    def _generate_suggestion(self, failure: Dict[str, Any]) -> str:
        """Generate fix suggestion based on failure type."""
        error_type = failure.get('error_type', '')
        actual_status = failure.get('actual_status')
        expected_status = failure.get('expected_status')
        endpoint = failure.get('endpoint', '')

        suggestions = {
            'status_code_mismatch': f'Check endpoint {endpoint} returns {expected_status}, got {actual_status}',
            'connection_error': 'Ensure API server is running and endpoint is accessible',
            'timeout': 'Optimize endpoint performance or increase timeout threshold',
            'json_parse_error': 'Verify endpoint returns valid JSON response',
            'validation_error': 'Check request payload matches expected schema',
            'not_found': f'Verify endpoint {endpoint} exists and route is registered',
            'unauthorized': 'Check authentication credentials and headers',
            'forbidden': 'Verify user has required permissions for this endpoint',
            'bad_request': 'Review request payload for missing or invalid fields',
            'internal_server_error': 'Check server logs for exception details',
        }

        # Try error type first
        if error_type in suggestions:
            return suggestions[error_type]

        # Try status code category
        if actual_status:
            status_key = str(actual_status)
            category = self.ERROR_CATEGORIES.get(status_key)
            if category and category in suggestions:
                return suggestions[category]

        return 'Review test failure output and check endpoint implementation'


# Register with feedback registry
def register(registry):
    """Register API test normalizer with the feedback registry."""
    from ..feedback_registry import FeedbackRegistry
    registry.register_normalizer('pytest_api', ApiTestNormalizer())
