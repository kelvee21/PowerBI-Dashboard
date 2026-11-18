"""Prepare the Dare Careers learner-progress star schema from the raw lab files.

Run from anywhere:  python etl/prepare_data.py   (requires pandas + openpyxl)

Inputs:  data/raw/<track folder>/...
Outputs (data/curated/):
    DimLearner.csv        one row per learner enrolment (Cohort|Track|email) incl. outcome attributes
    ClassSchedule.csv     one row per cohort x track x class day (each Zoom file is one class day)
    DimDate.csv           one row per calendar day, first to last class day (contiguous)
    FactAttendance.csv    one row per Zoom participant session (learner x class day here)
    FactParticipation.csv one row per learner name listed on a participation day
    FactAssessment.csv    one row per learner x week x assessment type (Lab / Quiz)

Business rules (see docs/data-dictionary.md):
    * Attended            = a Zoom session of MORE than 30 minutes (strict >)
    * Incomplete attendance = AttendedClassDays < ScheduledClassDays for the learner's cohort and track
    * Dropout             = Non Graduate AND Not Certified AND incomplete attendance (all three)
"""
from pathlib import Path
import re

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent          # repository root
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'data' / 'curated'
OUT.mkdir(parents=True, exist_ok=True)

ATTEND_MINUTES = 30      # attended only if DurationMinutes > ATTEND_MINUTES
# One row per cohort x track (same as powerquery/Tracks.m). The folder is relative to data/raw and
# may include a cohort subfolder, e.g. '2025/Cloud Training'. Add a row for every future cohort.
TRACKS = [  # folder, track, certification type, cohort
    ('PowerBI Training', 'Power BI', 'Power BI', '2024'),
    ('Cloud Training', 'AWS Cloud', 'AWS', '2024'),
]


def name_key(text: str) -> str:
    """Letters-only, lower-case key used to match participation names to roster emails."""
    return re.sub(r'[^a-z]', '', str(text).casefold())


def duration_minutes(value) -> float:
    """Power BI exports h:mm:ss, AWS Cloud exports numeric minutes: detect from the value."""
    text = str(value).strip()
    try:
        if ':' in text:
            return pd.to_timedelta(text).total_seconds() / 60
        return float(text)
    except (ValueError, TypeError):
        return 0.0


def first_file(folder: Path, pattern: str) -> Path:
    files = sorted(folder.glob(pattern))
    if not files:
        raise FileNotFoundError(f'No {pattern} in {folder}')
    return files[0]


learners, attendance, participation, assessment, schedule = [], [], [], [], []

for folder, track, cert_type, cohort in TRACKS:
    base = RAW / folder
    common = dict(Track=track, Cohort=cohort, CertificationType=cert_type)
    ct_key = f'{cohort}|{track}'
    key = lambda e, ct=ct_key: f'{ct}|{e}'

    # ---- roster + outcomes (one row per learner) -------------------------------------
    status = pd.read_excel(first_file(base / 'Status of Learners', '*.xlsx'))
    status.columns = [c.strip() for c in status.columns]
    roster = {}
    for _, r in status.iterrows():
        email = str(r['email']).strip().lower()
        roster[name_key(email.split('@')[0])] = email
        learners.append(dict(
            LearnerKey=key(email), Email=email, **common,
            GraduationStatus=str(r['Graduation Status']).strip() if pd.notna(r['Graduation Status']) else '',
            CertificationStatus=str(r['Certification Status']).strip() if pd.notna(r['Certification Status']) else '',
        ))

    # ---- assessments: wide Week 1..10 -> long ----------------------------------------
    workbook = first_file(base / 'Labs & Quizes', '*.xlsx')
    for sheet, a_type in [('Labs', 'Lab'), ('Quizzes', 'Quiz')]:
        wide = pd.read_excel(workbook, sheet_name=sheet)
        long = wide.melt(id_vars='email', var_name='WeekLabel', value_name='Score')
        for r in long.itertuples(index=False):
            email = str(r.email).strip().lower()
            score = None if pd.isna(r.Score) else float(r.Score)
            assessment.append(dict(
                LearnerKey=key(email), Email=email, **common,
                WeekNumber=int(r.WeekLabel.replace('Week', '').strip()),
                AssessmentType=a_type, Score=score,
                IsCompleted=int(score is not None and score > 0),
            ))

    # ---- Zoom attendance: one CSV per class day inside Week N folders ----------------
    # Each file is one class day of THIS cohort-track: that is the class schedule.
    zoom_files = sorted((base / 'Zoom Attendance').rglob('*.csv'))
    days = {pd.to_datetime(f.stem, format='%d-%b-%Y').date(): int(re.search(r'Week (\d+)', str(f)).group(1))
            for f in zoom_files}
    week1_mon = pd.Timestamp(min(days)) - pd.Timedelta(days=min(days).weekday())
    for day, folder_week in sorted(days.items()):
        week = (pd.Timestamp(day) - week1_mon).days // 7 + 1   # this cohort-track's own programme week
        assert week == folder_week, f'{ct_key}: {day} is in the Week {folder_week} folder but computes to {week}'
        schedule.append(dict(CohortTrackKey=ct_key, Cohort=cohort, Track=track,
                             Date=day.isoformat(), ProgrammeWeek=week))
    for f in zoom_files:
        day = pd.to_datetime(f.stem, format='%d-%b-%Y').date()
        for r in pd.read_csv(f).itertuples(index=False):
            email = str(r.Email).strip().lower()
            if not email or email == 'nan':
                continue
            mins = duration_minutes(r.Duration)
            attendance.append(dict(
                LearnerKey=key(email), Email=email, **common,
                Date=day.isoformat(), DurationMinutes=round(mins, 2),
                Attended=int(mins > ATTEND_MINUTES), Role=str(r.Role),
            ))

    # ---- participation: comma-separated names per day -> one row per name ------------
    part = pd.read_excel(first_file(base / 'Participation', '*.xlsx'))
    for r in part.itertuples(index=False):
        day = pd.to_datetime(r.Date, format='%d-%b-%Y').date()
        seen = set()
        for nm in str(r.Participants).split(','):
            nm = nm.strip()
            if not nm or nm.lower() == 'nan' or name_key(nm) in seen:
                continue  # skip blanks and duplicate mentions of the same person on the same day
            seen.add(name_key(nm))
            email = roster.get(name_key(nm), '')
            participation.append(dict(
                LearnerKey=key(email) if email else '', Email=email, ParticipantName=nm, **common,
                Date=day.isoformat(), Participated=1, NameMatched=int(bool(email)),
            ))

