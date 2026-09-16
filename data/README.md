# Data

## `processed/` (IOG-34)

Structured CSVs generated from the approved 150-student workbook in
`data/dataset/`: `grades.csv`, `rubric_comments.csv`, and
`silo_mappings.csv`. They are the inspectable tables IOG-34 asked for —
same columns the pipeline already uses, written by
`python -m src.connect.export_processed`. See `data/processed/README.md`.

## `sample/`

Small, entirely synthetic CSVs (fake subject, fake students, fake grades)
used so the pipeline runs end-to-end with zero setup - `pytest` and
`python -m src.parse.cleaners` both read from here by default. **None of
this is real student data.** Column names match exactly what
`src/parse/schema_validation.py` expects; keep them in sync if you add a
column.

| File | Purpose |
|---|---|
| `subjects_sample.csv` | Subject code/name/description |
| `learning_outcomes_sample.csv` | SILOs per subject |
| `rubrics_sample.csv` | Rubric criteria, optionally linked to a SILO |
| `students_sample.csv` | Synthetic students (no real names/IDs) |
| `assessment_results_sample.csv` | Synthetic grades + feedback text |

## `provided/` (not in this repo yet)

Once the subject coordinator supplies the real historical dataset
(subjects, assessments, rubrics, student records, feedback - this is
IOG-33), create a `data/provided/` folder, drop the real files in using
the **same column names** as the sample files above, and switch
`DATA_DIR` in `src/connect/historical_dataset_loader.py` to point at it.

`data/provided/` should be added to `.gitignore` before any real student
data goes anywhere near it - real student records must never be
committed to a GitHub repo, private or not. Add that line to `.gitignore`
yourself the moment this folder exists; it's deliberately not
pre-added here so nobody copy-pastes real data into a path they assume
is already safe.
