"""Execute solver output and complete every room via production movement."""
import unittest
from collections import deque
from legacy import load_rooms
from legacy import GameSession
from puzzle_maze.solver import solve_boxes

DIRECTIONS=((1,0),(-1,0),(0,1),(0,-1))

def walk(session,target):
    start=(session.player.x,session.player.y)
    queue=deque([(start,[])]);seen={start}
    while queue:
        pos,path=queue.popleft()
        if pos==tuple(target):
            for delta in path:
                if not session.move(*delta):raise AssertionError('Path blocked')
                session.tick(.13)
            return
        for dx,dy in DIRECTIONS:
            nxt=pos[0]+dx,pos[1]+dy
            if nxt not in seen and session.puzzles.can_enter(*nxt):
                seen.add(nxt);queue.append((nxt,path+[(dx,dy)]))
    raise AssertionError(f'No route to {target}')

def use(session,pos,pulse=False):
    walk(session,pos)
    result=session.puzzles.interact(session.player,pulse)
    if not result:raise AssertionError('Interaction unavailable')
    session.tick(0)

class PlaythroughTests(unittest.TestCase):
    def test_push_state_search_and_replay(self):
        for name in ('r3','r8'):
            with self.subTest(room=name):
                s=GameSession();s.enter(name)
                solution=solve_boxes(s.rooms.data)
                self.assertIsNotNone(solution)
                for behind,delta in solution:
                    walk(s,behind);self.assertTrue(s.move(*delta))
                self.assertTrue(all(o.state.active for o in s.puzzles.objects.values() if o.data['type']=='plate'))

    def test_eight_room_complete_route(self):
        s=GameSession()
        for name in list(load_rooms())[:8]:
            self.assertEqual(s.rooms.current,name)
            if name=='r1':use(s,(4,7))
            elif name=='r2':walk(s,(7,7))
            elif name in ('r3','r8'):
                for behind,delta in solve_boxes(s.rooms.data):
                    walk(s,behind);self.assertTrue(s.move(*delta));s.tick(.13)
                if name=='r8':
                    walk(s,(10,3));use(s,(13,7),True)
                    use(s,(18,10));use(s,(19,5));use(s,(23,7))
            elif name=='r4':walk(s,(7,5));use(s,(13,7))
            elif name=='r5':use(s,(6,4));use(s,(6,10))
            elif name=='r6':use(s,(13,7),True)
            elif name=='r7':use(s,(9,7))
            walk(s,(33,7));self.assertTrue(s.transition())
        self.assertTrue(s.finished)
        self.assertEqual(len(s.completed),8)

    def test_unsolvable_stone_layout_detected(self):
        room=load_rooms()['r3']
        room['objects'][0]['pos']=[1,1]
        self.assertIsNone(solve_boxes(room))

    def test_optional_hidden_room(self):
        s=GameSession();s.enter('r6')
        use(s,(13,7),True);use(s,(28,11),True)
        walk(s,(29,14));self.assertTrue(s.transition())
        self.assertEqual(s.rooms.current,'r9')
        use(s,(6,4));use(s,(6,10));walk(s,(18,7))
        self.assertTrue(s.puzzles.solved)
        walk(s,(1,7));self.assertTrue(s.transition())
        self.assertEqual(s.rooms.current,'r6')
