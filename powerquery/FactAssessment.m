// FactAssessment — one row per learner x programme week x assessment type (Lab / Quiz).
// AssessmentDate = last class day of that programme week FOR THAT COHORT AND TRACK, so the Month
// and Week slicers (DimDate) filter assessments exactly like attendance and participation, and a
// later cohort's "Week 1" gets its own dates.
// IsCompleted = 1 when a score above 0 was recorded (a 0 is treated as not submitted).
// References only (no direct file access): stgAssessment, ClassSchedule.
let
    Valid = Table.SelectRows(stgAssessment, each [WeekNumber] >= 1
                                             and ([Score] = null or ([Score] >= 0 and [Score] <= 100))),
    Completed = Table.AddColumn(Valid, "IsCompleted", each if [Score] <> null and [Score] > 0 then 1 else 0, Int64.Type),
    Key = Table.AddColumn(Completed, "LearnerKey", each [Cohort] & "|" & [Track] & "|" & [Email], type text),
    CohortTrack = Table.AddColumn(Key, "CohortTrackKey", each [Cohort] & "|" & [Track], type text),
    // (cohort-track, programme week) -> last class day of that week
    WeekEnd = Table.Group(ClassSchedule, {"CohortTrackKey", "ProgrammeWeek"},
                          {{"AssessmentDate", each List.Max([Date]), type date}}),
    WithDate = Table.ExpandTableColumn(
                   Table.NestedJoin(CohortTrack, {"CohortTrackKey", "WeekNumber"}, WeekEnd, {"CohortTrackKey", "ProgrammeWeek"}, "WE", JoinKind.LeftOuter),
                   "WE", {"AssessmentDate"}),
    Final = Table.SelectColumns(WithDate, {"LearnerKey", "Email", "Track", "Cohort", "CertificationType", "WeekNumber", "AssessmentDate", "AssessmentType", "Score", "IsCompleted"}),
    Typed = Table.TransformColumnTypes(Final, {
        {"LearnerKey", type text}, {"Email", type text}, {"Track", type text}, {"Cohort", type text},
        {"CertificationType", type text}, {"WeekNumber", Int64.Type}, {"AssessmentDate", type date},
        {"AssessmentType", type text}, {"Score", type number}, {"IsCompleted", Int64.Type}})
in
    Typed
