# Puzzle Maze 4.4 — Emberglass Hollow

An original Python / Pygame dungeon adventure upgraded in place. Twenty-seven
rooms over 1F and B1F combine branch exploration, returning routes, cross-room
circuits, fire sequences, carried weights, enemy weaknesses and six secret
collections. The original free Arcade cabinet now opens this 4.4 campaign. No story is included.

## 4.4 royal key, lower-floor circuit and treasure vault

The live campaign has **27 rooms, 37 chests, 61 entrance records and 41 effective
actuators**. The resource search retains 409/409 winning states and six Small
Keys for five costs. The existing 1F/B1F layout, all six hidden rooms, nonlinear
branches, enemies, Boss phases, abilities and recoverable Iron Orb remain.

Boss Key now has an original 16-pixel golden crown/jewel silhouette; Small Key
is a smaller silver key. The same royal silhouette appears in HUD, map inventory,
large acquisition popup and the Boss Gate. Its hidden chest has gold edging and
a jewel. Acquisition takes priority over ordinary pickup messages, shows
**BOSS KEY ACQUIRED** for 2.4 seconds and plays a dedicated cue. The stone Boss
Gate opens over 0.6 seconds, retains the non-consumable key and saves its timer.

New-game key route: shatter the Storage pillar on 1F and the Foundry pillar on
B1F with the same Orb; their flags lower the optional stairs. Carry the Orb to
r22 and drop it on the crowned socket at (9,12). The lower circuit posts a saved
royal resonance flag, visibly waking the matching upper circuit in r6. Finish
the existing Boots/timed gate, Prism and Warden conditions to reveal the royal
key chest. Recall remains T; walls and forbidden portals still stop the Orb.
The design uses original room layouts and pixel art, applying the broad ideas
of transporting a weight, changing access and returning after a floor changes.

Before Dungeon Map, both map views expose only the current room. The Map chest
unlocks non-secret outlines; unexplored rooms stay gray and secret rooms stay
hidden until visited. Compass is a separate obtainable chest reward and adds
known treasure/Boss scope. New tests cover both acquisitions and the circuit.

Defeating Golem waits for its death animation before opening the route to r18.
Open r18's original treasure and dawn gate, then walk east into the independent
**r27 Royal Treasure Vault**. No settlement happens when the Boss dies or when
the vault is entered. The compact room has gold/silver coin heaps, colored gems,
gold pillars, stone inlay, runes, reliefs, warm torches and sparse sparkle motes.
Visibly empty, open display chests differ from the three locked interactive
coffers. All three have legal walking/interaction approaches and save once-only
openings. The minimap moves to the top center here to expose the treasure.

The floating central scroll at (11,7) has a bob, halo and orbiting pixels.
Approach and press E (P2: Enter) for **COMING SOON**. Enter/E/Esc closes the modal;
gameplay clocks freeze while it is open. No story, quest or achievement is
implemented. MysteryScroll's content identifier is the extension point.

Royal coffers contain the first-clear base bonus of **1,000 Tokens / 300 Tickets**
and the original **Emberglass Crown** collection. Open all three and walk through
the east exit to finish. Existing exploration rewards remain in the escrow too.
RoyalClearHistory records one immutable receipt per run ID: the first royal clear
keeps the 1,000/300 bonus; subsequent royal clears reduce that part to **100/30**.
Revisiting, reloading or calling settlement again does not generate another
receipt. Death/retry rolls back to the room-entry bag and chest checkpoint.
Leaving before completion produces no clear receipt.

**External Arcade account payout is disabled.** The host currently supplies no
persistent cross-run grant identifier for this cabinet. The requested fallback
is implemented entirely inside Puzzle Maze: reward policy, escrow, per-owner
receipts and a read-only adapter accessor. MiniGameResult retains the existing
free-trial zero-payout behavior; no Lobby economy or other game's module changes.
The victory screen identifies this policy. These records are not a second wallet.

CampaignProfile isolates Lobby players by their existing profile ID under
`puzzle_maze/profiles/<hashed-owner>/`. Each owns a campaign and authoritative
royal-history file. New runs preserve history; Continue merges compatible saved
receipts. Writes are atomic; malformed/wrong-owner histories block new reward
records rather than resetting first-clear eligibility. Standalone play continues
using the original `save_v4.json`, with its own isolated royal history. Old shared
Lobby progress remains available through standalone Continue and is not silently
copied into another person's profile. 4.0–4.3 saves retain earned keys, opened
rewards, Orb state and completed runs; old completions do not consume the new
royal first-clear bonus. Loading leaves source files unchanged.

Validation: all **206 Puzzle Maze + 1,827 Arcade Lobby tests passed** (2,033 total),
including the full 27-room/37-chest production-action witness. Regression source
was verified identical in an isolated tree to keep runtime saves separate.