dim_learner = pd.DataFrame(learners)
dim_learner['CohortTrackKey'] = dim_learner.Cohort + '|' + dim_learner.Track
class_sched = pd.DataFrame(schedule)
fact_att = pd.DataFrame(attendance)
fact_part = pd.DataFrame(participation)
fact_asmt = pd.DataFrame(assessment)

# ---- DimDate: contiguous calendar (required to mark as date table) --------------------
class_dates = set(pd.to_datetime(class_sched.Date).dt.date)
first_day, last_day = min(class_dates), max(class_dates)
cal = pd.DataFrame({'Date': pd.date_range(first_day, last_day, freq='D')})
week1_monday = pd.Timestamp(first_day) - pd.Timedelta(days=pd.Timestamp(first_day).weekday())
cal['Year'] = cal.Date.dt.year
cal['MonthNumber'] = cal.Date.dt.month
cal['MonthName'] = cal.Date.dt.strftime('%B')
cal['MonthYear'] = cal.Date.dt.strftime('%b %Y')
cal['MonthYearSort'] = cal.Year * 100 + cal.MonthNumber          # sort-by column for MonthYear
cal['WeekNumber'] = ((cal.Date - week1_monday).dt.days // 7 + 1).astype(int)  # weeks since the first class week
cal['WeekLabel'] = 'Week ' + cal.WeekNumber.astype(str)
cal['IsClassDay'] = cal.Date.dt.date.isin(class_dates).astype(int)
cal['DayName'] = cal.Date.dt.strftime('%A')
cal['DayOfWeek'] = cal.Date.dt.weekday + 1

# ---- assessments get a date (last class day of THEIR cohort-track's week) ----------------
week_end = (class_sched.groupby(['CohortTrackKey', 'ProgrammeWeek']).Date.max()
            .rename('AssessmentDate').reset_index())
fact_asmt['CohortTrackKey'] = fact_asmt.Cohort + '|' + fact_asmt.Track
fact_asmt = fact_asmt.merge(week_end, left_on=['CohortTrackKey', 'WeekNumber'],
                            right_on=['CohortTrackKey', 'ProgrammeWeek'], how='left')

# ---- learner-level attendance completeness + dropout (stored on DimLearner) ------------
att_days = (fact_att[fact_att.Attended == 1].groupby('LearnerKey')
            .agg(AttendedClassDays=('Date', 'nunique'), LastAttendedDate=('Date', 'max')))
sched = class_sched.groupby('CohortTrackKey').Date.agg(ScheduledClassDays='nunique', LastScheduledDate='max')
dim_learner = (dim_learner.merge(att_days, on='LearnerKey', how='left')
               .merge(sched, left_on='CohortTrackKey', right_index=True, how='left'))
dim_learner['AttendedClassDays'] = dim_learner.AttendedClassDays.fillna(0).astype(int)
dim_learner['LastAttendedDate'] = dim_learner.LastAttendedDate.fillna('')
dim_learner['AttendanceCompletion'] = (dim_learner.AttendedClassDays / dim_learner.ScheduledClassDays).round(4)
dim_learner['HasIncompleteAttendance'] = (dim_learner.AttendedClassDays < dim_learner.ScheduledClassDays).astype(int)
dim_learner['IsDropout'] = ((dim_learner.GraduationStatus == 'Non Graduate')
                            & (dim_learner.CertificationStatus == 'Not Certified')
                            & (dim_learner.HasIncompleteAttendance == 1)).astype(int)
dim_learner['DropoutStatus'] = dim_learner.IsDropout.map({1: 'Dropout', 0: 'Not Dropout'})
dim_learner['ProgramStatus'] = dim_learner.GraduationStatus.apply(lambda s: 'Completed' if s else 'Ongoing')
dim_learner['LearnerName'] = dim_learner.Email.str.split('@').str[0].str.replace(r'[._]', ' ', regex=True).str.title()
# Power BI local-part emails have no separator (emilyjohnson) -> use the Zoom display name instead
zoom_names = {}
for folder, track, _, cohort in TRACKS:
    for f in sorted((RAW / folder / 'Zoom Attendance').rglob('*.csv')):
        z = pd.read_csv(f)
        zoom_names.update({f'{cohort}|{track}|{e.strip().lower()}': n.strip() for e, n in zip(z.Email, z.Name)})
dim_learner['LearnerName'] = dim_learner.LearnerKey.map(zoom_names).fillna(dim_learner.LearnerName)

# ---- validation: fail loudly instead of publishing wrong numbers -----------------------
checks = {
    'LearnerKey unique in DimLearner': dim_learner.LearnerKey.is_unique,
    'Date unique in DimDate': cal.Date.is_unique,
    'No attendance rows for unknown learners': fact_att.LearnerKey.isin(dim_learner.LearnerKey).all(),
    'No assessment rows for unknown learners': fact_asmt.LearnerKey.isin(dim_learner.LearnerKey).all(),
    'Scores within 0-100': fact_asmt.Score.dropna().between(0, 100).all(),
    'Assessment grain unique': not fact_asmt.duplicated(['LearnerKey', 'WeekNumber', 'AssessmentType']).any(),
    'Participation learner-day unique': not fact_part[fact_part.NameMatched == 1].duplicated(['LearnerKey', 'Date']).any(),
    'Every learner has a class schedule': dim_learner.ScheduledClassDays.notna().all(),
    'Every assessment has a date': fact_asmt.AssessmentDate.notna().all(),
    'ClassSchedule grain unique': not class_sched.duplicated(['CohortTrackKey', 'Date']).any(),
    'All fact dates inside DimDate': set(fact_att.Date) | set(fact_part.Date) | set(fact_asmt.AssessmentDate)
                                     <= set(cal.Date.dt.strftime('%Y-%m-%d')),
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit('Validation failed: ' + '; '.join(failed))

# ---- write ------------------------------------------------------------------------------
cal['Date'] = cal.Date.dt.strftime('%Y-%m-%d')
outputs = {
    'DimLearner': dim_learner[['LearnerKey', 'LearnerName', 'Email', 'Track', 'Cohort', 'CohortTrackKey',
                               'CertificationType',
                               'GraduationStatus', 'CertificationStatus', 'ProgramStatus',
                               'AttendedClassDays', 'ScheduledClassDays', 'AttendanceCompletion',
                               'LastAttendedDate', 'LastScheduledDate',
                               'HasIncompleteAttendance', 'IsDropout', 'DropoutStatus']],
    'ClassSchedule': class_sched,
    'DimDate': cal,
    'FactAttendance': fact_att,
    'FactParticipation': fact_part,
    'FactAssessment': fact_asmt[['LearnerKey', 'Email', 'Track', 'Cohort', 'CertificationType', 'WeekNumber',
                                 'AssessmentDate', 'AssessmentType', 'Score', 'IsCompleted']],
}
for name, df in outputs.items():
    df.to_csv(OUT / f'{name}.csv', index=False)
for stale in ('DimWeek.csv', 'FactLearnerStatus.csv'):   # merged into DimDate / DimLearner
    (OUT / stale).unlink(missing_ok=True)

# ---- reconciliation summary (quote these numbers in the defence) -----------------------
dl = outputs['DimLearner']
print('rows:', {k: len(v) for k, v in outputs.items()})
print('validation checks passed:', len(checks))
print('learners by track:', dl.Track.value_counts().to_dict())
print('class days:', int(cal.IsClassDay.sum()), 'calendar days:', len(cal))
print('attendance rate (attended learner-days / scheduled learner-days): '
      f'{fact_att.Attended.sum() / dl.ScheduledClassDays.sum():.1%}')
print('sessions of exactly 30 min (NOT attended):', int((fact_att.DurationMinutes == 30).sum()))
print('participation rows:', len(fact_part), 'unmatched names:', int((fact_part.NameMatched == 0).sum()))
print('graduates:', int((dl.GraduationStatus == 'Graduate').sum()),
      'certified:', int((dl.CertificationStatus == 'Certified').sum()),
      'dropouts:', int(dl.IsDropout.sum()))
print(dl.groupby(['Track', 'GraduationStatus', 'CertificationStatus', 'HasIncompleteAttendance']).size().to_string())
