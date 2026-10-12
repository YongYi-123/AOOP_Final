# Puzzle Maze 4.0 — Emberglass Hollow

An original Python / Pygame dungeon adventure upgraded in place. Twenty-two
rooms over 1F and B1F combine branch exploration, returning routes, cross-room
circuits, fire sequences, carried weights, enemy weaknesses and five secret
collections. The original free Arcade cabinet now opens this 4.0 campaign. No story is included.

## Run

```bash
.venv/bin/python -m puzzle_maze
```

For another environment install `puzzle_maze/requirements.txt`, then run
`python3 -m puzzle_maze`. The resizable window starts at 960×720. Sound falls back
to silence when mixer initialization fails.

New expedition plays a six-second introduction; Enter skips to the tutorial.
Left/Right switch the two tutorial pages and Enter begins. Quick start skips both.
Continue expedition loads 4.0 without onboarding. Pause, full map and onboarding
freeze gameplay clocks, enemy AI and bomb fuses.

## Controls

| Key | Action |
| --- | --- |
| WASD / arrows | Move / face; push permitted crates with Gloves |
| J | Basic Sword, attack a crystal switch, or strike an exposed core |
| E | Interact; Gloves lift pots; while carrying, place the pot ahead |
| G | Throw the carried pot up to four tiles; walls stop it |
| P | Spend Magic Powder on the faced, adjacent unlit brazier |
| B | Place a bomb, 1.6-second fuse |
| Q | Cycle pulse / acquired Mirror / acquired Magnet |
| Space | Selected tool; Magnet repels a metal weight |
| F | Magnetic pull |
| Shift | Three-tile dash after Boots, 1.2-second cooldown |
| H | Spend a potion to heal up to three hearts |
| Tab | Full map; Left/Right switch floors |
| R | Reset this room to its entrance checkpoint |
| Esc | Pause / return |
| M | Toggle music |

Repeated P/G/B/J/E/Space key events do not double-consume supplies. A carried pot
must be dropped or thrown before changing rooms; lit bombs must finish first.
The starting Sword remains available, with a one-tile facing hitbox and 0.25-second
cooldown. Damage grants 1.1 seconds of invulnerability.

## Explore branches and loops

The central atrium now has a crystal circuit. Blue opens the library route, red
opens the watch route. The weight/light branch offers Gloves, while the shrine
provides Magic Powder and a flame relay. Library and weight/light relays plus the
flame relay power the lower stairs; two Small Keys unlock them.

You can first explore the glove branch, then the shrine, then Pot Storage for a
bomb bundle and the workshop shortcut. Alternatively, take the combat-key watch
route to the workshop. Boots later unlock another return loop. B1F adds Warden /
prism connections and a circuit shortcut, so returning need not follow the same
corridor. Small Key costs remain five, with six authored keys available.

The old eighteen rooms retain their working box, light, magnetic and dash puzzles.
Four new rooms provide distinct mechanics rather than blank space:

| Room | Connected challenges |
| --- | --- |
| Torch Shrine | Powder chest/refill, numbered fire sequence, revealed Ghost, flame relay, secret fire |
| Pot Storage | Gloves, throwable pots, Pot Hunter, carried three-weight plate, flame-controlled gate and shortcut |
| Crystal Warden | Red/blue circuit, projectile mini-boss, two finite summons, blue exit and cracked sanctuary wall |
| Hidden Sanctuary | Slime → Bat → Mirror Mask order, hidden skin reward, cross-room relic and optional caches |

The Boss Key still requires returning to the earlier dash room, now after the
Warden challenge as well. The final Boss door also reads the Warden clear flag.
The graph and minimap read actual RoomManager exits, including stairs and loops.
Map reveals gray unexplored rooms; Compass marks known treasure and bosses.
Hidden rooms and conditional secret chests remain concealed until discovered.

## New puzzle rules

