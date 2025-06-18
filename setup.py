import setuptools
from pathlib import Path

# setup.py 파일이 있는 디렉토리
here = Path(__file__).parent.resolve()

# README.md 읽기
long_description = (here / "README.md").read_text(encoding="utf-8")

# requirements.txt 위치 탐색 (현재 디렉토리 혹은 부모 디렉토리)
req_file = here / "requirements.txt"
if not req_file.is_file():
    req_file = here.parent / "requirements.txt"

# 파일이 있으면 읽어서 리스트로, 없으면 빈 리스트
if req_file.is_file():
    install_requires = req_file.read_text(encoding="utf-8").splitlines()
else:
    install_requires = []

setuptools.setup(
    name="nlptutti",
    version="0.0.0.10",
    author="hyeonsangjeon",
    author_email="wingnut0310@gmail.com",
    description="nlp measurement package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hyeonsangjeon/computing-Korean-STT-error-rates",
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)