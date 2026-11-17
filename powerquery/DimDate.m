// DimDate — one row per calendar day from the first to the last class day of ANY cohort
// (contiguous, so it can be marked as the date table). Weekends are included with IsClassDay = 0.
// WeekNumber counts weeks from the Monday of the first class day in the data. With one cohort it
// equals the programme week ("Week N" source folders). Each cohort's own programme week is
// ClassSchedule[ProgrammeWeek] and FactAssessment[WeekNumber].
// References only (no direct file access): ClassSchedule.
let
    ClassDates = List.Buffer(List.Distinct(ClassSchedule[Date])),
    FirstDay = List.Min(ClassDates),
    LastDay = List.Max(ClassDates),
    Week1Monday = Date.StartOfWeek(FirstDay, Day.Monday),
    Calendar = Table.FromList(
        List.Dates(FirstDay, Duration.Days(LastDay - FirstDay) + 1, #duration(1, 0, 0, 0)),
        Splitter.SplitByNothing(), type table [Date = date]),
    AddYear = Table.AddColumn(Calendar, "Year", each Date.Year([Date]), Int64.Type),
    AddMonthNo = Table.AddColumn(AddYear, "MonthNumber", each Date.Month([Date]), Int64.Type),
    AddMonth = Table.AddColumn(AddMonthNo, "MonthName", each Date.MonthName([Date], "en-US"), type text),
    AddMonthYear = Table.AddColumn(AddMonth, "MonthYear", each Date.ToText([Date], [Format = "MMM yyyy", Culture = "en-US"]), type text),
    AddMonthSort = Table.AddColumn(AddMonthYear, "MonthYearSort", each [Year] * 100 + [MonthNumber], Int64.Type),
    AddWeek = Table.AddColumn(AddMonthSort, "WeekNumber", each Number.IntegerDivide(Duration.Days([Date] - Week1Monday), 7) + 1, Int64.Type),
    AddWeekLabel = Table.AddColumn(AddWeek, "WeekLabel", each "Week " & Text.From([WeekNumber]), type text),
    AddClassDay = Table.AddColumn(AddWeekLabel, "IsClassDay", each if List.Contains(ClassDates, [Date]) then 1 else 0, Int64.Type),
    AddDayName = Table.AddColumn(AddClassDay, "DayName", each Date.DayOfWeekName([Date], "en-US"), type text),
    AddDayNo = Table.AddColumn(AddDayName, "DayOfWeek", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type)
in
    AddDayNo
