
import csv
import json
import os
import re
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE_URL = os.getenv(
    "COMPANY_DIRECTORY_URL",
    "https://getchayan.com/career-pages-of-companies-in-india/",
).strip()
HEADERS = {
    "User-Agent": "AI-Job-Hunter/0.1 (+public-job-directory-fetcher)",
    "Accept": "text/html,application/xhtml+xml",
}


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def extract_registry(html):
    soup = BeautifulSoup(html, "html.parser")
    records = []

    # Locate the directory table by its column headings.
    target_table = None
    for table in soup.find_all("table"):
        heading_text = clean_text(table.get_text(" ", strip=True)).lower()
        if "company" in heading_text and "hiring system" in heading_text:
            target_table = table
            break

    if target_table is None:
        raise RuntimeError(
            "Could not locate the company table. The page structure may have changed."
        )

    for row in target_table.find_all("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 4:
            continue

        company_cell, cities_cell, roles_cell, ats_cell = cells[:4]
        anchor = company_cell.find("a", href=True)
        if not anchor:
            continue

        company = clean_text(anchor.get_text(" ", strip=True))
        careers_url = urljoin(SOURCE_URL, anchor["href"])
        cities_text = clean_text(cities_cell.get_text(" ", strip=True))
        roles_text = clean_text(roles_cell.get_text(" ", strip=True))
        ats_provider = clean_text(ats_cell.get_text(" ", strip=True))

        if not company:
            continue

        cities = [x.strip() for x in cities_text.split(",") if x.strip()]
        try:
            tech_roles_count = int(re.sub(r"[^\d]", "", roles_text))
        except ValueError:
            tech_roles_count = None

        records.append({
            "company": company,
            "careers_url": careers_url,
            "india_locations": cities,
            "tech_roles_count_at_source_snapshot": tech_roles_count,
            "ats_provider": ats_provider,
            "source_url": SOURCE_URL,
        })

    # De-duplicate by company + exact destination while preserving order.
    unique = []
    seen = set()
    for item in records:
        key = (item["company"].casefold(), item["careers_url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def main():
    response = requests.get(SOURCE_URL, headers=HEADERS, timeout=45)
    response.raise_for_status()

    records = extract_registry(response.text)
    if len(records) < 500:
        raise RuntimeError(
            f"Only extracted {len(records)} companies; expected roughly 561. "
            "Do not treat this as a complete export."
        )

    with open("company_registry.json", "w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

    with open("company_registry.csv", "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "company",
                "careers_url",
                "india_locations",
                "tech_roles_count_at_source_snapshot",
                "ats_provider",
                "source_url",
            ],
        )
        writer.writeheader()
        for item in records:
            row = item.copy()
            row["india_locations"] = "; ".join(row["india_locations"])
            writer.writerow(row)

    print(f"Exported {len(records)} companies.")
    print("Created company_registry.json and company_registry.csv")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        sys.exit(1)
