import subprocess
import sys


def test_validator_strict_passes():
    # Ruft den Validator strikt auf und erwartet Exit-Code 0
    res = subprocess.run([
        sys.executable, 'validate_callbacks.py', '--strict'
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr


