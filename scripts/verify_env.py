"""
verify_env.py — Tempo environment verification.
Run with: python scripts/verify_env.py
Exits 0 if all dependencies import correctly, 1 if anything is missing.
This is the P0 gate — do not proceed to P1 until this passes cleanly.
"""

import sys
import importlib
import importlib.metadata

REQUIRED = [
    ("pandas",    "pandas"),
    ("numpy",     "numpy"),
    ("pyarrow",   "pyarrow"),
    ("requests",  "requests"),
    ("sklearn",   "scikit-learn"),
    ("xgboost",   "xgboost"),
    ("shap",      "shap"),
    ("pydantic",  "pydantic"),
    ("streamlit", "streamlit"),
    ("plotly",    "plotly"),
    ("dotenv",    "python-dotenv"),
    ("pytest",    "pytest"),
]


def get_version(pip_name: str) -> str:
    try:
        return importlib.metadata.version(pip_name)
    except importlib.metadata.PackageNotFoundError:
        return "(version unknown)"


def main() -> None:
    print("=" * 60)
    print("Tempo — Environment Verification")
    print(f"Python: {sys.version}")
    print("=" * 60)

    passed = []
    failed = []

    for import_name, pip_name in REQUIRED:
        try:
            importlib.import_module(import_name)
            version = get_version(pip_name)
            print(f"  OK   {pip_name:<22} {version}")
            passed.append(pip_name)
        except ImportError as exc:
            print(f"  FAIL {pip_name:<22} ImportError: {exc}")
            failed.append(pip_name)

    print("=" * 60)

    if failed:
        print(f"FAILED — {len(failed)} package(s) missing or broken:")
        for pkg in failed:
            print(f"  - {pkg}  (pip install {pkg})")
        print("\nDo not proceed to P1 until this script exits 0.")
        sys.exit(1)

    print(f"PASSED — all {len(passed)} dependencies verified.")
    print("Environment is ready for P1.")
    sys.exit(0)


if __name__ == "__main__":
    main()
