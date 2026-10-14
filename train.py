"""CPU-only supervised dispatch model and held-out policy evaluation.

Run `python train.py`. No third-party libraries. This is regression, not RL.
"""
import json
from pathlib import Path
from engine import Simulation

ROOT=Path(__file__).parent
FEATURES=['bias','pickup_distance / 40','delivery_distance / 40','robots_near_pickup / 10','busy_robots / 10','outstanding_orders / 50']
TRAIN_SEEDS=[11,12,13,14,15,16]
TEST_SEEDS=[101,202,303]

def fit(rows, alpha=0.1):
    # Solve (X^T X + alpha I)w = X^T y using pivoted elimination.
    n=len(FEATURES)
    matrix=[[sum(r['features'][i]*r['features'][j] for r in rows)+(alpha if i==j and i else 0) for j in range(n)] + [sum(r['features'][i]*r['service_ticks'] for r in rows)] for i in range(n)]
    for i in range(n):
        pivot=max(range(i,n),key=lambda k:abs(matrix[k][i]))
        matrix[i],matrix[pivot]=matrix[pivot],matrix[i]
        divisor=matrix[i][i]
        if abs(divisor)<1e-12: raise ValueError('Singular training matrix')
        matrix[i]=[v/divisor for v in matrix[i]]
        for k in range(n):
            if k==i:continue
            factor=matrix[k][i]
            matrix[k]=[a-factor*b for a,b in zip(matrix[k],matrix[i])]
    return [row[-1] for row in matrix]

def run(seed,fleet,policy,ticks=220):
    sim=Simulation(seed,fleet,policy)
    for t in range(ticks):
        if t and t%30==0:sim.add_orders(3)
        sim.step()
    return sim

def main():
    rows=[]; unfinished=0
    for i,seed in enumerate(TRAIN_SEEDS):
        sim=run(seed,4 if i%2==0 else 8,'random')
        rows.extend(sim.completed);unfinished+=len(sim.jobs)
        print(f'Training seed {seed}: {len(sim.completed)} completed examples',flush=True)
    weights=fit(rows)
    model=dict(kind='ridge regression',features=FEATURES,weights=weights,alpha=0.1,
               training_seeds=TRAIN_SEEDS,samples=len(rows),excluded_unfinished=unfinished,
               target='ticks from dispatch to delivery; completed jobs only')
    (ROOT/'model.json').write_text(json.dumps(model,indent=2))
    results=[]
    for seed in TEST_SEEDS:
        for fleet in (4,8):
            for policy in ('fifo','nearest','learned'):
                sim=run(seed,fleet,policy)
                error=sum(abs(sum(w*x for w,x in zip(weights,j['features']))-j['service_ticks']) for j in sim.completed)/max(1,len(sim.completed))
                results.append(dict(seed=seed,fleet=fleet,policy=policy,ticks=220,
                                    prediction_mae=round(error,2),**sim.state()['metrics']))
                print(f'Eval {seed}/{fleet}/{policy}: {len(sim.completed)} deliveries',flush=True)
    summary=[]
    for policy in ('fifo','nearest','learned'):
        subset=[r for r in results if r['policy']==policy]
        summary.append(dict(policy=policy,mean_completed=round(sum(r['completed'] for r in subset)/len(subset),2),
                            mean_pending=round(sum(r['pending'] for r in subset)/len(subset),2),
                            mean_run_latency=round(sum(r['mean_latency'] for r in subset)/len(subset),2),
                            mean_prediction_mae=round(sum(r['prediction_mae'] for r in subset)/len(subset),2)))
    report=dict(training=model,evaluation_seeds=TEST_SEEDS,results=results,summary=summary,
                limitations=['Completed-job targets exclude unfinished jobs and can bias estimates.',
                             'Only one layout; no claim of transfer to new warehouses.',
                             'Small sample; no significance claim. AI can underperform heuristics.',
                             'Mean run latency averages run means, not individual deliveries.'])
    (ROOT/'evaluation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
