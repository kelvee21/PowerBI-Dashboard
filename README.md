# Dare Careers: Learner Progress & Performance dashboard

A Power BI dashboard that tracks attendance, participation, lab/quiz scores and outcomes for one
2024 cohort across two learning tracks: **Power BI** (100 learners) and **AWS Cloud** (40).

| Metric | Value |
| --- | --- |
| Graduation rate | 85.0% (119) |
| Certification rate | 65.7% (92) |
| Dropout rate | 5.0% (7, all AWS Cloud) |
| Attendance rate (sessions > 30 min) | 94.1% |
| Participation rate | 86.2% |
| Average assessment score | 50.8 / 100 |

## Repository layout

```text
data/
  raw/                 source exports, never edited (PowerBI Training/, Cloud Training/)
  curated/             model tables written by etl/prepare_data.py
etl/prepare_data.py    Python ETL with 11 validation checks (Option B)
powerquery/            Power Query M queries that build the model from data/raw (Option A)
model/measures.dax     every DAX measure, with expected values
report/                theme.json, the .pbix, pbip/ (the Power BI project) and Final-Report.pdf
docs/
  lab-brief.md                   the assignment
  build-guide.md                 step-by-step build, polish checklist, change log
  issues-and-fixes.md            issues found and how each was fixed
  update-existing-report.md      click-by-click update + data reload of the existing PBIX
  transformation-walkthrough.md  every step from raw files to report pages, with checks + demo script
  data-dictionary.md             tables, columns, business rules, expected values
  report-spec.md                 requirement → visual traceability + acceptance checklist
  model-overview.md              star schema and design decisions
  dimensional-modeling-guide.md  grain, facts vs dimensions, method
  final-report.md                final report: pipeline, model, report pages, checks (PDF: report/Final-Report.pdf)
  img/                           report figures (pipeline, semantic model, page layouts)
  reviewer-clarifications.md     mentor clarifications and how they are met
index.html             the build guide as a browsable page (generated, see below)
fixes.html, update.html, walkthrough.html, report.html  more docs as browsable pages (generated)
tools/build_site.py    regenerates the HTML guides from the Markdown
tools/build_pbip.py    regenerates the project's semantic model from powerquery/ and model/measures.dax
exercises/             unrelated practice CSVs
```

## Quick start

```bash
pip install pandas openpyxl markdown
python etl/prepare_data.py     # rebuild data/curated (expects "validation checks passed: 11")
python tools/build_site.py     # rebuild index.html after editing docs/build-guide.md
```

Then follow [docs/build-guide.md](docs/build-guide.md) in Power BI Desktop (2.159, October 2026 or
later). Load the data with Power Query (`powerquery/`) or from `data/curated/`.

## Business rules

- **Attended:** a Zoom session **longer than 30 minutes** (exactly 30 does not count).
- **Incomplete attendance:** attended fewer class days than were scheduled.
- **Dropout:** Non-Graduate **and** Not Certified **and** incomplete attendance.
- **One cohort, two tracks, ready for more.** `LearnerKey` includes Cohort, Track and e-mail, and
  a `ClassSchedule` table holds the class days of each cohort and track, so future cohorts stay
  separate. Adding one is a row in `powerquery/Tracks.m` (and `TRACKS` in `etl/prepare_data.py`).
- **Certification Type** slicer: AWS / Power BI.
