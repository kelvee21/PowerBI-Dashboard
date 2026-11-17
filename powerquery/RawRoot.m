// RawRoot — absolute path of data\raw\ built from the pRootFolder parameter
// (right-click > untick "Enable load").
// pRootFolder = the repository root, e.g. C:\Workstation\Amalitech\PowerBI-Dashboard\
// A missing trailing backslash is tolerated.
let
    Root = if Text.EndsWith(pRootFolder, "\") then pRootFolder else pRootFolder & "\",
    Raw = Root & "data\raw\"
in
    Raw
