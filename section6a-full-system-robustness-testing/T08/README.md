# T08 - Semantic / synonym / transferable-skill match (Leo Chen)

## Scenario and observed finding

Parser recognized TypeScript, REST APIs and relational database design alongside Node.js, Express and PostgreSQL. Tailoring recognized Node.js/JavaScript/REST coverage and distinguished missing React/AWS/MongoDB. It retained 2.4-to-0.9-second query timing and personal project limitations. Matching remained 51%/0% attainability before and after reload, identical to the baker. The CV includes explicit technology names as well as synonyms, so it is not an isolated synonym-only benchmark. All new cases showed the same 24-role list and Node.js 51% fit, 0% attainability, 100% barrier and generic covered-requirements statement.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. The saved final text is in `05_observed_output/`.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. Full per-call provider request/response logs and independent model attestation were not collected. The database copies in 05_observed_output are saved system output, not browser downloads. Parsed profiles remained user_confirmed=false; confirmation was not exercised. No separately named parse-start capture is available; parse task timestamps and parsed-state captures are retained.

## File index

- [01_input/08_Leo_Chen.pdf](01_input/08_Leo_Chen.pdf) - test input
- [01_input/08_Leo_Chen.txt](01_input/08_Leo_Chen.txt) - test input
- [02_screenshots/T08_job_detail.png](02_screenshots/T08_job_detail.png) - screenshot
- [02_screenshots/T08_matches_after_reload.png](02_screenshots/T08_matches_after_reload.png) - screenshot
- [02_screenshots/T08_matches_before_reload.png](02_screenshots/T08_matches_before_reload.png) - screenshot
- [02_screenshots/T08_output_T09_parsed.png](02_screenshots/T08_output_T09_parsed.png) - screenshot
- [02_screenshots/T08_parsed.png](02_screenshots/T08_parsed.png) - screenshot
- [02_screenshots/T08_rationale.png](02_screenshots/T08_rationale.png) - screenshot
- [02_screenshots/T08_tailoring_started.png](02_screenshots/T08_tailoring_started.png) - screenshot
- [02_screenshots/T08_uploaded.png](02_screenshots/T08_uploaded.png) - screenshot
- [03_ui_observations/T08_job_detail.txt](03_ui_observations/T08_job_detail.txt) - records / observed text
- [03_ui_observations/T08_matches_after_reload.txt](03_ui_observations/T08_matches_after_reload.txt) - records / observed text
- [03_ui_observations/T08_matches_before_reload.txt](03_ui_observations/T08_matches_before_reload.txt) - records / observed text
- [03_ui_observations/T08_output_T09_parsed.txt](03_ui_observations/T08_output_T09_parsed.txt) - records / observed text
- [03_ui_observations/T08_parsed.txt](03_ui_observations/T08_parsed.txt) - records / observed text
- [03_ui_observations/T08_rationale.txt](03_ui_observations/T08_rationale.txt) - records / observed text
- [03_ui_observations/T08_tailoring_started.txt](03_ui_observations/T08_tailoring_started.txt) - records / observed text
- [03_ui_observations/T08_uploaded.txt](03_ui_observations/T08_uploaded.txt) - records / observed text
- [04_records/T08_database_snapshot.json](04_records/T08_database_snapshot.json) - records / observed text
- [04_records/case_database_extract.json](04_records/case_database_extract.json) - records / observed text
- [04_records/task_timing_extract.json](04_records/task_timing_extract.json) - records / observed text
- [05_observed_output/08_system_output.txt](05_observed_output/08_system_output.txt) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
