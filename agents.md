# AGENTS.md — AI Job Hunter

## 1. Project Overview

Build an AI-powered job discovery and resume optimization platform.

The application should:

1. Discover SDE-1 and entry-level software engineering jobs from public job APIs.
2. Filter opportunities by location, experience, technology and work mode.
3. Analyze job descriptions using an LLM.
4. Optimize the candidate's existing LaTeX resume for each job.
5. Evaluate resume-to-JD compatibility using an ATS-style scoring engine.
6. Generate complete, compilable LaTeX source code.
7. Allow the candidate to copy the generated source directly into Overleaf.
8. Track discovered jobs and application status.

The system must prioritize factual accuracy, modularity, maintainability and reliability.

---

## 2. Technology Stack

### Backend
- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- Redis
- Celery
- httpx
- asyncio

### AI
- OpenAI API
- Structured Outputs
- LLM-based JD analysis
- LLM-based resume optimization
- Embeddings for semantic matching

### Resume Processing
- LaTeX
- PyLaTeX / pylatexenc
- pdflatex or Tectonic
- PyMuPDF

### Frontend (future phase)
- React
- TypeScript
- Tailwind CSS

### Infrastructure
- Docker
- Docker Compose
- Environment-based configuration
- Pytest

---

## 3. Project Architecture

Follow a modular architecture.

```text
ai-job-agent/
│
├── AGENTS.md
├── README.md
├── requirements.txt
├── .env.example
├── docker-compose.yml
│
├── config/
│   ├── resume_optimizer.yaml
│   ├── ats_scoring.yaml
│   └── job_search.yaml
│
├── data/
│   ├── master_resume.tex
│   └── candidate_profile.yaml
│
├── app/
│   ├── main.py
│   ├── config_loader.py
│   │
│   ├── agents/
│   │   ├── job_discovery_agent.py
│   │   ├── jd_analysis_agent.py
│   │   ├── resume_optimizer.py
│   │   └── ats_evaluator.py
│   │
│   ├── integrations/
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   ├── ashby.py
│   │   ├── adzuna.py
│   │   └── smartrecruiters.py
│   │
│   ├── services/
│   │   ├── job_filter.py
│   │   ├── deduplication.py
│   │   ├── resume_parser.py
│   │   ├── latex_editor.py
│   │   ├── latex_validator.py
│   │   └── scoring_engine.py
│   │
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── workers/
│   └── prompts/
│
└── tests/
    ├── test_job_discovery.py
    ├── test_resume_optimizer.py
    ├── test_latex_editor.py
    └── test_ats_scoring.py
```

Do not create every file immediately. Implement components incrementally as required by the current development phase.

---

## 4. Job Discovery Requirements

The system should discover software engineering opportunities from public job APIs.

### Initial locations

- Gurugram
- Gurgaon
- Bengaluru
- Bangalore
- Hyderabad
- Pune
- Remote (India)

### Target job titles

- SDE-1
- Software Engineer I
- Software Engineer
- Backend Engineer
- Java Developer
- Python Developer
- Associate Software Engineer

### Experience range

0–2 years initially, configurable through YAML.

### Target technologies

- Java
- Python
- C++
- Spring Boot
- SQL
- PostgreSQL
- Redis
- Kafka
- Apache Spark
- Distributed Systems

### Job sources

Implement integrations for:

- Greenhouse
- Lever
- Ashby
- Adzuna
- SmartRecruiters
- Other supported public job APIs

### Public web-scraping approach

Use the generated `company_registry.json` and `company_registry.csv` as the initial company seed list. The registry is sourced from the public directory at:

`https://getchayan.com/career-pages-of-companies-in-india/`

For each company, fetch only publicly accessible career pages or documented public job-board endpoints. Prefer structured public endpoints over HTML scraping when available:

- Greenhouse public job-board endpoints.
- Lever public postings endpoints.
- Ashby public job-board pages/endpoints.
- SmartRecruiters public posting endpoints.

The scraper must:

1. Read company name, career URL, ATS provider and India locations from the registry.
2. Route each company to the correct ATS adapter.
3. Retrieve published/listed jobs only.
4. Support pagination, retries with exponential backoff and request timeouts.
5. Cache responses and avoid repeated requests when the source data has not changed.
6. Respect `robots.txt`, provider terms, rate limits and reasonable request delays.
7. Never bypass authentication, CAPTCHAs, paywalls or access controls.
8. Preserve the source provider, company, original job URL and posting date.
9. Normalize all results into a common job schema.
10. Deduplicate jobs by provider job ID and canonical application URL.
11. Attempt unsupported providers through a conservative public HTML fallback; record
    the provider, source URL and parsing result, and never guess missing job data.