New classes: BossKeyIcon, OrbSocket, MysteryScroll, RoyalVaultArt,
RoyalRewardPolicy, RoyalClearHistory and CampaignProfile. Full development,
file/commit and verification records are in [DEVELOPMENT.md](DEVELOPMENT.md).
Manual checks still needed: sound levels, key/gate timing, Orb socket clarity,
vault visual readability, P1/P2 keyboard feel and continuous Boss difficulty.

## Historical 4.3 exploration and combat update

The current dungeon has 26 rooms, 34 chests (24 truly hidden), six hidden rooms,
59 entrance records, and 40 effective puzzle actuators. Four new bomb-only
branches contain a mineral switch and bat encounter, an archive flame puzzle,
a weighted mint floor, and a blue-crystal shrine. Their rewards include Heart
Fragments, the Music Disc, a sword skin, collections, and private Tokens/Tickets.
Existing nonlinear routes, keys, abilities, multi-floor stairs and Boss progression
remain intact. The menu and original Arcade cabinet both load 4.3.

Hidden chests are absent from rendering, prompts, collision and Compass markers
until their conditions complete. They remember a completed trigger even while a
player, enemy, crate, pot or Iron Orb occupies the spawn tile. A short rise,
room flash, sparkles and distinct cue announce each reveal. Spawn timers, pending
triggers and opened rewards survive save/load and revisits.

Bomb walls use SEALED / REVEALING / OPEN states. During the 0.6-second break they
remain impassable; themed cracks, debris and dust replace explicit bomb prompts.
Secret rooms remain off the atlas until visited. All entrances have reciprocal
absolute directions and safe return landings.

Every authored enemy spawn stays at least three Manhattan tiles from each
entrance landing; doors, stairs and important objects are reserved. Live return
encounters repair unsafe enemy positions. One second of entry protection permits
movement; a sword attack, successful bomb placement or a thrown weapon cancels it.
Damage uses the existing 1.1-second hurt immunity. Boss weakness windows suppress
attacks and allow Sword approaches. Warden retains color defense and permits at
most three hits per window, requiring multiple Sword rounds. Golem still requires
the original dash/bomb/crystal sequence. Hurt stagger and readable danger tiles
supplement the existing attack windups and recovery timers.

Original pixel expressions, idle bobs, interpolated enemy steps and death motes
retain each silhouette. Library dust, crystal sparks, mine grit, pulsing local
lights, chest light and explosion/Boss illumination remain clipped above the HUD.
Lighting does not darken the scene or use smooth image scaling.

4.2 saves migrate in memory: earned rewards and already-revealed chests persist;
formerly visible but locked rewards gain real hidden conditions. A save standing
on a new wall receives a neighboring safe landing, including its carried Orb.
The existing 4.0/4.1 migration runs first when necessary. Loading does not rewrite
the source save. New saves still use `save_v4.json` with `content_revision: 4.3`.

Tokens/Tickets remain in the existing private expedition escrow and settle only
at a living victory. Retry restores the entry checkpoint's reward bag. The free
Arcade trial cabinet retains its existing **zero external payout** and no-score
policy; this update does not change the host economy or other games.

Validation passed: 189 Puzzle Maze tests and 1,827 complete Arcade Lobby tests
(2,016 total), plus integrity, map-builder equality and headless startup.

The production-action campaign visits all 26 rooms and opens all 34 chests, using
real movement, puzzles, bombs, combat clocks and both Boss mechanics, then checks
the saved, repeatable settlement receipt. This is a targeted action witness;
it does not exhaust every possible real-time combat trajectory. Manually verify
keyboard feel, clue subtlety, continuous Boss difficulty, sound levels and FPS on
the target computer.

## Run

```bash
.venv/bin/python -m puzzle_maze
```

For another environment install `puzzle_maze/requirements.txt`, then run
`python3 -m puzzle_maze`. The resizable window starts at 960×720. Sound falls back
to silence when mixer initialization fails.

New expedition plays a six-second introduction; Enter skips to the tutorial.
Left/Right switch the two tutorial pages and Enter begins. Quick start skips both.
Continue expedition loads 4.4 without onboarding. Pause, full map and onboarding
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
| T | Recall Iron Orb to Pot Storage |
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
bomb bundle and the north Workshop route. Boots Trial lies east of Workshop
and north of Copper Watch. Library has a secret west connection to Watch.
B1F branches west to Warden, north to Foundry/Prism, and east to Hungry Portal.
Two Orb pillars unlock a separate floor-changing return loop. Small Key costs remain five, with six authored keys available.

The old eighteen rooms retain their working box, light, magnetic and dash puzzles.
Four new rooms provide distinct mechanics rather than blank space:

| Room | Connected challenges |
| --- | --- |
| Torch Shrine | Powder chest/refill, numbered fire sequence, revealed Ghost, flame relay, secret fire |
| Pot Storage | Gloves, throwable pots, Pot Hunter, carried three-weight plate, flame-controlled gate and shortcut |
| Crystal Warden | Red/blue circuit, projectile mini-boss, two finite summons and north cracked sanctuary wall |
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

