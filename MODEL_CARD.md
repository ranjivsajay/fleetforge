# Learned delivery-cost dispatcher

## Purpose

Predict how long a newly assigned order will take from dispatch to delivery. For each queued order, score all available robots and assign the lowest predicted cost. This is a small supervised model, not reinforcement learning or a robotics foundation model. Collision avoidance remains the same explicit planner for every strategy.

## Model and data

Ridge regression fitted with a pivoted linear-system solver implemented in Python. Inputs: intercept, BFS pickup distance, BFS delivery distance, robots near the pickup, busy robots, and outstanding orders. Inputs are scaled by fixed constants; regularization is 0.1 and excludes the intercept.

`train.py` collects completed deliveries from random dispatch on seeds 11–16, alternating four and eight robots. Random dispatch has its own RNG, separate from order generation, so dispatch choices do not change future order arrivals. Labels are observed service ticks, not synthetic distance formulas. `model.json` records fitted coefficients, feature order, sample count, and data provenance.

Only pickup distance and nearby-robot count vary across candidates for the same order. Other features help fit service-time context but cancel out when comparing candidates under this linear model. A nonlinear model or route-specific congestion features would allow richer interactions.

## Evaluation

Seeds 101, 202, and 303 are reserved for evaluation. Each uses four and eight robots for 220 ticks, with identical order streams for FIFO, nearest, and learned dispatch: 18 runs total. Training and evaluation use the same warehouse layout and arrival distribution. No hyperparameter selection uses evaluation results.

`evaluation.json` stores each run and aggregate results. Compare deliveries and backlog alongside completed-order latency. Prediction MAE is measured on completed jobs under each policy; policy-dependent data distributions mean these MAEs are not directly comparable accuracy rankings.

## Limitations

- Unfinished orders are excluded from regression labels. This censoring can favor easier jobs and understate delays.
- Random-policy training and learned-policy deployment differ in state distribution.
- Small dataset and one fixed layout; no claim of statistical significance, physical transfer, or general superiority.
- Linear regression can produce negative estimates outside its training distribution. These are ranking scores, not guaranteed durations.
- The bounded prioritized planner can stall; learning the dispatcher does not remove that limitation.
- No hardware, sensor, dynamics, or safety certification.

## Reproduce

`python train.py` retrains and overwrites the model and evaluation. Restart the server afterward so new learned simulations load the updated model. `python -m unittest discover -s tests -v` checks regression, split isolation, dispatch selection, and simulation behavior.

## Interview talking points

Explain why order RNG is separate from policy exploration; why test seeds remain unseen; why low completed-job latency alone can mislead; how reservations prevent collisions; and why a simple learned model may lose to a strong distance heuristic. Do not describe this model as RL.
