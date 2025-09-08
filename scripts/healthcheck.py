import os
import sys
import urllib.request
import urllib.error


def main() -> int:
    ci = os.getenv("SMOKE_TEST_CI", "SO-0000063")
    url = f"http://localhost:8050/plot?ci={ci}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            status = resp.getcode()
            body = resp.read(4096).decode("utf-8", errors="ignore")
            if status != 200:
                print(f"healthcheck: non-200 status {status}")
                return 1
            # Simple content checks for server errors
            error_markers = [
                "Internal Server Error",
                "Komponente nicht gefunden",
                "Callback error",
            ]
            if any(marker in body for marker in error_markers):
                print("healthcheck: error marker found in response body")
                return 1
            print("healthcheck: ok")
            return 0
    except urllib.error.URLError as e:
        print(f"healthcheck: request failed: {e}")
        return 1
    except Exception as e:
        print(f"healthcheck: unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


