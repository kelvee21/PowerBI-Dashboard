// stgRoster — STAGING (untick "Enable load"). Learner roster + outcomes from the
// "Status of Learners" workbooks. Kept separate so DimLearner only *references* queries
// (avoids the Formula.Firewall "rebuild this data combination" error).
let
    PerTrack = Table.AddColumn(Tracks, "Rows", (t) =>
        let
            file = Table.SelectRows(Folder.Files(RawRoot & t[Folder] & "\Status of Learners\"), each Text.Lower([Extension]) = ".xlsx"){0}[Content],
            sheet = Table.PromoteHeaders(Excel.Workbook(file, null, true){0}[Data], [PromoteAllScalars = true]),
            kept = Table.SelectColumns(sheet, {"email", "Graduation Status", "Certification Status"}, MissingField.UseNull),
            withTrack = Table.AddColumn(kept, "TrackInfo", each t, type record)
        in
            Table.ExpandRecordColumn(withTrack, "TrackInfo", {"Track", "Cohort", "CertificationType"})
    ),
    Roster = Table.Combine(PerTrack[Rows]),
    Renamed = Table.RenameColumns(Roster, {{"email", "Email"}, {"Graduation Status", "GraduationStatus"}, {"Certification Status", "CertificationStatus"}}),
    Clean = Table.TransformColumns(Renamed, {
        {"Email", each Text.Lower(Text.Trim(Text.From(_))), type text},
        {"GraduationStatus", each if _ = null then "" else Text.Trim(Text.From(_)), type text},
        {"CertificationStatus", each if _ = null then "" else Text.Trim(Text.From(_)), type text}}),
    NonBlank = Table.SelectRows(Clean, each [Email] <> ""),
    Key = Table.AddColumn(NonBlank, "LearnerKey", each [Cohort] & "|" & [Track] & "|" & [Email], type text)
in
    Key
