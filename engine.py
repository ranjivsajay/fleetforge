"""Deterministic grid fleet simulator. Coordinates are (x, y)."""
import heapq
import random
import json
from pathlib import Path
from collections import deque

WIDTH, HEIGHT = 24, 16
SHELVES = {(x, y) for x in (5, 6, 10, 11, 15, 16) for y in range(3, 13) if y != 8}
PICKUPS = [(4, 4), (9, 6), (14, 10), (17, 5), (4, 11), (12, 12)]
DROPS = [(22, 3), (22, 7), (22, 12)]

def distance(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

class Simulation:
    def __init__(self, seed=42, fleet=6, policy='nearest'):
        self.seed, self.policy = seed, policy
        self.rng = random.Random(seed)
        self.dispatch_rng = random.Random(seed + 9000)
        self.model = None
        if policy == 'learned':
            self.model = json.loads((Path(__file__).parent / 'model.json').read_text())
        self.tick = 0
        self.blocks = set()
        self.robots = [dict(id=i, pos=(1, i+1), job=None, phase='idle', moves=0, waits=0, online=True) for i in range(max(1, min(10, fleet)))]
        self.jobs, self.completed, self.events = [], [], deque(maxlen=16)
        self.next_id = 1
        self.add_orders(10)

    def event(self, message):
        self.events.appendleft(dict(tick=self.tick, message=message))

    def add_orders(self, count=1):
        for _ in range(max(1, min(50, count))):
            self.jobs.append(dict(id=self.next_id, pickup=self.rng.choice(PICKUPS), drop=self.rng.choice(DROPS), created=self.tick, assigned=None))
            self.next_id += 1

    def neighbors(self, pos):
        x,y = pos
        for p in ((x+1,y), (x-1,y), (x,y+1), (x,y-1)):
            if 0 <= p[0] < WIDTH and 0 <= p[1] < HEIGHT and p not in SHELVES and p not in self.blocks:
                yield p

    def route_distance(self, start, goal):
        queue = deque([(start, 0)])
        seen = {start}
        while queue:
            p,d = queue.popleft()
            if p == goal: return d
            for n in self.neighbors(p):
                if n not in seen:
                    seen.add(n); queue.append((n,d+1))
        return 10000

    def assign(self):
        available = [r for r in self.robots if r['online'] and r['job'] is None]
        for job in self.jobs:
            if job['assigned'] is not None or not available: continue
            if self.policy == 'fifo':
                r = available[0]
            elif self.policy == 'random':
                r = self.dispatch_rng.choice(available)
            elif self.policy == 'learned':
                r = min(available, key=lambda r: (sum(w*x for w,x in zip(self.model['weights'], self.features(r,job))), r['id']))
            else:
                r = min(available, key=lambda r: (self.route_distance(r['pos'],job['pickup']), r['id']))
            available.remove(r)
            r['job'], r['phase'] = job, 'pickup'
            job['assigned'] = r['id']
            job['features'] = self.features(r,job)
            job['started'] = self.tick
            r['prediction'] = round(sum(w*x for w,x in zip(self.model['weights'],job['features'])),1) if self.model else None

    def features(self, robot, job):
        """Only information available at dispatch time; scale inputs for ridge fitting."""
        nearby = sum(distance(r['pos'],job['pickup']) <= 4 for r in self.robots if r['id'] != robot['id'])
        return [1, min(100,self.route_distance(robot['pos'],job['pickup']))/40,
                min(100,self.route_distance(job['pickup'],job['drop']))/40,
                nearby/10, sum(r['job'] is not None for r in self.robots)/10, len(self.jobs)/50]

    def step(self):
        self.assign()
        # Reserve every starting cell: unplanned/disabled robots are stationary obstacles.
        horizon = 32
        occupied = {(r['pos'], t) for r in self.robots for t in range(1,horizon+1)}
        edges = set()
        proposals = {}
        ordered = self.robots[self.tick % len(self.robots):] + self.robots[:self.tick % len(self.robots)]
        for r in ordered:
            start = r['pos']
            if not r['online'] or r['job'] is None:
                r['path'] = []
                proposals[r['id']] = start; continue
            for t in range(1,horizon+1): occupied.discard((start,t))
            goal = r['job'][r['phase'] if r['phase']=='pickup' else 'drop']
            initial = (start,0)
            queue = [(distance(start,goal),0,start)]
            costs, parent = {initial:0}, {}
            best, score = initial, (distance(start,goal),0)
            found = None
            while queue:
                _,g,p = heapq.heappop(queue)
                if (distance(p,goal),g) < score:
                    best, score = (p,g), (distance(p,goal),g)
                if p == goal:
                    found = (p,g); break
                if g >= horizon: continue
                for n in [*self.neighbors(p),p]:
                    state = (n,g+1)
                    if (n,g+1) in occupied or (n,p,g+1) in edges or state in costs: continue
                    costs[state] = g+1; parent[state] = (p,g)
                    heapq.heappush(queue,(g+1+distance(n,goal),g+1,n))
            end = found or best
            path = []
            while end != initial:
                path.append(end[0]); end = parent[end]
            path.reverse()
            if not path: path = [start]
            r['path'] = [start] + path
            previous = start
            for t in range(1,horizon+1):
                p = path[min(t-1,len(path)-1)]
                occupied.add((p,t)); edges.add((previous,p,t)); previous=p
            proposals[r['id']] = path[0]
        old = {r['id']:r['pos'] for r in self.robots}
        assert len(set(proposals.values())) == len(self.robots), 'Vertex collision'
        for a in self.robots:
            for b in self.robots:
                if a['id'] < b['id']:
                    assert not (proposals[a['id']]==old[b['id']] and proposals[b['id']]==old[a['id']]), 'Edge collision'
        self.tick += 1
        for r in self.robots:
            p = proposals[r['id']]
            if r['online'] and r['job']:
                r['moves' if p != r['pos'] else 'waits'] += 1
            r['pos'] = p
            if not r['online'] or r['job'] is None: continue
            job = r['job']
            if r['phase']=='pickup' and p==job['pickup']:
                r['phase']='deliver'
            elif r['phase']=='deliver' and p==job['drop']:
                self.completed.append(dict(id=job['id'], latency=self.tick-job['created'],
                                           service_ticks=self.tick-job['started'], features=job['features']))
                self.jobs.remove(job); r['job']=None; r['phase']='idle'
                self.event(f"Robot {r['id']+1} delivered order #{job['id']}")

    def block(self, x, y):
        p=(x,y)
        if not (0<=x<WIDTH and 0<=y<HEIGHT) or p in SHELVES or p in PICKUPS or p in DROPS or any(r['pos']==p for r in self.robots):
            return False
        if p in self.blocks: self.blocks.remove(p)
        else: self.blocks.add(p)
        self.event(f'Aisle changed at {x}, {y}')
        return True

    def toggle(self, robot_id):
        r=self.robots[robot_id]
        r['online']=not r['online']
        if not r['online'] and r['job']:
            r['job']['assigned']=None; r['job']=None; r['phase']='idle'
        self.event(f"Robot {robot_id+1} {'recovered' if r['online'] else 'offline; job released'}")

    def state(self):
        moves=sum(r['moves'] for r in self.robots)
        waits=sum(r['waits'] for r in self.robots)
        return dict(seed=self.seed, policy=self.policy, tick=self.tick, width=WIDTH, height=HEIGHT,
                    shelves=sorted(SHELVES), pickups=PICKUPS, drops=DROPS, blocks=sorted(self.blocks),
                    robots=self.robots, jobs=self.jobs, events=list(self.events),
                    metrics=dict(completed=len(self.completed), pending=len(self.jobs), moves=moves, waits=waits,
                                 mean_latency=round(sum(j['latency'] for j in self.completed)/len(self.completed),1) if self.completed else 0,
                                 throughput=round(100*len(self.completed)/self.tick,2) if self.tick else 0))

def benchmark(seed=42, fleet=6, ticks=400):
    results=[]
    for policy in ('fifo','nearest','learned'):
        sim=Simulation(seed,fleet,policy)
        for t in range(ticks):
            if t and t%30==0: sim.add_orders(3)
            sim.step()
        results.append(dict(policy=policy,**sim.state()['metrics']))
    return dict(seed=seed,fleet=fleet,ticks=ticks,results=results)
