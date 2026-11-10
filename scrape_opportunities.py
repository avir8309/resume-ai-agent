"""Fetch and filter public job postings from the company registry."""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml


ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "company_registry.json"
CONFIG_PATH = ROOT / "config" / "job_search.yaml"
SUPPORTED_PROVIDERS = {"Greenhouse", "Lever", "Ashby", "SmartRecruiters"}
USER_AGENT = "AI-Job-Hunter/0.1 (public-job-discovery)"
LOG_LEVEL = os.getenv("JOB_SCRAPER_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("job_scraper")


def load_config() -> dict[str, Any]:
    logger.debug("Loading job-search configuration from %s", CONFIG_PATH)
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    for key in ("locations", "titles", "experience_years", "technologies"):
        if key not in config:
            raise ValueError(f"Missing required job-search configuration: {key}")
    logger.info(
        "Loaded job-search configuration: %d titles, %d locations, %d technologies",
        len(config["titles"]),
        len(config["locations"]),
        len(config["technologies"]),
    )
    return config


def load_registry() -> list[dict[str, Any]]:
    logger.debug("Loading company registry from %s", REGISTRY_PATH)
    with REGISTRY_PATH.open(encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list):
        raise ValueError("company_registry.json must contain a JSON list")
    logger.info("Loaded %d companies from registry", len(records))
    return records


def board_slug(careers_url: str) -> str | None:
    path_parts = [part for part in urlparse(careers_url).path.split("/") if part]
    return path_parts[-1] if path_parts else None


def endpoint(provider: str, careers_url: str) -> str | None:
    slug = board_slug(careers_url)
    if not slug:
        return None
    if provider == "Greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    if provider == "Lever":
        return f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=100"
    if provider == "Ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    if provider == "SmartRecruiters":
        return (
            "https://api.smartrecruiters.com/v1/companies/"
            f"{slug}/postings?limit=100&offset=0&country=IN"
        )
    return None


def clean_text(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def location_text(job: dict[str, Any]) -> str:
    values = [job.get("location"), job.get("locationName"), job.get("locationRestrictions")]
    return clean_text(" ".join(str(value) for value in values if value))


def normalize(provider: str, company: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    if provider == "Greenhouse":
        title = raw.get("title")
        description = raw.get("content")
        location = ", ".join(
            clean_text(item.get("location")) for item in raw.get("offices", [])
        )
        apply_url = raw.get("absolute_url")
        job_id = raw.get("id")
        posted_at = raw.get("updated_at")
    elif provider == "Lever":
        title = raw.get("text")
        description = raw.get("descriptionPlain") or raw.get("description")
        location = ", ".join(raw.get("categories", {}).get("location", []) if isinstance(raw.get("categories", {}).get("location"), list) else [raw.get("categories", {}).get("location", "")])
        apply_url = raw.get("hostedUrl") or raw.get("applyUrl")
        job_id = raw.get("id")
        posted_at = raw.get("createdAt")
    elif provider == "Ashby":
        title = raw.get("title")
        description = raw.get("descriptionHtml") or raw.get("description")
        location = raw.get("location") or raw.get("locationName")
        apply_url = raw.get("jobUrl") or raw.get("applyUrl")
        job_id = raw.get("id")
        posted_at = raw.get("publishedAt")
    else:
        title = raw.get("name") or raw.get("title")
        description = raw.get("jobAd", {}).get("sections", {}) if isinstance(raw.get("jobAd"), dict) else raw.get("description")
        location = raw.get("location", {}).get("city") if isinstance(raw.get("location"), dict) else raw.get("location")
        apply_url = raw.get("ref") or raw.get("applyUrl")
        job_id = raw.get("id") or raw.get("uuid")
        posted_at = raw.get("releasedDate")

    return {
        "source": provider,
        "company": company.get("company"),
        "job_id": str(job_id or ""),
        "title": clean_text(title),
        "description": clean_text(description),
        "location": clean_text(location),
        "posted_at": posted_at,
        "application_url": apply_url,
        "source_url": company.get("careers_url"),
    }


def extract_jobs(provider: str, payload: Any) -> list[dict[str, Any]]:
    if provider == "Lever":
        return payload if isinstance(payload, list) else []
    if provider == "SmartRecruiters":
        return payload.get("content", []) if isinstance(payload, dict) else []
    if provider == "Ashby":
        return payload.get("jobs", payload.get("results", [])) if isinstance(payload, dict) else []
    return payload.get("jobs", []) if isinstance(payload, dict) else []


def matches(job: dict[str, Any], config: dict[str, Any]) -> bool:
    searchable = f"{job['title']} {job['description']} {job['location']}".casefold()
    title_casefolded = job["title"].casefold()
    title_match = any(title.casefold() in title_casefolded for title in config["titles"])
    excluded_match = any(
        term.casefold() in title_casefolded
        for term in config.get("excluded_title_terms", [])
    )
    location_match = any(location.casefold() in searchable for location in config["locations"])
    technology_match = any(technology.casefold() in searchable for technology in config["technologies"])
    return title_match and not excluded_match and location_match and technology_match


def fetch(url: str, config: dict[str, Any]) -> Any:
    retries = config["request"]["max_retries"]
    timeout = config["request"]["timeout_seconds"]
    for attempt in range(retries + 1):
        try:
            logger.debug("Fetching %s (attempt %d/%d)", url, attempt + 1, retries + 1)
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            response.raise_for_status()
            logger.debug("Fetched %s with HTTP %s", url, response.status_code)
            return response.json()
        except requests.RequestException as exc:
            if attempt == retries:
                logger.error("Request failed after %d attempts: %s", retries + 1, exc)
                raise
            logger.warning("Request failed; retrying in %d seconds: %s", 2**attempt, exc)
            time.sleep(2**attempt)
    raise RuntimeError("Unreachable")


def write_outputs(jobs: list[dict[str, Any]], config: dict[str, Any]) -> None:
    json_path = ROOT / config["output"]["json"]
    csv_path = ROOT / config["output"]["csv"]
    json_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["source", "company", "job_id", "title", "location", "posted_at", "application_url", "source_url"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: job.get(field) for field in fields} for job in jobs)
    logger.info("Wrote %d opportunities to %s and %s", len(jobs), json_path, csv_path)


def main() -> None:
    logger.info("Starting public job opportunity scraper")
    config = load_config()
    registry = load_registry()
    jobs: list[dict[str, Any]] = []
    skipped = 0
    scanned = 0
    for company in registry:
        provider = company.get("ats_provider", "")
        if provider not in SUPPORTED_PROVIDERS:
            skipped += 1
            logger.debug("Skipping unsupported provider %s for %s", provider, company.get("company"))
            continue
        url = endpoint(provider, company.get("careers_url", ""))
        if not url:
            skipped += 1
            logger.warning("Could not build endpoint for %s (%s)", company.get("company"), provider)
            continue
        scanned += 1
        try:
            logger.info("Scanning %s via %s", company.get("company"), provider)
            for raw in extract_jobs(provider, fetch(url, config)):
                job = normalize(provider, company, raw)
                if matches(job, config):
                    jobs.append(job)
            logger.debug("Finished scanning %s", company.get("company"))
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.error("Skipped %s (%s): %s", company.get("company"), provider, exc)
        time.sleep(config["request"]["delay_seconds"])

    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for job in jobs:
        key = (job["source"], job["job_id"] or job["application_url"] or job["title"])
        unique.setdefault(key, job)
    results = list(unique.values())
    write_outputs(results, config)
    logger.info(
        "Scraper complete: scanned=%d, matching=%d, skipped=%d",
        scanned,
        len(results),
        skipped,
    )


if __name__ == "__main__":
    main()
