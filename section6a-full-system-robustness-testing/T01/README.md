# T01 - Jordan Lee - normal technical fit

## Scenario and observed finding

Upload/parse completed; new upload parsing took 56.3 s. Earlier Jordan record was used for the 130.5 s completed rewrite. Output preserved key facts; 51% fit with 0% attainability contradicted covered requirements. These are two resume records, not one uninterrupted fresh run.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. Available output is embedded in the original UI captures; no output has been recreated.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. No historical full database/variant export or standalone system-output file was collected; available output/rationale is in UI captures. Jordan has two parse task records; the completed rewrite used the earlier resume record. This is not one continuous fresh upload-to-rewrite run.

## File index

- [01_input/01_Jordan_Lee_NodeJS_Developer-source.txt](01_input/01_Jordan_Lee_NodeJS_Developer-source.txt) - test input
- [01_input/01_Jordan_Lee_NodeJS_Developer.pdf](01_input/01_Jordan_Lee_NodeJS_Developer.pdf) - test input
- [02_screenshots/J01-upload-error.png](02_screenshots/J01-upload-error.png) - screenshot
- [02_screenshots/J02-parse-start.png](02_screenshots/J02-parse-start.png) - screenshot
- [02_screenshots/J03-parsed-result.png](02_screenshots/J03-parsed-result.png) - screenshot
- [02_screenshots/J04-matches.png](02_screenshots/J04-matches.png) - screenshot
- [02_screenshots/J05-job-detail.png](02_screenshots/J05-job-detail.png) - screenshot
- [02_screenshots/J06-rewrite-queued.png](02_screenshots/J06-rewrite-queued.png) - screenshot
- [02_screenshots/J07-generating.png](02_screenshots/J07-generating.png) - screenshot
- [02_screenshots/J08-rewrite-result.png](02_screenshots/J08-rewrite-result.png) - screenshot
- [02_screenshots/J09-rationale.png](02_screenshots/J09-rationale.png) - screenshot
- [02_screenshots/J11-upload-success.png](02_screenshots/J11-upload-success.png) - screenshot
- [02_screenshots/J12-new-parse-complete.png](02_screenshots/J12-new-parse-complete.png) - screenshot
- [03_ui_observations/J01-upload-error.txt](03_ui_observations/J01-upload-error.txt) - records / observed text
- [03_ui_observations/J02-parse-start.txt](03_ui_observations/J02-parse-start.txt) - records / observed text
- [03_ui_observations/J03-parsed-result.txt](03_ui_observations/J03-parsed-result.txt) - records / observed text
- [03_ui_observations/J04-matches.txt](03_ui_observations/J04-matches.txt) - records / observed text
- [03_ui_observations/J05-job-detail.txt](03_ui_observations/J05-job-detail.txt) - records / observed text
- [03_ui_observations/J06-rewrite-queued.txt](03_ui_observations/J06-rewrite-queued.txt) - records / observed text
- [03_ui_observations/J07-generating.txt](03_ui_observations/J07-generating.txt) - records / observed text
- [03_ui_observations/J08-rewrite-result.txt](03_ui_observations/J08-rewrite-result.txt) - records / observed text
- [03_ui_observations/J09-rationale.txt](03_ui_observations/J09-rationale.txt) - records / observed text
- [03_ui_observations/J11-upload-success.txt](03_ui_observations/J11-upload-success.txt) - records / observed text
- [03_ui_observations/J12-new-parse-complete.txt](03_ui_observations/J12-new-parse-complete.txt) - records / observed text
- [04_records/capture_timestamps.json](04_records/capture_timestamps.json) - records / observed text
- [04_records/parse-task-timings.json](04_records/parse-task-timings.json) - records / observed text
- [04_records/rewrite-task-timings.json](04_records/rewrite-task-timings.json) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
