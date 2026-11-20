# Data dictionary and business rules

Both preparation paths produce these tables with the same columns and values:
`powerquery/*.m` (inside Power BI) and `etl/prepare_data.py` (writes `data/curated/*.csv`).

## Tables

| Table | Type | Grain: one row is… | Rows |
| --- | --- | --- | --- |
| `DimLearner` | Dimension | one learner enrolment in a cohort and track (`Cohort\|Track\|email`) | 140 |
| `ClassSchedule` | Schedule (hidden) | one class day of one cohort-track (one Zoom export file) | 100 |
| `DimDate` | Dimension | one calendar day, first to last class day (contiguous) | 68 |
| `FactAttendance` | Fact | one Zoom participant session (here one per learner per class day) | 7,000 |
| `FactParticipation` | Fact | one roster learner listed as participating on a class day | 6,037 |
| `FactAssessment` | Fact | one learner × programme week × assessment type (Lab / Quiz) | 2,800 |

### DimLearner

| Column | Type | Meaning |
| --- | --- | --- |
| LearnerKey | Text (key) | `Cohort\|Track\|email` (lower-case, trimmed). Unique. A learner who repeats a track in a later cohort is a new enrolment |
| LearnerName | Text | Display name from the Zoom exports (Power BI e-mails have no separator) |
| Email | Text | Personal data: hide from report consumers |
| Track | Text | `Power BI` / `AWS Cloud` |
| Cohort | Text | `2024`. Independent of track, so future cohorts append rows |
| CohortTrackKey | Text | `Cohort\|Track`, e.g. `2024\|AWS Cloud`. Links the learner to `ClassSchedule` (hidden) |
| CertificationType | Text | `Power BI` / `AWS` (certification programme; drives the required slicer) |
| GraduationStatus | Text | `Graduate` / `Non Graduate` (source) |
| CertificationStatus | Text | `Certified` / `Not Certified` (source) |
| ProgramStatus | Text | `Completed` if an outcome exists, else `Ongoing` |
| AttendedClassDays | Whole | distinct class days with a session > 30 min |
| ScheduledClassDays | Whole | class days scheduled for the learner's cohort and track, from `ClassSchedule` (50) |
| AttendanceCompletion | Decimal | AttendedClassDays / ScheduledClassDays |
| LastAttendedDate / LastScheduledDate | Date | for transparency in the learner table |
| HasIncompleteAttendance | Whole 0/1 | `AttendedClassDays < ScheduledClassDays` |
| IsDropout | Whole 0/1 | Dropout rule, see below |
| DropoutStatus | Text | `Dropout` / `Not Dropout` (readable version for slicers/tables) |

### DimDate

| Column | Type | Meaning |
| --- | --- | --- |
| Date | Date (key) | Mark as date table on this column |
| Year, MonthNumber, MonthName | | MonthName sorted by MonthNumber |
| MonthYear | Text | `Aug 2024`, sorted by **MonthYearSort** (`202408`) |
| WeekNumber, WeekLabel | Whole / Text | Week 1–10, counted from the Monday of the first class day in the data (with one cohort, the programme week). Filled for every day, weekends included. Each cohort's own week is `ClassSchedule[ProgrammeWeek]` |
| IsClassDay | Whole 0/1 | 1 on the 50 days on which any cohort-track had a class. Informational: the attendance denominator comes from `ClassSchedule` |
| DayName, DayOfWeek | | Monday = 1 |

### ClassSchedule

`CohortTrackKey, Cohort, Track, Date, ProgrammeWeek`. One row per Zoom export file, i.e. per class
day of a cohort-track. `ProgrammeWeek` counts from the Monday of that cohort-track's first class day.
All columns are hidden. Used by the `Class Days` and `Scheduled Learner Days` measures, by
`DimLearner[ScheduledClassDays]` and by `FactAssessment[AssessmentDate]`.

### FactAttendance

`LearnerKey, Email, Track, Cohort, CertificationType, Date, DurationMinutes, Attended, Role`.
`Attended = 1` when `DurationMinutes > 30`.

### FactParticipation

`LearnerKey, Email, ParticipantName, Track, Cohort, CertificationType, Date, Participated, NameMatched`.
Unmatched names keep a blank `LearnerKey` and `NameMatched = 0` (0 rows in the current data).

### FactAssessment

`LearnerKey, Email, Track, Cohort, CertificationType, WeekNumber, AssessmentDate, AssessmentType, Score, IsCompleted`.
`AssessmentDate` = last class day of that programme week for the learner's cohort and track. `IsCompleted = 1` when `Score > 0`.

## Relationships

All are one-to-many, single direction, active. There are no fact-to-fact joins.

| One side | Many side |
| --- | --- |
| `DimLearner[LearnerKey]` | `FactAttendance[LearnerKey]`, `FactParticipation[LearnerKey]`, `FactAssessment[LearnerKey]` |
| `DimDate[Date]` | `FactAttendance[Date]`, `FactParticipation[Date]`, `FactAssessment[AssessmentDate]`, `ClassSchedule[Date]` |