12. Record fetch time, source URL, HTTP status and parsing errors for observability.

Web scraping is a coverage mechanism, not a guarantee of every open role. The system must report the sources and companies attempted, successfully scanned, failed and matched. Generic HTML extraction must never invent listings or application links.

Initial opportunity filters must follow the configured values in `config/job_search.yaml` and include India locations, remote India roles, target entry-level titles, 0–2 years of experience and supported technologies. Filtering must occur after normalization so all sources use the same rules.

Important:
- Use official public APIs wherever available.
- Respect API rate limits and terms of service.
- Do not bypass authentication or access controls.
- Support pagination and retries.
- Normalize all job responses into a common schema.
- Deduplicate jobs.
- Store source and original application URL.
- Track job posting dates where available.
- Never invent job listings or application links.

---

## 5. Resume Optimization Agent

This is the most important component.

### Inputs

1. Original LaTeX resume.
2. Job description.
3. Verified candidate profile.
4. YAML optimization configuration.

### Main objective

Optimize the existing resume for a particular job description while preserving the original LaTeX template.

### Strict rules

1. Preserve the original LaTeX template.
2. Never change `\documentclass`.
3. Never change existing packages.
4. Never modify custom macros or command definitions.
5. Never invent skills, projects, metrics or experience.
6. Prioritize relevant achievements.
7. Incorporate JD keywords naturally where supported by candidate evidence.
8. Maintain concise, impact-oriented bullet points.
9. Preserve working LaTeX syntax.
10. Never modify contact information.
11. Maintain the original page limit unless explicitly authorized.
12. Do not remove important achievements without a relevance-based reason.
13. Do not introduce unsupported technical claims.
14. Preserve original factual meaning.
15. Generate complete compilable `.tex` source.

### LaTeX editing strategy

Do not regenerate the entire resume from scratch.

Instead:

1. Parse the original LaTeX document.
2. Identify sections, environments, macros and content blocks.
3. Build a structured representation of editable sections.
4. Send relevant content and JD context to the LLM.
5. Receive structured proposed edits.
6. Validate every proposed edit against candidate evidence.
7. Apply edits only to permitted content regions.
8. Preserve all protected LaTeX content.
9. Generate the complete updated `.tex` document.
10. Compare original and modified documents.

Protected content includes:

- Document class.
- Package imports.
- Macro definitions.
- Contact information.
- Page geometry.
- Font configuration.
- Header and footer definitions.
- Custom LaTeX environments.

### Editable content

Subject to factual validation:

- Professional summary.
- Experience descriptions.
- Achievement bullet points.
- Technical skills ordering.
- Project descriptions.
- Relevant section ordering.

---

## 6. YAML Configuration

All agent behavior must be configurable.

Use:

- `config/resume_optimizer.yaml`
- `config/ats_scoring.yaml`
- `config/job_search.yaml`
- `data/candidate_profile.yaml`

Do not hardcode agent instructions, scoring weights, target locations or experience limits in Python.

Use Pydantic validation for configuration loading.

Fail with a descriptive error when required configuration is invalid.

---

## 7. Candidate Information and Fact Verification

The candidate profile is the source of truth for resume claims.

Every generated resume claim must be supported by verified candidate information.

Rules:

- Never assume a technology was used professionally simply because it appears in a general skills list.
- Distinguish professional experience, project experience and theoretical knowledge.
- Preserve exact metrics.
- Never fabricate employment dates.
- Never invent project contributions.
- Never claim proficiency without supporting evidence.
- Track the source of each achievement where possible.

If the JD requires an unsupported skill, report it as missing instead of adding it to the resume.

---

## 8. ATS Evaluation Engine

Implement an internal resume-to-JD compatibility score.

Initial scoring weights:

| Dimension | Weight |
|---|---:|
| Required skill coverage | 30 |
| Experience relevance | 25 |
| Keyword coverage | 15 |
| Project relevance | 15 |
| Education and qualifications | 5 |
| Formatting and parsability | 10 |
| Total | 100 |

Requirements:

