# T02 - Maya - career transition / missing skills

Extracted from the existing QA report; this is a report excerpt, not a new execution. Original report-relative links below refer to the former layout; use README.md in this folder for the package file paths.

- Severity: High (historical matching defect); Medium empty-search UI.
- Area: upload, parsing, matching, tailoring and UI.
- Environment: historical frontend 5e27b87; backend da34149 with then-existing local fixes; historical report observed openrouter/qwen3.7-plus.
- Input: evidence/tests_01_03_historical/inputs/02_Maya_Lim_Career_Change.pdf.
- Steps: historical upload → parse → active resume → job list/details → tailoring → rationale/output as available. See unchanged original report for exact sequence.
- Expected: Do not turn four years of customer support into analyst/developer experience or a 40-hour course into a degree.
- Actual: Parsing completed in 69.8 s; rewrite completed in 91.3 s with No tailoring applied. No unsupported development skills added. Data Analyst search returned no results with the wrong upload prompt. Used Node.js for negative grounding check.
- Evidence: [original report](evidence/tests_01_03_historical/完整测试报告.md), [case evidence](evidence/tests_01_03_historical/M09-rationale.txt); tailoring task `74769ecd-f276-43de-afbf-47aed716b234`.
- Reproducible: not rerun in this continuation; original observations and limitations retained.

