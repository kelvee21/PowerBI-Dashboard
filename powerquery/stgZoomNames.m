// stgZoomNames — STAGING (untick "Enable load"). LearnerKey -> display name from the Zoom
// exports. Needed because Power BI-track e-mails have no name separator (emilyjohnson@...).
let
    PerTrack = List.Transform(Table.ToRecords(Tracks), (t) =>
        let
            files = Table.SelectRows(Folder.Files(RawRoot & t[Folder] & "\Zoom Attendance\"), each Text.Lower([Extension]) = ".csv"),
            tables = List.Transform(files[Content], (c) =>
                Table.SelectColumns(
                    Table.PromoteHeaders(Csv.Document(c, [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]), [PromoteAllScalars = true]),
                    {"Name", "Email"})),
            combined = Table.Combine(tables),
            nonBlank = Table.SelectRows(combined, each [Email] <> null and Text.Trim([Email]) <> "")
        in
            Table.AddColumn(nonBlank, "LearnerKey", each t[Cohort] & "|" & t[Track] & "|" & Text.Lower(Text.Trim([Email])), type text)),
    Combined = Table.Combine(PerTrack),
    OnePerLearner = Table.Distinct(Table.SelectColumns(Combined, {"LearnerKey", "Name"}), {"LearnerKey"})
in
    OnePerLearner
