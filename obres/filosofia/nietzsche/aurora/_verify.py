#!/usr/bin/env python3
import re
with open("original.md") as f:
    content = f.read()
nums = [int(m) for m in re.findall(r"^### (\d+)\.", content, re.M)]
print(f"Total: {len(nums)}, Range: {min(nums)}-{max(nums)}")
expected = set(range(1, 576))
actual = set(nums)
missing = sorted(expected - actual)
if missing:
    print(f"Missing: {missing}")
else:
    print("All 575 aphorisms present!")
for line in content.split("\n"):
    if line.startswith("## ") and "Buch" in line:
        print(f"  Book: {line}")
