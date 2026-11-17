// ClassSchedule — one row per cohort x track x class day (loaded; all columns hidden).
// The source of truth for "scheduled": every Zoom export file is one class day of that
// cohort-track, so each cohort keeps its own timetable.
// ProgrammeWeek counts from the Monday of that cohort-track's first class day, so a cohort that
// starts later still has its own Week 1.
let
    PerTrack = Table.AddColumn(Tracks, "Rows", (t) =>
        let
            files = Table.SelectRows(Folder.Files(RawRoot & t[Folder] & "\Zoom Attendance\"), each Text.Lower([Extension]) = ".csv"),
            dates = List.Distinct(List.Transform(files[Name], (n) =>
                Date.FromText(Text.BeforeDelimiter(n, "."), [Format = "dd-MMM-yyyy", Culture = "en-US"]))),
            week1Monday = Date.StartOfWeek(List.Min(dates), Day.Monday),
            asTable = Table.FromList(dates, Splitter.SplitByNothing(), type table [Date = date]),
            withWeek = Table.AddColumn(asTable, "ProgrammeWeek", each Number.IntegerDivide(Duration.Days([Date] - week1Monday), 7) + 1, Int64.Type)
        in
            withWeek),
    Expanded = Table.ExpandTableColumn(Table.SelectColumns(PerTrack, {"Cohort", "Track", "Rows"}), "Rows", {"Date", "ProgrammeWeek"}),
    Key = Table.AddColumn(Expanded, "CohortTrackKey", each [Cohort] & "|" & [Track], type text),
    Final = Table.SelectColumns(Key, {"CohortTrackKey", "Cohort", "Track", "Date", "ProgrammeWeek"}),
    Typed = Table.TransformColumnTypes(Final, {
        {"CohortTrackKey", type text}, {"Cohort", type text}, {"Track", type text},
        {"Date", type date}, {"ProgrammeWeek", Int64.Type}})
in
    Typed
