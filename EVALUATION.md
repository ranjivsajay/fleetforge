# Held-out evaluation results

Training: 143 completed-job samples from six seeds. Evaluation: three unseen seeds, two fleet sizes, 220 ticks per run; six matched runs per policy.

| Policy | Mean deliveries | Mean backlog | Mean run latency |
|---|---:|---:|---:|
| fifo | 24.0 | 7.0 | 57.93 |
| nearest | 23.0 | 8.0 | 55.37 |
| learned | 23.0 | 8.0 | 55.37 |

The learned model matched nearest dispatch on these runs. FIFO completed more deliveries on average. No improvement claim is supported. Latency includes only finished orders. Training excludes 43 unfinished orders; see MODEL_CARD.md for censoring and generalization limits.

Reproduce with `python train.py`. Full per-run results: `evaluation.json`.
