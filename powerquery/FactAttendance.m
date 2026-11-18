// FactAttendance — one row per Zoom participant session (here: one per learner per class day).
// Rule: Attended = 1 only when DurationMinutes > 30 (strict; exactly 30 is NOT attended).
let
    PerTrack = Table.AddColumn(Tracks, "Rows", (t) =>
        let
            files = Folder.Files(RawRoot & t[Folder] & "\Zoom Attendance\"),
            csvs = Table.SelectRows(files, each Text.Lower([Extension]) = ".csv"),
            perFile = Table.AddColumn(csvs, "Data", (f) =>
                let
                    // file name = class date, e.g. 05-Aug-2024.csv
                    sessionDate = Date.FromText(Text.BeforeDelimiter(f[Name], "."), [Format = "dd-MMM-yyyy", Culture = "en-US"]),
                    csv = Csv.Document(f[Content], [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
                    promoted = Table.PromoteHeaders(csv, [PromoteAllScalars = true]),
                    kept = Table.SelectColumns(promoted, {"Email", "Duration", "Role"}, MissingField.UseNull)
                in
                    Table.AddColumn(kept, "Date", each sessionDate, type date)
            ),
            combined = Table.Combine(perFile[Data]),
            withTrack = Table.AddColumn(combined, "TrackInfo", each t, type record)
        in
            Table.ExpandRecordColumn(withTrack, "TrackInfo", {"Track", "Cohort", "CertificationType"})
    ),
    Combined = Table.Combine(PerTrack[Rows]),
    CleanEmail = Table.TransformColumns(Combined, {{"Email", each if _ = null then null else Text.Lower(Text.Trim(Text.From(_))), type nullable text}}),
    NonBlank = Table.SelectRows(CleanEmail, each [Email] <> null and [Email] <> ""),
    // Two encodings: Power BI exports h:mm:ss, AWS Cloud exports numeric minutes.
    // The format is detected from the value itself rather than assumed from the folder.
    // A blank or unreadable duration becomes 0 minutes (never attended) instead of a row error.
    Minutes = Table.AddColumn(NonBlank, "DurationMinutes", each
        let d = Text.Trim(if [Duration] = null then "" else Text.From([Duration]))
        in  try Number.Round(
                    if Text.Contains(d, ":")
                    then Duration.TotalMinutes(Duration.FromText(d))
                    else Number.From(d, "en-US"), 2)
            otherwise 0,
        type number),
    Attended = Table.AddColumn(Minutes, "Attended", each if [DurationMinutes] > 30 then 1 else 0, Int64.Type),
    Key = Table.AddColumn(Attended, "LearnerKey", each [Cohort] & "|" & [Track] & "|" & [Email], type text),
    Final = Table.SelectColumns(Key, {"LearnerKey", "Email", "Track", "Cohort", "CertificationType", "Date", "DurationMinutes", "Attended", "Role"}),
    Typed = Table.TransformColumnTypes(Final, {
        {"LearnerKey", type text}, {"Email", type text}, {"Track", type text}, {"Cohort", type text},
        {"CertificationType", type text}, {"Date", type date}, {"DurationMinutes", type number},
        {"Attended", Int64.Type}, {"Role", type text}})
in
    Typed
