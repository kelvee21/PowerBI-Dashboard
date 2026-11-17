// Tracks — configuration table (right-click > untick "Enable load").
// One row per cohort x track. Folder is relative to data\raw\ and may include a cohort
// subfolder, e.g. "2025\Cloud Training". To add a future cohort or track, add a row here;
// LearnerKey (Cohort|Track|email) and ClassSchedule keep every cohort separate.
let
    Source = #table(
        type table [Folder = text, Track = text, CertificationType = text, Cohort = text],
        {
            {"PowerBI Training", "Power BI",  "Power BI", "2024"},
            {"Cloud Training",   "AWS Cloud", "AWS",      "2024"}
        }
    )
in
    Source
