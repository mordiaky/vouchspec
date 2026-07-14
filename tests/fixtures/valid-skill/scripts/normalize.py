from pathlib import Path


def normalize(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    destination.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")