Magic Powder caps at 30. P ignites the marked braziers in order 1 → 2 → 3. Wrong
order extinguishes the group and allows another try. Supply stands repeatedly
refill up to 12; an already-lit or invalid target consumes nothing. The Ghost
is attackable only when its linked brazier is lit.

Gloves lift intact pots. A carried pot weighs two plus the player's one, enough
for a three-weight plate. Putting it down restores collision and enables lighter
weight plates. G throws it: pots damage enemies, reveal contained treasure or
release a short-fuse bomb. Renewable pot racks prevent mandatory combat deadlocks.
Rare pot contents are source-deduplicated and cannot be farmed.

J toggles a red/blue crystal circuit shared by both floors. The matching color's
barriers rise; the other color lowers. Occupied barriers remain down until player,
enemy or weight leaves. Crystal state persists. Magnetic-only weights still
require Magnet and cannot be manually pushed around their water slots.

The sanctuary's carved enemy order is Slime, Bat, then Mirror Mask. A wrong kill
resets the encounter with safe spawn positions and a visible cue. These foes do
not drop farmable loot during failed attempts. Room reset remains available.

## Enemies and bosses

The original Slime, Bat, Guardian, Blink Mage, Armored Beetle and Bomb Eater remain.

- Mirror Mask moves opposite your steps, obeys walls and has frontal armor. Flank
  it or use a bomb/pot. The campaign witness searches coupled player/mask states.
- Pot Hunter rushes carried pots and blocks the Basic Sword; a thrown pot inflicts major damage. Bombs
  can also hurt it, and the room supplies renewable pots.
- Crystal Ghost stays translucent and protected until its brazier is lit.
- Elite Guardian combines telegraphed melee/lunging movement with ranged shots,
  using the original Guardian's HP rather than difficulty through HP inflation.
- Crystal Warden is a mini-boss: red reveals its core, ranged windups threaten
  the arena and two pre-authored summons wake at half health. Summons are finite,
  cannot appear on the player, and persist in saves. Blue lowers the exit.

Ancient Golem reuses the existing three-stage strategy: dash the anchor and sword
its core, bomb the armor and sword it, then combine dash/bomb/sword again. Its last
phase additionally requires BLUE crystal state. A local crystal and explosive
pots support the arena puzzle. Its 1.2-second death animation opens the exit,
then the final treasury/lever completes the run. Game Over offers Retry room or
Main menu; zero health rejects gameplay input.

## Secret treasures and private rewards

The treasure catalog includes Small Key, Boss Key, Bomb Bundle, Magic Powder,
Heart Recovery, Heart Fragment, Map, Compass, Token Cache, Ticket Bundle, Golden
Cat Statue, Secret Music Disc, Crystal Sword Skin and Lucky Cat Charm. All have
original pixel icons, a brief pickup animation and an English label.

Five collections use different conditions:

| Collection | Discovery |
| --- | --- |
| Golden Cat | Bomb-cracked optional treasury |
| Secret Music Disc | Correct fire sequence and an extra hidden brazier |
| Lucky Cat Charm | An inscribed breakable pot |
| Crystal Sword Skin | Correct sanctuary enemy order |
| Ancient Star Stamp | The shrine flame and Warden signals combined |

Four unique Heart Fragments grant an extra heart and recovery. Capacity and
fragments save correctly; duplicate treasure sources do not grant another.

DungeonRewardBag escrows Tokens, Tickets and collections for the current run.
Completing the dungeon turns the bag into one local receipt with a run id and
records its claimed state. Repeated settlement returns that same receipt without
adding rewards again. Death or abandoning a run does not pay pending rewards.
Nothing imports or mutates the Arcade Lobby economy, profiles, tokens or tickets.
A future external integration must consume/deduplicate the receipt by run id.

## Visual improvements

Room palettes now include Torch Shrine, Pot Storage, Crystal Hall, Underground
Library, Forgotten Vault, Ancient Workshop, Hidden Sanctuary and Boss Chamber.
Room-scale mosaics, runners, medallions, broken paving, staggered columns and
alcoves vary the old repeated structure. Background art is clipped to real floor;
statues, walls and bookshelves retain real terrain collision.

