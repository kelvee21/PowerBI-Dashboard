// DimLearner — one row per learner enrolment (Cohort|Track|email), with outcome attributes.
// Outcomes are learner attributes (1:1 with the learner), so they live here rather than in a
// separate 1:1 "status" table: slicers on them then filter every fact through DimLearner.
// Dropout = Non Graduate AND Not Certified AND HasIncompleteAttendance (all three).
// Scheduled days come from ClassSchedule for the learner's own cohort and track, so cohorts with
// different timetables are each measured against their own class days.
// References only (no direct file access): stgRoster, stgZoomNames, FactAttendance, ClassSchedule.
let
    // ---- display name ---------------------------------------------------------------------
    WithName = Table.ExpandTableColumn(
        Table.NestedJoin(stgRoster, {"LearnerKey"}, stgZoomNames, {"LearnerKey"}, "Z", JoinKind.LeftOuter), "Z", {"Name"}, {"ZoomName"}),
    LearnerName = Table.AddColumn(WithName, "LearnerName", each
        if [ZoomName] <> null then Text.Trim([ZoomName])
        else Text.Proper(Text.Replace(Text.Replace(Text.BeforeDelimiter([Email], "@"), ".", " "), "_", " ")), type text),
    CohortTrack = Table.AddColumn(LearnerName, "CohortTrackKey", each [Cohort] & "|" & [Track], type text),

    // ---- attendance completeness (from FactAttendance, > 30 min rule already applied) ------
    AttendedRows = Table.SelectRows(FactAttendance, each [Attended] = 1),
    PerLearner = Table.Group(Table.Distinct(Table.SelectColumns(AttendedRows, {"LearnerKey", "Date"})), {"LearnerKey"}, {
        {"AttendedClassDays", each Table.RowCount(_), Int64.Type},
        {"LastAttendedDate", each List.Max([Date]), type date}}),
    PerCohortTrack = Table.Group(ClassSchedule, {"CohortTrackKey"}, {
        {"ScheduledClassDays", each Table.RowCount(_), Int64.Type},
        {"LastScheduledDate", each List.Max([Date]), type date}}),
    J1 = Table.ExpandTableColumn(Table.NestedJoin(CohortTrack, {"LearnerKey"}, PerLearner, {"LearnerKey"}, "A", JoinKind.LeftOuter), "A", {"AttendedClassDays", "LastAttendedDate"}),
    J2 = Table.ExpandTableColumn(Table.NestedJoin(J1, {"CohortTrackKey"}, PerCohortTrack, {"CohortTrackKey"}, "S", JoinKind.LeftOuter), "S", {"ScheduledClassDays", "LastScheduledDate"}),
    NoNullDays = Table.ReplaceValue(J2, null, 0, Replacer.ReplaceValue, {"AttendedClassDays"}),   // never attended -> 0 days

    // ---- business rules ---------------------------------------------------------------------
    Completion = Table.AddColumn(NoNullDays, "AttendanceCompletion", each Number.Round([AttendedClassDays] / [ScheduledClassDays], 4), type number),
    Incomplete = Table.AddColumn(Completion, "HasIncompleteAttendance", each if [AttendedClassDays] < [ScheduledClassDays] then 1 else 0, Int64.Type),
    Dropout = Table.AddColumn(Incomplete, "IsDropout", each
        if [GraduationStatus] = "Non Graduate" and [CertificationStatus] = "Not Certified" and [HasIncompleteAttendance] = 1 then 1 else 0, Int64.Type),
    DropoutLabel = Table.AddColumn(Dropout, "DropoutStatus", each if [IsDropout] = 1 then "Dropout" else "Not Dropout", type text),
    Program = Table.AddColumn(DropoutLabel, "ProgramStatus", each if [GraduationStatus] = "" then "Ongoing" else "Completed", type text),

    Final = Table.SelectColumns(Program, {
        "LearnerKey", "LearnerName", "Email", "Track", "Cohort", "CohortTrackKey", "CertificationType",
        "GraduationStatus", "CertificationStatus", "ProgramStatus",
        "AttendedClassDays", "ScheduledClassDays", "AttendanceCompletion", "LastAttendedDate", "LastScheduledDate",
        "HasIncompleteAttendance", "IsDropout", "DropoutStatus"}),
    Typed = Table.TransformColumnTypes(Final, {
        {"LearnerKey", type text}, {"LearnerName", type text}, {"Email", type text}, {"Track", type text},
        {"Cohort", type text}, {"CohortTrackKey", type text}, {"CertificationType", type text}, {"GraduationStatus", type text},
        {"CertificationStatus", type text}, {"ProgramStatus", type text},
        {"AttendedClassDays", Int64.Type}, {"ScheduledClassDays", Int64.Type}, {"AttendanceCompletion", type number},
        {"LastAttendedDate", type date}, {"LastScheduledDate", type date},
        {"HasIncompleteAttendance", Int64.Type}, {"IsDropout", Int64.Type}, {"DropoutStatus", type text}})
in
    Typed
