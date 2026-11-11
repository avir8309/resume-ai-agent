# AI Job Hunter

AI-powered job discovery and resume optimization platform for entry-level software engineering roles in India and remote India.

## Current status

The project currently includes the first job-discovery increment:

- A company registry generated from the public GetChayan directory.
- Public job fetching for Greenhouse, Lever, Ashby, and SmartRecruiters.
- Configurable title, location, experience, and technology filters.
- Retry, timeout, delay, deduplication, and logging support.
- JSON and CSV opportunity exports.

Resume optimization, ATS evaluation, database persistence, and the frontend are planned phases and are not implemented yet.

## Project files

```text
agents.md                 Project requirements and development rules
companies_url.py          Builds the company registry from the public directory
company_registry.json     Normalized company registry in JSON
company_registry.csv      Normalized company registry in CSV
remote_jobs.json          Remote-friendly company seed URLs
remoteintech_companies.json  Export of all company profiles from remoteintech/remote-jobs
remoteintech_companies.csv   Tabular export of the same company profiles
import_remoteintech.py    Converts the upstream Markdown company profiles to JSON
scrape_opportunities.py   Fetches and filters public job postings
config/job_search.yaml    Job discovery filters and scraper settings
requirements.txt          Python dependencies
```

## Requirements

- Python 3.12+
- Network access to public job endpoints
- The dependencies in `requirements.txt`

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

If the environment blocks PyPI, install the dependencies from an internet-enabled machine or provide an offline wheel directory.

## Generate the company registry

The registry source is:

```text
https://getchayan.com/career-pages-of-companies-in-india/
```

Run:

```powershell
python companies_url.py
```

This creates:

- `company_registry.json`
- `company_registry.csv`

To override the source URL:

```powershell
$env:COMPANY_DIRECTORY_URL="https://example.com/company-directory"
python companies_url.py
```

## Fetch job opportunities

Run the scraper after generating the registry:

```powershell
python scrape_opportunities.py
```

The scraper reads `company_registry.json` and, when present, also reads `remote_jobs.json`. It routes supported companies to their public ATS endpoint, filters matching jobs, and creates:

- `opportunities.json`
- `opportunities.csv`

The current filters target:

- Gurugram/Gurgaon
- Bengaluru/Bangalore
- Hyderabad
- Pune
- India and remote roles
- SDE-1 and related software engineering titles
- Entry-level roles while excluding senior, staff, lead, principal, manager, director, and architect titles
- Java, Python, C++, Spring Boot, SQL, PostgreSQL, Redis, Kafka, Apache Spark, and distributed systems

`remote_jobs.json` contains remote-friendly company career URLs, not guaranteed active vacancies or proof of India hiring eligibility. URLs that can be identified as Greenhouse, Lever, Ashby, or SmartRecruiters are scraped automatically. Generic career pages are logged as unsupported until a provider-specific adapter is added.

## Import Remote In Tech profiles

The `remoteintech/remote-jobs` repository is a directory of remote-friendly company profiles, not a live vacancy feed. After cloning it locally, export all profiles with:

```powershell
python import_remoteintech.py C:\path\to\remote-jobs --output remoteintech_companies.json
```

The command generates both `remoteintech_companies.json` and `remoteintech_companies.csv` by default. The JSON preserves company metadata, parsed Markdown sections, raw profile Markdown, and each upstream source file. The CSV flattens technologies and serializes sections for spreadsheet use. Neither file invents individual job postings, job IDs, or posting dates that are not present in the source repository.

Modify `config/job_search.yaml` to change these filters, request behavior, or output names. The scraper does not invent an experience level when a posting does not state one; title and description evidence are used for filtering.

## Logging

Normal logging:

```powershell
python scrape_opportunities.py
```

Detailed request and parsing logs:

```powershell
$env:JOB_SCRAPER_LOG_LEVEL="DEBUG"
python scrape_opportunities.py
```

Supported levels include `DEBUG`, `INFO`, `WARNING`, and `ERROR`.

## Public-source rules

The scraper must only access publicly available career pages and documented public job endpoints. It must:

- Respect provider terms, `robots.txt`, rate limits, and reasonable delays.
- Fetch published/listed jobs only.
- Never bypass authentication, CAPTCHAs, paywalls, or access controls.
- Preserve the original application URL and source provider.
- Mark unsupported ATS providers as skipped instead of guessing endpoints.
- Treat results as source coverage, not a guarantee of every open role in India.

Workday, SuccessFactors, Oracle, Darwinbox, Eightfold, Workable, and company-owned career sites are attempted through a conservative generic public-HTML fallback. Because these pages vary widely and may be JavaScript-rendered, some requests can fail or produce no reliable job candidates. Provider-specific adapters should be added for higher coverage and accuracy.

## Validation

Run basic syntax checks:

```powershell
python -m py_compile companies_url.py scrape_opportunities.py
```

Network-backed scraping cannot be fully tested in environments where outbound access is disabled.

## Roadmap

1. Complete public job-source adapters and provider-specific pagination.
2. Add PostgreSQL persistence and job-status tracking.
3. Add job-description parsing and skill extraction.
4. Add factual resume optimization using verified candidate data.
5. Add controlled LaTeX editing and compilation validation.
6. Add explainable ATS-style scoring.
7. Add dashboard and scheduled discovery.
