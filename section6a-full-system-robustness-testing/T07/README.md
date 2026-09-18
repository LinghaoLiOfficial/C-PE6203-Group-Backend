# T07 - Very weak cross-domain fit (Clara Wong)

## Scenario and observed finding

Pastry experience, 150 items per morning, two trainees and culinary qualification were preserved. Technical requirements were marked 0% in rationale. Nevertheless the job page claimed core requirements covered and showed the same 51% fit as technical candidates; full page reload did not change the recommendation list. All new cases showed the same 24-role list and Node.js 51% fit, 0% attainability, 100% barrier and generic covered-requirements statement.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. The saved final text is in `05_observed_output/`.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. Full per-call provider request/response logs and independent model attestation were not collected. The database copies in 05_observed_output are saved system output, not browser downloads. Parsed profiles remained user_confirmed=false; confirmation was not exercised. Some upload/parsing evidence appears in the preceding case's combined-stage capture; cross-case copies are listed below.

## File index

- [01_input/07_Clara_Wong.pdf](01_input/07_Clara_Wong.pdf) - test input
- [01_input/07_Clara_Wong.txt](01_input/07_Clara_Wong.txt) - test input
- [02_screenshots/T07_job_detail.png](02_screenshots/T07_job_detail.png) - screenshot
- [02_screenshots/T07_matches_after_reload.png](02_screenshots/T07_matches_after_reload.png) - screenshot
- [02_screenshots/T07_matches_before_reload.png](02_screenshots/T07_matches_before_reload.png) - screenshot
- [02_screenshots/T07_output.png](02_screenshots/T07_output.png) - screenshot
- [02_screenshots/T07_parse_started.png](02_screenshots/T07_parse_started.png) - screenshot
- [02_screenshots/T07_parsed.png](02_screenshots/T07_parsed.png) - screenshot
- [02_screenshots/T07_rationale.png](02_screenshots/T07_rationale.png) - screenshot
- [02_screenshots/T07_tailoring_started.png](02_screenshots/T07_tailoring_started.png) - screenshot
- [03_ui_observations/T07_job_detail.txt](03_ui_observations/T07_job_detail.txt) - records / observed text
- [03_ui_observations/T07_matches_after_reload.txt](03_ui_observations/T07_matches_after_reload.txt) - records / observed text
- [03_ui_observations/T07_matches_before_reload.txt](03_ui_observations/T07_matches_before_reload.txt) - records / observed text
- [03_ui_observations/T07_output.txt](03_ui_observations/T07_output.txt) - records / observed text
- [03_ui_observations/T07_parse_started.txt](03_ui_observations/T07_parse_started.txt) - records / observed text
- [03_ui_observations/T07_parsed.txt](03_ui_observations/T07_parsed.txt) - records / observed text
- [03_ui_observations/T07_rationale.txt](03_ui_observations/T07_rationale.txt) - records / observed text
- [03_ui_observations/T07_tailoring_started.txt](03_ui_observations/T07_tailoring_started.txt) - records / observed text
- [04_records/T07_database_snapshot.json](04_records/T07_database_snapshot.json) - records / observed text
- [04_records/case_database_extract.json](04_records/case_database_extract.json) - records / observed text
- [04_records/task_timing_extract.json](04_records/task_timing_extract.json) - records / observed text
- [05_observed_output/07_system_output.txt](05_observed_output/07_system_output.txt) - records / observed text
- [06_cross_case_context/T06_output_T07_uploaded.png](06_cross_case_context/T06_output_T07_uploaded.png) - screenshot
- [06_cross_case_context/T06_output_T07_uploaded.txt](06_cross_case_context/T06_output_T07_uploaded.txt) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
