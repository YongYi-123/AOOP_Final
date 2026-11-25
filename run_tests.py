"""Run every test suite in the repository, headless, and print one summary line per suite.

    python run_tests.py                 every suite (the hub's modules run in parallel)
    python run_tests.py arcade_lobby    only the named suites (any of the names in SUITES)
    python run_tests.py -j 4            at most 4 test processes at a time (default: the CPU count)

Each suite runs the way its own package expects (see docs/DEVELOPER_GUIDE.md, "Running the tests"):

* arcade_lobby: one process per test_*.py module, from inside arcade_lobby/
* retro_racer:  unittest discovery inside retro_racer/ (its tests sit next to the code)
* the others:   unittest discovery inside <package>/tests, with the repository root AND arcade_lobby/ on
                PYTHONPATH (NEON BRAWL and the Puzzle Maze draw with the hub's font and Miao Meow sprites)

SDL's dummy video and audio drivers are forced, so no window opens and no sound plays. Tests build their own
temporary profiles: the real saves in arcade_lobby/saves/ and puzzle_maze/profiles/ are never opened.
Exit status 0 only when every suite passed.
"""
import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
LOBBY = os.path.join(ROOT, "arcade_lobby")
PACKAGE_SUITES = ("cat_minesweeper", "cat_territory", "galaxy_defender", "neon_brawl", "neon_cat_maze",
                  "pixel_volleyball", "puzzle_maze")
SUITES = ("arcade_lobby", "retro_racer") + PACKAGE_SUITES
RAN = re.compile(r"^Ran (\d+) tests?", re.M)


def _env():
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (ROOT, LOBBY, env.get("PYTHONPATH")) if p)
    return env


def _run(label, args, cwd):
    """One unittest process. Returns (label, ok, tests run, output)."""
    proc = subprocess.run([sys.executable, "-m", "unittest", *args], cwd=cwd, env=_env(),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    found = RAN.findall(proc.stdout)
    return label, proc.returncode == 0, sum(map(int, found)), proc.stdout


def _jobs(suites):
    """(label, unittest args, working folder) for every process to start."""
    jobs = []
    if "arcade_lobby" in suites:
        for name in sorted(os.listdir(LOBBY)):
            if name.startswith("test_") and name.endswith(".py"):
                jobs.append((f"arcade_lobby/{name[:-3]}", [name[:-3]], LOBBY))
    if "retro_racer" in suites:
        jobs.append(("retro_racer", ["discover", "-p", "test_*.py"], os.path.join(ROOT, "retro_racer")))
    for pkg in PACKAGE_SUITES:
        if pkg in suites:
            jobs.append((pkg, ["discover"], os.path.join(ROOT, pkg, "tests")))
    return jobs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("suites", nargs="*", metavar="SUITE",
                        help="suites to run (default: all): " + ", ".join(SUITES))
    parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 2)
    parser.add_argument("-v", "--verbose", action="store_true", help="print the output of failing runs in full")
    args = parser.parse_args(argv)
    unknown = sorted(set(args.suites) - set(SUITES))
    if unknown:
        parser.error(f"unknown suite(s): {', '.join(unknown)} (choose from {', '.join(SUITES)})")
    suites = set(args.suites or SUITES)

    start = time.time()
    totals = {}                                     # suite -> [processes ok, processes, tests]
    failures = []
    with ThreadPoolExecutor(max(1, args.jobs)) as pool:
        for label, ok, count, output in pool.map(lambda job: _run(*job), _jobs(suites)):
            suite = label.split("/")[0]
            row = totals.setdefault(suite, [0, 0, 0])
            row[0] += ok
            row[1] += 1
            row[2] += count
            if not ok:
                failures.append((label, output))

    for suite in SUITES:
        if suite in totals:
            ok, runs, count = totals[suite]
            print(f"{'OK  ' if ok == runs else 'FAIL'} {suite:18} {count:5d} tests" +
                  (f"  ({runs - ok} of {runs} modules failed)" if ok != runs else ""))
    tests = sum(row[2] for row in totals.values())
    print(f"{'-' * 40}\n{tests} tests in {time.time() - start:.0f}s: "
          + ("ALL PASSED" if not failures else f"{len(failures)} failing run(s)"))
    for label, output in failures:
        print(f"\n===== {label} =====")
        print(output if args.verbose else "\n".join(output.splitlines()[-25:]))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