`ClassSchedule` has no relationship to `DimLearner`, because its key is the cohort-track, not the
learner. The `Class Days` measure passes the learner filter across with `TREATAS` on
`CohortTrackKey`.

## Business rules

### 1. Attended (brief: "more than 30 minutes")

`DurationMinutes > 30`, strictly greater. **19 sessions last exactly 30 minutes and are not
attended.** The two tracks encode duration differently (Power BI `h:mm:ss`, AWS Cloud numeric
minutes). Both are converted to decimal minutes before the rule is applied. The brief says the rule
applies to *all* attendance calculations, so `Class Hours` also only sums qualifying sessions.

### 2. Incomplete (truncated) attendance

`HasIncompleteAttendance = 1` when the learner attended fewer class days than were scheduled:
`AttendedClassDays < ScheduledClassDays`. A learner who never attended gets 0 days and is flagged.

**Why this definition.** Every learner appears in every daily Zoom export (7,000 rows = 140 × 50),
so nobody literally disappears from the data. "Truncated" can only show up as days on which a
learner did not reach 30 minutes. The previous definition (`LastAttendedDate < LastScheduledDate`)
only checked the final class. It flagged a learner who attended 45/50 days but missed the last one,
and missed a learner who attended 31/50 but was present on the last day. That made the dropout
count depend on a single day.

| Definition | Dropouts | Comment |
| --- | --- | --- |
| **Attended < scheduled (implemented)** | **7** | All 7 AWS Cloud non-graduates (31–45 of 50 days). The 14 Power BI non-graduates attended 50/50, so they completed the course but failed: not dropouts. |
| Missed the last class only (previous) | 2 | Arbitrary: depends on one date |
| No attendance in the final week | 0 | Nobody stopped attending |

If the programme owner later supplies a threshold (for example under 80% attended), change one
expression in `DimLearner.m` / `prepare_data.py`. `AttendanceCompletion` is already in the model.

### 3. Dropout (mentor clarification, all three at once)

`GraduationStatus = "Non Graduate"` **AND** `CertificationStatus = "Not Certified"` **AND**
`HasIncompleteAttendance = 1`. Result: **7 dropouts (5.0%)**, all AWS Cloud (17.5% of that track).

### 4. Cohort, track, certification type

One cohort (`2024`) with two learning tracks. `Cohort` is an independent column, so another
cohort is new rows, not a redesign. `CertificationType` (`AWS` / `Power BI`) feeds the required
Certification Type slicer.

### 5. Labs completed

There is no "submitted" flag and no pass mark in the source. A lab counts as completed when a score
above 0 is recorded (1,383 of 1,400 labs; 17 zeros). This is an assumption: if a pass mark is
supplied, change `IsCompleted`.

### 6. Program status

All source learners have an outcome, so every learner is `Completed`. The slicer is kept because
the brief asks for it and it starts working as soon as an in-progress cohort is loaded.

### 7. Participation

The participation workbook lists display names with no e-mail. Names are matched to the roster by a
letters-only, lower-case key of the e-mail local part (`fnNormalizeName`). All 6,037 names match.
Duplicate mentions of a person on the same day are counted once.

## Expected values (whole cohort)

| Measure | All | Power BI | AWS Cloud |
| --- | --- | --- | --- |
| Total Learners | 140 | 100 | 40 |
| Total Graduations / Rate | 119 / 85.0% | 86 / 86.0% | 33 / 82.5% |
| Total Certifications / Rate | 92 / 65.7% | 68 / 68.0% | 24 / 60.0% |
| Total Dropouts / Rate | 7 / 5.0% | 0 / 0.0% | 7 / 17.5% |
| Attendance Rate | 94.1% | 100.0% | 79.25% |
| Avg Participation Rate per Learner | 86.2% | 85.1% | 89.2% |
| Avg Assessment Score (Lab / Quiz) | 50.8 (50.1 / 51.5) | 50.4 (49.8 / 51.0) | 51.8 (50.9 / 52.8) |
| Labs Completed / Avg per Learner | 1,383 / 9.88 | 987 / 9.87 | 396 / 9.90 |
| Class Hours / Avg per Learner | 10,565.7 / 75.5 | 8,752.7 / 87.5 | 1,813.0 / 45.3 |

Filter checks: **Oct 2024** has 9 class days, an attendance rate of 94.0%, and assessments from
weeks 9–10.

## Data-quality controls

`etl/prepare_data.py` stops with an error unless all of these hold:

- learner keys and dates are unique;
- every fact row points at a known learner;
- every score is between 0 and 100;
- the assessment grain is unique;
- participation learner-days are unique;
- every fact date is in `DimDate`;
- every learner has a class schedule, every assessment has a date, and `ClassSchedule` has one row
  per cohort-track and day;
- each class day's computed programme week matches its `Week N` source folder.

Learner e-mails are personal data. Hide `Email` in the report and show `LearnerName` instead.
