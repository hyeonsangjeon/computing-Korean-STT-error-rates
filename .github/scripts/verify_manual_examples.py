"""Execute explicitly marked examples from a trusted local Pages HTML file."""

import argparse
import json
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


class Examples(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.examples = {}
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            identifier = dict(attrs).get("data-nlptutti-example")
            if identifier is not None:
                if identifier in self.examples:
                    raise ValueError("duplicate manual example " + identifier)
                self.current = identifier
                self.examples[identifier] = ""

    def handle_data(self, data):
        if self.current is not None:
            self.examples[self.current] += data

    def handle_endtag(self, tag):
        if tag == "pre":
            self.current = None


def verify(html, contract):
    parser = Examples()
    parser.feed(html)
    if set(parser.examples) != set(contract):
        raise ValueError("manual example IDs must match the package contract")
    with tempfile.TemporaryDirectory() as directory:
        for identifier, snippet in parser.examples.items():
            result = subprocess.run([sys.executable, "-c", snippet], cwd=directory,
                                    check=True, capture_output=True, text=True,
                                    encoding="utf-8", timeout=30)
            if result.stdout.replace("\r\n", "\n") != contract[identifier]:
                raise ValueError("manual example output differs: " + identifier)
            print("verified manual example: " + identifier)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path, help="trusted local HTML; marked Python examples are executed")
    parser.add_argument("--contract", type=Path, default=Path(__file__).resolve().parents[2] / "docs/manual-examples.json")
    args = parser.parse_args()
    verify(args.html.read_text(encoding="utf-8"), json.loads(args.contract.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
