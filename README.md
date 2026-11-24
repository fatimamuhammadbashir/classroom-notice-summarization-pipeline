# FIP Beginner Capstone 03 - Classroom Notice Summarization Pipeline

A rule-based Python pipeline that turns a classroom notice into an **extractive
summary** while preserving every date/time and critical instruction. It checks
the result against an accuracy checklist, suggests missing details, lets a
teacher edit or override the summary, and logs failures locally.

**Status:** complete prototype, tested, and documented. This is Project 3 of the
8 FIP Beginner capstone projects.

> **Sample data notice:** all notices in `data/notices/` are synthetic examples
> written for this capstone. They are not real school communications.

---

## What it does

The project addresses the brief with a deterministic, standard-library pipeline.
There is no paid API, no model call, and no hidden rewriting of the source.

| Requirement | Implementation |
|---|---|
| Notice upload | CLI file input, stdin or pasted text; validated UTF-8 `.txt`/`.md` |
| Extractive baseline | Rule-based sentence scoring, with mandatory date/instruction sentences |
| Summary generation | Structured headline, audience, summary, key dates, critical instructions, actions and next step |
| Accuracy checklist | Audience, date, action, next step, critical instructions, date specificity, extractive warning and length |
| Preserve dates | Date/time mentions are extracted and added to a mandatory preservation set |
| Preserve critical instructions | Cue-based instruction extraction, with an explicit preserved/ missing check |
| Missing-detail suggestions | Checklist produces concrete suggestions when audience/date/action/next step is absent |
| Teacher override | `edit` command applies validated overrides and records an edit history |
| Failure logging | Checklist failures are appended to a local JSONL failure log |
| Safe errors | Validation, storage and edit errors return readable JSON, not tracebacks |

---

## Quick start

Requirements: **Python 3.13** (the project uses only the standard library).

Open a terminal in the project folder, then run:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Validate a notice
python app.py validate data/notices/year7_museum_visit.txt

# Create an extractive summary and result files
python app.py summarize data/notices/year7_museum_visit.txt

# Show the full result as JSON
python app.py summarize data/notices/year7_museum_visit.txt --json

# Run the complete scripted demonstration
python app.py demo

# Run the automated test suite
python -m unittest discover -s tests -v
```

`requirements.txt` contains no third-party packages. The virtual environment is
optional.

---

## Commands

| Command | Purpose |
|---|---|
| `python app.py validate NOTICE` | Check that a notice file is supported and valid |
| `python app.py summarize NOTICE [--json] [--out FILE]` | Summarize one notice and save JSON/Markdown |
| `python app.py summarize --text "..."` | Summarize pasted text instead of a file |
| `python app.py summarize -` | Read notice text from stdin |
| `python app.py batch DIRECTORY [--out-dir DIR]` | Process every `.txt`/`.md` notice in a directory |
| `python app.py checklist RESULT.json` | Show the checklist stored in a result |
| `python app.py edit RESULT.json --edits EDITS.json --actor NAME` | Apply teacher overrides |
| `python app.py failures [--limit N] [--json]` | Show recent logged failures |
| `python app.py demo` | Run the scripted demonstration |

All commands run from the project folder. Use `--store PATH` before the command
to keep generated results and logs somewhere other than `var/`.

By default, `summarize` saves:

- `var/results/<notice-id>.json`
- `var/results/<notice-id>.md`

Use `--out some/path/result.json` to write a copy somewhere else. The Markdown
export is written beside it.

---

## Pipeline

```text
Notice file or text
        |
        v
Validation and normalization
        |
        v
Sentence splitting
        |
        v
Rule-based analysis
  - audience
  - dates and times
  - actions
  - critical instructions
  - next step
        |
        v
Extractive baseline
  - score sentences
  - preserve mandatory date/instruction sentences
  - select remaining sentences up to limits
        |
        v
Structured summary generation
        |
        v
Accuracy checklist and missing-detail suggestions
        |
        v
