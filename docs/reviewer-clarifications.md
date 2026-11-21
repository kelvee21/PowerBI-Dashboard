# Reviewer Clarification Analysis

> **Status (21 Nov 2026):** the first fix round below is history. The way it implemented
> "truncated attendance" turned out to be wrong, so a second review changed it. File paths in this
> section are the old ones (`powerbi/...`). The current rules are in
> [data-dictionary.md](data-dictionary.md).


## Context
This document explains why the lab reviewer issued clarification on (1) cohort/track structure, (2) dropout classification, and (3) the Certification Type slicer. It is based on a scan of the current implementation in this workspace.

**Scope scanned:** `powerbi/prepare_data.py`, `powerbi/measures.dax`, `powerbi/report_spec.md`, `powerbi/data_dictionary.md`, `powerbi/README.md`, `powerbi/Final_Report.md`, `powerbi/PowerQuery_FactAttendance.m`, `powerbi/PowerQuery_FactAssessment.m`, and prepared model inputs in `powerbi/data/` (`DimLearner.csv`, `FactLearnerStatus.csv`, `FactAttendance.csv`, `DimDate.csv`, `DimWeek.csv`, `FactAssessment.csv`, `FactParticipation.csv`).

## Reviewer clarification (as provided)
1. **Single cohort, two tracks:** Do not treat each track as a separate cohort. The dataset represents a single cohort, with Power BI and AWS Cloud being the two learning tracks. The dashboard should be designed with the flexibility to accommodate additional cohorts in the future.
2. **Dropout classification:** A participant should only be classified as a dropout where all three conditions are met simultaneously: (a) the participant is a Non-Graduate, (b) the participant is Not Certified, and (c) the participant has incomplete (truncated) attendance.
3. **Certification Type slicer:** Retain it. The certification types are AWS and Power BI, so users should be able to filter and analyse outcomes by certification type.

## Why the clarification was necessary

### 1. Cohort and track are modeled the wrong way around (not future-cohort-ready)

**Current implementation**
- **ETL (`powerbi/prepare_data.py`)** hard-codes tracks and derives cohort from track:
  - `for folder,track in [('PowerBI Training','Power BI'),('Cloud Training','AWS Cloud')]` (line 5)
  - Writes `Cohort=track+' 2024'` into `DimLearner`, `FactLearnerStatus`, `FactAttendance`, `FactParticipation`, and `FactAssessment` (lines 17, 19, 23, 27, 43, 51).
- **Prepared data (`powerbi/data/DimLearner.csv`)** contains two distinct cohort values aligned 1:1 with track: `Power BI -> Power BI 2024` (100 learners) and `AWS Cloud -> AWS Cloud 2024` (40 learners), representing 140 learners total in one dataset period.
- **Documentation/spec** explicitly encode this interpretation:
  - `powerbi/data_dictionary.md` (lines 5, 15): `DimLearner` grain includes `Track, Cohort`; states “The source provides a single cohort per track. ‘Cohort’ is therefore represented as `Power BI 2024` / `AWS Cloud 2024`…”
  - `powerbi/report_spec.md` (lines 8–12, 16, 18): visuals and slicers use “Track/Cohort” and include both `Cohort` and `Track`.
  - `powerbi/Final_Report.md` (lines 5, 49, 60, 64): frames two learner programs/cohorts and cohort comparisons.
  - `powerbi/README.md` (line 22): model exposes `DimLearner { ... Track string Cohort }`.

**Gap vs. clarification**
- The model presents Power BI and AWS Cloud as separate cohorts, but the dataset is a single cohort with two learning tracks.
- `Cohort` is coupled to track naming in ETL and schema, so adding another real cohort would require structural changes rather than adding cohort values/records. The design does not separate cohort membership from track/program.

### 2. Dropout is defined as “Non Graduate” only (missing required conditions and no truncated-attendance logic)

**Current implementation**
- **DAX (`powerbi/measures.dax`, lines 37–40):**
  - `Total Dropouts = CALCULATE ( DISTINCTCOUNT ( FactLearnerStatus[LearnerKey] ), FactLearnerStatus[GraduationStatus] = "Non Graduate" )`
  - `Dropout Rate = DIVIDE ( [Total Dropouts], [Total Learners] )`
- **Report spec (`powerbi/report_spec.md`, lines 7–8, 16):** “Total Dropouts” and “Dropout Rate” are headline KPIs/comparisons; learner detail shows `Graduation Status` and `Certification Status` but no dropout/attendance-completeness indicator.
- **Data model inputs:** `powerbi/data/FactLearnerStatus.csv` contains `GraduationStatus` and `CertificationStatus` only; there is no learner-level “incomplete/truncated attendance” field and no DAX/ETL logic derives it.

**Gap vs. clarification**
- A learner is currently counted as a dropout if `GraduationStatus = "Non Graduate"` only. The required definition is stricter and conjunctive: **Non-Graduate AND Not Certified AND incomplete (truncated) attendance** (all three must be satisfied).
- `CertificationStatus = "Not Certified"` is not part of the dropout measure (in the current prepared data all 21 non-graduates are not certified, but the rule is not enforced by logic).
- “Incomplete (truncated) attendance” is not implemented. Attendance facts and calendar exist (`FactAttendance.csv`, `DimDate.csv`; 50 class dates per track; `Attended = DurationMinutes > 30` in ETL/semantic intent), but there is no computed flag/measure for truncated/incomplete attendance (e.g. attendance ending before program end or not spanning/completing the scheduled attendance period) at learner grain.

