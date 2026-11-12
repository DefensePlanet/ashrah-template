#!/bin/bash
# Quick test script for CAPTCHA solver

echo "🧪 Testing Universal CAPTCHA Solver"
echo "===================================="
echo ""

# Test 1: CAPTCHA Solver on Demo Page
echo "Test 1: Running universal_captcha_solver.py on reCAPTCHA demo..."
cd {{CATALYST_ROOT}}/tools
python3 universal_captcha_solver.py

echo ""
echo "Test complete! Check browser window for results."
echo ""
echo "Next steps:"
echo "1. If test passed, try: python3 account_creator.py create-auto --service github --purpose test"
echo "2. Check /tmp/ for screenshots if issues occur"
echo "3. Review tools/CAPTCHA_IMPLEMENTATION_NOTES.md for architecture details"
