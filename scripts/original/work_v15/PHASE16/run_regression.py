import subprocess
r = subprocess.run(
    ["/usr/bin/python3", "-B", "-m", "unittest", "discover",
     "-s", "/home/REDACTED_USER/codex-work/work_v15/PHASE16/REGRESSION_TESTS", "-v"],
    cwd="/home/REDACTED_USER/codex-work", capture_output=True, text=True)
log = r.stdout + r.stderr + f"\nEXIT_CODE={r.returncode}\n"
open("/home/REDACTED_USER/codex-work/work_v15/PHASE16/hermes_regression.log", "w").write(log)
print(log, end="")
