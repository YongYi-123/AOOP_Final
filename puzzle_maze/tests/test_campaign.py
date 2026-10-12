"""Production campaign witnesses replay movement and pushing, rather than bypassing collision."""
import unittest
from puzzle_maze.session import GameSession
from puzzle_maze.rooms import load_rooms
from puzzle_maze.solver import solve_boxes
from test_playthrough import walk,use

def boxes(session,ids,plates):
    open_ids=[o.id for o in session.puzzles.objects.values() if o.state.active]
    solution=solve_boxes(session.rooms.data,ids,plates,(session.player.x,session.player.y),open_ids)
    if solution is None:raise AssertionError('No push-state solution')
    for behind,delta in solution:
        walk(session,behind)
        if not session.move(*delta):raise AssertionError('Invalid solver push')
        session.tick(.13)


def solve_room(s):
    name=s.rooms.current
    if name=='r1':use(s,(9,11))
    if name=='r5':use(s,(9,11))
    if name=='r6':use(s,(11,10))
    if name=='r1':use(s,(4,7))
    elif name=='r2':walk(s,(7,7))
    elif name in ('r3','r8'):
        boxes(s,['box1','box2'],['plate1','plate2'])
        if name=='r8':
            walk(s,(10,3));use(s,(13,7),True)
            use(s,(18,10));use(s,(19,5));use(s,(23,7))
    elif name=='r4':walk(s,(7,5));use(s,(13,7))
    elif name=='r5':use(s,(6,4));use(s,(6,10))
    elif name=='r6':use(s,(13,7),True)
    elif name=='r7':use(s,(9,7))
    walk(s,(16 if name!='r8' else 26,7))
    if name=='r3':use(s,(26,10))
    if name in ('r5','r7','r8'):use(s,(34,10))
    if name in ('r1','r3'):
        walk(s,(33,13));use(s,(39,17))
    elif name=='r4':
        use(s,(33,13));use(s,(34,17))
        s.player.facing=(1,0)
        if not s.dash():raise AssertionError('Boots dash required')
    elif name in ('r6','r7','r8'):
        walk(s,(30,17));s.player.facing=(1,0)
        for _ in range(3):
            if s.puzzles.magnet(s.player) is None:raise AssertionError('Magnet route blocked')
    else:boxes(s,['relay_box'],['relay_plate'])
    walk(s,(53,17))

class CampaignTests(unittest.TestCase):
    def test_eight_enlarged_rooms_complete_in_order(self):
        s=GameSession()
        for name in list(load_rooms())[:8]:
            self.assertEqual(s.rooms.current,name)
            solve_room(s);self.assertTrue(s.transition())
        self.assertTrue(s.finished)

    def test_forward_portals_enforce_conditions(self):
        s=GameSession()
        for name,room in list(s.rooms.rooms.items())[:8]:
            self.assertEqual((len(room['tiles'][0]),len(room['tiles'])),(56,34))
            s.enter(name);s.player.x,s.player.y=53,17
            self.assertFalse(s.transition())
            self.assertGreaterEqual(len(room['objects']),6)
