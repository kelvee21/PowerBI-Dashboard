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
  curated/             reference tables written by the verification script
etl/prepare_data.py    verification only: rebuilds the tables independently, 11 checks
powerquery/            Power Query M queries: the transformation engine of the model
model/measures.dax     every DAX measure, with expected values
report/                theme.json, the .pbix, pbip/ (the Power BI project) and Final-Report.pdf
docs/                  lab brief, mentor clarifications, data dictionary, report spec, final report, figures (img/)
report.html            local browsable final report, generated from docs/final-report.md (not tracked)
tools/build_pbip.py    regenerates the project's semantic model from powerquery/ and model/measures.dax
exercises/             unrelated practice CSVs
```

## Quick start

```bash
pip install pandas openpyxl markdown
python etl/prepare_data.py     # verify: rebuild reference tables, run checks ("validation checks passed: 11")
python tools/build_site.py     # rebuild local HTML pages from docs (outputs are not tracked)
```

Open `report/pbip/DareCareers.pbip` in Power BI Desktop (2.159, October 2026 or later) and refresh.
The data is loaded and transformed with Power Query (`powerquery/`); compare the
refreshed model with the expected values from `etl/prepare_data.py`.

## Business rules

- **Attended:** a Zoom session **longer than 30 minutes** (exactly 30 does not count).
- **Incomplete attendance:** attended fewer class days than were scheduled.
- **Dropout:** Non-Graduate **and** Not Certified **and** incomplete attendance.
- **One cohort, two tracks, ready for more.** `LearnerKey` includes Cohort, Track and e-mail, and
  a `ClassSchedule` table holds the class days of each cohort and track, so future cohorts stay
  separate. Adding one is a row in `powerquery/Tracks.m` (and `TRACKS` in `etl/prepare_data.py`).
- **Certification Type** slicer: AWS / Power BI.
