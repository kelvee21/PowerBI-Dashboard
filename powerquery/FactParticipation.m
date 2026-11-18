// FactParticipation — one row per learner listed as participating on a class day.
// The source lists comma-separated display names (no e-mail), so names are matched to the
// roster through fnNormalizeName. Unmatched names are KEPT with NameMatched = 0 and a null
// LearnerKey so they can be audited instead of silently disappearing.
let
    PerTrack = Table.AddColumn(Tracks, "Rows", (t) =>
        let
            // roster lookup: normalised e-mail local part -> e-mail
            statusFile = Table.SelectRows(Folder.Files(RawRoot & t[Folder] & "\Status of Learners\"), each Text.Lower([Extension]) = ".xlsx"){0}[Content],
            statusSheet = Table.PromoteHeaders(Excel.Workbook(statusFile, null, true){0}[Data], [PromoteAllScalars = true]),
            emails = Table.TransformColumns(Table.SelectColumns(statusSheet, {"email"}), {{"email", each Text.Lower(Text.Trim(Text.From(_))), type text}}),
            lookup = Table.Buffer(Table.AddColumn(emails, "NameKey", each fnNormalizeName(Text.BeforeDelimiter([email], "@")), type text)),

            partFile = Table.SelectRows(Folder.Files(RawRoot & t[Folder] & "\Participation\"), each Text.Lower([Extension]) = ".xlsx"){0}[Content],
            partSheet = Table.PromoteHeaders(Excel.Workbook(partFile, null, true){0}[Data], [PromoteAllScalars = true]),
            base = Table.SelectColumns(partSheet, {"Date", "Participants"}),
            typedDate = Table.TransformColumns(base, {{"Date", each
                if _ is date then _
                else if _ is datetime then Date.From(_)
                else Date.FromText(Text.From(_), [Format = "dd-MMM-yyyy", Culture = "en-US"]), type date}}),
            names = Table.AddColumn(typedDate, "ParticipantName", each
                List.Select(List.Transform(Text.Split(if [Participants] = null then "" else Text.From([Participants]), ","), Text.Trim), (n) => n <> "")),
            oneRowPerName = Table.ExpandListColumn(Table.RemoveColumns(names, {"Participants"}), "ParticipantName"),
            withKey = Table.AddColumn(oneRowPerName, "NameKey", each fnNormalizeName([ParticipantName]), type text),
            // the same person listed twice on one day counts once
            deduped = Table.Distinct(withKey, {"Date", "NameKey"}),
            matched = Table.NestedJoin(deduped, {"NameKey"}, lookup, {"NameKey"}, "Match", JoinKind.LeftOuter),
            expanded = Table.ExpandTableColumn(matched, "Match", {"email"}, {"Email"}),
            withTrack = Table.AddColumn(expanded, "TrackInfo", each t, type record)
        in
            Table.ExpandRecordColumn(withTrack, "TrackInfo", {"Track", "Cohort", "CertificationType"})
    ),
    Combined = Table.Combine(PerTrack[Rows]),
    Matched = Table.AddColumn(Combined, "NameMatched", each if [Email] = null then 0 else 1, Int64.Type),
    Participated = Table.AddColumn(Matched, "Participated", each 1, Int64.Type),
    Key = Table.AddColumn(Participated, "LearnerKey", each if [Email] = null then null else [Cohort] & "|" & [Track] & "|" & [Email], type nullable text),
    Final = Table.SelectColumns(Key, {"LearnerKey", "Email", "ParticipantName", "Track", "Cohort", "CertificationType", "Date", "Participated", "NameMatched"}),
    Typed = Table.TransformColumnTypes(Final, {
        {"LearnerKey", type text}, {"Email", type text}, {"ParticipantName", type text}, {"Track", type text},
        {"Cohort", type text}, {"CertificationType", type text}, {"Date", type date},
        {"Participated", Int64.Type}, {"NameMatched", Int64.Type}})
in
    Typed
