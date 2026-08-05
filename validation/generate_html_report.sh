#!/bin/bash
#
# Generate HTML validation report
#

SUMMARY_JSON="$1"
MASTER_LOG="$2"
OUTPUT_HTML="$3"

if [[ ! -f "$SUMMARY_JSON" ]]; then
    echo "Error: Summary JSON not found: $SUMMARY_JSON"
    exit 1
fi

cat > "$OUTPUT_HTML" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFiT v3.0.0-rc.1 Validation Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .summary {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .phase {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .phase-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .status.passed {
            background: #d4edda;
            color: #155724;
        }
        .status.failed {
            background: #f8d7da;
            color: #721c24;
        }
        .status.skipped {
            background: #fff3cd;
            color: #856404;
        }
        .log-section {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            max-height: 500px;
            overflow-y: auto;
        }
        .overall-status {
            text-align: center;
            padding: 30px;
            font-size: 2em;
            font-weight: bold;
        }
        .overall-status.pass {
            color: #28a745;
        }
        .overall-status.fail {
            color: #dc3545;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ WiFiT v3.0.0-rc.1</h1>
        <p>Hardware Validation Report</p>
    </div>
EOF

# Add summary data
python3 << 'PYEOF' >> "$OUTPUT_HTML"
import json
import sys

summary_file = sys.argv[1]
with open(summary_file) as f:
    data = json.load(f)

print('<div class="summary">')
print(f'<h2>Validation Summary</h2>')
print(f'<p><strong>Target BSSID:</strong> {data["validation_run"]["target_bssid"]}</p>')
print(f'<p><strong>Timestamp:</strong> {data["validation_run"]["timestamp"]}</p>')
print(f'<p><strong>WiFiT Version:</strong> {data["validation_run"]["wifit_version"]}</p>')
print(f'<p><strong>Branch:</strong> {data["validation_run"]["branch"]}</p>')

passed = data["summary"]["passed"]
total = data["summary"]["total_phases"]
overall = data["summary"]["overall_status"]

print(f'<p><strong>Phases Passed:</strong> {passed} / {total}</p>')
print('</div>')

# Phase results
print('<div class="phases">')
print('<h2>Phase Results</h2>')

phase_names = {
    "phase_1": "Environment Setup",
    "phase_2": "Scanner Validation",
    "phase_3": "PIN Generation",
    "phase_4": "Process Management",
    "phase_5": "WPS Attack Validation",
    "phase_6": "Reporter Validation",
    "phase_7": "Stress Testing",
    "phase_8": "Recovery & Cleanup"
}

for phase_key, status in data["phases"].items():
    phase_name = phase_names.get(phase_key, phase_key)
    status_lower = status.lower()
    print(f'<div class="phase">')
    print(f'<div class="phase-header">')
    print(f'<h3>{phase_name}</h3>')
    print(f'<span class="status {status_lower}">{status}</span>')
    print(f'</div>')
    print(f'</div>')

print('</div>')

# Overall status
overall_class = "pass" if overall == "PASS" else "fail"
print(f'<div class="overall-status {overall_class}">')
print(f'{overall}')
print('</div>')
PYEOF "$SUMMARY_JSON"

cat >> "$OUTPUT_HTML" << 'EOF'
</body>
</html>
EOF

echo "HTML report generated: $OUTPUT_HTML"
