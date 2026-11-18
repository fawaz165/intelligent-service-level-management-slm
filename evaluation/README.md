# ISLM evaluation harness

The experimental harness calls existing ISLM SLA evaluation and enrichment functions against existing SQLite ticket and incident rows. It does not seed, insert, update, or delete records. All new run artifacts are written under `evaluation/runs/` with timestamped names so existing evaluation files are preserved.

From the repository root, run:

```powershell
python evaluation/run_experiment.py --repetitions 2 --case-limit 12
python evaluation/check_fallback.py
```

The first command repeats each of 12 fixed cases and writes raw per-call CSV plus a Markdown summary. Use `--repetitions N` and `--case-limit N` to adjust the run; model inference can take around a minute per call on CPU. The second command deliberately points the service at unreachable local port 1, invokes the normal enrichment path, restores the configured URL in a `finally` block, and records the fallback response to a separate CSV. It tests connection refusal only.

The CSV includes raw parsed responses, latency, whole-host CPU and memory samples, six-section completeness, SQLite-derived versus returned SLA metric objects, and an automatic runbook relevance proxy. Review the report limitations before interpreting those automated scores as semantic quality.