JSON + Markdown result, optional teacher edit, failure log
```

### Notice validation

The upload layer checks:

- file exists and is a file
- extension is `.txt` or `.md`
- UTF-8 encoding (BOM accepted)
- minimum and maximum character limits
- no null characters
- non-empty normalized text

Invalid input returns a safe JSON error with exit code `2`.

### Date and time extraction

The rule set recognizes:

- `Friday 5 March 2027`
- `5 March 2027`
- `March 5, 2027`
- `2027-03-05`
- `5/3/2027`
- relative references such as `tomorrow`, `today`, `next Friday`
- times such as `7:45 am`, `8:00 am`, `4:30 pm`, `noon`

Exact source text is retained. Calendar dates also receive an ISO-normalized
value. Relative dates are detected but are flagged by the specificity check
because they do not give a calendar date.

### Critical instruction extraction

A sentence is treated as critical when it contains a strong cue such as:

`must`, `must not`, `required`, `need to`, `ensure`, `do not`,
`no later than`, `deadline`, `urgent`, `important`, `only`, `not allowed`,
`permission`.

An action sentence is also critical when it contains an action cue together
with a date/time or a deadline phrase. This keeps sentences such as “return the
signed permission slip by Wednesday” in the mandatory set.

### Audience, action and next step

- **Audience** patterns include parents, guardians, carers, families, students,
  pupils, teachers, staff, `Year N` and class names.
- **Actions** are source sentences containing cues such as bring, return, submit,
  sign, pay, complete, arrive, collect, register, book, wear, pack, contact or
  reply.
- **Next step** prefers return/submit/sign/pay/complete/register/book/reply
  actions with a deadline, then other deadline actions, then date-linked
  actions.

---

## Extractive baseline

`src/summarizer.py` scores each non-heading source sentence using:

- keyword frequency
- position in the notice
- date/time presence
- critical instruction presence
- action presence
- audience presence
- sentence length fit

The score breakdown is stored in `baseline.candidate_scores`.

**Mandatory preservation:** every sentence containing a date/time or a critical
instruction is selected automatically. The baseline then fills the remaining
space with the highest-scoring optional sentences, preserving source order.
If mandatory sentences exceed `max_sentences` or `max_words`, they are still
kept and `limit_exceeded` is set to `true`.

The default limits are 8 sentences and 220 summary words. They can be changed
with `--max-sentences` and `--max-words`.

This is an **extractive** baseline: every generated summary sentence is copied
from the notice. It is not paraphrased.

---

## Structured summary

The generated summary contains:

```json
{
  "headline": "Year 7 Science Museum Visit",
  "audience": ["Year 7", "parents", "guardians", "students"],
  "sentences": [
    {"sentence_id": 2, "text": "...", "score": 8.4, "mandatory": true, "manual": false}
  ],
  "key_dates": ["Friday 5 March 2027", "7:45 am"],
  "critical_instructions": ["Students must arrive at school by 7:45 am."],
  "actions": ["Please return the signed permission slip..."],
  "next_steps": ["Please return the signed permission slip..."],
  "word_count": 103,
  "generator": "rule-based-extractive-v1",
  "rendered": "..."
}
```

The JSON result also includes the source text, sentence records, full analysis,
baseline scoring, checklist and edit history. Markdown export uses the rendered
summary.

---

## Accuracy checklist

Every result includes a checklist with required and warning-only checks.

| Check | Required | What it verifies |
|---|---|---|
| Audience is clear | Yes | Audience is detected in the notice and present in the summary |
| All dates and times are preserved | Yes | Every source date/time appears in the rendered summary |
| Action is clear | Yes | At least one reader action is identified |
| Next step is clear | Yes | The summary contains a concrete next step |
| Critical instructions are preserved | Yes | Every critical instruction appears in the rendered summary |
| Dates are specific | Yes | No relative date such as “tomorrow” is left unresolved |
| Baseline stays extractive | Warning | Summary sentences match the source (manual edits are flagged) |
| Baseline length is controlled | Warning | Selected summary sentences fit the word limit |

If a required check fails, the result gets:

```json
"quality_status": "needs_attention"
```

The checklist also generates `missing_details` suggestions, for example:

- Add the intended audience, for example parents of Year 7.
- Add at least one specific date or deadline.
- Add the action required from the reader.
- Add a clear next step: who should do what, and by when.
- Replace relative date(s) with calendar dates: tomorrow.
- Keep every source date in the summary: Friday 5 March 2027.
- Keep the critical instruction(s): Students must wear school uniform.

---

## Teacher editing and override

Generated output is a draft. A teacher can apply a JSON edit file:

```json
{
  "headline": "Year 7 museum visit — key details",
  "next_steps": [
    "Return the signed permission slip to the school office by Wednesday 3 March 2027."
  ],
  "note": "Clarified the headline and kept the deadline."
}
```

```powershell
python app.py edit var/results/NTC-....json --edits data/sample_edits.json --actor "Ms. Rivera"
```

Editable fields:

- `headline`
- `audience`
- `sentences`
- `key_dates`
- `critical_instructions`
- `actions`
- `next_steps`

Edits are validated, re-rendered and re-checked against the original notice.
The edit is recorded in `edits` with timestamp, actor, note and changed fields.

If an override removes a date or critical instruction, the checklist fails and
the result is still saved with `quality_status: "needs_attention"`. This is a
deliberate override, not a silent success. The failure is logged.

---

## Failure log

Failures are appended to `var/logs/failures.jsonl` and can be inspected with:

```powershell
python app.py failures --limit 10
```

Each record contains timestamp, notice ID, source, event (`generated` or
`edited`), quality status, failed check IDs and missing-detail suggestions.
The full notice text is **not** written to the failure log.

`var/` is excluded by `.gitignore`.

---

## Sample data

| Notice | Purpose |
|---|---|
| `year7_museum_visit.txt` | Complete notice with multiple dates, payment deadline, permission slip and safety instructions |
| `year11_exam_update.txt` | Exam timetable with arrival times and equipment rules |
| `book_fair.txt` | Optional purchase notice with family session times |
| `sports_day.txt` | Sports day with equipment and attendance instructions |
| `relative_date_notice.txt` | Contains “tomorrow” to demonstrate the date-specificity warning |
| `incomplete_notice.txt` | Deliberately lacks audience, date, action and next step |

`data/sample_edits.json` demonstrates a normal teacher edit.  
`data/override_removing_date.json` demonstrates a deliberate override that
removes dates and critical instructions so the checklist and failure log can
catch it.

---

## Demo

```powershell
python app.py demo
```

The demo runs:

1. A complete notice: extractive summary, preserved dates/instructions and a passing checklist.
2. An incomplete notice: failed checks and missing-detail suggestions.
3. A relative-date notice: date-specificity warning.
4. A teacher edit: override the headline and next step.
5. A deliberate override that removes dates: checklist failure and failure log.

Captured output is in `outputs/demo_transcript.md`.  
A sample generated result is in `outputs/sample_summary.json` and
`outputs/sample_summary.md`.

---

## Testing

```powershell
python -m unittest discover -s tests -v
```

**Result: 81 tests passed, 0 failed.**

The tests cover:

- text normalization and sentence splitting
- date/time formats and relative dates
- audience, action, critical-instruction and next-step detection
- extractive baseline scoring, verbatim selection and mandatory preservation
- structured summary fields and rendered output
- every checklist check and missing-detail suggestion
- teacher editing, validation and override failure
- result storage, Markdown export and failure logging
- notice validation and safe CLI errors
- batch processing, checklist command and complete demo

The suite is fully offline and uses temporary directories.

---

## Project structure

```text
03-Classroom-Notice-Summarization-Pipeline\
|-- app.py                         # CLI entry point
|-- config.json                    # limits, thresholds and storage paths
|-- requirements.txt               # standard library only
|-- README.md
|-- data\
|   |-- notices\                   # synthetic classroom notices
|   |-- sample_edits.json
|   `-- override_removing_date.json
|-- src\
|   |-- validation.py              # notice upload validation
|   |-- text_processing.py         # normalization and sentence splitting
|   |-- analysis.py                # dates, audience, actions and instructions
|   |-- summarizer.py              # extractive baseline and summary rendering
|   |-- checklist.py               # accuracy checklist and suggestions
|   |-- editing.py                 # teacher overrides and edit history
|   |-- storage.py                 # JSON/Markdown results and failure log
|   |-- pipeline.py                # end-to-end processing
|   |-- service.py                 # application workflow
|   |-- demo.py                    # scripted demonstration
|   |-- cli.py                     # CLI commands
|   |-- config.py
|   |-- errors.py
|   `-- __init__.py
|-- tests\                         # 8 test modules plus helpers
|-- outputs\
|   |-- demo_transcript.md
|   |-- sample_summary.json
|   `-- sample_summary.md
`-- var\                           # runtime results and failure log, ignored by Git
```

---

## Design decisions

1. **Extractive before generative.** The baseline copies source sentences, so
   dates and critical wording cannot drift.
2. **Mandatory preservation beats length.** Date/instruction sentences are never
   dropped to satisfy a word target. If they exceed the target, the result says
   so explicitly.
3. **Rule-based detection is inspectable.** Dates, audience, actions and critical
   cues are regular expressions and word lists in `src/analysis.py`.
4. **Checklist after generation, not before.** The summary is checked against the
   original source, so a teacher can see exactly what was lost.
5. **Human override is supported, not hidden.** Edits are recorded and a
   deliberate incomplete override is saved with a failing checklist and a
   failure-log entry.
6. **Failures are data.** The JSONL log supports later review of notices that
   need better source information.
7. **No content in failure logs.** The log records source names and failed
   checks, not the full notice text.
8. **Synthetic samples.** The notices contain no real student, parent or staff
   information.

---

## Limitations

- Date detection is rule-based and covers English-language formats only.
- Relative dates such as “tomorrow” are detected but rejected by the
  specificity check because the calendar date cannot be inferred.
- Critical-instruction detection depends on cue words. A vague instruction with
  no cue may be missed.
- Audience detection is phrase-based and may return broad groups such as
  `students` rather than a narrower class.
- The extractive baseline can be verbose when a notice contains many critical
  instructions. It reports `limit_exceeded` rather than dropping them.
- The pipeline is a local CLI tool. There is no web UI, authentication or
  multi-user database.
- The checklist is a quality aid, not a legal or safeguarding review.

---

## Security and privacy

- No API keys, credentials or paid services are used.
- No network calls are made by the application or test suite.
- `.gitignore` excludes `.venv/`, `.env*`, caches, logs and `var/`.
- Failure logs deliberately omit full notice text.
- Result files contain notice text and teacher edit notes, so `var/` should be
  reviewed before sharing or committing.
- All sample notices are synthetic.
