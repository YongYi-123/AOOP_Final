"""Production campaign witnesses replay movement and pushing, rather than bypassing collision."""
import unittest
from puzzle_maze.session import GameSession
from puzzle_maze.rooms import load_rooms
from puzzle_maze.solver import solve_boxes
from collections import deque
from test_playthrough import DIRECTIONS

def walk(session,target):
    for _ in range(600):
        start=(session.player.x,session.player.y)
        if start==tuple(target):return
        if session.player.hp<=2:session.heal()
        queue=deque([(start,None)]);seen={start};step=None
        while queue:
            pos,first=queue.popleft()
            if pos==tuple(target):step=first;break
            for dx,dy in DIRECTIONS:
                nxt=pos[0]+dx,pos[1]+dy
                if nxt not in seen and session.puzzles.can_enter(*nxt):
                    seen.add(nxt);queue.append((nxt,first or (dx,dy)))
        if step is None:raise AssertionError(f'No route to {target}')
        if not session.move(*step):raise AssertionError('Movement disabled')
        session.tick(.13)
    raise AssertionError('Movement witness did not converge')

def use(session,pos,pulse=False):
    walk(session,pos)
    if not session.puzzles.interact(session.player,pulse):raise AssertionError('Interaction blocked')
    session.tick(0)


def boxes(session,ids,plates):
    open_ids=[o.id for o in session.puzzles.objects.values() if o.state.active]
    solution=solve_boxes(session.rooms.data,ids,plates,(session.player.x,session.player.y),open_ids)
    if solution is None:raise AssertionError('No push-state solution')
    for behind,delta in solution:
        walk(session,behind)
        if not session.move(*delta):raise AssertionError('Invalid solver push')
        session.tick(.13)


def fight_encounter(s):
    for enemy in s.combat.enemies:
        safety=0
        while enemy.hp>0:
            if s.player.hp<=2:s.heal()
            safety+=1
            if safety>12:raise AssertionError('Combat route failed')
            candidates=[(enemy.x-1,enemy.y),(enemy.x+1,enemy.y),(enemy.x,enemy.y-1),(enemy.x,enemy.y+1)]
            for target in candidates:
                if s.puzzles.can_enter(*target):
                    walk(s,target);break
            delta=enemy.x-s.player.x,enemy.y-s.player.y
            if abs(delta[0])+abs(delta[1])<=1:
                s.player.facing=delta
                s.attack();s.tick(.26)
            if s.player.hp<=0:raise AssertionError('Player died during combat witness')
        s.tick(.4);walk(s,enemy.pos)


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
    if name=='r1':
        use(s,(34,22),True);use(s,(35,24))
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
    if name=='r8':fight_encounter(s)
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

    def test_upgraded_secret_archive_roundtrip(self):
        s=GameSession();s.enter('r6')
        use(s,(13,7),True);use(s,(28,11),True)
        walk(s,(29,14));self.assertTrue(s.transition())
        self.assertEqual(s.rooms.current,'r9')
        use(s,(6,4));use(s,(6,10));walk(s,(18,7))
        self.assertTrue(s.puzzles.solved)
        walk(s,(1,7));self.assertTrue(s.transition())
        self.assertEqual(s.rooms.current,'r6')

    def test_short_clock_fails_on_foot_and_succeeds_with_dash(self):
        s=GameSession();s.inventory.abilities.add('boots');s.enter('r4')
        walk(s,(7,5));use(s,(13,7));use(s,(33,13));use(s,(34,17))
        walk(s,(39,17))
        self.assertFalse(s.puzzles.can_enter(40,17))
        use(s,(34,17));s.player.facing=(1,0)
        self.assertEqual(s.dash(),3)
        walk(s,(41,17))
        self.assertTrue(s.puzzles.objects['seal'].latched)
