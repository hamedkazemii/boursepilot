import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

print("Project root:", ROOT)

print("Checking imports...")

modules=[
    "api",
    "core",
    "services",
    "reports"
]

for m in modules:
    try:
        __import__(m)
        print("OK:",m)
    except Exception as e:
        print("FAIL:",m,e)
        sys.exit(1)

print("Project import check completed successfully")
