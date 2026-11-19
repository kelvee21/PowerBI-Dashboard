"""Generate the Power BI project's semantic model (TMDL) from the repository sources.

    python tools/build_pbip.py

Reads  powerquery/*.m  and  model/measures.dax
Writes report/pbip/DareCareers.SemanticModel/   (definition.pbism + definition/*.tmdl)
       report/pbip/DareCareers.pbip              (if missing)

The report pages live in report/pbip/DareCareers.Report/ (edited in Power BI Desktop, not generated).
Open report/pbip/DareCareers.pbip in Power BI Desktop, then Home > Refresh.
"""
from pathlib import Path
import json
import re
import shutil
import uuid

ROOT = Path(__file__).resolve().parent.parent
PQ = ROOT / 'powerquery'
OUT = ROOT / 'report' / 'pbip'
SM = OUT / 'DareCareers.SemanticModel'
NS = uuid.UUID('6f1c2a52-9a3e-4b0e-9d0a-2c1b5e7d4a10')
T = '\t'


def tag(*parts: str) -> str:
    """Stable lineage tag so regenerating does not look like a new object to Power BI."""
    return str(uuid.uuid5(NS, '|'.join(parts)))


def q(name: str) -> str:
    """Quote a TMDL object name when needed."""
    return name if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) else "'" + name.replace("'", "''") + "'"


def body(text: str, tabs: int) -> str:
    lines = [ln.rstrip() for ln in text.strip('\n').split('\n')]
    return '\n'.join(T * tabs + ln for ln in lines if ln.strip())


def m_source(name: str) -> str:
    return (PQ / f'{name}.m').read_text(encoding='utf-8-sig')


# ------------------------------------------------------------------ tables and columns
STR, INT, DBL, DATE = 'string', 'int64', 'double', 'date'
TABLES = {
    'DimLearner': [
        ('LearnerKey', STR, dict(hidden=True)), ('LearnerName', STR, {}), ('Email', STR, dict(hidden=True)),
        ('Track', STR, {}), ('Cohort', STR, {}), ('CohortTrackKey', STR, dict(hidden=True)),
        ('CertificationType', STR, {}),
        ('GraduationStatus', STR, {}), ('CertificationStatus', STR, {}), ('ProgramStatus', STR, {}),
        ('AttendedClassDays', INT, {}), ('ScheduledClassDays', INT, {}),
        ('AttendanceCompletion', DBL, dict(fmt='0.0%')),
        ('LastAttendedDate', DATE, {}), ('LastScheduledDate', DATE, {}),
        ('HasIncompleteAttendance', INT, {}), ('IsDropout', INT, {}), ('DropoutStatus', STR, {}),
    ],
    'ClassSchedule': [
        ('CohortTrackKey', STR, dict(hidden=True)), ('Cohort', STR, dict(hidden=True)),
        ('Track', STR, dict(hidden=True)), ('Date', DATE, dict(hidden=True)),
        ('ProgrammeWeek', INT, dict(hidden=True)),
    ],
    'DimDate': [
        ('Date', DATE, dict(key=True)), ('Year', INT, {}), ('MonthNumber', INT, {}),
        ('MonthName', STR, dict(sort='MonthNumber')), ('MonthYear', STR, dict(sort='MonthYearSort')),
        ('MonthYearSort', INT, dict(hidden=True)), ('WeekNumber', INT, {}),
        ('WeekLabel', STR, dict(sort='WeekNumber')), ('IsClassDay', INT, {}),
        ('DayName', STR, dict(sort='DayOfWeek')), ('DayOfWeek', INT, dict(hidden=True)),
    ],
    'FactAttendance': [
        ('LearnerKey', STR, dict(hidden=True)), ('Email', STR, dict(hidden=True)), ('Track', STR, dict(hidden=True)),
        ('Cohort', STR, dict(hidden=True)), ('CertificationType', STR, dict(hidden=True)), ('Date', DATE, {}),
        ('DurationMinutes', DBL, dict(sum=True, fmt='#,0.0')), ('Attended', INT, {}), ('Role', STR, {}),
    ],
    'FactParticipation': [
        ('LearnerKey', STR, dict(hidden=True)), ('Email', STR, dict(hidden=True)), ('ParticipantName', STR, {}),
        ('Track', STR, dict(hidden=True)), ('Cohort', STR, dict(hidden=True)), ('CertificationType', STR, dict(hidden=True)),
        ('Date', DATE, {}), ('Participated', INT, {}), ('NameMatched', INT, {}),
    ],
    'FactAssessment': [
        ('LearnerKey', STR, dict(hidden=True)), ('Email', STR, dict(hidden=True)), ('Track', STR, dict(hidden=True)),
        ('Cohort', STR, dict(hidden=True)), ('CertificationType', STR, dict(hidden=True)),
        ('WeekNumber', INT, dict(hidden=True)), ('AssessmentDate', DATE, dict(hidden=True)),
        ('AssessmentType', STR, {}), ('Score', DBL, dict(fmt='#,0.0')), ('IsCompleted', INT, {}),
    ],
}
RELATIONSHIPS = [
    ('FactAttendance', 'LearnerKey', 'DimLearner', 'LearnerKey'),
    ('FactParticipation', 'LearnerKey', 'DimLearner', 'LearnerKey'),
    ('FactAssessment', 'LearnerKey', 'DimLearner', 'LearnerKey'),
    ('FactAttendance', 'Date', 'DimDate', 'Date'),
    ('FactParticipation', 'Date', 'DimDate', 'Date'),
    ('FactAssessment', 'AssessmentDate', 'DimDate', 'Date'),
    ('ClassSchedule', 'Date', 'DimDate', 'Date'),
]
# load-disabled queries, in dependency order
EXPRESSIONS = ['Tracks', 'RawRoot', 'fnNormalizeName', 'stgRoster', 'stgZoomNames', 'stgAssessment']

