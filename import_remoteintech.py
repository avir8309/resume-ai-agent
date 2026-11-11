"""Export Remote In Tech company profiles to a structured JSON file.

The upstream repository is a directory of company profiles, not a live vacancy
API. This importer preserves profile metadata and parses the Markdown sections
without inventing job records.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


UPSTREAM_REPOSITORY = "https://github.com/remoteintech/remote-jobs"


def yaml_value(value: Any) -> Any:
    """Convert YAML date values into JSON-safe ISO strings."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [yaml_value(item) for item in value]
    if isinstance(value, dict):
        return {key: yaml_value(item) for key, item in value.items()}
    return value


def parse_profile(path: Path, source_root: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(?P<frontmatter>.*?)\n---\s*\n?(?P<body>.*)\Z", content, re.DOTALL)
    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path}")

    metadata = yaml.safe_load(match.group("frontmatter")) or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"Frontmatter must be a mapping: {path}")

    body = match.group("body").strip()
    sections: dict[str, str] = {}
    current_heading: str | None = None
    section_lines: list[str] = []
    for line in body.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            if current_heading is not None:
                sections[current_heading] = "\n".join(section_lines).strip()
            current_heading = heading.group(1)
            section_lines = []
        elif current_heading is not None:
            section_lines.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(section_lines).strip()

    relative_path = path.relative_to(source_root).as_posix()
    return {
        **yaml_value(metadata),
        "source_file": relative_path,
        "source_repository": UPSTREAM_REPOSITORY,
        "sections": sections,
        "raw_markdown": body,
    }


def csv_record(profile: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested/list profile values for a tabular CSV representation."""
    record = dict(profile)
    record["technologies"] = "; ".join(profile.get("technologies") or [])
    record["sections"] = json.dumps(
        profile.get("sections", {}), ensure_ascii=False, separators=(",", ":")
    )
    return record


def write_csv(profiles: list[dict[str, Any]], csv_path: Path) -> None:
    fields = [
        "title",
        "slug",
        "website",
        "careers_url",
        "region",
        "remote_policy",
        "company_size",
        "technologies",
        "addedAt",
        "updatedAt",
        "source_file",
        "source_repository",
        "sections",
        "raw_markdown",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_record(profile) for profile in profiles)


def export_profiles(
    source_root: Path, output_path: Path, csv_output_path: Path
) -> int:
    company_dir = source_root / "src" / "companies"
    paths = sorted(company_dir.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"No company profiles found in {company_dir}")

    profiles = [parse_profile(path, source_root) for path in paths]
    output = {
        "source": UPSTREAM_REPOSITORY,
        "source_directory": "src/companies",
        "record_type": "company_profile",
        "company_count": len(profiles),
        "note": (
            "The upstream repository lists remote-friendly companies and career "
            "pages; it does not publish live job vacancies."
        ),
        "companies": profiles,
    }
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(profiles, csv_output_path)
    return len(profiles)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Cloned remote-jobs repository")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("remoteintech_companies.json"),
        help="Destination JSON path",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        help="Destination CSV path (defaults to the JSON path with a .csv suffix)",
    )
    args = parser.parse_args()
    csv_output = args.csv_output or args.output.with_suffix(".csv")
    count = export_profiles(
        args.source.resolve(), args.output.resolve(), csv_output.resolve()
    )
    print(
        f"Exported {count} company profiles to "
        f"{args.output.resolve()} and {csv_output.resolve()}"
    )


if __name__ == "__main__":
    main()
