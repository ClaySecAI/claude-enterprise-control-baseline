#!/usr/bin/env python3
"""
Structural check on the baseline's control tables.

Stage 2 edits these tables unattended, so this guards the two ways that
can go wrong silently: a row whose column count no longer matches its
header (renders as a broken table), and a control row missing or
malforming its Drafted date (destroys the triage signal Stage 2 depends
on to find controls that predate an upstream change).

Exits non-zero with a per-row report on failure. No dependencies.
"""
import re
import sys
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "claude-enterprise-control-baseline.md"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEP = re.compile(r"^\|[\s:|-]+\|\s*$")


def cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def main() -> int:
    lines = DOC.read_text().split("\n")
    problems: list[str] = []
    tables = control_rows = 0
    i = 0

    while i < len(lines):
        if lines[i].startswith("|") and i + 1 < len(lines) and SEP.match(lines[i + 1]):
            header = cells(lines[i])
            width = len(header)
            tables += 1
            if len(cells(lines[i + 1])) != width:
                problems.append(f"line {i+2}: separator has {len(cells(lines[i+1]))} columns, header has {width}")

            is_control_table = header[0] == "#"
            if is_control_table and header[-1] != "Drafted":
                problems.append(f"line {i+1}: control table's last column is {header[-1]!r}, expected 'Drafted'")

            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                row = cells(lines[j])
                if len(row) != width:
                    problems.append(f"line {j+1}: {len(row)} columns, header has {width} :: {lines[j][:60]}")
                elif is_control_table and re.match(r"^\d+\.\d+$", row[0]):
                    control_rows += 1
                    if not DATE.match(row[-1]):
                        problems.append(f"line {j+1}: control {row[0]} has Drafted={row[-1]!r}, expected YYYY-MM-DD")
                j += 1
            i = j
            continue
        i += 1

    for p in problems:
        print(f"FAIL {p}")
    print(f"\n{tables} tables, {control_rows} control rows checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
