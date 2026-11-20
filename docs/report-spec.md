# Report specification and requirement traceability

Every line of the [lab brief](lab-brief.md) and of the mentor clarification maps to a visual, field
or rule below. Layout and formatting steps are in the [build guide](build-guide.md).

## Page 1: Overall Performance

| Brief requirement | Visual | Field / measure |
| --- | --- | --- |
| Graduation rates (bar) | Clustered column by Track | `[Graduation Rate]` |
| Certification rates (bar) | Clustered column by Track | `[Certification Rate]` |
| Dropout rates (bar) | Clustered column by Track | `[Dropout Rate]` |
| Average attendance (bar) | Clustered column by Track | `[Attendance Rate]` |
| Average participation (bar) | Clustered column by Track | `[Average Participation Rate per Learner]` |
| Average assessment scores, quiz and lab (bar) | Clustered column by Track, legend AssessmentType | `[Average Assessment Score]` |
| Cards: Total Certifications, Learners, Dropouts, Graduations | One multi-callout Card (or 4 cards) | `[Total Certifications]`, `[Total Learners]`, `[Total Dropouts]`, `[Total Graduations]` |
| Slicer: Cohort | Slicer | `DimLearner[Cohort]` |
| Slicer: Track | Slicer | `DimLearner[Track]` |
| Slicer: Certification Type (retain, per mentor) | Slicer | `DimLearner[CertificationType]` (AWS, Power BI) |
| Slicer: Learner Status (Certified / Not Certified) | Slicer | `DimLearner[CertificationStatus]` |

"Per cohort" in the brief: the X-axis is Track because the dataset holds one cohort. When a second
cohort is loaded, put `DimLearner[Cohort]` on the X-axis and Track in the legend (or use small
multiples). No model change is needed.

## Page 2: Learner Insights

| Brief requirement | Visual | Field / measure |
| --- | --- | --- |
| Learner table with track, attendance, participation, assessment | Table | LearnerName, Track, CertificationType, `[Attendance Rate]`, `[Average Participation Rate per Learner]`, `[Average Assessment Score]`, `[Labs Completed]`, `[Class Hours]`, Graduation, Certification, DropoutStatus |
| Count of Labs | Card | `[Labs Completed]` |
| Average Labs Completed | Card | `[Average Labs Completed per Learner]` |
| Total Hours Spent in Class | Card (and a table column, per learner) | `[Class Hours]` |
| Average Attendance Rate | Card | `[Average Attendance Rate per Learner]` |
| Average Participation Rate | Card | `[Average Participation Rate per Learner]` |
| Average Assessment Scores | Card | `[Average Assessment Score]` |
| Slicers: Cohort, Track, Month, Week, Learner Status, Program Status | Slicers | `Cohort`, `Track`, `DimDate[MonthYear]`, `DimDate[WeekLabel]`, `DimLearner[CertificationStatus]`, `DimLearner[ProgramStatus]` (+ Certification Type) |

## Additional instructions

| Instruction | Where it is met |
| --- | --- |
| Attended only if > 30 minutes; applies to all attendance calculations | `FactAttendance[Attended]`, `[Attended Learner Days]`, `[Class Hours]`, `DimLearner[AttendedClassDays]` |
| Structured, cleaned data | `powerquery/*.m` or `etl/prepare_data.py` (8 automated checks) |
| Daily directories used for the 30-minute rule | 100 daily Zoom CSVs → `FactAttendance` |
| Weekly lab/quiz averages and totals, learner and cohort level | Unpivoted `FactAssessment`; measures respond to learner, track, cohort, week and month |
| DAX for attendance %, averages, certification/graduation rates | `model/measures.dax` |
| Relationships between attendance, participation, labs, quizzes, learner status | Star schema: `DimLearner` and `DimDate` filter all three facts; learner status = `DimLearner` attributes |

## Mentor clarification

| Clarification | Implementation |
| --- | --- |
| Single cohort, two tracks; ready for more cohorts | `Cohort` column independent of `Track`; `Tracks.m` config table |
| Dropout = Non-Graduate AND Not Certified AND incomplete attendance | `DimLearner[IsDropout]` and the `[Total Dropouts]` measure, which states all three conditions explicitly |
| Retain Certification Type slicer (AWS, Power BI) | `DimLearner[CertificationType]` slicer on both pages |

## Acceptance checklist

- [ ] Row counts: 140 / 68 / 7,000 / 6,037 / 2,800.
- [ ] Seven relationships, all one-to-many and single direction (six to the facts, one `DimDate` → `ClassSchedule`); `DimDate` marked as date table.
- [ ] No slicer uses a column from a fact table.
- [ ] Cards with no slicers: 140 learners · 119 graduations · 92 certifications · 7 dropouts.
- [ ] Attendance 94.1% · participation 86.2% · avg score 50.8 · labs completed 1,383.
- [ ] Learner Status = Not Certified → Total Learners 48; Track = AWS Cloud → dropout rate 17.5%.
- [ ] Week slicer is in order (Week 1 … Week 10) and changes attendance and assessment values.
- [ ] All required visuals present (6 charts and 4 KPIs on page 1; table and 6 KPIs on page 2).
- [ ] Polish checklist (build guide §8) complete.
