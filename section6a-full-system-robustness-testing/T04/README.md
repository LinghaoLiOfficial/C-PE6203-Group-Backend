# T04 - Ambiguous experience wording (Evan Tan)

## Scenario and observed finding

Parser kept a support/coordinator role but shortened introductory JavaScript and team-result caveats in the skill/highlight summary. Full source evidence and final output preserved the limits: no production coding, no cloud provisioning, and team-level 20% savings. Tailoring marked most technical requirements not met. All new cases showed the same 24-role list and Node.js 51% fit, 0% attainability, 100% barrier and generic covered-requirements statement.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. The saved final text is in `05_observed_output/`.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. Full per-call provider request/response logs and independent model attestation were not collected. The database copies in 05_observed_output are saved system output, not browser downloads. Parsed profiles remained user_confirmed=false; confirmation was not exercised.

## File index

- [01_input/04_Evan_Tan.pdf](01_input/04_Evan_Tan.pdf) - test input
- [01_input/04_Evan_Tan.txt](01_input/04_Evan_Tan.txt) - test input
- [02_screenshots/T04_job_detail.png](02_screenshots/T04_job_detail.png) - screenshot
- [02_screenshots/T04_matches.png](02_screenshots/T04_matches.png) - screenshot
- [02_screenshots/T04_output_T05_uploaded.png](02_screenshots/T04_output_T05_uploaded.png) - screenshot
- [02_screenshots/T04_parse_started.png](02_screenshots/T04_parse_started.png) - screenshot
- [02_screenshots/T04_parsed.png](02_screenshots/T04_parsed.png) - screenshot
- [02_screenshots/T04_rationale.png](02_screenshots/T04_rationale.png) - screenshot
- [02_screenshots/T04_tailoring_running.png](02_screenshots/T04_tailoring_running.png) - screenshot
- [02_screenshots/T04_upload.png](02_screenshots/T04_upload.png) - screenshot
- [03_ui_observations/T04_job_detail.txt](03_ui_observations/T04_job_detail.txt) - records / observed text
- [03_ui_observations/T04_matches.txt](03_ui_observations/T04_matches.txt) - records / observed text
- [03_ui_observations/T04_output_T05_uploaded.txt](03_ui_observations/T04_output_T05_uploaded.txt) - records / observed text
- [03_ui_observations/T04_parse_started.txt](03_ui_observations/T04_parse_started.txt) - records / observed text
- [03_ui_observations/T04_parsed.txt](03_ui_observations/T04_parsed.txt) - records / observed text
- [03_ui_observations/T04_rationale.txt](03_ui_observations/T04_rationale.txt) - records / observed text
- [03_ui_observations/T04_tailoring_running.txt](03_ui_observations/T04_tailoring_running.txt) - records / observed text
- [03_ui_observations/T04_upload.txt](03_ui_observations/T04_upload.txt) - records / observed text
- [04_records/T04_database_snapshot.json](04_records/T04_database_snapshot.json) - records / observed text
- [04_records/case_database_extract.json](04_records/case_database_extract.json) - records / observed text
- [04_records/task_timing_extract.json](04_records/task_timing_extract.json) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