Original pixel flames, crystal glows, faint dust, shadows, ghost translucency,
carried pots, thrown pot arcs, shard bursts, opening chest lids and circuit rings
provide feedback. Boss panels choose a position away from live actors. Pickup
cards and HUD remain above world art. The original solid-pixel 5×7 font is drawn
at integer size on final output; world scaling uses nearest neighbor.

HUD shows hearts, sword, keys, bombs, powder, Boss Key, abilities, carried pot,
potions, fragments, collection count, global crystal color and floor.

## Saves and archives

4.0 uses `puzzle_maze/save_v4.json` with atomic replacement. It leaves `save_v3.json`,
`save_v2.json`, legacy `save.json` and their backups intact. Invalid saves fall back
without rewriting the file. Dead sessions do not replace the last living save.
Room reset restores entry inventory, enemy progress, carried objects and pending
reward sources. A settled receipt cannot be reset into another claim.

Archived expeditions opens the 3.0 / 2.1 campaign menu without overwriting the
current save. They are also available directly:

```bash
.venv/bin/python -m puzzle_maze --campaign 3
.venv/bin/python -m puzzle_maze --campaign 2
```

See `README_V3.md` and `README_V21.md`. The original Arcade cabinet now uses the 4.0 campaign through `lobby_scene.py`.
P1 uses J / E / Space / LShift; P2 uses K / Enter / KP0 / RShift. Both use
B bombs, P powder and G pots. Private reward receipts do not pay lobby currency.

## Architecture and maps

AdvancedDungeonSession extends DungeonSession and composes AdvancedPuzzleManager,
existing CombatManager, BombManager and DungeonRewardBag. PuzzleObject factories
add Brazier, TorchSequence, LiftablePot, WeightPlate, CrystalSwitch, CrystalBarrier,
OrderedSeal and replenishment stands. Enemy subclasses add separate damage/AI
strategies while keeping the same encounter lifecycle and persistence.

Game keeps its scene machine and adds an archive menu and two tutorial pages.
RoomArt caches presentation-only room layers; IconHUD, Renderer and the bitmap
font draw feedback. No second collision engine, economy or manually drawn map
connection system is introduced.

Editable map data is `maps/dungeon_v4.json`; `python -m puzzle_maze.build_dungeon_v4`
regenerates it from the original authoring script. Keep direct edits and authoring
consistent. DungeonValidator reads actual costs/rewards and annotated access
alternatives, and searches all key spending orders in a monotone abstraction.

## Tests and practical limits

```bash
.venv/bin/python -m unittest discover -s puzzle_maze/tests -v
.venv/bin/python -m puzzle_maze --headless --frames 60
.venv/bin/python -m puzzle_maze --headless --screenshot /tmp/puzzle-maze.png
```

137 tests pass. They cover all prior regressions, all 22 room visits, the complete
five-secret victory route, crystals, carried weights, fire/enemy orders, pot combat,
finite Warden summons, both Bosses, receipt idempotence, death, corrupt/active saves,
archives and UI bounds at five resolutions. All 341 abstract resource states have
a winning continuation. Geometry and abilities are separately replayed through
production movement; coupled mirror movement is searched for a legal approach.

This is not exhaustive proof over every enemy timing or crate arrangement. Route
walking does not advance the clock per movement step; combat and fuses receive
explicit ticks. Real-time balance still needs human playtesting. Headless image
review covers the rooms, fire shrine, carried pots, Warden and tutorial.
A 180-frame cached Warden draw benchmark averaged 1.87 ms/frame here; it measures
rendering, not full interactive FPS.

Manually check input feel, powder/pot discoverability, real-time Warden/Golem
balance, audio volume, native display scaling and actual FPS. All edits are confined to `puzzle_maze/`; no push, pull, merge or backup-branch
changes were made. The cabinet selects 4.0 explicitly without changing host modules.
