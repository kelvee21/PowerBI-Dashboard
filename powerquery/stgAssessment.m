// stgAssessment — STAGING (untick "Enable load"). Labs & Quizzes sheets unpivoted from
// wide (Week 1 ... Week 10) to one row per learner x week x assessment type.
let
    PerTrack = Table.AddColumn(Tracks, "Rows", (t) =>
        let
            file = Table.SelectRows(Folder.Files(RawRoot & t[Folder] & "\Labs & Quizes\"), each Text.Lower([Extension]) = ".xlsx"){0}[Content],
            wb = Excel.Workbook(file, null, true),
            ReadSheet = (sheetName as text, assessmentType as text) as table =>
                let
                    sheet = Table.PromoteHeaders(Table.SelectRows(wb, each [Name] = sheetName){0}[Data], [PromoteAllScalars = true]),
                    unpivoted = Table.UnpivotOtherColumns(sheet, {"email"}, "WeekLabel", "Score"),
                    weeksOnly = Table.SelectRows(unpivoted, each Text.StartsWith([WeekLabel], "Week ")),
                    withType = Table.AddColumn(weeksOnly, "AssessmentType", each assessmentType, type text)
                in
                    withType,
            both = Table.Combine({ReadSheet("Labs", "Lab"), ReadSheet("Quizzes", "Quiz")}),
            withTrack = Table.AddColumn(both, "TrackInfo", each t, type record)
        in
            Table.ExpandRecordColumn(withTrack, "TrackInfo", {"Track", "Cohort", "CertificationType"})
    ),
    Combined = Table.Combine(PerTrack[Rows]),
    Email = Table.TransformColumns(Combined, {{"email", each Text.Lower(Text.Trim(Text.From(_))), type text}}),
    Renamed = Table.RenameColumns(Email, {{"email", "Email"}}),
    Week = Table.AddColumn(Renamed, "WeekNumber", each Number.From(Text.AfterDelimiter([WeekLabel], "Week ")), Int64.Type),
    Score = Table.TransformColumns(Week, {{"Score", each try Number.From(_) otherwise null, type nullable number}})
in
    Score