4.2 uses `puzzle_maze/save_v4.json` with atomic replacement. It leaves `save_v3.json`,
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

See `README_V3.md` and `README_V21.md`. The original Arcade cabinet now uses the 4.2 campaign through `lobby_scene.py`.
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

169 tests pass. They cover all prior regressions, all 22 room visits, the complete
five-secret victory route, crystals, carried weights, fire/enemy orders, pot combat,
finite Warden summons, both Bosses, receipt idempotence, death, corrupt/active saves,
archives and UI bounds at five resolutions. All 341 abstract resource states have
a winning continuation. Geometry and abilities are separately replayed through
production movement; coupled mirror movement is searched for a legal approach.

This is not exhaustive proof over every enemy timing or crate arrangement. Puzzle/cleared-room walking advances 0.13 seconds per step; combat uses
targeted actions plus real damage, AI, fuse and death ticks. Real-time balance still needs human playtesting. Headless image
review covers the rooms, fire shrine, carried pots, Warden and tutorial.
A 180-frame cached Warden draw benchmark averaged 1.87 ms/frame here; it measures
rendering, not full interactive FPS.

Manually check input feel, powder/pot discoverability, real-time Warden/Golem
balance, audio volume, native display scaling and actual FPS. All edits are confined to `puzzle_maze/`; no push, pull, merge or backup-branch
changes were made. The cabinet selects the current v4 campaign explicitly without changing host modules.


## Historical 4.2 absolute geometry and progression repair

[Complete Chinese walkthrough](PLAYER_ROUTE.md) documents the current dungeon, extending the 4.2
coordinates, door directions, resource order, puzzle solutions, optional Orb
route, Boss phases and the final room. The cabinet and standalone menu show
**PUZZLE MAZE 4.3**; restart a running host process to load the updated modules.

Every room has authoritative floor/grid_x/grid_y coordinates. The atlas derives
from those fields. DoorConnection/RoomCoordinate and DoorValidator check unique
room placement, cardinal adjacency, correct wall edge, reciprocal connection
IDs and opposite-entry landing. Inconsistent loops were replaced with physical
neighbors. No new main-route cheat portal was added. The existing Hungry Portal
has its own glow marker and explicitly refuses carried Iron Orbs.

There are 51 entrance records: 49 repaired regular/secret/stair/final records,
plus two optional transformation stair records. The original 1F/B1F stairs and
new pair total four stair records. Gates guard their actual exit tiles. Interior
multi-condition controllers use gear indicators instead of fake door art.
The lower landing no longer overlaps the Atrium east-door arrival. First success
on a timed dash gate enables normal return walking; timers still restrict the
first crossing. Five secret-entry records cover the two bomb walls, reciprocal
library/watch walk-through and remote foundry/sanctuary connection.

All 30 chests have interaction routes and actual rewards; 13 are hidden. Library
Compass and Prism key now require their real puzzle controller. Thirty-six
actuators have consumers derived by PuzzleDependencyValidator from actual
objects, exits, global flags, light receivers, enemies and transformation rules.
ChestValidator supplements the physical campaign witness with post-condition
local collision checks; it does not assume that connectivity solves puzzles.

IronOrb is one recoverable world object: Gloves/E lift or place, G throws,
T recalls to Pot Storage. It persists across allowed room/floor transitions,
save/load and room reset. It cannot coexist with a carried pot. Storage and
Foundry pillars unlock the optional new stairs and a reward chest; map edges
appear with the real transformation state. Correctly marked heavy-block
placement reveals another chest. Blue crystal plus the Prism puzzle reveals a
third new chest. Original return routes remain intact.

Before Map, minimap shows only the current room and Tab shows visited records.
Map unlocks gray unvisited outlines; hidden rooms stay undisclosed. Compass only
marks known reward/Boss scope. New stairs do not draw before their real unlock.

Old saves load read-only through migration42 using archived dungeon_v41.json:
validate old snapshots, update static gate/entrance positions, add optional
objects, choose legal landings and retain inventory, locks, enemies, completion,
exploration and private rewards. The save geometry identifier remains 4.0 with
content_revision 4.2 identifying this additive migration. Loading never rewrites
an existing save file.

Validation commands:

```bash
.venv/bin/python -m puzzle_maze.integrity
.venv/bin/python -m unittest discover -s puzzle_maze/tests -q
.venv/bin/python -m puzzle_maze --headless --frames 60
```

The integrity search retains 341/341 winning resource states (six Small Keys for
five costs), plus crate search and door/chest/dependency audits. The extended
production-action campaign opens every authored chest, traverses both floors
and the transformed stairs, defeats Warden/Golem and finishes r18 with an
idempotent saved receipt. Cleared-room/puzzle walking advances 0.13 seconds per
step; combat uses targeted action witnesses and real AI/damage/fuse/death timers.
This does not exhaustively simulate continuous human combat or every walking
trajectory. Real play is still required for difficulty, sound balance, clue
visibility and FPS on the user's machine.