# ------------------------------------------------------------------ measure formats / folders
PCT, DEC1, DEC2, WHOLE = '0.0%', '#,0.0', '#,0.00', '#,0'
MEASURE_META = {
    'Total Learners': (WHOLE, 'Outcomes'), 'Total Graduations': (WHOLE, 'Outcomes'),
    'Total Certifications': (WHOLE, 'Outcomes'), 'Total Dropouts': (WHOLE, 'Outcomes'),
    'Graduation Rate': (PCT, 'Outcomes'), 'Certification Rate': (PCT, 'Outcomes'), 'Dropout Rate': (PCT, 'Outcomes'),
    'Incomplete Attendance Learners': (WHOLE, 'Outcomes'),
    'Class Days': (WHOLE, 'Attendance'), 'Attended Learner Days': (WHOLE, 'Attendance'),
    'Scheduled Learner Days': (WHOLE, 'Attendance'), 'Attendance Rate': (PCT, 'Attendance'),
    'Average Attendance Rate per Learner': (PCT, 'Attendance'), 'Class Hours': (DEC1, 'Attendance'),
    'Average Class Hours per Learner': (DEC1, 'Attendance'),
    'Participation Days': (WHOLE, 'Participation'), 'Participation Rate': (PCT, 'Participation'),
    'Average Participation Rate per Learner': (PCT, 'Participation'),
    'Unmatched Participation Names': (WHOLE, 'Participation'),
    'Average Assessment Score': (DEC1, 'Assessment'), 'Average Lab Score': (DEC1, 'Assessment'),
    'Average Quiz Score': (DEC1, 'Assessment'), 'Labs Completed': (WHOLE, 'Assessment'),
    'Average Labs Completed per Learner': (DEC2, 'Assessment'),
    'Learner Attendance %': (PCT, 'Helpers'), 'Learner Participation %': (PCT, 'Helpers'),
    'Learner Assessment Score': (DEC1, 'Helpers'),
    'Selection Summary': (None, 'Helpers'), 'Attendance Flag Colour': (None, 'Helpers'),
    'Dropout Background': (None, 'Helpers'), 'Dropout Font Colour': (None, 'Helpers'),
}


