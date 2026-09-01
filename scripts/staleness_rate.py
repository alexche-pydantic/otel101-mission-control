"""Measure Seed 2: how often does the agent present 187-sol-old weather as current?

    uv run python scripts/staleness_rate.py

Needs a model key and the ground station running. Acceptance bar is >=6/10.
Every run is scored automatically and printed, so you can check the scoring yourself.
"""

import pathlib
import re
import sys

from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
load_dotenv()

from agent import mission_control  # noqa: E402

QUESTION = "What's the weather at Elysium Base?"
RUNS = 10

# The payload's readings are real, so quoting them is correct. The bug is quoting
# them as CURRENT: the data is from sol 1102 and the mission is on sol 1289.
REPORTS_VALUES = re.compile(r"63\.2|71\.8|4\.6|705")
# An explicit staleness caveat. Merely citing "sol 1102" is not a caveat — several
# runs print the sol number and still call the reading current.
CAVEATS = re.compile(
    r"stale|outdated|out of date|not current|187|old data|older|previous sol"
    r"|earlier sol|may not reflect|no recent|not the latest",
    re.IGNORECASE,
)

missed = 0
for run in range(1, RUNS + 1):
    answer = mission_control.run_sync(QUESTION).output
    reports = bool(REPORTS_VALUES.search(answer))
    caveated = bool(CAVEATS.search(answer))
    miss = reports and not caveated
    missed += miss
    label = "STALE-AS-CURRENT" if miss else ("caveated" if caveated else "no values")
    print(f"\n--- run {run}: {label}")
    print(answer.strip()[:400])

print(f"\npresented stale data as current: {missed}/{RUNS}")
print("PASS — record this in the README" if missed >= 6 else "BELOW BAR — see README")
