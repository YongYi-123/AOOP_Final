# Puzzle Maze 3.0 — Clockwork Hollow

An original standalone Python / Pygame dungeon, extending the existing movement,
room, puzzle, combat and save architecture. Eighteen compact 26×16 rooms form a
branching dungeon over 1F and B1F. No story, external artwork or new lobby integration.

## Run

From the AOOP_Final root:

```bash
.venv/bin/python -m puzzle_maze
```

For another environment, install `puzzle_maze/requirements.txt`, then run
`python3 -m puzzle_maze`. The resizable window starts at 960×720. Audio-device
initialization failure leaves gameplay available with silent sound.

New expedition plays the six-second sword/gate introduction. Enter skips to the
control card; Enter confirms gameplay. Quick start bypasses both. Onboarding,
pause and the full map freeze enemy AI, bomb fuses and puzzle clocks.

## Controls

| Key | Action |
| --- | --- |
| WASD / arrows | Move and face; push crates after obtaining Gloves |
| J | Basic Sword, equipped immediately; one front tile, 0.25 s cooldown |
| E | Chest, lever, key lock, supply jar or mirror pedestal |
| B | Place a bomb, 1.6 s fuse; repeat events do not consume another bomb |
| Q | Cycle pulse, acquired Mirror and acquired Magnet |
| Space | Selected tool; Magnet repels a faced metal weight |
| F | Magnetic pull; maximum six tiles |
| Shift | Three-tile dash, after finding Boots; 1.2 s cooldown |
| H | Spend a potion to recover up to three hearts |
| Tab | Full dungeon map |
| Left / Right in map | Switch 1F / B1F |
| R | Reset the current room to its entrance checkpoint |
| Esc | Pause / return |
| M | Toggle music |

Sword hits flash and knock enemies back. Player damage grants 1.1 seconds of
invulnerability. Dashes stop at walls and live enemies. Timed dash gates require
an actual dash; they have a safe return portal on their far side.

## Dungeon and progression

| Room | Purpose |
| --- | --- |
| Stone Vestibule | Basic combat, map chest and lever gate |
| Relay Atrium | Central branches; two remote relays and a two-key stair lock |
| Copper Watch | Clear Slime/Bat, reveal two keys, spend one to reach the workshop |
| Weight and Light | Gloves, heavy crate plate, Mirror beam and west relay |
| Ancient Library | Lever, Mirror, crate plate, east relay, Compass and branch key |
| Returning Runner | Return with Boots and the lower prism signal; dash for Boss Key |
| Powder Workshop | Bomb chest, renewable supply, lever route and cracked secret wall |
| Hidden Treasury | Optional reward and bomb-activated bonus chest |
| Boots Trial | Guardian/Beetle combat and a heavy plate unlock Boots |
| Lower Landing | B1F crossroads, lever gate and restorative chest |
| Magnetic Foundry | Blink Mage and lever unlock Magnet |
| Prism Engine | Magnet-only weight, powered beam, Mirror, relay and key |
| Hungry Portal | Renewable bombs, Bomb Eater, combat key and activated portal |
| Threefold Circuit | Magnet plate + Mirror receiver + timed dash gate |
| Sentinel Gallery | Three enemy styles and a two-key lock |
| Golem Antechamber | Boss Key seal, healing chest and bomb refill |
| Ancient Golem | Three ability-driven boss phases and death-gated exit |
| Dawn Reservoir | Treasure and final lever complete the expedition |

Six Small Keys cover five lock costs, leaving one spare. Doors consume keys
atomically and retain their unlocked state. Boss Key remains owned after opening
the boss seal. Progress, chests, killed enemies, global relays and exploration
persist across room and floor changes. Hidden Treasury is optional.

Bombs cap at 20. Supply jars refill up to eight and can be used repeatedly; required
bomb encounters have a jar. Explosions damage the player and enemies, stop at
permanent walls/closed doors and break marked cracked walls. An active bomb must
finish before changing rooms. Special enemies can drop bombs.

Magnet-only crates cannot be pushed manually. Mirror rotation requires ownership.
Heavy crates require Gloves. The prism relay powers the earlier Boss Key room,
so returning to the old floor is required.

## Enemy weaknesses and boss

Slime hunts slowly; Bat has periodic bursts; Guardian commits to a visible melee
windup. Blink Mage blinks along legal clear paths and telegraphs projectiles.
Armored Beetle blocks frontal sword strikes: flank it, bomb its armor or dash
into it. Bomb Eater ignores swords and pursues/swallow bombs, taking extra damage.
All encounters are finite, collision-aware and save their life state.