def parse_measures() -> list:
    """Split model/measures.dax into (name, expression) pairs."""
    text = (ROOT / 'model' / 'measures.dax').read_text(encoding='utf-8-sig')
    measures, cur = [], None
    for line in text.split('\n'):
        # a measure starts at column 0 with "Name =" where Name has no brackets/parens and isn't a VAR
        m = re.match(r'^([A-Za-z][A-Za-z0-9 %_]*?)\s*=(?!=)\s*(.*)$', line)
        if m and not line.startswith('VAR '):
            cur = [m.group(1).strip(), [m.group(2)]]
            measures.append(cur)
        elif cur is not None:
            cur[1].append(line)
    out = []
    for name, lines in measures:
        while lines and (not lines[-1].strip() or lines[-1].lstrip().startswith('--')):
            lines.pop()
        expr = '\n'.join(lines).strip()
        expr = re.sub(r'\s+--[^\n]*$', '', expr) if '\n' not in expr else expr  # drop trailing note on one-liners
        out.append((name, expr))
    missing = set(MEASURE_META) - {n for n, _ in out}
    extra = {n for n, _ in out} - set(MEASURE_META)
    if missing or extra:
        raise SystemExit(f'measure list mismatch: missing={missing} extra={extra}')
    return out


def column_tmdl(table: str, name: str, dtype: str, opt: dict) -> str:
    lines = [f'{T}column {q(name)}', f'{T*2}dataType: {"dateTime" if dtype == DATE else dtype}']
    if dtype == DATE:
        lines.append(f'{T*2}formatString: yyyy-mm-dd')
    elif opt.get('fmt'):
        lines.append(f'{T*2}formatString: {opt["fmt"]}')
    elif dtype == INT:
        lines.append(f'{T*2}formatString: 0')
    if opt.get('key'):
        lines.append(f'{T*2}isKey')
    if opt.get('hidden'):
        lines.append(f'{T*2}isHidden')
    lines.append(f'{T*2}lineageTag: {tag(table, name)}')
    lines.append(f'{T*2}summarizeBy: {"sum" if opt.get("sum") else "none"}')
    lines.append(f'{T*2}sourceColumn: {name}')
    if opt.get('sort'):
        lines.append(f'{T*2}sortByColumn: {opt["sort"]}')
    lines.append('')
    lines.append(f'{T*2}annotation SummarizationSetBy = User')
    if dtype == DATE:
        lines.append('')
        lines.append(f'{T*2}annotation UnderlyingDateTimeDataType = Date')
    return '\n'.join(lines)


def table_tmdl(name: str, columns: list) -> str:
    parts = [f'table {q(name)}', f'{T}lineageTag: {tag(name)}']
    if name == 'DimDate':
        parts.insert(1, f'{T}dataCategory: Time')
    parts.append('')
    for c in columns:
        parts.append(column_tmdl(name, *c))
        parts.append('')
    parts.append(f'{T}partition {q(name)} = m')
    parts.append(f'{T*2}mode: import')
    parts.append(f'{T*2}source =')
    parts.append(body(m_source(name), 4))
    parts.append('')
    parts.append(f'{T}annotation PBI_ResultType = Table')
    return '\n'.join(parts) + '\n'


def measures_table_tmdl() -> str:
    parts = ['table _Measures', f'{T}lineageTag: {tag("_Measures")}', '']
    for name, expr in parse_measures():
        fmt, folder = MEASURE_META[name]
        if '\n' in expr:
            parts.append(f'{T}measure {q(name)} =')
            parts.append(body(expr, 3))
        else:
            parts.append(f'{T}measure {q(name)} = {expr}')
        if fmt:
            parts.append(f'{T*2}formatString: {fmt}')
        parts.append(f'{T*2}displayFolder: {folder}')
        parts.append(f'{T*2}lineageTag: {tag("_Measures", name)}')
        parts.append('')
    parts += [f'{T}column Column1', f'{T*2}dataType: string', f'{T*2}isHidden',
              f'{T*2}lineageTag: {tag("_Measures", "Column1")}', f'{T*2}summarizeBy: none',
              f'{T*2}sourceColumn: Column1', '', f'{T*2}annotation SummarizationSetBy = Automatic', '',
              f'{T}partition _Measures = m', f'{T*2}mode: import', f'{T*2}source =',
              body('let\n    Source = #table(type table [Column1 = text], {})\nin\n    Source', 4), '',
              f'{T}annotation PBI_ResultType = Table']
    return '\n'.join(parts) + '\n'


