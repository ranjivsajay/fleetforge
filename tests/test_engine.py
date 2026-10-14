import unittest
from engine import Simulation, benchmark, SHELVES

class EngineTests(unittest.TestCase):
    def test_delivers_and_is_deterministic(self):
        a,b=Simulation(42,6),Simulation(42,6)
        for _ in range(120): a.step(); b.step()
        self.assertEqual(a.state(),b.state())
        self.assertGreater(len(a.completed),0)

    def test_safety_under_disruptions(self):
        for seed in (1,42,77):
            s=Simulation(seed,10)
            for t in range(150):
                if t%25==0: s.add_orders(3)
                if t==20: s.block(8,8)
                if t==40: s.toggle(3)
                if t==80: s.toggle(3); s.block(8,8)
                old=[r['pos'] for r in s.robots]
                s.step()
                new=[r['pos'] for r in s.robots]
                self.assertEqual(len(new),len(set(new)))
                self.assertFalse(set(new)&(SHELVES|s.blocks))
                for i in range(len(new)):
                    for j in range(i+1,len(new)):
                        self.assertFalse(new[i]==old[j] and new[j]==old[i])

    def test_failure_releases_order(self):
        s=Simulation();s.step();r=s.robots[0];job=r['job']
        self.assertIsNotNone(job)
        s.toggle(0)
        self.assertIsNone(job['assigned']);self.assertIsNone(r['job'])
        p=r['pos'];s.step();self.assertEqual(p,r['pos'])

    def test_protected_cells(self):
        s=Simulation()
        self.assertFalse(s.block(*s.robots[0]['pos']))
        self.assertFalse(s.block(4,4))
        self.assertFalse(s.block(-1,8))

    def test_unreachable_robot_waits(self):
        s=Simulation(fleet=1);s.assign()
        s.blocks.update(s.neighbors(s.robots[0]['pos']))
        p=s.robots[0]['pos']
        for _ in range(5):s.step()
        self.assertEqual(p,s.robots[0]['pos'])

if __name__=='__main__': unittest.main()
