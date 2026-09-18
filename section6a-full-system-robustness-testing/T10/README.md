# T10 - Contradictory / unusual CV (Sam Rivera)

## Scenario and observed finding

Parser noted the unverified five-year claim and incomplete degree, retaining reversed and overlapping dates in evidence. Tailoring kept the incomplete degree and original dates; rationale explicitly said overlapping/inverted dates were retained without correction. However its summary invented the broader scope "full-stack personal projects" although the source describes only one backend API exercise, with no front-end work. Grounding therefore fails for scope despite correct date/degree handling. The deterministic check also removed supported Express.js because source used Express; stored claims attached an unrelated project title as AWS evidence (internal provenance defect, not a final AWS claim). An impossible job search produced the wrong upload/confirm prompt; clearing it restored 24 jobs. All new cases showed the same 24-role list and Node.js 51% fit, 0% attainability, 100% barrier and generic covered-requirements statement.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. The saved final text is in `05_observed_output/`.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. Full per-call provider request/response logs and independent model attestation were not collected. The database copies in 05_observed_output are saved system output, not browser downloads. Parsed profiles remained user_confirmed=false; confirmation was not exercised.

## File index

- [01_input/10_Sam_Rivera.pdf](01_input/10_Sam_Rivera.pdf) - test input
- [01_input/10_Sam_Rivera.txt](01_input/10_Sam_Rivera.txt) - test input
- [02_screenshots/T10_empty_search.png](02_screenshots/T10_empty_search.png) - screenshot
- [02_screenshots/T10_job_detail.png](02_screenshots/T10_job_detail.png) - screenshot
- [02_screenshots/T10_job_viewport.png](02_screenshots/T10_job_viewport.png) - screenshot
- [02_screenshots/T10_matches.png](02_screenshots/T10_matches.png) - screenshot
- [02_screenshots/T10_output.png](02_screenshots/T10_output.png) - screenshot
- [02_screenshots/T10_output_viewport.png](02_screenshots/T10_output_viewport.png) - screenshot
- [02_screenshots/T10_parse_started.png](02_screenshots/T10_parse_started.png) - screenshot
- [02_screenshots/T10_parsed.png](02_screenshots/T10_parsed.png) - screenshot
- [02_screenshots/T10_rationale.png](02_screenshots/T10_rationale.png) - screenshot
- [02_screenshots/T10_search_recovered.png](02_screenshots/T10_search_recovered.png) - screenshot
- [02_screenshots/T10_tailoring_started.png](02_screenshots/T10_tailoring_started.png) - screenshot
- [02_screenshots/T10_uploaded.png](02_screenshots/T10_uploaded.png) - screenshot
- [03_ui_observations/T10_empty_search.txt](03_ui_observations/T10_empty_search.txt) - records / observed text
- [03_ui_observations/T10_job_detail.txt](03_ui_observations/T10_job_detail.txt) - records / observed text
- [03_ui_observations/T10_matches.txt](03_ui_observations/T10_matches.txt) - records / observed text
- [03_ui_observations/T10_output.txt](03_ui_observations/T10_output.txt) - records / observed text
- [03_ui_observations/T10_parse_started.txt](03_ui_observations/T10_parse_started.txt) - records / observed text
- [03_ui_observations/T10_parsed.txt](03_ui_observations/T10_parsed.txt) - records / observed text
- [03_ui_observations/T10_rationale.txt](03_ui_observations/T10_rationale.txt) - records / observed text
- [03_ui_observations/T10_search_recovered.txt](03_ui_observations/T10_search_recovered.txt) - records / observed text
- [03_ui_observations/T10_tailoring_started.txt](03_ui_observations/T10_tailoring_started.txt) - records / observed text
- [03_ui_observations/T10_uploaded.txt](03_ui_observations/T10_uploaded.txt) - records / observed text
- [04_records/T10_database_snapshot.json](04_records/T10_database_snapshot.json) - records / observed text
- [04_records/case_database_extract.json](04_records/case_database_extract.json) - records / observed text
- [04_records/task_timing_extract.json](04_records/task_timing_extract.json) - records / observed text
- [05_observed_output/10_system_output.txt](05_observed_output/10_system_output.txt) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