- Distinguish mandatory and preferred skills.
- Measure keyword coverage.
- Evaluate semantic relevance.
- Identify missing requirements.
- Provide evidence for matched skills.
- Penalize missing mandatory qualifications appropriately.
- Do not reward fabricated skills.
- Keep scoring explainable.

Never describe this score as a guaranteed ATS score or claim that it predicts an employer's actual ATS ranking.

---

## 9. LaTeX Validation

Every generated resume must undergo validation.

Checks:

1. Verify the document class is unchanged.
2. Verify packages are unchanged.
3. Verify custom macros are unchanged.
4. Verify contact information is unchanged.
5. Verify protected sections are preserved.
6. Check for malformed LaTeX commands.
7. Check balanced braces and environments.
8. Compile the generated `.tex` source.
9. Extract text from the generated PDF.
10. Verify page count against the original limit.
11. Verify no factual claims were introduced without evidence.

If validation fails:

- Do not mark the resume as complete.
- Return compilation errors.
- Attempt safe correction.
- Never overwrite the master resume.

The original `master_resume.tex` must always remain unchanged.

---

## 10. Expected Resume Optimizer Output

Return a structured result:

```json
{
  "company": "Company Name",
  "job_title": "Software Engineer I",
  "match_score": 85,
  "matched_keywords": [
    "Java",
    "Python",
    "SQL"
  ],
  "missing_skills": [
    "AWS"
  ],
  "modifications": [
    "Reordered experience bullets",
    "Improved professional summary"
  ],
  "latex_validation": {
    "syntax_valid": true,
    "compilation_success": true,
    "page_limit_preserved": true
  },
  "resume_source": "Complete LaTeX source"
}
```

The actual output must contain the entire generated LaTeX source, not a placeholder.

---

## 11. Development Standards

Follow these engineering practices:

- Use type hints.
- Follow PEP 8.
- Apply SOLID principles where appropriate.
- Keep business logic separate from API routes.
- Use dependency injection.
- Use async I/O for network operations.
- Implement structured logging.
- Handle exceptions explicitly.
- Use environment variables for secrets.
- Never commit API keys.
- Write unit and integration tests.
- Avoid unnecessary abstractions.
- Document important architectural decisions.

Do not introduce additional frameworks without a clear requirement.

---

## 12. Codex Working Instructions

Before implementing any feature:

1. Inspect the existing repository.
2. Read this AGENTS.md file.
3. Read the relevant YAML configurations.
4. Understand existing implementations.
5. Identify dependencies and affected modules.
6. Explain the implementation approach.

While implementing:

- Work incrementally.
- Avoid modifying unrelated files.
- Reuse existing components.
- Do not overwrite user data.
- Add or update tests.
- Run relevant tests after implementation.

After implementing:

1. Summarize modified files.
2. Explain architectural decisions.
3. Report tests executed.
4. Report any failing tests.
5. Identify remaining limitations.

Never claim a feature is complete unless its implementation and relevant tests have been verified.

---

## 13. Development Roadmap

Implement in this order:

### Phase 1 — Job Discovery
- Public ATS API and web-scraping integrations.
- Company registry ingestion from `company_registry.json` and `company_registry.csv`.
- Greenhouse, Lever, Ashby and SmartRecruiters adapters.
- Provider routing, pagination, retries, caching and fetch logging.
- Job normalization.
- Location and title filtering.
- Deduplication.
- PostgreSQL persistence.

### Phase 2 — JD Intelligence
- JD parsing.
- Skill extraction.
- Required versus preferred classification.
- Job relevance evaluation.

### Phase 3 — Resume Intelligence
- LaTeX parser.
- Candidate profile validation.
- Editable section extraction.
- Resume optimization.

### Phase 4 — LaTeX Editing
- Controlled content replacement.
- Protected content verification.
- Complete `.tex` generation.
- LaTeX compilation validation.

### Phase 5 — ATS Evaluation
- Keyword matching.
- Semantic matching.
- Explainable scoring.
- Missing skill analysis.

### Phase 6 — Dashboard and Automation
- Job feed.
- Resume preview and download.
- Match score dashboard.
- Application tracking.
- Scheduled job discovery.

---

## 14. Most Important Project Principle

**Factual accuracy and preservation of the original LaTeX template take priority over ATS score optimization.**

The system must produce a truthful, relevant, professionally written resume that compiles successfully in Overleaf.

Never sacrifice accuracy, formatting integrity or candidate credibility to increase a numerical match score.
