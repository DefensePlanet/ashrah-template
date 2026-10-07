"""
Normalizer for ruff linting output.

Parses ruff output and extracts structured linting violations.
"""

import re
import json
from typing import Dict, List, Any
from ..feedback_schema import ValidationFeedback, ErrorInfo, SeverityLevel


class RuffNormalizer:
    """Parse and normalize ruff linting output."""

    # ruff output format: filename:line:col: CODE message
    ERROR_PATTERN = re.compile(
        r'^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<code>[A-Z]+\d+)\s+(?P<message>.+)$'
    )

    # Map ruff error codes to categories
    ERROR_CATEGORIES = {
        'E': 'pycodestyle_error',
        'W': 'pycodestyle_warning',
        'F': 'pyflakes',
        'C': 'complexity',
        'B': 'bugbear',
        'A': 'builtins',
        'I': 'imports',
        'N': 'naming',
        'D': 'docstring',
        'S': 'security',
        'T': 'print_statements',
        'Q': 'quotes',
        'RSE': 'raise_statements',
        'RET': 'return_statements',
        'SIM': 'simplification',
        'ARG': 'unused_arguments',
        'PTH': 'path_usage',
        'ERA': 'commented_code',
        'PL': 'pylint',
    }

    # Fixable vs non-fixable codes
    AUTO_FIXABLE_CODES = {
        'F401',  # unused import
        'I001',  # import sorting
        'E501',  # line too long (sometimes)
        'W291',  # trailing whitespace
        'W292',  # no newline at end of file
        'Q000',  # single vs double quotes
        'COM812',  # trailing comma
    }

    def normalize(self, validation_output: Dict[str, Any]) -> ValidationFeedback:
        """
        Normalize ruff output into structured feedback.

        Args:
            validation_output: Dict with 'stdout', 'stderr', 'exit_code'

        Returns:
            ValidationFeedback with parsed lint violations
        """
        stdout = validation_output.get('stdout', '')
        stderr = validation_output.get('stderr', '')
        exit_code = validation_output.get('exit_code', 0)

        # Try JSON format first (if --format json was used)
        if stdout.strip().startswith('[') or stdout.strip().startswith('{'):
            return self._parse_json_format(stdout, exit_code)

        # Otherwise parse text format
        return self._parse_text_format(stdout + '\n' + stderr, exit_code)

    def _parse_text_format(self, output: str, exit_code: int) -> ValidationFeedback:
        """Parse standard text output from ruff."""
        errors = []
        warnings = []

        for line in output.splitlines():
            match = self.ERROR_PATTERN.match(line.strip())
            if not match:
                continue

            error_data = match.groupdict()
            code = error_data['code']

            error_info = ErrorInfo(
                type=self._categorize_error(code),
                message=f"{code}: {error_data['message']}",
                file=error_data['file'],
                line=int(error_data['line']),
                column=int(error_data['col']),
                severity=self._determine_severity(code),
                suggestion=self._generate_suggestion(code, error_data['message']),
                metadata={
                    'code': code,
                    'auto_fixable': code in self.AUTO_FIXABLE_CODES
                }
            )

            if error_info.severity == SeverityLevel.ERROR:
                errors.append(error_info)
            else:
                warnings.append(error_info)

        success = exit_code == 0 and len(errors) == 0

        return ValidationFeedback(
            tool_name='ruff',
            success=success,
            errors=errors,
            warnings=warnings,
            metadata={
                'exit_code': exit_code,
                'total_violations': len(errors) + len(warnings),
                'auto_fixable_count': sum(1 for e in errors + warnings if e.metadata.get('auto_fixable'))
            }
        )

    def _parse_json_format(self, json_output: str, exit_code: int) -> ValidationFeedback:
        """Parse JSON format output from ruff."""
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError:
            return ValidationFeedback(
                tool_name='ruff',
                success=False,
                errors=[ErrorInfo(
                    type='parse_error',
                    message='Failed to parse ruff JSON output',
                    severity=SeverityLevel.ERROR
                )],
                warnings=[]
            )

        errors = []
        warnings = []

        for item in data:
            code = item.get('code', 'UNKNOWN')

            error_info = ErrorInfo(
                type=self._categorize_error(code),
                message=f"{code}: {item.get('message', '')}",
                file=item.get('filename', ''),
                line=item.get('location', {}).get('row', 0),
                column=item.get('location', {}).get('column', 0),
                severity=self._determine_severity(code),
                suggestion=self._generate_suggestion(code, item.get('message', '')),
                metadata={
                    'code': code,
                    'auto_fixable': item.get('fix') is not None
                }
            )

            if error_info.severity == SeverityLevel.ERROR:
                errors.append(error_info)
            else:
                warnings.append(error_info)

        success = exit_code == 0 and len(errors) == 0

        return ValidationFeedback(
            tool_name='ruff',
            success=success,
            errors=errors,
            warnings=warnings,
            metadata={
                'exit_code': exit_code,
                'total_violations': len(errors) + len(warnings),
                'auto_fixable_count': sum(1 for e in errors + warnings if e.metadata.get('auto_fixable'))
            }
        )

    def _categorize_error(self, code: str) -> str:
        """Categorize error based on ruff error code."""
        # Get the letter prefix (e.g., 'F' from 'F401')
        prefix = ''.join(c for c in code if not c.isdigit())
        return self.ERROR_CATEGORIES.get(prefix, 'unknown_lint_error')

    def _determine_severity(self, code: str) -> SeverityLevel:
        """Determine severity based on error code."""
        # Errors that should block execution
        blocking_codes = ['F', 'E9', 'B9', 'S']

        prefix = ''.join(c for c in code if not c.isdigit())

        if any(code.startswith(bc) for bc in blocking_codes):
            return SeverityLevel.ERROR
        else:
            return SeverityLevel.WARNING

    def _generate_suggestion(self, code: str, message: str) -> str:
        """Generate fix suggestion based on error code."""

        suggestions = {
            'F401': 'Remove unused import or use the imported module',
            'F841': 'Remove unused variable or use it in the code',
            'E501': 'Break line into multiple lines or refactor expression',
            'I001': 'Run ruff with --fix to auto-sort imports',
            'N806': 'Use lowercase variable name following PEP 8',
            'D100': 'Add module docstring at the top of the file',
            'S101': 'Remove assert statement or replace with explicit check',
            'B006': 'Use None as default argument and initialize in function body',
            'B008': 'Move function call outside of default argument',
            'ARG001': 'Remove unused function argument or use it',
            'ARG002': 'Remove unused method argument or use it',
            'PTH123': 'Use pathlib.Path instead of os.path methods',
            'SIM108': 'Use ternary operator for simple if-else assignment',
            'RET504': 'Remove unnecessary variable assignment before return',
        }

        # Check for exact code match
        if code in suggestions:
            return suggestions[code]

        # Check for prefix match
        prefix = ''.join(c for c in code if not c.isdigit())
        if prefix in suggestions:
            return suggestions[prefix]

        # Auto-fixable suggestion
        if code in self.AUTO_FIXABLE_CODES:
            return 'Run ruff with --fix flag to automatically fix this issue'

        return 'Review the lint violation and adjust code accordingly'


# Register with feedback registry
def register(registry):
    """Register ruff normalizer with the feedback registry."""
    from ..feedback_registry import FeedbackRegistry
    registry.register_normalizer('ruff', RuffNormalizer())
