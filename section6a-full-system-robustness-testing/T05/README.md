# T05 - Missing technical information (Nora Lee)

## Scenario and observed finding

Parser explicitly said no programming, database, cloud or framework proficiency was indicated. Final output retained the administrative role, non-development volunteer project and Communication degree; it did not add missing technical skills. Rationale separated elapsed work duration from role mismatch. All new cases showed the same 24-role list and Node.js 51% fit, 0% attainability, 100% barrier and generic covered-requirements statement.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. The saved final text is in `05_observed_output/`.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. Full per-call provider request/response logs and independent model attestation were not collected. The database copies in 05_observed_output are saved system output, not browser downloads. Parsed profiles remained user_confirmed=false; confirmation was not exercised. Some upload/parsing evidence appears in the preceding case's combined-stage capture; cross-case copies are listed below.

## File index

- [01_input/05_Nora_Lee.pdf](01_input/05_Nora_Lee.pdf) - test input
- [01_input/05_Nora_Lee.txt](01_input/05_Nora_Lee.txt) - test input
- [02_screenshots/T05_job_detail.png](02_screenshots/T05_job_detail.png) - screenshot
- [02_screenshots/T05_matches.png](02_screenshots/T05_matches.png) - screenshot
- [02_screenshots/T05_output_T06_uploaded.png](02_screenshots/T05_output_T06_uploaded.png) - screenshot
- [02_screenshots/T05_parse_status.png](02_screenshots/T05_parse_status.png) - screenshot
- [02_screenshots/T05_parsed.png](02_screenshots/T05_parsed.png) - screenshot
- [02_screenshots/T05_rationale.png](02_screenshots/T05_rationale.png) - screenshot
- [02_screenshots/T05_tailoring_started.png](02_screenshots/T05_tailoring_started.png) - screenshot
- [03_ui_observations/T05_job_detail.txt](03_ui_observations/T05_job_detail.txt) - records / observed text
- [03_ui_observations/T05_matches.txt](03_ui_observations/T05_matches.txt) - records / observed text
- [03_ui_observations/T05_output_T06_uploaded.txt](03_ui_observations/T05_output_T06_uploaded.txt) - records / observed text
- [03_ui_observations/T05_parse_status.txt](03_ui_observations/T05_parse_status.txt) - records / observed text
- [03_ui_observations/T05_parsed.txt](03_ui_observations/T05_parsed.txt) - records / observed text
- [03_ui_observations/T05_rationale.txt](03_ui_observations/T05_rationale.txt) - records / observed text
- [03_ui_observations/T05_tailoring_started.txt](03_ui_observations/T05_tailoring_started.txt) - records / observed text
- [04_records/T05_database_snapshot.json](04_records/T05_database_snapshot.json) - records / observed text
- [04_records/case_database_extract.json](04_records/case_database_extract.json) - records / observed text
- [04_records/task_timing_extract.json](04_records/task_timing_extract.json) - records / observed text
- [06_cross_case_context/T04_output_T05_uploaded.png](06_cross_case_context/T04_output_T05_uploaded.png) - screenshot
- [06_cross_case_context/T04_output_T05_uploaded.txt](06_cross_case_context/T04_output_T05_uploaded.txt) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
