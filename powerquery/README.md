# Power Query: the transformation engine

These `.m` files load and transform the whole model inside Power BI from `data/raw/`. The Python
script `etl/prepare_data.py` is used only to verify them: it rebuilds the same tables independently
(written to `data/curated/*.csv`) so the refreshed model can be compared against them.

## 1. Parameter

Power Query Editor → **Home → Manage Parameters → New Parameter**

| Setting | Value |
| --- | --- |
| Name | `pRootFolder` |
| Type | Text, Required |
| Current value | the **repository root**, e.g. `C:\Workstation\Amalitech\PowerBI-Dashboard\` |

The queries append `data\raw\<track folder>\...` themselves (`RawRoot.m`), and a missing trailing
backslash is tolerated.

## 2. Queries — create in this order

For each file: **Home → New Source → Blank Query → Advanced Editor → paste → Done**, then rename the
query to the file name (without `.m`).

| # | File | Load? | Purpose |
| --- | --- | --- | --- |
| 1 | `Tracks.m` | **off** | config: one row per cohort × track: folder → Track, CertificationType, Cohort |
| 2 | `RawRoot.m` | **off** | `pRootFolder` + `data\raw\` |
| 3 | `fnNormalizeName.m` | n/a (function) | name → letters-only key |
| 4 | `stgRoster.m` | **off** | staging: status workbooks |
| 5 | `stgZoomNames.m` | **off** | staging: display names from Zoom |
| 6 | `stgAssessment.m` | **off** | staging: labs/quizzes unpivoted |
| 7 | `ClassSchedule.m` | on (hidden) | one row per cohort × track × class day, with that cohort's `ProgrammeWeek` |
| 8 | `FactAttendance.m` | on | session grain, `Attended = DurationMinutes > 30` |
| 9 | `DimDate.m` | on | contiguous calendar over all cohorts, `IsClassDay`, week |
| 10 | `FactParticipation.m` | on | learner-day grain, unmatched names kept |
| 11 | `FactAssessment.m` | on | learner × week × type, `AssessmentDate` per cohort-track, `IsCompleted` |
| 12 | `DimLearner.m` | on | learner + outcomes + incomplete attendance (vs own cohort-track schedule) + dropout |

Keys: `LearnerKey` = Cohort, Track and e-mail joined by `|` (e.g. `2024|AWS Cloud|james.williams@msc.com`);
`CohortTrackKey` = Cohort and Track (`2024|AWS Cloud`).

To turn load off, right-click the query in the **Queries** pane and untick **Enable load**. The
query then turns italic and won't appear in the model.

Optional tidy-up: select the staging/helper queries → right-click → **Move to group** → `Staging`.

## 3. Why the `stg*` queries exist (Formula.Firewall)

Power Query refuses to let one step **read a data source and combine it with another query** that
also reads a data source. The error is *"Formula.Firewall: Query 'X' references other queries or
steps, so it may not directly access a data source. Please rebuild this data combination."*
So every query that opens files either:

- reads files only (`stg*`, `ClassSchedule`, `FactAttendance`, `FactParticipation`), or
- references other queries only (`DimDate`, `DimLearner`, `FactAssessment`).

`Tracks`, `RawRoot` and `fnNormalizeName` contain no data source, so any query may reference them.
If you still see a firewall or privacy prompt, set both sources to **Organizational**, or for this
local lab use **File → Options and settings → Options → Current File → Privacy → Ignore the
Privacy Levels**.

## 4. Check before Close & Apply

| Query | Rows |
| --- | --- |
| DimLearner | 140 |
| ClassSchedule | 100 (50 class days × 2 tracks) |
| DimDate | 68 (50 with `IsClassDay = 1`) |
| FactAttendance | 7,000 |
| FactParticipation | 6,037 (`NameMatched = 0`: 0) |
| FactAssessment | 2,800 |

The bottom-left status bar of the editor shows the row count of the selected query, and
**View → Column profile** shows the distinct values.

## 5. Rules implemented (same as `etl/prepare_data.py`)

- **Attendance:** `DurationMinutes > 30`. The duration format is detected from the value:
  `h:mm:ss` (Power BI track) or numeric minutes (AWS Cloud).
- **Incomplete attendance:** `AttendedClassDays < ScheduledClassDays`, where scheduled = the class
  days of the learner's own cohort and track (from `ClassSchedule`).
- **Dropout:** `Non Graduate` AND `Not Certified` AND `HasIncompleteAttendance = 1`.
- **Lab completed:** score recorded and `> 0`.
- **Assessment date:** last class day of that cohort-track's programme week.
- **Cohort:** taken from `Tracks` (`2024`).

## 6. Adding a future cohort

1. Put its files under `data\raw\`, for example `data\raw\2025\Cloud Training\`, with the same four
   subfolders (`Zoom Attendance\Week N\dd-MMM-yyyy.csv`, `Participation`, `Status of Learners`,
   `Labs & Quizes`).
2. Add one row per track to `Tracks`, e.g. `{"2025\Cloud Training", "AWS Cloud", "AWS", "2025"}`,
   and the same row to `TRACKS` in `etl/prepare_data.py` if you use the CSV path.
3. **Home → Refresh.** No other query or measure changes.

What keeps cohorts apart:

- `LearnerKey` includes the cohort, so a learner who repeats a track is a new enrolment.
- `ClassSchedule` gives every cohort-track its own class days and programme weeks, so attendance
  denominators and assessment dates stay correct when cohorts run on different dates.
- The `Week` slicer on `DimDate` counts weeks from the first class day in the data. With several
  cohorts on different dates, select a Cohort as well, or use the Month slicer.

Tested with `etl/prepare_data.py` on a simulated 2025 AWS cohort that reuses the same e-mails:
180 learners, 50 scheduled days per cohort-track, 2025 assessments dated from February 2025,
7 dropouts per cohort.