Ancient Golem has 12 HP:

1. Dash across the inlaid anchor, then sword the exposed core.
2. Bomb the armor, then sword the core.
3. Dash the anchor again, bomb the armor, then sword the core.

Each phase needs four sword hits. Phase changes close the previous exposure.
The boss telegraphs attacks; later phases move and fire projectiles, ending with
four-way volleys. The arena refills bombs. The death animation lasts 1.2 seconds
before the exit opens. Game Over offers Main menu or Retry room.

## Pixel UI and environment

The original 5×7 bitmap font is drawn at integer pixel sizes on the final output,
without antialiasing or smoothscale. World art uses nearest-neighbor scaling.
Original icons display hearts, Sword, Small Key, Boss Key, bombs, Gloves, Boots,
Mirror, Magnet, Map, Compass, selected tool and potions. Pickups bounce briefly
with a short name/control label and sound. Gray icons indicate unowned items.

Stone, wood/library, metal, crystal, guard, vault and sanctum materials use cached
original pixel tiles, wall-mounted decorations, animated lights and shadows.
B1F has colder palettes. Columns and bookshelf obstacles use actual collision
terrain; decorative wall overlays never introduce collision. Bombs, projectiles,
shield exposure, enemy windups, death bursts and dash trails have distinct art.

The map reads RoomManager and actual exit data. Without Map it shows visited
rooms; Map reveals gray unexplored rooms on the selected floor. Secrets remain
hidden until visited. Compass adds discovered chests and a boss marker when the
boss room or an adjacent room is known. Stair corners identify floor connections.

## Saves and the 2.1 archive

3.0 uses `puzzle_maze/save_v3.json`, with atomic temporary-file replacement. It
never overwrites `save_v2.json`, `save.json` or the 2.0 backup. Invalid saves fall
back to a new session without editing the invalid file. Dead sessions do not
replace the last living save; Retry room restores its entrance checkpoint.

The original campaign remains available:

```bash
.venv/bin/python -m puzzle_maze --legacy
```

If an old save exists, the standalone menu also provides Continue 2.1 archive.
New 3.0 progression is separate because the floor graph and room geometry changed.
See `README_V21.md` for the original campaign and its 2.0 migration details.
The pre-existing optional lobby adapter remains on that older campaign.

## Architecture

`DungeonSession(GameSession)` composes the existing RoomManager, Player,
PuzzleManager, CombatManager, Inventory and Exploration with BombManager.
PuzzleObject subclasses add CrackedWall, BombSupply, DashSwitch, RemoteRelay,
RemoteSwitch and BlastSwitch through the existing factory. Door/Chest reuse the
existing condition system for multi-key locks, Boss Key and delayed rewards.
Enemy subclasses override damage and AI: BlinkMage, ArmoredBeetle, BombEater and
AncientGolem. GameScene continues to manage onboarding, pause, map, death and
victory; IconHUD/IconAtlas and the bitmap font provide presentation.

Editable data is `maps/dungeon_v3.json`. The deterministic authoring script
`python -m puzzle_maze.build_dungeon` regenerates it. Keep direct JSON changes and
that authoring script consistent. DungeonValidator reads progression annotations
on actual reward/door objects, derives quantities/costs and searches resource
states; there is no separate manually drawn minimap graph.

## Validation

```bash
.venv/bin/python -m unittest discover -s puzzle_maze/tests -v
.venv/bin/python -m puzzle_maze --headless --frames 60
.venv/bin/python -m puzzle_maze --headless --screenshot /tmp/puzzle-maze.png
```

108 automated tests pass, including the original regression suite, all eighteen
room visits, the complete victory route, three boss phases, live bomb/save states,
resource spending orders, box corner deadlocks, floor exploration, input repeats,
UI bounds at five resolutions and silent audio fallback.

The resource abstraction has 109 reachable states; all 109 can finish. Production
action witnesses separately verify geometry, interactions, crate pushes, magnetic
weights, mirrors, timed dashes and combat. These are deterministic witnesses, not
an exhaustive search over every enemy timing, player input or all crate arrangements.
Movement steps in the route witness do not advance time; combat/fuses/dash timers
are advanced explicitly. Real-time difficulty still needs human playtesting.

Headless screenshots have been reviewed. A cached boss-scene draw benchmark was
2.56 ms/frame over 180 frames on this environment; this measures rendering only,
not interactive FPS. Manually check keyboard response, boss readability/difficulty,
attack and dash feel, audio volume, the smallest window and physical-display FPS.
