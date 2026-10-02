"""Build once, then test the installed wheel outside the source tree on any OS."""

import argparse
import os
import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jiwer", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="nlptutti-compat-") as directory:
        work = Path(directory)
        dist = work / "dist"
        subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)], cwd=root, check=True)
        environment = work / "venv"
        venv.create(environment, with_pip=True)
        binaries = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binaries / ("python.exe" if os.name == "nt" else "python")
        wheel, = dist.glob("*.whl")
        subprocess.run([str(python), "-m", "pip", "install", str(wheel), args.jiwer, "pytest"], check=True)
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"],
                   PYTHONUTF8="1", GITHUB_WORKSPACE=str(root))
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python), str(root / ".github/scripts/smoke_installed_package.py")], cwd=work, env=env, check=True)
        subprocess.run([str(python), "-m", "pytest", str(root / "test"), "-q"], cwd=work, env=env, check=True)
    print("Compatibility check completed in {:.1f}s".format(time.perf_counter() - start))


if __name__ == "__main__":
    main()
