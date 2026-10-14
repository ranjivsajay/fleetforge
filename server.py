"""Standard-library HTTP server; no install or API key required."""
import argparse
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Lock
from engine import Simulation, benchmark

ROOT=Path(__file__).parent / 'static'
sim=Simulation()
lock=Lock()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def reply(self,data,status=200):
        body=json.dumps(data).encode()
        self.send_response(status); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path=='/api/state':
            with lock: self.reply(sim.state())
        elif self.path=='/api/evaluation':
            path=Path(__file__).parent/'evaluation.json'
            self.reply(json.loads(path.read_text()) if path.exists() else {'error':'Run python train.py first'},200 if path.exists() else 404)
        else: super().do_GET()
    def do_POST(self):
        global sim
        try:
            size=int(self.headers.get('Content-Length',0))
            if size>10000: raise ValueError('Request too large')
            data=json.loads(self.rfile.read(size) or '{}')
            if self.path=='/api/benchmark':
                self.reply(benchmark(int(data.get('seed',42)),int(data.get('fleet',6)),400)); return
            with lock:
                if self.path=='/api/reset':
                    policy=data.get('policy','nearest')
                    if policy not in ('nearest','fifo','learned'): raise ValueError('Unknown policy')
                    sim=Simulation(int(data.get('seed',42)),int(data.get('fleet',6)),policy)
                elif self.path=='/api/step':
                    for _ in range(max(1,min(100,int(data.get('steps',1))))): sim.step()
                elif self.path=='/api/orders': sim.add_orders(int(data.get('count',3)))
                elif self.path=='/api/block': sim.block(int(data['x']),int(data['y']))
                elif self.path=='/api/robot':
                    i=int(data['id'])
                    if not 0<=i<len(sim.robots): raise ValueError('Invalid robot')
                    sim.toggle(i)
                else: self.reply({'error':'Not found'},404); return
                self.reply(sim.state())
        except (ValueError,KeyError,TypeError) as exc: self.reply({'error':str(exc)},400)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    print(f'FleetForge running at http://localhost:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
