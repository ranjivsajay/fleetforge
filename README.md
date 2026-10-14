# FleetForge

A reproducible warehouse fleet coordination simulator with a live browser dashboard. Built with Python's standard library and vanilla JavaScript; no hardware, GPU, paid API, or dependency installation required.

## Run

Requires Python 3.10 or newer. From this directory:

```sh
python server.py
```

Open http://localhost:8765. On Windows you can also double-click `start.bat`. The server listens only on your own computer. This is a development server, not an internet-facing service.

## Try a demo

1. Start the fleet and watch orders move from gold pickup cells to teal delivery cells.
2. Click an empty aisle to introduce a blockage. Click again to reopen it.
3. Click a robot in Fleet Status to disable it. Its order returns to the queue; its body remains an obstacle. Click again to recover it.
4. Add orders to create congestion.
5. Pause and run the controlled dispatch benchmark.
6. Export a JSON run containing up to 5,000 observed frames for offline analysis. This version exports traces but does not provide an interactive replay viewer. Dashed lines show currently planned routes; hover over a learned-policy robot to see its dispatch-time prediction.

## Architecture

`engine.py` owns simulation state, seeded order generation, dispatch, planning, and metrics. `server.py` provides a local HTTP API and static files. `static/app.js` renders engine state and sends commands; it does not fake robot movement.

Each tick:

1. Assign queued jobs to available robots. FIFO chooses the first available robot; nearest chooses the shortest reachable pickup distance using BFS; learned dispatch uses fitted regression to rank predicted service cost.
2. Reserve unplanned robots as stationary obstacles across a 32-tick horizon.
3. Run A* on `(position, time)` for each active robot. Movement and waiting each cost one tick. The Manhattan heuristic is admissible for this grid. Reject occupied destination cells and reverse edges to prevent head-on swaps.
4. Reserve the planned route, including its final position. Rotate planning priority each tick.
5. Execute only the first action of each plan simultaneously; validate vertex and edge safety, update pickups and deliveries, then replan next tick.

Reservations deliberately treat not-yet-planned robots conservatively. This protects safety but can reduce throughput. If no goal-reaching path fits the horizon, the planner selects its closest explored state. Prioritized bounded planning is incomplete: it can stall and does not guarantee deadlock freedom or eventual delivery.

## Experiments

```sh
python -m unittest discover -s tests -v
python benchmark.py --seed 42 --fleet 6 --ticks 400
```

All three strategies receive the same initial orders and three new orders every 30 ticks. They share the same planner. The experiment isolates dispatch strategy, not pathfinding quality. Report multiple seeds and fleet sizes before claiming a general improvement.

Metrics: completed deliveries; outstanding queued and assigned orders; active movement/wait ticks; mean end-to-end latency of completed orders only; deliveries per 100 ticks. Mean latency excludes unfinished orders, so also report pending backlog to avoid misleading comparisons. A tick is a logical unit, not a real second.

`benchmark-results.json` contains an actual local run. It is not an estimated performance claim.

## HTTP API

- `GET /api/state`
- `POST /api/reset` — `{ "seed": 42, "fleet": 6, "policy": "nearest" }`
- `POST /api/step` — `{ "steps": 1 }`
- `POST /api/orders` — `{ "count": 3 }`
- `POST /api/block` — `{ "x": 8, "y": 8 }`
- `POST /api/robot` — `{ "id": 0 }` (zero-based robot index)
- `POST /api/benchmark` — `{ "seed": 42, "fleet": 6 }`

The server serializes state mutations with a lock. Benchmarks use independent state. Live traffic from multiple tabs controls the same simulation.

## Scope and future work

This is discrete software simulation, not a ROS deployment or a physical robot digital twin. It has no sensor noise, inertia, battery model, or hardware validation. It includes a trained supervised dispatch model; see `MODEL_CARD.md` for its provenance and limitations. The UI optionally fetches Google Fonts; local fallback fonts work without internet.

Useful extensions: interactive trace replay, fairer task assignment, deadlock detection, collision-based search comparisons, automated multi-seed evaluation, and a ROS/Gazebo adapter. The learned dispatcher has heuristic baselines and held-out seed evaluation. Future ML work should address censored labels and test new warehouse layouts.

## Portfolio use

Describe this honestly as a simulation and acknowledge AI assistance. Before listing it on your resume, run it yourself and be able to explain time-expanded planning, reservations, dispatch baselines, incomplete planning, and evaluation limitations. Do not claim hardware deployment or reinforcement learning. The included regression training is documented in `MODEL_CARD.md`.

Suggested factual description: “Developed an AI-assisted warehouse fleet simulator with space-time A* planning, collision reservations, robot failure recovery, and reproducible dispatch benchmarks.” Adjust wording to reflect your own contributions.

## GitHub

This directory is ready to become a repository. Create an empty repository on GitHub, then run:

```sh
git init
git add .
git commit -m "Build FleetForge warehouse simulation"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fleetforge.git
git push -u origin main
```

Use GitHub authentication when prompted. Never put access tokens in source files.

## Trained dispatcher

Choose **Learned delivery-cost model**, then reset the experiment. Click **Load evaluation** to inspect six held-out runs per policy. Run `python train.py` to regenerate `model.json` and `evaluation.json`. Training and evaluation require no GPU or dependencies. The model is supervised ridge regression, not RL. Read `MODEL_CARD.md` before making performance claims.
