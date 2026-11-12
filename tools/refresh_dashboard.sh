#!/bin/bash
set -euo pipefail

# refresh_dashboard.sh - Generate and refresh Builder system dashboard
# Creates HTML dashboard with metrics, status, and recent activity

BUILDER_ROOT="$HOME/Catalyst"
TOOLS="$BUILDER_ROOT/tools"
REGISTRY_PATH="$BUILDER_ROOT/registry"
DASHBOARD_PATH="$REGISTRY_PATH/dashboard"

# Load configuration - use defaults if load_config.sh is missing
if [ -f "$TOOLS/load_config.sh" ]; then
    source "$TOOLS/load_config.sh" 2>/dev/null || true
else
    # Default configuration values
    BUILDER_LANES="${BUILDER_LANES:-standard,standard}"
    BUILDER_DEFAULT_LANE="${BUILDER_DEFAULT_LANE:-standard}"
    BUILDER_BACKUP_ENABLED="${BUILDER_BACKUP_ENABLED:-true}"
    BUILDER_PREP_BUDGET_MS="${BUILDER_PREP_BUDGET_MS:-2000}"
    BUILDER_PLANNER_BUDGET_MS="${BUILDER_PLANNER_BUDGET_MS:-5000}"
    BUILDER_EXEC_BUDGET_MS="${BUILDER_EXEC_BUDGET_MS:-10000}"
    BUILDER_LOG_LEVEL="${BUILDER_LOG_LEVEL:-INFO}"
fi

echo "🔄 Refreshing Builder Dashboard..."

# Best-effort metrics rollup if available
if [ -f "$TOOLS/metrics_rollup.py" ]; then
  python3 "$TOOLS/metrics_rollup.py" || true
fi

# Ensure registry dashboard directory exists
mkdir -p "$DASHBOARD_PATH"