def expressions_tmdl() -> str:
    root = str(ROOT) + '\\'
    parts = [f'expression pRootFolder = "{root}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
             f'{T}lineageTag: {tag("expr", "pRootFolder")}', '',
             f'{T}annotation PBI_ResultType = Text', '']
    for name in EXPRESSIONS:
        kind = 'Function' if name.startswith('fn') else ('Text' if name == 'RawRoot' else 'Table')
        parts += [f'expression {q(name)} =', body(m_source(name), 2),
                  f'{T}lineageTag: {tag("expr", name)}', '', f'{T}annotation PBI_ResultType = {kind}', '']
    return '\n'.join(parts)


def main() -> None:
    d = SM / 'definition'
    if d.exists():
        shutil.rmtree(d)
    (d / 'tables').mkdir(parents=True)
    (d / 'database.tmdl').write_text('database\n\tcompatibilityLevel: 1601\n\n', encoding='utf-8')
    order = ['_Measures', 'ClassSchedule', 'DimDate', 'FactAttendance', 'DimLearner', 'FactParticipation',
             'FactAssessment']
    query_order = json.dumps(['pRootFolder'] + EXPRESSIONS + order[1:] + ['_Measures'])
    (d / 'model.tmdl').write_text('\n'.join([
        'model Model', f'{T}culture: en-US', f'{T}defaultPowerBIDataSourceVersion: powerBI_V3',
        f'{T}sourceQueryCulture: en-US', f'{T}dataAccessOptions', f'{T*2}legacyRedirects',
        f'{T*2}returnErrorValuesAsNull', '',
        f'annotation __PBI_TimeIntelligenceEnabled = 0', '',
        f'annotation PBI_QueryOrder = {query_order}', '',
        *[f'ref table {q(t)}' for t in order], '']), encoding='utf-8')
    (d / 'expressions.tmdl').write_text(expressions_tmdl(), encoding='utf-8')
    for name, cols in TABLES.items():
        (d / 'tables' / f'{name}.tmdl').write_text(table_tmdl(name, cols), encoding='utf-8')
    (d / 'tables' / '_Measures.tmdl').write_text(measures_table_tmdl(), encoding='utf-8')
    rels = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        rels += [f'relationship {tag("rel", ft, fc, tt, tc)}', f'{T}fromColumn: {ft}.{fc}', f'{T}toColumn: {tt}.{tc}', '']
    (d / 'relationships.tmdl').write_text('\n'.join(rels), encoding='utf-8')

    (SM / 'definition.pbism').write_text(json.dumps({
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json',
        'version': '4.2', 'settings': {}}, indent=2), encoding='utf-8')
    (SM / '.platform').write_text(json.dumps({
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json',
        'metadata': {'type': 'SemanticModel', 'displayName': 'DareCareers'},
        'config': {'version': '2.0', 'logicalId': tag('logical', 'semanticmodel')}}, indent=2), encoding='utf-8')
    pbip = OUT / 'DareCareers.pbip'
    if not pbip.exists():
        pbip.write_text(json.dumps({
            '$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json',
            'version': '1.0', 'artifacts': [{'report': {'path': 'DareCareers.Report'}}],
            'settings': {'enableAutoRecovery': True}}, indent=2), encoding='utf-8')
    n = len(parse_measures())
    print(f'wrote {SM.relative_to(ROOT)}: {len(TABLES) + 1} tables, {n} measures, '
          f'{len(RELATIONSHIPS)} relationships, {len(EXPRESSIONS) + 1} shared queries')


if __name__ == '__main__':
    main()
