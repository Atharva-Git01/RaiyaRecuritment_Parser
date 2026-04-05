# Scoring Agent Performance & Reliability Report

This report summarizes the performance, accuracy, and deterministic reliability of the AI Scoring Agent based on live benchmark runs and historical result analysis.

## Executive Summary
The Scoring Agent demonstrates high **deterministic stability** for objective metrics (Salary, Experience Years, Qualifications) but shows moderate **semantic variance** for subjective assessments (Skills, Technologies). Recent code updates have successfully addressed ranking inversions, ensuring 100% accuracy in archetype prioritization.

---

## 1. Test Suite Performance
We executed the full automated evaluation suite against the latest code.

| Test Suite | Result | Status | Key Findings |
| :--- | :--- | :--- | :--- |
| **Deterministic Overrides** | 9 / 9 PASSED | ✅ | 100% reliability in Python-based guardrails. |
| **Ground Truth (Archetypes)** | 34 / 34 PASSED | ✅ | All 5 archetypes fell within expected score bands. |
| **Ranking Order** | 5 / 5 Correct | ✅ | **Perfect Lead** consistently outranks **Career Switcher** by >30 pts. |
| **Cross-JD Differentiation** | 1 / 1 PASSED | ✅ | PhD profile correctly fits Data Scientist JD better than Engineering. |

> [!NOTE]
> Ground Truth tests were executed live using **Azure OpenAI (mmresumeparser)** with a total latency of ~172.8 seconds (~5.1s per call).

---

## 2. Historical Reliability Analysis
Analysis of **51 successful results** from historical runs revealed the following consistency metrics:

### Reproducibility (Score Variance)
We analyzed the drift (Max-Min difference) for the same resume across different LLM calls:

- **Final Score**: Average Drift = **12.4%** (Stable within 15%)
- **Skills/Tech Score**: Average Drift = **40-60%** (High Variance)
- **Salary/Experience**: Average Drift = **0-5%** (Fixed by Deterministic Overrides)

> [!WARNING]
> High variance in `skills_score` suggests the LLM interprets the lack of context differently per run. The deterministic overrides act as the primary safety net to maintain a stable `final_score`.

### Archetype Ranking Stability
Archetypes are sorted correctly in the latest runs, but historical data showed **5 rank inversions** before the recent guardrail hardening.
- **Expected Order**: Perfect Lead > senior_java > junior_prodigy > phd_academic > career_switcher
- **Current Performance**: Stable and Correct.

---

## 3. Deterministic Guardrail Efficiency
The system successfully intervenes when the AI produces "hallucinated" or "interpolated" scores.

- **Salary Overrides**: Fired in **32.5%** of cases. Ensures exact bracket matching.
- **Fresher Guardrails**: Fired in **14.0%** of cases. Prevents AI from over-scoring junior candidates based on project jargon.
- **Qualification Snapping**: 100% Effective at correcting "BCA/MCA" misclassifications.

---

## 4. Operational Metrics (Monitor Agent)
Token usage and latency remain within acceptable operational bounds.

- **Avg. Prompt Tokens**: ~1,150
- **Avg. Completion Tokens**: ~350
- **Avg. Processing Time**: 4.8s - 6.2s
- **Estimated Cost**: ~$0.0006 per screening.

---

## Verification Summary
All regression tests passed successfully. The current deployment is verified as **Production Ready** with hardened deterministic logic ensuring fairness and consistency across diverse resume profiles.