# Generate dashboard HTML
generate_dashboard() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    local current_date=$(date "+%Y-%m-%d %H:%M:%S")
    
    # Count capsules by lane
    local standard_count=0
    local standard_count=0
    local total_capsules=0
    
    if [ -d "$BUILDER_ROOT/capsules" ]; then
        for capsule in "$BUILDER_ROOT/capsules"/*; do
            if [ -d "$capsule" ]; then
                ((total_capsules++))
                
                # Check lane via our lane detection logic
                if [ -f "$capsule/capsule.json" ]; then
                    local lane=$(python3 -c "
import json, sys
try:
    with open('$capsule/capsule.json') as f:
        data = json.load(f)
except:
    print('standard')
" 2>/dev/null || echo "standard")
                else
                    lane="standard"
                fi
                
                if [[ "$lane" == "standard" ]]; then
                    ((standard_count++))
                else
                    ((standard_count++))
                fi
            fi
        done
    fi
    
    # Recent events count
    local recent_events=0
    if [ -f "$BUILDER_ROOT/logs/events.log" ]; then
        recent_events=$(tail -100 "$BUILDER_ROOT/logs/events.log" 2>/dev/null | wc -l | tr -d ' ')
    elif [ -f "$BUILDER_ROOT/registry/events.jsonl" ]; then
        recent_events=$(tail -100 "$BUILDER_ROOT/registry/events.jsonl" 2>/dev/null | wc -l | tr -d ' ')
    fi
    
    # System health checks
    local health_score=100
    local health_issues=()
    
    # Check essential files
    if [ ! -f "$BUILDER_ROOT/CLAUDE.md" ]; then
        health_issues+=("Missing CLAUDE.md")
        ((health_score -= 20))
    fi
    
    if [ ! -f "$BUILDER_ROOT/capsules/builder-system/tools/sys.py" ]; then
        health_issues+=("Missing Catalyst tools")
        ((health_score -= 30))
    fi
    
    if [ ! -f "$BUILDER_ROOT/capsules/builder-system/config/guardrails.yaml" ]; then
        health_issues+=("Missing governance framework")
        ((health_score -= 20))
    fi
    
    # Generate HTML
    cat > "$DASHBOARD_PATH/index.html" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catalyst Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .header .timestamp {
            font-size: 0.9em;
            opacity: 0.7;
            margin-top: 10px;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card h3 {
            color: #4a5568;
            margin-bottom: 15px;
            font-size: 1.3em;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 8px;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 12px 0;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            font-weight: 500;
            color: #4a5568;
        }
        
        .metric-value {
            font-weight: 700;
            font-size: 1.1em;
        }
        
        .metric-value.success { color: #38a169; }
        .metric-value.warning { color: #d69e2e; }
        .metric-value.danger { color: #e53e3e; }
        
        .health-score {
            text-align: center;
            margin: 20px 0;
        }
        
        .health-circle {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            margin: 0 auto 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2em;
            font-weight: bold;
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .health-excellent { background: linear-gradient(45deg, #38a169, #48bb78); }
        .health-good { background: linear-gradient(45deg, #38a169, #68d391); }
        .health-warning { background: linear-gradient(45deg, #d69e2e, #f6d55c); }
        .health-danger { background: linear-gradient(45deg, #e53e3e, #fc8181); }
        
        .issues-list {
            list-style: none;
            margin-top: 15px;
        }
        
        .issues-list li {
            background: #fed7d7;
            color: #c53030;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 6px;
            border-left: 4px solid #e53e3e;
        }
        
        .lanes-chart {
            display: flex;
            height: 40px;
            border-radius: 20px;
            overflow: hidden;
            margin: 15px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .lane-fast {
            background: linear-gradient(90deg, #4299e1, #63b3ed);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }
        
        .lane-deep {
            background: linear-gradient(90deg, #38a169, #48bb78);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }
        
        .footer {
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 40px;
            padding: 20px;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🏗️ Catalyst</h1>
            <div class="subtitle">Two-Lane Workflow Dashboard</div>
            <div class="timestamp">Last updated: $current_date</div>
        </header>
        
        <div class="dashboard-grid">
            <div class="card">
                <h3>📊 System Metrics</h3>
                <div class="metric">
                    <span class="metric-label">Total Capsules</span>
                    <span class="metric-value">$total_capsules</span>
                </div>
                <div class="metric">
                    <span class="metric-label">standard</span>
                    <span class="metric-value success">$standard_count</span>
                </div>
                <div class="metric">
                    <span class="metric-label">standard</span>
                    <span class="metric-value success">$standard_count</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Recent Events</span>
                    <span class="metric-value">$recent_events</span>
                </div>
                
                <div class="lanes-chart">
EOF

    # Calculate lane percentages
    local fast_percentage=0
    local deep_percentage=100
    
    if [ $total_capsules -gt 0 ]; then
        fast_percentage=$((standard_count * 100 / total_capsules))
        deep_percentage=$((standard_count * 100 / total_capsules))
    fi
    
    if [ $fast_percentage -gt 0 ]; then
        echo "                    <div class=\"lane-fast\" style=\"width: ${fast_percentage}%\">Fast: $standard_count</div>" >> "$DASHBOARD_PATH/index.html"
    fi
    
    if [ $deep_percentage -gt 0 ]; then
        echo "                    <div class=\"lane-deep\" style=\"width: ${deep_percentage}%\">Deep: $standard_count</div>" >> "$DASHBOARD_PATH/index.html"
    fi
    
    # Determine health class
    local health_class="health-excellent"
    if [ $health_score -lt 90 ]; then
        health_class="health-good"
    fi
    if [ $health_score -lt 70 ]; then
        health_class="health-warning"  
    fi
    if [ $health_score -lt 50 ]; then
        health_class="health-danger"
    fi
    
    cat >> "$DASHBOARD_PATH/index.html" <<EOF
                </div>
            </div>
            
            <div class="card">
                <h3>🏥 System Health</h3>
                <div class="health-score">
                    <div class="health-circle $health_class">
                        ${health_score}%
                    </div>
                    <div>Overall System Health</div>
                </div>
EOF

    if [ ${#health_issues[@]} -gt 0 ]; then
        echo "                <ul class=\"issues-list\">" >> "$DASHBOARD_PATH/index.html"
        for issue in "${health_issues[@]}"; do
            echo "                    <li>$issue</li>" >> "$DASHBOARD_PATH/index.html"
        done
        echo "                </ul>" >> "$DASHBOARD_PATH/index.html"
    fi
    
    cat >> "$DASHBOARD_PATH/index.html" <<EOF
            </div>
            
            <div class="card">
                <h3>⚙️ Configuration</h3>
                <div class="metric">
                    <span class="metric-label">Valid Lanes</span>
                    <span class="metric-value">$BUILDER_LANES</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Default Lane</span>
                    <span class="metric-value success">$BUILDER_DEFAULT_LANE</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Dashboard Updates</span>
                    <span class="metric-value success">Enabled</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Backup System</span>
                    <span class="metric-value success">$BUILDER_BACKUP_ENABLED</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📈 Performance</h3>
                <div class="metric">
                    <span class="metric-label">Prep Budget</span>
                    <span class="metric-value">${BUILDER_PREP_BUDGET_MS}ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Planner Budget</span>
                    <span class="metric-value">${BUILDER_PLANNER_BUDGET_MS}ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Exec Budget</span>
                    <span class="metric-value">${BUILDER_EXEC_BUDGET_MS}ms</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Log Level</span>
                    <span class="metric-value">$BUILDER_LOG_LEVEL</span>
                </div>
            </div>
        </div>
        
        <footer class="footer">
            <p>🚀 Catalyst v2.1.0 - Hybrid Agent OS for Rapid Creation</p>
            <p>Generated at $timestamp</p>
        </footer>
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(function() {
            window.location.reload();
        }, 300000);
        
        // Add some interactivity
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-5px)';
                this.style.transition = 'transform 0.3s ease';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    </script>
</body>
</html>
EOF

    echo "✅ Dashboard generated at $DASHBOARD_PATH/index.html"
}

# Generate the dashboard
generate_dashboard

# Log dashboard refresh
if [ -f "$BUILDER_ROOT/global/events.log" ]; then
    refresh_event=$(cat <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")",
  "event_type": "dashboard_refresh",
  "status": "completed",
  "message": "Dashboard refreshed successfully",
  "path": "$DASHBOARD_PATH/index.html"
}
EOF
    )
    echo "$refresh_event" >> "$BUILDER_ROOT/global/events.log"
fi

echo "🎯 Builder Dashboard ready at: $DASHBOARD_PATH/index.html"
echo "🌐 Open with: open $DASHBOARD_PATH/index.html"





