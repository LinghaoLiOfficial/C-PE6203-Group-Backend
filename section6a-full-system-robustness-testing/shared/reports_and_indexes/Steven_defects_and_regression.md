# Steven - defects and targeted regression handoff

Observed 2026-09-16/17, Lucas full-system track. No code fixes applied; no message sent to Steven. Severity is a QA recommendation. Current frontend c90eaf9, backend 8fb1c1a, with pre-existing local changes. Exact commits, timestamps, IDs and raw evidence are in the QA report and database snapshot.

## FS-01 - High: missing requirement data breaks score/coverage consistency

**Observed:** all seven new candidates, from pastry baker to principal engineer, received the same 24-role ordering and Node.js 51% fit, 0% attainability, 100% barrier and 70% confidence. The page says “Core requirements appear covered by the current profile.” It simultaneously displays aws/javascript/react/rest requirements. T07 and T08 remain unchanged after reload. Tailoring correctly distinguishes technical coverage, so this is not proof that all AI personalization failed.

**Expected:** unavailable requirement data must be labelled unknown; scores and explanations must use the same normalized requirements and active candidate. A salary-weighted opportunity score must not be presented as demonstrated skill coverage.

**Evidence:** T04–T10 job_detail screenshots/text; T07/T08 before/after reload; database_latest.json: job 90c35b3c-01ac-45be-885e-a42b08bf69c4 has skill_tags=null and no job_market_profiles row.

**Diagnostic lead (source inspection, no patch):** job_portal_service.py `_score_job` uses stored market skills or job.skill_tags. `_get_job_requirement_summary` can extract requirements from description. `_compute_gap_notes` uses only job.skill_tags and treats no gaps as covered. For this observed data, skill overlap is zero and other vector terms dominate. `_compute_transfer_notes` also falls back to a generic sentence. Do not fix only browser caching.

**Regression:** use T07, T08 and T09 against this exact job; test both populated and absent requirement metadata. Require grounded differences or explicit unknowns, no false “covered” statement, and consistent results after reload and active-resume changes. Do not assert an arbitrary exact expected score.

## FS-02 - Medium: canonical job profile loses qualifications and seniority bounds

**Observed:** original JD says Computer Science graduates (B.Tech preferred), 2–8 years, Node.js/Express/REST and DB technologies. Canonical detail shows Education: None, Experience: 2+ years and an incomplete/misclassified requirement list, while tailoring rationale sees the degree and 2–8-year range. T09 therefore sees its overqualification only in tailoring rationale.

**Evidence:** all job_detail files; database job_description; T09_rationale.

**Regression:** retain essential versus desirable requirements, the degree requirement and both experience bounds. Check Node.js/Express/REST/DB requirements against original text rather than relying on the word “experience” or “degree” alone.

## FS-03 - Medium: fresh result displayed with stale Cached date

**Observed:** T04–T10 new completed tasks display Latest Cached 2026/9/8, although their creation/finish timestamps are 2026-09-16/17. Records show actual generation completed, so “Cached” is not evidence of no LLM call.

**Expected:** distinguish source creation, generation completion, version and cache-hit times. Preserve the correct resume/task provenance.

**Evidence:** output screenshots and task_timings.json.

**Regression:** generate for two different resumes against one job; ensure both saved versions remain identifiable and the current card displays the current generation timestamp.

## FS-04 - Medium: search-empty state incorrectly asks for a resume

**Observed:** with T10 parsed and active, search `zz_no_such_role_qa_10` shows “No ranked opportunities yet. Upload and confirm a resume first.” Clearing the search restores 24 roles without uploading or confirming anything.

**Evidence:** T10_empty_search and T10_search_recovered. This reproduces historical Maya's empty-search complaint on the current version.

**Regression:** distinguish no resume, unconfirmed profile, no recommendations and zero filtered matches; preserve the search and offer a clear-filter action.

## FS-05 - High: unsupported project scope survives final rewrite

**Observed:** T10 source contains one personal Stockroom API project using Node.js, Express and SQLite, with no frontend. Generated summary says “full-stack personal projects”. This adds full-stack scope and plural projects. Date/degree handling is otherwise careful: incomplete degree and inverted/overlapping dates were retained, and five-year tenure not asserted.

**Evidence:** inputs/10_Sam_Rivera.txt versus generated_outputs/10_system_output.txt, T10_output.png, T10_rationale.txt; task 2726450d-7dd2-45f8-8198-43d2fea8816e. Observed once; independent stochastic reproduction not run.

**Diagnostic lead:** `_enforce_fidelity` checks the discrete skills array; it does not validate every semantic claim in summaries and experience. Checking for source words alone cannot prove supported scope or proficiency.

**Regression:** repeat T10 and inspect every summary/experience claim. Allow “backend/API personal project”; reject unsupported full-stack scope, extra projects and fabricated dates. Also review T09 “specializing in AWS” because source lists AWS without establishing specialization.

## FS-06 - Medium: alias-sensitive fidelity check rejects supported Express

**Observed:** T10 validation_results removes Express.js as not in source, although the source project explicitly lists Express. Final skills omit it while project text and rationale retain Express/Express.js. This is a false positive in the deterministic check, separate from FS-05.

**Evidence:** database_latest.json → T10 variant validation_results (`removed_skills: ["Express.js"]`), source TXT, output skills/project.

**Regression:** supported Express ↔ Express.js aliases must survive; unrelated technologies must not. Verify skills list, summary and coverage remain consistent after filtering.

## FS-07 - Medium: unrelated source text attached as claim evidence

**Observed:** T10 stored claims include “Highlights aws for the target role” supported only by “Stockroom API | Personal project | 2024”. The candidate source has no AWS evidence. This is an internal provenance defect; final candidate output does not claim AWS.

**Diagnostic lead:** `_claim_evidence_for_skill` falls back to the first source span when no matching skill evidence exists. A non-empty span is not entailment.

**Regression:** unsupported candidate skills must have no supporting claim or be flagged as a gap. Job requirements must not become candidate evidence. Confirm evidence actually supports each claim.

## Historical issues requiring future retest

- Priya: fallback segmentation and long/truncated generation. Existing task now visibly Failed; no Retry submitted in this continuation. Test with corrected output budgets/chunking/fallback boundaries and bounded retry time.
- No fix/build was supplied during this run, so post-fix targeted regression is **pending**, not passed.
- LLM cases were generated once each. Matching defects were observed across seven inputs and reloads; generative defects need independent reruns after a fix.
