import argparse
import json
from engine import benchmark

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=42);p.add_argument('--fleet',type=int,default=6);p.add_argument('--ticks',type=int,default=400)
    a=p.parse_args();print(json.dumps(benchmark(a.seed,a.fleet,a.ticks),indent=2))
