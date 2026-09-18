# T03 - Priya - complex multi-page research CV

Extracted from the existing QA report; this is a report excerpt, not a new execution. Original report-relative links below refer to the former layout; use README.md in this folder for the package file paths.

- Severity: High (historical fallback parsing and generation failure).
- Area: upload, parsing, matching, tailoring and UI.
- Environment: historical frontend 5e27b87; backend da34149 with then-existing local fixes; historical report observed openrouter/qwen3.7-plus.
- Input: evidence/tests_01_03_historical/inputs/03_Priya_Rao_ML_Research.pdf.
- Steps: historical upload → parse → active resume → job list/details → tailoring → rationale/output as available. See unchanged original report for exact sequence.
- Expected: Preserve 2 degrees, 2 projects, publications and distinction between technical report and reviewed paper; finish or explain failure.
- Actual: Parsing completed in 213.1 s using FALLBACK after token truncation; 0 projects, 10 education fragments and section contamination. Historical observation stopped at 55% after at least 9m22s with no terminal result. On 2026-09-16, the existing task card displayed Failed: Structured tailored resume generation failed after two attempts. No retry submitted; terminal finish time not independently recovered here.
- Evidence: [original report](evidence/tests_01_03_historical/完整测试报告.md), [case evidence](evidence/tests_01_03_historical/P04-fallback-result.txt); tailoring task `096580a7-afea-4b84-800f-4b45187d00a9`.
- Reproducible: not rerun in this continuation; original observations and limitations retained.

