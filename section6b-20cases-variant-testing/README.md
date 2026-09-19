# Stage 6 — A/B/C Variant Comparison (20 Test Cases)

Real, live evaluation — not hand-simulated. Every number in this folder comes from actually calling the deployed app's tailoring logic and the same LLM (`meta-llama/Llama-3.3-70B-Instruct`, via the Hugging Face router) the app uses in production, then scoring the outputs with an LLM judge, in two rounds.

## Method

4 candidate resumes, each tailored against the same fixed set of 5 real job postings already seeded in the app's database (Software Engineer, Machine Learning, DevOps Engineer, Database Administrator, Full Stack Developer) → **4 × 5 = 20 test cases**.

Each test case runs through three system variants:

- **A — Minimal LLM**: bare prompt, *"Rewrite this resume for this job."*
- **B — Simplified system**: *"Extract relevant skills and tailor this resume to the job."* — no schema, no anti-fabrication instruction.
- **C — Full system**: the actual deployed app logic (`JobPortalService._generate_tailored_resume`), structured JSON output, evidence required per claim, explicit anti-fabrication instruction, plus a deterministic post-generation fidelity check (`_enforce_fidelity`).

Scored on 4 criteria (Grounding/No Fabrication, Personalization/Relevance, Correctness & Completeness, Clarity & Change Evidence), 1–5 each, in two judge rounds:

- **Round 1 — naive judge**: no explicit fabrication penalty.
- **Round 2 — grounding-gated judge**: any fabricated skill/employer/metric caps that variant's scores, regardless of fluency. This is the corrected methodology and the one reported as the headline result.

**Why the same 5 jobs for every resume:** keeps the comparison controlled — any score difference is attributable to the resume/system variant, not to different jobs being tested. The Jobs page's per-resume recommendation feature couldn't be used for this instead because, at the time of testing, it didn't refresh when the active resume changed. That bug has since been fixed upstream, but the fixed job list is kept here on purpose for comparability.

**Mid-evaluation system fix:** partway through testing, the team shipped `_enforce_fidelity` to System C. Trixie Mok, Alex Chen, and John Doe were all retested against the fixed code (their pre-fix baselines are kept as `*_PREFIX.json` for before/after comparison); Alex Mercer was tested directly against the already-fixed code. **All numbers reported here are current, post-fix.**

## Resumes tested

| Resume | Scenario type | Background |
|---|---|---|
| `trixie_resume_test/` | Ambiguous query | Real resume (candidate's own); MSc Enterprise AI, partial genuine overlap with several jobs |
| `fresh_grad_resume_test/` | Missing information | Alex Chen — final-year BBA, no paid work experience |
| `graphic_design_resume_test/` | Low-relevance / misleading-context case | John Doe — BS Graphic Design, 100% retail/service work history since |
| `overqualified_resume_test/` | Normal | Alex Mercer — 10+ years real, deep front-end expertise, stepping back to an IC role |

## Headline result (Round 2, grounding-gated judge)

| Resume | A — Minimal | B — Simplified | C — Full system | Winner |
|---|---|---|---|---|
| Trixie Mok | 2.85 | 2.85 | **4.55** | C |
| Alex Chen | 2.85 | 3.50 | **4.50** | C |
| John Doe | 2.95 | 3.35 | **3.55** | C |
| Alex Mercer | 2.30 | 2.30 | **4.40** | C |
| **Average (all 20 cases)** | 2.74 | 3.00 | **4.25** | C |

C wins on every resume, by the widest margin on Alex Mercer's (4.40 vs. 2.30). A and B fabricate skills/experience on at least one job in every resume tested; C has zero fabrications in 3 of 4 resumes, and its one remaining flag (John Doe, Machine Learning job) is a judge-methodology false positive — the judge misread System C's own caught-and-removed-fabrication log as live output, not an actual fabrication in the delivered resume.

For the full narrative, per-job breakdowns, findings, and Stage 7 failure analysis, see `../final_report/ThreeVariantFindings.pdf` (or `.docx`) and `../final_report/Section6_Combined_Evaluation.pdf`.

## What's in each resume folder

Each `<resume>_resume_test/` folder is self-contained:

| File | What it is |
|---|---|
| `stage6_variant_comparison.ipynb` | **The canonical write-up.** Runnable notebook — loads the JSON below, computes and prints both rounds' tables live (not manually transcribed), walks through the fabrication examples, and (for the 3 retested resumes) the before/after comparison. Re-execute it and the numbers regenerate from the same source data — nothing here is hand-typed. |
| `variant_comparison_results.json` | Current (post-fix) Round 1 raw output: full text/JSON for A, B, C per job, plus naive judge scores. |
| `variant_comparison_results_grounded_judge.json` | Current (post-fix) Round 2 raw output: grounding-gated judge scores + fabricated items caught per variant. |
| `variant_comparison_results_PREFIX.json` / `variant_comparison_results_grounded_judge_PREFIX.json` | *(Trixie, Alex Chen, John Doe only)* Original pre-fix results, kept for the before/after retest comparison. |
| `run_variant_comparison.py` | Generates A/B/C outputs for the 5 jobs + scores them with the naive judge. Writes `variant_comparison_results.json`. |
| `rejudge_grounded.py` | Re-scores the same A/B/C outputs with the grounding-gated judge (no new generation calls). Writes `variant_comparison_results_grounded_judge.json`. |

## How to re-run any resume

Both scripts import the backend's app package and read its `.env` (for DB access and the LLM API key), so they must run with the backend's virtualenv, from inside the resume's own folder (each script writes its output next to itself):

```bash
cd stage6_evaluation/<resume>_resume_test
../../C-PE6203-Group-Backend/.venv/Scripts/python.exe run_variant_comparison.py
../../C-PE6203-Group-Backend/.venv/Scripts/python.exe rejudge_grounded.py
```

Requires: the backend's `.venv` already set up, PostgreSQL running with the job data seeded, a valid `LLM_API_KEY` in `C-PE6203-Group-Backend/.env`, and the target account's active resume set to the one you want to test (`run_variant_comparison.py` looks up the currently active resume for `trixgracemok@gmail.com` — swap the email in the script to test a different account).

To re-execute a notebook after regenerating its JSON, use `nbclient`/`nbformat` (installed in the backend's venv) rather than editing cell outputs by hand — this is how every notebook here was produced, and it's what keeps the numbers trustworthy.
