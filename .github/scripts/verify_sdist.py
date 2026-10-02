"""Run the shipped tests against an independently extracted source archive."""

import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def main():
    archive = Path(sys.argv[1]).resolve()
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory)
        with tarfile.open(str(archive), "r:gz") as source:
            for member in source.getmembers():
                path = PurePosixPath(member.name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not (member.isfile() or member.isdir())
                ):
                    raise ValueError(
                        "unsafe source archive member: {}".format(member.name)
                    )
            source.extractall(str(destination))
        roots = list(destination.iterdir())
        if len(roots) != 1 or not (roots[0] / "pyproject.toml").is_file():
            raise ValueError("expected one project root in source archive")
        root = roots[0]
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import nlptutti; assert Path(nlptutti.__file__).resolve().parent.parent == Path.cwd().resolve()",
            ],
            cwd=str(root),
            env=environment,
            check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "pytest", "test", "-q"],
            cwd=str(root),
            env=environment,
            check=True,
        )


if __name__ == "__main__":
    main()
