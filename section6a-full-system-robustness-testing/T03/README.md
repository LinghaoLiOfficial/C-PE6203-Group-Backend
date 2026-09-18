# T03 - Priya - complex multi-page research CV

## Scenario and observed finding

Parsing completed in 213.1 s using FALLBACK after token truncation; 0 projects, 10 education fragments and section contamination. Historical observation stopped at 55% after at least 9m22s with no terminal result. On 2026-09-16, the existing task card displayed Failed: Structured tailored resume generation failed after two attempts. No retry submitted; terminal finish time not independently recovered here.

## Trace the execution

1. Start with `01_input/` (original collected resume and source text).
2. Review `02_screenshots/` and `03_ui_observations/` for upload, parsing, recommendations, job details and tailoring. Filenames preserve the original stage labels, not a newly reconstructed sequence.
3. Use `04_records/` to resolve task IDs and timestamps. JSON extracts are labelled and derived only from collected records.
4. Read `OBSERVED_RESULTS.md` for expected versus actual behavior. Available output is embedded in the original UI captures; no output has been recreated.
5. Mixed-stage captures, where available, are under `06_cross_case_context/`; they can show more than one candidate. Match task/resume IDs before attributing output.

## Missing evidence and limitations

Not collected: independent repeated same-input LLM runs, post-fix regression results, and verified browser-downloaded tailored PDF/DOCX files. Screenshots and saved output text are not download-verification evidence. No historical full database/variant export or standalone system-output file was collected; available output/rationale is in UI captures. No successful tailored output/rationale exists in the collected evidence. Historical timing records show running with null finish time; the later UI capture shows Failed. Exact terminal failure timestamp and complete backend diagnostic logs were not collected. No retry was performed.

## File index

- [01_input/03_Priya_Rao_ML_Research-source.txt](01_input/03_Priya_Rao_ML_Research-source.txt) - test input
- [01_input/03_Priya_Rao_ML_Research.pdf](01_input/03_Priya_Rao_ML_Research.pdf) - test input
- [02_screenshots/P01-upload-error.png](02_screenshots/P01-upload-error.png) - screenshot
- [02_screenshots/P02-upload-success.png](02_screenshots/P02-upload-success.png) - screenshot
- [02_screenshots/P03-long-running.png](02_screenshots/P03-long-running.png) - screenshot
- [02_screenshots/P04-fallback-result.png](02_screenshots/P04-fallback-result.png) - screenshot
- [02_screenshots/P05-matches.png](02_screenshots/P05-matches.png) - screenshot
- [02_screenshots/P06-job-detail.png](02_screenshots/P06-job-detail.png) - screenshot
- [02_screenshots/P06-job-viewport.png](02_screenshots/P06-job-viewport.png) - screenshot
- [02_screenshots/P07-rewrite-start.png](02_screenshots/P07-rewrite-start.png) - screenshot
- [02_screenshots/P08-generation-wait-viewport.png](02_screenshots/P08-generation-wait-viewport.png) - screenshot
- [02_screenshots/baseline_priya_terminal_failed.png](02_screenshots/baseline_priya_terminal_failed.png) - screenshot
- [03_ui_observations/P01-upload-error.txt](03_ui_observations/P01-upload-error.txt) - records / observed text
- [03_ui_observations/P02-upload-success.txt](03_ui_observations/P02-upload-success.txt) - records / observed text
- [03_ui_observations/P03-long-running.txt](03_ui_observations/P03-long-running.txt) - records / observed text
- [03_ui_observations/P04-fallback-result.txt](03_ui_observations/P04-fallback-result.txt) - records / observed text
- [03_ui_observations/P05-matches.txt](03_ui_observations/P05-matches.txt) - records / observed text
- [03_ui_observations/P06-job-detail.txt](03_ui_observations/P06-job-detail.txt) - records / observed text
- [03_ui_observations/P07-rewrite-start.txt](03_ui_observations/P07-rewrite-start.txt) - records / observed text
- [03_ui_observations/baseline_priya_terminal_failed.txt](03_ui_observations/baseline_priya_terminal_failed.txt) - records / observed text
- [04_records/capture_timestamps.json](04_records/capture_timestamps.json) - records / observed text
- [04_records/parse-task-timings.json](04_records/parse-task-timings.json) - records / observed text
- [04_records/rewrite-task-timings.json](04_records/rewrite-task-timings.json) - records / observed text
- [OBSERVED_RESULTS.md](OBSERVED_RESULTS.md) - records / observed text
