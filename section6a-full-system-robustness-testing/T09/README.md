# T09 - Overqualified / senior candidate (Diana Koh)

## Scenario and observed finding

Parser preserved 16 years and three roles. Tailoring retained Principal/Senior titles, dates, eight mentees and three migrated products; rationale said Exceeds (16 years) against the 2-8-year job range. The job page still showed generic 51%/0% attainability. Output said specializing in AWS although source only listed AWS as a skill: degree of expertise is an overstatement risk, not a newly invented technology. Target is mid-level, not explicitly junior. All new cases showed the same 24-role list and Node.js 51% fit, 0% attainability, 100% barrier and generic covered-requirements statement.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. The saved final text is in `05_observed_output/`.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. Full per-call provider request/response logs and independent model attestation were not collected. The database copies in 05_observed_output are saved system output, not browser downloads. Parsed profiles remained user_confirmed=false; confirmation was not exercised. Some upload/parsing evidence appears in the preceding case's combined-stage capture; cross-case copies are listed below. No separately named parse-start capture is available; parse task timestamps and parsed-state captures are retained.

## File index

- [01_input/09_Diana_Koh.pdf](01_input/09_Diana_Koh.pdf) - test input
- [01_input/09_Diana_Koh.txt](01_input/09_Diana_Koh.txt) - test input
- [02_screenshots/T09_job_detail.png](02_screenshots/T09_job_detail.png) - screenshot
- [02_screenshots/T09_matches.png](02_screenshots/T09_matches.png) - screenshot
- [02_screenshots/T09_output.png](02_screenshots/T09_output.png) - screenshot
- [02_screenshots/T09_parsed.png](02_screenshots/T09_parsed.png) - screenshot
- [02_screenshots/T09_rationale.png](02_screenshots/T09_rationale.png) - screenshot
- [02_screenshots/T09_tailoring_started.png](02_screenshots/T09_tailoring_started.png) - screenshot
- [02_screenshots/T09_uploaded.png](02_screenshots/T09_uploaded.png) - screenshot
- [03_ui_observations/T09_job_detail.txt](03_ui_observations/T09_job_detail.txt) - records / observed text
- [03_ui_observations/T09_matches.txt](03_ui_observations/T09_matches.txt) - records / observed text
- [03_ui_observations/T09_output.txt](03_ui_observations/T09_output.txt) - records / observed text
- [03_ui_observations/T09_parsed.txt](03_ui_observations/T09_parsed.txt) - records / observed text
- [03_ui_observations/T09_rationale.txt](03_ui_observations/T09_rationale.txt) - records / observed text
- [03_ui_observations/T09_tailoring_started.txt](03_ui_observations/T09_tailoring_started.txt) - records / observed text
- [03_ui_observations/T09_uploaded.txt](03_ui_observations/T09_uploaded.txt) - records / observed text
- [04_records/T09_database_snapshot.json](04_records/T09_database_snapshot.json) - records / observed text
- [04_records/case_database_extract.json](04_records/case_database_extract.json) - records / observed text
- [04_records/task_timing_extract.json](04_records/task_timing_extract.json) - records / observed text
- [05_observed_output/09_system_output.txt](05_observed_output/09_system_output.txt) - records / observed text
- [06_cross_case_context/T08_output_T09_parsed.png](06_cross_case_context/T08_output_T09_parsed.png) - screenshot
- [06_cross_case_context/T08_output_T09_parsed.txt](06_cross_case_context/T08_output_T09_parsed.txt) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
