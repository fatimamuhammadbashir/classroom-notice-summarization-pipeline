CLASSROOM NOTICE SUMMARIZATION - DEMO
========================================================
Rule-based extractive summarization. No API keys are used.

1. COMPLETE NOTICE: EXTRACTIVE SUMMARY + CHECKLIST
--------------------------------------------------------
Source: year7_museum_visit.txt
Notice ID: NTC-20261124-140946-ACDAF7
Headline: Year 7 Science Museum Visit
Selected sentences: 8 / 8
Quality: pass

Year 7 Science Museum Visit

Audience: Year 7, parents, guardians, students

Summary:
- Our Year 7 science trip to the Northbridge Science Museum will take place on Friday 5 March 2027.
- Students must arrive at school by 7:45 am.
- The coach will leave at 8:00 am and return to school at approximately 4:30 pm.
- Please return the signed permission slip to the school office by Wednesday 3 March 2027.
- The visit costs ┬ú8, and payment must be made by Monday 1 March 2027.
- Do not include nuts or peanut products in packed lunches.
- Students must wear school uniform and comfortable shoes.
- If you have questions, contact the Year 7 office before the visit.

Key dates and times:
- Friday 5 March 2027
- 7:45 am
- 8:00 am
- 4:30 pm
- Wednesday 3 March 2027
- Monday 1 March 2027

Critical instructions:
- Students must arrive at school by 7:45 am.
- The coach will leave at 8:00 am and return to school at approximately 4:30 pm.
- Please return the signed permission slip to the school office by Wednesday 3 March 2027.
- The visit costs ┬ú8, and payment must be made by Monday 1 March 2027.
- Do not include nuts or peanut products in packed lunches.
- Students must wear school uniform and comfortable shoes.

Actions:
- Students must arrive at school by 7:45 am.
- The coach will leave at 8:00 am and return to school at approximately 4:30 pm.
- Please return the signed permission slip to the school office by Wednesday 3 March 2027.
- Students should bring a packed lunch and a water bottle.
- Students must wear school uniform and comfortable shoes.
- If you have questions, contact the Year 7 office before the visit.

Next step:
- Please return the signed permission slip to the school office by Wednesday 3 March 2027.

Checklist:
  [PASS] Audience is clear: Audience: Year 7, parents, guardians, students
  [PASS] All dates and times are preserved: 6 of 6 temporal mentions preserved.
  [PASS] Action is clear: At least one action is identified.
  [PASS] Next step is clear: A next step is included.
  [PASS] Critical instructions are preserved: 6 of 6 critical instructions preserved.
  [PASS] Dates are specific: All date references are calendar dates.
  [PASS] Baseline stays extractive: Summary sentences are copied from the notice.
  [PASS] Baseline length is controlled: 103 summary words; limit 220.
Result JSON: var\results\NTC-20261124-140946-ACDAF7.json
Result Markdown: var\results\NTC-20261124-140946-ACDAF7.md

2. INCOMPLETE NOTICE: CHECKLIST SUGGESTIONS
--------------------------------------------------------
Source: incomplete_notice.txt
Quality: needs_attention
Checklist:
  [FAIL] Audience is clear: The intended audience is missing from the notice or summary.
  [FAIL] All dates and times are preserved: No date or time was found in the notice.
  [FAIL] Action is clear: No clear action from the reader was found.
  [FAIL] Next step is clear: Add a clear next step: who should do what, and by when.
  [PASS] Critical instructions are preserved: No critical instruction cues were detected.
  [FAIL] Dates are specific: No specific date was found.
  [PASS] Baseline stays extractive: Summary sentences are copied from the notice.
  [PASS] Baseline length is controlled: 15 summary words; limit 220.
Suggested missing details:
  - Add the intended audience, for example parents of Year 7.
  - Add at least one specific date or deadline.
  - Add the action required from the reader.
  - Add a clear next step: who should do what, and by when.

3. RELATIVE DATE: SPECIFICITY WARNING
--------------------------------------------------------
Source: relative_date_notice.txt
Quality: needs_attention
Checklist:
  [PASS] Audience is clear: Audience: Year 7, students
  [PASS] All dates and times are preserved: 1 of 1 temporal mentions preserved.
  [PASS] Action is clear: At least one action is identified.
  [PASS] Next step is clear: A next step is included.
  [PASS] Critical instructions are preserved: No critical instruction cues were detected.
  [FAIL] Dates are specific: Relative date(s) found: tomorrow
  [PASS] Baseline stays extractive: Summary sentences are copied from the notice.
  [PASS] Baseline length is controlled: 26 summary words; limit 220.
Suggested missing details:
  - Replace relative date(s) with calendar dates: tomorrow

4. TEACHER EDIT: OVERRIDE GENERATED OUTPUT
--------------------------------------------------------
Edited quality: pass
New headline: Year 7 museum visit ΓÇö key details
Edit history: 1 change(s)
Edited result: var\results\NTC-20261124-140946-ACDAF7.json

5. OVERRIDE THAT REMOVES A DATE: FAILURE IS LOGGED
--------------------------------------------------------
Quality after override: needs_attention
Checklist:
  [PASS] Audience is clear: Audience: Year 7, parents, guardians, students
  [FAIL] All dates and times are preserved: 4 of 6 temporal mentions preserved. Missing: Friday 5 March 2027, Monday 1 March 2027.
  [PASS] Action is clear: At least one action is identified.
  [PASS] Next step is clear: A next step is included.
  [FAIL] Critical instructions are preserved: 4 of 6 critical instructions preserved. Missing: The visit costs ┬ú8, and payment must be made by Monday 1 March 2027. | Do not include nuts or peanut products in packed lunches.
  [PASS] Dates are specific: All date references are calendar dates.
  [FAIL] Baseline stays extractive: The summary contains manually edited text; verify it against the source.
  [PASS] Baseline length is controlled: 24 summary words; limit 220.
Suggested missing details:
  - Keep every source date in the summary: Friday 5 March 2027; Monday 1 March 2027
  - Keep the critical instruction(s): The visit costs ┬ú8, and payment must be made by Monday 1 March 2027.; Do not include nuts or peanut products in packed lunches.
  - The edited summary includes new text; check it against the original notice.
Failure log entries available: 3
Failure log: var\logs\failures.jsonl

DEMO COMPLETE
The generated baseline is extractive; teacher edits are recorded separately.
