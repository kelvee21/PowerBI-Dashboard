// fnNormalizeName — letters-only, lower-case key used to match participation names
// ("Emily Johnson") to roster e-mail local parts ("emilyjohnson", "emily.johnson").
// Must stay identical to name_key() in etl/prepare_data.py.
(name as nullable text) as text =>
let
    lowered = if name = null then "" else Text.Lower(name),
    lettersOnly = Text.Select(lowered, {"a".."z"})
in
    lettersOnly
