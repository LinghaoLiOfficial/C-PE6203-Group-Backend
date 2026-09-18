# T02 - Maya - career transition / missing skills

## Scenario and observed finding

Parsing completed in 69.8 s; rewrite completed in 91.3 s with No tailoring applied. No unsupported development skills added. Data Analyst search returned no results with the wrong upload prompt. Used Node.js for negative grounding check.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. Available output is embedded in the original UI captures; no output has been recreated.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. No historical full database/variant export or standalone system-output file was collected; available output/rationale is in UI captures.

## File index

- [01_input/02_Maya_Lim_Career_Change-source.txt](01_input/02_Maya_Lim_Career_Change-source.txt) - test input
- [01_input/02_Maya_Lim_Career_Change.pdf](01_input/02_Maya_Lim_Career_Change.pdf) - test input
- [02_screenshots/M01-upload-error.png](02_screenshots/M01-upload-error.png) - screenshot
- [02_screenshots/M02-upload-success.png](02_screenshots/M02-upload-success.png) - screenshot
- [02_screenshots/M03-parsed.png](02_screenshots/M03-parsed.png) - screenshot
- [02_screenshots/M04-matches.png](02_screenshots/M04-matches.png) - screenshot
- [02_screenshots/M05-data-analyst-no-results.png](02_screenshots/M05-data-analyst-no-results.png) - screenshot
- [02_screenshots/M06-job-detail.png](02_screenshots/M06-job-detail.png) - screenshot
- [02_screenshots/M06-job-viewport.png](02_screenshots/M06-job-viewport.png) - screenshot
- [02_screenshots/M07-rewrite-queued.png](02_screenshots/M07-rewrite-queued.png) - screenshot
- [02_screenshots/M08-rewrite-result.png](02_screenshots/M08-rewrite-result.png) - screenshot
- [02_screenshots/M09-rationale.png](02_screenshots/M09-rationale.png) - screenshot
- [03_ui_observations/M01-upload-error.txt](03_ui_observations/M01-upload-error.txt) - records / observed text
- [03_ui_observations/M02-upload-success.txt](03_ui_observations/M02-upload-success.txt) - records / observed text
- [03_ui_observations/M03-parsed.txt](03_ui_observations/M03-parsed.txt) - records / observed text
- [03_ui_observations/M04-matches.txt](03_ui_observations/M04-matches.txt) - records / observed text
- [03_ui_observations/M05-data-analyst-no-results.txt](03_ui_observations/M05-data-analyst-no-results.txt) - records / observed text
- [03_ui_observations/M06-job-detail.txt](03_ui_observations/M06-job-detail.txt) - records / observed text
- [03_ui_observations/M07-rewrite-queued.txt](03_ui_observations/M07-rewrite-queued.txt) - records / observed text
- [03_ui_observations/M08-rewrite-result.txt](03_ui_observations/M08-rewrite-result.txt) - records / observed text
- [03_ui_observations/M09-rationale.txt](03_ui_observations/M09-rationale.txt) - records / observed text
- [04_records/capture_timestamps.json](04_records/capture_timestamps.json) - records / observed text
- [04_records/parse-task-timings.json](04_records/parse-task-timings.json) - records / observed text
- [04_records/rewrite-task-timings.json](04_records/rewrite-task-timings.json) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
