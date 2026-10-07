#!/usr/bin/env python3
"""
Browser Automation Testing Framework
Tests registration_automation.py against various sites to measure and improve anti-bot detection
"""

import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TestSite:
    """Configuration for a test site"""
    name: str
    url: str
    protection_level: str  # cooperative, moderate, aggressive
    captcha_type: Optional[str] = None  # recaptcha_v2, recaptcha_v3, hcaptcha, turnstile, none
    requires_phone: bool = False
    requires_verification: bool = True
    notes: str = ""


@dataclass
class TestResult:
    """Result of a registration test"""
    site_name: str
    timestamp: str
    success: bool
    captcha_encountered: bool
    captcha_solved: bool
    bot_detection_triggered: bool
    error_message: Optional[str]
    execution_time_seconds: float
    screenshots: List[str]
    detection_signals: List[str]  # What triggered detection if any


class RegistrationTester:
    """Framework for testing registration automation"""

    # Test site definitions by protection level
    TEST_SITES = {
        'cooperative': [
            TestSite(
                name='GitHub',
                url='https://github.com/signup',
                protection_level='cooperative',
                captcha_type='recaptcha_v2',
                notes='Standard form, cooperative with automation'
            ),
            TestSite(
                name='GitLab',
                url='https://gitlab.com/users/sign_up',
                protection_level='cooperative',
                captcha_type='recaptcha_v2',
                notes='Standard form, email verification required'
            ),
        ],
        'moderate': [
            TestSite(
                name='Shopify',
                url='https://accounts.shopify.com/signup',
                protection_level='moderate',
                captcha_type='hcaptcha',
                notes='hCaptcha, moderate bot protection'
            ),
            TestSite(
                name='OpenAI',
                url='https://platform.openai.com/signup',
                protection_level='moderate',
                captcha_type='turnstile',
                notes='Cloudflare Turnstile protection'
            ),
        ],
        'aggressive': [
            TestSite(
                name='Instagram',
                url='https://www.instagram.com/accounts/emailsignup/',
                protection_level='aggressive',
                captcha_type='recaptcha_v2',
                requires_phone=True,
                notes='Aggressive bot detection, phone verification'
            ),
            TestSite(
                name='Facebook',
                url='https://www.facebook.com/reg/',
                protection_level='aggressive',
                captcha_type='custom',
                requires_phone=True,
                notes='Extremely aggressive detection'
            ),
        ]
    }

    def __init__(self, results_dir: Path = None):
        self.results_dir = results_dir or Path('{{CATALYST_ROOT}}/testing/registration-tests')
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.results_file = self.results_dir / 'test_results.jsonl'
        self.metrics_file = self.results_dir / 'metrics_summary.json'

    def run_registration_test(self, site: TestSite, email: str, password: str,
                             username: Optional[str] = None) -> TestResult:
        """
        Run registration test on a single site

        Args:
            site: TestSite configuration
            email: Email alias to use
            password: Password to use
            username: Optional username

        Returns:
            TestResult with outcome and metrics
        """

        logger.info(f"🧪 Testing {site.name} ({site.protection_level})")

        start_time = time.time()
        detection_signals = []

        # Build command
        cmd = [
            'python3',
            '{{CATALYST_ROOT}}/tools/registration_automation.py',
            site.url,
            '--email', email,
            '--password', password
        ]

        if username:
            cmd.extend(['--username', username])

        # Execute registration
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            execution_time = time.time() - start_time

            # Parse output
            output = result.stdout

            # Detect success/failure
            success = '✅ SUCCESS' in output or result.returncode == 0

            # Detect CAPTCHA
            captcha_encountered = 'CAPTCHA detected' in output or 'CAPTCHA' in output
            captcha_solved = 'CAPTCHA solved' in output or captcha_encountered and success

            # Detect bot detection signals
            bot_detected = any([
                'bot' in output.lower(),
                'blocked' in output.lower(),
                'access denied' in output.lower(),
                'cloudflare' in output.lower() and 'challenge' in output.lower(),
                'suspicious activity' in output.lower()
            ])

            if bot_detected:
                if 'cloudflare' in output.lower():
                    detection_signals.append('cloudflare_challenge')
                if 'blocked' in output.lower():
                    detection_signals.append('access_blocked')
                if 'suspicious' in output.lower():
                    detection_signals.append('suspicious_activity_flag')

            # Extract error message
            error_message = None
            if not success:
                # Try to extract error from output
                if '❌' in output:
                    error_lines = [line for line in output.split('\n') if '❌' in line]
                    if error_lines:
                        error_message = error_lines[0]
                elif result.stderr:
                    error_message = result.stderr[:200]
                else:
                    error_message = "Registration failed - check logs"

            # Find screenshots
            screenshots = []
            import re
            screenshot_pattern = r'/tmp/registration_[^\.]+\.png'
            screenshots = re.findall(screenshot_pattern, output)

            test_result = TestResult(
                site_name=site.name,
                timestamp=datetime.now().isoformat(),
                success=success,
                captcha_encountered=captcha_encountered,
                captcha_solved=captcha_solved,
                bot_detection_triggered=bot_detected,
                error_message=error_message,
                execution_time_seconds=execution_time,
                screenshots=screenshots,
                detection_signals=detection_signals
            )

            logger.info(f"  Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
            if captcha_encountered:
                logger.info(f"  CAPTCHA: {'✅ Solved' if captcha_solved else '❌ Failed'}")
            if bot_detected:
                logger.warning(f"  ⚠️  Bot detection triggered: {', '.join(detection_signals)}")

            return test_result

        except subprocess.TimeoutExpired:
            logger.error(f"  ⏱️  Test timeout after 120 seconds")
            return TestResult(
                site_name=site.name,
                timestamp=datetime.now().isoformat(),
                success=False,
                captcha_encountered=False,
                captcha_solved=False,
                bot_detection_triggered=False,
                error_message="Test timeout after 120 seconds",
                execution_time_seconds=120.0,
                screenshots=[],
                detection_signals=['timeout']
            )

        except Exception as e:
            logger.error(f"  ❌ Test error: {e}")
            return TestResult(
                site_name=site.name,
                timestamp=datetime.now().isoformat(),
                success=False,
                captcha_encountered=False,
                captcha_solved=False,
                bot_detection_triggered=False,
                error_message=str(e),
                execution_time_seconds=time.time() - start_time,
                screenshots=[],
                detection_signals=['test_error']
            )

    def save_result(self, result: TestResult):
        """Save test result to JSONL file"""
        with open(self.results_file, 'a') as f:
            f.write(json.dumps(asdict(result)) + '\n')

    def load_results(self) -> List[TestResult]:
        """Load all test results from file"""
        results = []
        if self.results_file.exists():
            with open(self.results_file, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    results.append(TestResult(**data))
        return results

    def calculate_metrics(self) -> Dict:
        """Calculate aggregate metrics from test results"""
        results = self.load_results()

        if not results:
            return {}

        # Overall metrics
        total_tests = len(results)
        successful = sum(1 for r in results if r.success)
        captcha_encountered = sum(1 for r in results if r.captcha_encountered)
        captcha_solved = sum(1 for r in results if r.captcha_solved)
        bot_detected = sum(1 for r in results if r.bot_detection_triggered)

        # By protection level
        by_level = {}
        for level in ['cooperative', 'moderate', 'aggressive']:
            level_sites = [site.name for site in self.get_sites_by_level(level)]
            level_results = [r for r in results if r.site_name in level_sites]

            if level_results:
                by_level[level] = {
                    'total': len(level_results),
                    'success': sum(1 for r in level_results if r.success),
                    'success_rate': sum(1 for r in level_results if r.success) / len(level_results),
                    'bot_detection_rate': sum(1 for r in level_results if r.bot_detection_triggered) / len(level_results),
                    'avg_execution_time': sum(r.execution_time_seconds for r in level_results) / len(level_results)
                }

        # By site
        by_site = {}
        for result in results:
            if result.site_name not in by_site:
                by_site[result.site_name] = {
                    'attempts': 0,
                    'successes': 0,
                    'captcha_encounters': 0,
                    'captcha_solves': 0,
                    'bot_detections': 0
                }

            by_site[result.site_name]['attempts'] += 1
            if result.success:
                by_site[result.site_name]['successes'] += 1
            if result.captcha_encountered:
                by_site[result.site_name]['captcha_encounters'] += 1
            if result.captcha_solved:
                by_site[result.site_name]['captcha_solves'] += 1
            if result.bot_detection_triggered:
                by_site[result.site_name]['bot_detections'] += 1

        # Calculate rates
        for site_data in by_site.values():
            if site_data['attempts'] > 0:
                site_data['success_rate'] = site_data['successes'] / site_data['attempts']
                site_data['detection_rate'] = site_data['bot_detections'] / site_data['attempts']

        metrics = {
            'last_updated': datetime.now().isoformat(),
            'total_tests': total_tests,
            'overall': {
                'success_rate': successful / total_tests if total_tests > 0 else 0,
                'captcha_encounter_rate': captcha_encountered / total_tests if total_tests > 0 else 0,
                'captcha_solve_rate': captcha_solved / captcha_encountered if captcha_encountered > 0 else 0,
                'bot_detection_rate': bot_detected / total_tests if total_tests > 0 else 0
            },
            'by_protection_level': by_level,
            'by_site': by_site
        }

        # Save metrics
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        return metrics

    def get_sites_by_level(self, level: str) -> List[TestSite]:
        """Get test sites for a protection level"""
        return self.TEST_SITES.get(level, [])

    def print_metrics_report(self):
        """Print formatted metrics report"""
        metrics = self.calculate_metrics()

        if not metrics:
            print("No test results yet")
            return

        print("\n" + "="*70)
        print("REGISTRATION AUTOMATION TEST METRICS")
        print("="*70)

        print(f"\nTotal Tests: {metrics['total_tests']}")
        print(f"Last Updated: {metrics['last_updated']}")

        print("\n📊 OVERALL PERFORMANCE")
        print("-" * 70)
        overall = metrics['overall']
        print(f"Success Rate:         {overall['success_rate']:.1%}")
        print(f"Bot Detection Rate:   {overall['bot_detection_rate']:.1%}")
        print(f"CAPTCHA Encounter:    {overall['captcha_encounter_rate']:.1%}")
        print(f"CAPTCHA Solve Rate:   {overall['captcha_solve_rate']:.1%}")

        print("\n🎯 BY PROTECTION LEVEL")
        print("-" * 70)
        for level, data in metrics.get('by_protection_level', {}).items():
            print(f"\n{level.upper()}:")
            print(f"  Tests: {data['total']}")
            print(f"  Success Rate: {data['success_rate']:.1%}")
            print(f"  Bot Detection: {data['bot_detection_rate']:.1%}")
            print(f"  Avg Time: {data['avg_execution_time']:.1f}s")

        print("\n🌐 BY SITE")
        print("-" * 70)
        for site, data in metrics.get('by_site', {}).items():
            print(f"\n{site}:")
            print(f"  Attempts: {data['attempts']}")
            print(f"  Success Rate: {data['success_rate']:.1%}")
            print(f"  Detection Rate: {data['detection_rate']:.1%}")
            print(f"  CAPTCHA Encounters: {data['captcha_encounters']}")

        print("\n" + "="*70 + "\n")

    def run_test_suite(self, level: str, email_prefix: str):
        """
        Run full test suite for a protection level

        Args:
            level: 'cooperative', 'moderate', or 'aggressive'
            email_prefix: Prefix for generating test emails
        """

        sites = self.get_sites_by_level(level)

        if not sites:
            logger.error(f"No sites defined for level: {level}")
            return

        logger.info(f"\n🚀 Running test suite for {level.upper()} protection level")
        logger.info(f"Sites to test: {', '.join(site.name for site in sites)}\n")

        for i, site in enumerate(sites, 1):
            logger.info(f"[{i}/{len(sites)}] Testing {site.name}...")

            # Generate test credentials
            email = f"{email_prefix}.{site.name.lower()}.test{int(time.time())}@alias.example.com"
            password = f"TestPass{int(time.time())}!"
            username = f"{email_prefix}_{site.name.lower()}"

            # Run test
            result = self.run_registration_test(site, email, password, username)

            # Save result
            self.save_result(result)

            # Wait between tests to avoid rate limiting
            if i < len(sites):
                logger.info(f"  ⏸️  Waiting 10 seconds before next test...\n")
                time.sleep(10)

        logger.info("\n✅ Test suite complete\n")

        # Show updated metrics
        self.print_metrics_report()


def main():
    """CLI interface for testing framework"""
    import argparse

    parser = argparse.ArgumentParser(description="Browser Automation Testing Framework")
    parser.add_argument('action', choices=['test', 'metrics', 'test-suite'])
    parser.add_argument('--level', choices=['cooperative', 'moderate', 'aggressive'],
                       help='Protection level to test')
    parser.add_argument('--site', help='Specific site name to test')
    parser.add_argument('--email', help='Email to use for test')
    parser.add_argument('--password', default='TestPass123!', help='Password to use')
    parser.add_argument('--email-prefix', default='buildertest',
                       help='Email prefix for test suite')

    args = parser.parse_args()

    tester = RegistrationTester()

    if args.action == 'metrics':
        tester.print_metrics_report()

    elif args.action == 'test':
        if not args.site or not args.email:
            print("Error: --site and --email required for single test")
            return 1

        # Find site
        site = None
        for level_sites in tester.TEST_SITES.values():
            for s in level_sites:
                if s.name.lower() == args.site.lower():
                    site = s
                    break

        if not site:
            print(f"Error: Site '{args.site}' not found")
            return 1

        result = tester.run_registration_test(site, args.email, args.password)
        tester.save_result(result)
        tester.print_metrics_report()

    elif args.action == 'test-suite':
        if not args.level:
            print("Error: --level required for test suite")
            return 1

        tester.run_test_suite(args.level, args.email_prefix)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
