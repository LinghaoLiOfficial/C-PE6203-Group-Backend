# T05 - Missing technical information (Nora Lee)

Extracted from the existing QA report; this is a report excerpt, not a new execution. Original report-relative links below refer to the former layout; use README.md in this folder for the package file paths.

- Severity: High shared matching/coverage defect; Medium misleading Cached date. Additional observations described below.
- Area: parsing robustness, grounding, active-resume propagation, recommendations, score/explanation consistency, tailoring completion and rationale.
- Environment: new-case snapshot above; actual task timestamps below.
- Input: [PDF](inputs/05_Nora_Lee.pdf) and [source TXT](inputs/05_Nora_Lee.txt); SHA-256 `8752ddf88f92f0f846196247dbe13fbaec4f77ce1aac4c0a0c807ee00ac1e310`.
- Steps: Upload the designated PDF → verify new Active file and old Inactive state → click Parse → wait for completed state and inspect fields → Browse jobs → inspect recommendations → open Node js developer / HyperNova Consulting → inspect score, vector and canonical requirements → Plan tailored resume → inspect terminal output and Modification rationale. Save screenshot/visible text and read-only task records. No real application submitted.
- Expected: Keep missing technical skills unknown; do not invent frameworks, certifications or software delivery. Matching must be grounded and internally consistent; completion must not imply correctness without inspecting output.
- Actual: Parser explicitly said no programming, database, cloud or framework proficiency was indicated. Final output retained the administrative role, non-development volunteer project and Communication degree; it did not add missing technical skills. Rationale separated elapsed work duration from role mismatch. All new cases showed the same 24-role list and Node.js 51% fit, 0% attainability, 100% barrier and generic covered-requirements statement.
- Evidence: [T05_job_detail](evidence/T05_job_detail.txt), [T05_matches](evidence/T05_matches.txt), [T05_output_T06_uploaded](evidence/T05_output_T06_uploaded.txt), [T05_parse_status](evidence/T05_parse_status.txt), [T05_parsed](evidence/T05_parsed.txt), [T05_rationale](evidence/T05_rationale.txt), [T05_tailoring_started](evidence/T05_tailoring_started.txt); corresponding PNGs share each basename. Read-only source/task/variant evidence: [database snapshot](evidence/database_latest.json).
- Resume ID: `3ed06126-660d-4856-b1da-377b5ef51c1c`. Parse task: `006ab611-2224-4509-9d6d-d78c5318e5fd` (completed), 2026-09-16 18:39:09.206941+08:00 to 2026-09-16 18:39:46.910304+08:00. Tailoring task: `e40360d7-9e4c-4c2d-9c95-1ec2632c34df` (completed), 2026-09-16 18:40:34.270779+08:00 to 2026-09-16 18:41:44.471477+08:00.
- Reproducible: matching contradiction observed across seven distinct inputs; page reload repeated for T07/T08. Per-case LLM generation run once, not an independent same-input repeat. No post-fix regression performed.

