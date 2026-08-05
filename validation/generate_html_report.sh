#!/bin/bash
#
# Generate an HTML validation summary.
#

set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <SUMMARY_JSON> <MASTER_LOG> <OUTPUT_HTML>"
    exit 1
fi

SUMMARY_JSON="$1"
MASTER_LOG="$2"
OUTPUT_HTML="$3"

if [[ ! -f "$SUMMARY_JSON" ]]; then
    echo "Error: Summary JSON not found: $SUMMARY_JSON"
    exit 1
fi
if [[ ! -f "$MASTER_LOG" ]]; then
    echo "Error: Master log not found: $MASTER_LOG"
    exit 1
fi

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
else
    echo "Error: Python 3 not found"
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT_HTML")"
OUTPUT_TMP="$(mktemp "${OUTPUT_HTML}.tmp.XXXXXX")"
cleanup() {
    rm -f -- "$OUTPUT_TMP"
}
trap cleanup EXIT

cat > "$OUTPUT_TMP" << 'EOF'
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
        .header, .summary, .phase {
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }
        .summary, .phase {
            background: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
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
        }
        .status.passed { background: #d4edda; color: #155724; }
        .status.failed { background: #f8d7da; color: #721c24; }
        .status.skipped { background: #fff3cd; color: #856404; }
        .status.unknown { background: #e2e3e5; color: #383d41; }
        .overall-status {
            text-align: center;
            padding: 30px;
            font-size: 2em;
            font-weight: bold;
        }
        .overall-status.pass { color: #28a745; }
        .overall-status.fail { color: #dc3545; }
    </style>
</head>
<body>
    <div class="header">
        <h1>WiFiT v3.0.0-rc.1</h1>
        <p>Hardware Validation Report</p>
    </div>
EOF

"$PYTHON_BIN" - "$SUMMARY_JSON" >> "$OUTPUT_TMP" << 'PYEOF'
import html
import json
import sys

summary_file = sys.argv[1]
with open(summary_file, encoding="utf-8") as source:
    data = json.load(source)

validation_run = data["validation_run"]
summary = data["summary"]
phases = data["phases"]


def escape(value):
    return html.escape(str(value), quote=True)

print('<div class="summary">')
print('<h2>Validation Summary</h2>')
print(f'<p><strong>Target BSSID:</strong> {escape(validation_run["target_bssid"])}</p>')
print(f'<p><strong>Timestamp:</strong> {escape(validation_run["timestamp"])}</p>')
print(f'<p><strong>WiFiT Version:</strong> {escape(validation_run["wifit_version"])}</p>')
print(f'<p><strong>Branch:</strong> {escape(validation_run["branch"])}</p>')
print(
    f'<p><strong>Phases Passed:</strong> '
    f'{escape(summary["passed"])} / {escape(summary["total_phases"])}</p>'
)
print('</div>')

phase_names = {
    "phase_1": "Environment Setup",
    "phase_2": "Scanner Validation",
    "phase_3": "PIN Generation",
    "phase_4": "Process Management",
    "phase_5": "WPS Attack Validation",
    "phase_6": "Reporter Validation",
    "phase_7": "Stress Testing",
    "phase_8": "Recovery & Cleanup",
}
status_classes = {"PASSED": "passed", "FAILED": "failed", "SKIPPED": "skipped"}

print('<div class="phases">')
print('<h2>Phase Results</h2>')
for phase_key, status in phases.items():
    phase_name = phase_names.get(phase_key, phase_key)
    status_text = str(status).upper()
    status_class = status_classes.get(status_text, "unknown")
    print('<div class="phase"><div class="phase-header">')
    print(f'<h3>{escape(phase_name)}</h3>')
    print(f'<span class="status {status_class}">{escape(status_text)}</span>')
    print('</div></div>')
print('</div>')

overall = str(summary["overall_status"]).upper()
overall_class = "pass" if overall == "PASS" else "fail"
print(f'<div class="overall-status {overall_class}">{escape(overall)}</div>')
PYEOF

cat >> "$OUTPUT_TMP" << 'EOF'
</body>
</html>
EOF

chmod 600 "$OUTPUT_TMP"
mv -f -- "$OUTPUT_TMP" "$OUTPUT_HTML"
trap - EXIT

echo "HTML report generated: $OUTPUT_HTML"
