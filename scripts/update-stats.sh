../.venv/bin/python -u - <<'PY'
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cron
cfg = cron.load_core_config()
fn = cfg.get('file_name')
ok = cron.update_statistics_file(fn)
print('update_statistics_file:', ok)
p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'statistics.json')
if os.path.exists(p):
    d = json.load(open(p, 'r', encoding='utf-8'))
    print(json.dumps({k: d.get(k) for k in [
        'total_recording_minutes',
        'overall_availability_percentage_rollup',
        'total_incidents',
        'calculated_at'
    ]}, ensure_ascii=False))
PY