**Prepared-data observation (illustrative of impact)**
- Current non-graduates by status: 14 Power BI, 7 AWS Cloud (all `Not Certified`).
- Attendance patterns differ: all 14 Power BI non-graduates attended 50/50 class days with last attended date at program end (`2024-10-11`), while AWS Cloud non-graduates attended 31–45 of 50 days (some with last attended date before program end). Under the clarified rule, dropout counts will depend on the precise operational definition/derivation of “incomplete (truncated) attendance”; the current implementation cannot evaluate this condition.

### 3. “Certification Type” slicer was explicitly omitted and documented as unsupported

**Current implementation**
- **Report spec (`powerbi/report_spec.md`, line 12):** “Slicers: Cohort, Track, Certification Status. **Certification Type is omitted because it does not exist in source data; do not invent it.**”
- **Data dictionary (`powerbi/data_dictionary.md`, line 15):** “**Certification type is absent; no certification type analysis can be supported.**”
- **Final report (`powerbi/Final_Report.md`, line 53):** “Certification type is not provided.”
- **Report spec checklist (`powerbi/report_spec.md`, line 31):** marks “Data limitations called out: no certification type…” as complete.
- **Status/model fields:** `FactLearnerStatus` stores outcome flags only (`CertificationStatus`: Certified/Not Certified) with no certification-type field (`powerbi/data/FactLearnerStatus.csv` header: `Email,Track,Cohort,GraduationStatus,CertificationStatus,LearnerKey`).

**Gap vs. clarification**
- The implementation treated certification type as unavailable and removed the slicer, but the clarification states certification types are **AWS and Power BI** and the slicer must be retained for outcome analysis.
- Track/program identity exists in the data (`Track`: Power BI / AWS Cloud), but it is modeled and documented as track/cohort rather than exposed as “Certification Type.” As a result, the spec conflated semantics and excluded the requested slicer instead of mapping it to the available certification-program dimension.

## Net effect
The reviewer clarification was needed because the ETL, model fields, DAX, and report/docs encode different business definitions than intended: (a) the single cohort is split into track-derived “cohorts”, (b) dropout is based on graduation status alone with no certification-status or truncated-attendance criteria, and (c) certification type is explicitly omitted despite AWS/Power BI being the certification programs required for filtering and analysis.

## Fix direction (implied by clarification)
- **Cohort/track:** Represent one cohort for this dataset and model `Track` (Power BI, AWS Cloud) as the learning track; keep schema extensible for additional future cohorts (independent cohort identifier/name).
- **Dropout:** Implement dropout as `GraduationStatus = "Non Graduate" AND CertificationStatus = "Not Certified" AND IsIncompleteTruncatedAttendance = TRUE`, with a documented, data-driven derivation for truncated/incomplete attendance.
- **Certification Type:** Expose/retain a Certification Type slicer with values AWS and Power BI (aligned to the certification programs/tracks) for outcome analysis; update model/spec/measures accordingly.


---

## Second review (21 Nov 2026): how each clarification is now met

| Clarification | First fix round | Problem found | Current implementation |
| --- | --- | --- | --- |
| Single cohort, two tracks, extensible | `Cohort = "2024"` separate from `Track` | Correct, but the tracks and cohort were hard-coded in each of 7 queries | Kept. Tracks and cohort now come from one `Tracks` config query, so a new cohort is new rows |
| Dropout = Non-Graduate AND Not Certified AND incomplete (truncated) attendance | "Truncated" = `LastAttendedDate < LastScheduledDate` → 2 dropouts | Hinged on one day: a learner with 45/50 days attended counted as a dropout, one with 31/50 did not. A learner who never attended could not be flagged at all | "Incomplete" = attended fewer class days (> 30 min) than scheduled → **7 dropouts**, all AWS Cloud non-graduates. The 14 Power BI non-graduates attended 50/50 and are correctly excluded |
| Retain Certification Type slicer (AWS, Power BI) | `CertificationType` on every table | Correct. But the Certification **Status** slicer sat on a fact table and could not filter learners | Both attributes now live on `DimLearner`, and every slicer filters every visual |

### Why 7 and not 2 (the argument for the defence)

Each learner appears in **every** daily Zoom export (7,000 rows = 140 learners × 50 days), so
nobody's record literally stops. Attendance can only be "truncated" in the sense of class days on
which the learner did not reach 30 minutes. Measured that way:

- **Power BI non-graduates (14):** 50/50 days attended. They finished the course but did not
  graduate, so they are **not dropouts**.
- **AWS Cloud non-graduates (7):** 31–45 of 50 days attended, none certified, so all three
  conditions hold and they are **dropouts**.

If the programme owner defines a threshold instead (for example "under 80% attended"), only one
expression changes (`HasIncompleteAttendance`). `AttendanceCompletion` is already in the model so the
alternatives can be shown.
