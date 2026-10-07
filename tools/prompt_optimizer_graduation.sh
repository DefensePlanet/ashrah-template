#!/bin/bash
#
# Prompt Optimizer Graduation Scheduler
# Runs daily to evaluate and promote winning prompt variants
#
# Part of Catalyst Prompt Optimization System
# Schedule: Daily at 2:00 AM via launchd
#

set -e

# Configuration
CATALYST_ROOT="{{CATALYST_ROOT}}"
LOG_DIR="${CATALYST_ROOT}/registry/prompt-optimizer"
LOG_FILE="${LOG_DIR}/graduation.log"
PYTHON="/opt/homebrew/bin/python3"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${LOG_FILE}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== Starting Prompt Optimizer Graduation Cycle ==="

# Run graduation via Python
${PYTHON} << 'PYTHON_SCRIPT'
import sys
import json
from datetime import datetime

# Add prompt optimizer to path
sys.path.insert(0, '{{CATALYST_ROOT}}/global/rag/service')

try:
    from prompt_optimizer import PromptOptimizer

    optimizer = PromptOptimizer()

    print("Running graduation cycle...")

    # Get status before graduation
    status_before = optimizer.get_status()
    print(f"Status before: {status_before['total_variants']} variants, "
          f"{status_before['executions_24h']} executions in last 24h")

    # Find candidates first (for logging)
    candidates = optimizer.find_graduation_candidates(window_days=30)
    print(f"Found {len(candidates)} graduation candidates")

    for candidate in candidates:
        print(f"  - {candidate.variant.variant_name}: "
              f"delta={candidate.performance_delta:.2%}, "
              f"confidence={candidate.confidence_score:.2f}, "
              f"status={candidate.status.value}")

    # Run actual graduation
    winners = optimizer.run_graduation(window_days=30, dry_run=False)

    if winners:
        print(f"\nPromoted {len(winners)} variants:")
        for winner in winners:
            print(f"  ✓ Variant {winner.variant_id}: {winner.promotion_reason}")
            print(f"    Confidence: {winner.confidence_score:.2f}, "
                  f"Samples: {winner.sample_size}")
    else:
        print("\nNo variants promoted (none met graduation criteria)")

    # Log results to file
    result = {
        'timestamp': datetime.now().isoformat(),
        'candidates_evaluated': len(candidates),
        'variants_promoted': len(winners),
        'status': status_before,
        'winners': [
            {
                'variant_id': w.variant_id,
                'reason': w.promotion_reason,
                'confidence': w.confidence_score,
                'samples': w.sample_size,
                'delta': w.performance_delta
            }
            for w in winners
        ]
    }

    # Append to results log
    results_file = '{{CATALYST_ROOT}}/registry/prompt-optimizer/graduation_results.jsonl'
    with open(results_file, 'a') as f:
        f.write(json.dumps(result) + '\n')

    print(f"\nResults logged to {results_file}")
    print("Graduation cycle complete.")

except Exception as e:
    print(f"ERROR: Graduation cycle failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    log "Graduation cycle completed successfully"
else
    log "ERROR: Graduation cycle failed"
    exit 1
fi

log "=== Graduation Cycle Finished ==="
