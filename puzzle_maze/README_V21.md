# Puzzle Maze 2.1 — The Prism Chambers

An independent Python / Pygame dungeon game, upgraded in place. Eight connected
40×26 chambers and a 19×14 secret vault combine exploration, puzzles and combat.
All in-game text is English. This upgrade changes only `puzzle_maze/`.

## Launch

From the AOOP_Final root:

```bash
.venv/bin/python -m puzzle_maze
```

For another Python environment:

```bash
python3 -m pip install -r puzzle_maze/requirements.txt
python3 -m puzzle_maze
```

Use pygame-ce; do not install the original pygame alongside it.
The default resizable window is 960×720.

## Start and learn

**New expedition** equips a Basic Sword and plays a six-second sword / gate
animation. Enter skips the animation. The HOW TO PLAY card then waits for Enter
before gameplay begins. Enemies and puzzle clocks stay frozen during onboarding.
Esc cancels to the menu without overwriting progress.

**Quick start (skip tutorial)** starts a new run immediately. **Continue expedition**
loads progress without repeating onboarding. **Controls** opens the same live
control guide used by the tutorial. Repeated key events cannot accidentally
confirm the tutorial after skipping the animation.

## Controls

| Key | Action |
| --- | --- |
| WASD / arrows | Move; push heavy crates after finding Gloves |
| J | Swing the equipped Basic Sword |
| E | Chest, switch, key lock, or mirror pedestal |
| Space | Selected tool: pulse, mirror or magnetic repel |
| Q | Cycle pulse and acquired mirror / magnet tools |
| F | Magnetic pull, after acquiring the Magnet |
| Shift | Three-tile dash after acquiring Boots; 1.2-second cooldown |
| H | Use a potion to heal up to 3 HP |
| Tab | Dungeon graph and explored tiles / discovered markers |
| R | Restore this room's entrance checkpoint |
| Esc | Pause / return from menus |
| M | Toggle music |

The Basic Sword is equipped from the start, independent of chests and abilities.
Walking toward a living enemy turns the player without overlapping its body, so
you can aim and attack reliably. Crates and dashes also stop at living enemies.
The sword hits the adjacent tile directly in front of the player, once per swing, with
0.25 seconds between attacks. The blade remains visible at the belt; swings show
a moving blade and trail. Hits flash and knock enemies back, with a hit sound.

The HUD displays five hearts, potions, the selected tool, dash cooldown, sigils
and shards. G / B / L / M mark acquired Gloves / Boots / Mirror / Magnet.

## Rooms

Each main chamber retains its linked puzzle stages. Large unused floor areas,
decorative water pools and long exit detours have been removed. Only the three
magnetic slots retain water, which prevents direct access to their metal weights.
Mounted decorations never alter collision or hide important puzzle objects.

| Chamber | Theme and objective |
| --- | --- |
| Entrance Hall | Stonework, torches and a statue; Gloves chest, switch gate and key seal |
| Mechanism Room | Riveted metal and animated gears; entrance plate, heavy crate relay |
| Ruined Library | Shelves, planks and broken book piles; two crate plates, Boots and key |
| Guard Room | Slate, racks and columns; amber lock, signal and short dash gate |
| Crystal Chamber | Blue stone and glowing crystal; Mirror, signals, reflected light and weight |
| Mosswork Vault | Purple stone and gold sigils; cracked wall, Magnet and remote metal weight |
| Star Observatory | Constellation floors; clock gate, reflected light and magnetic relay |
| Prism Sanctum | Banners and inlaid stone; combined tools and three southern guards |
| Hidden Vault | Optional secret chamber; two lantern switches and a supply chest |

A cracked moss wall marks each optional supply alcove. A second secret passage in
Mosswork Vault reaches Hidden Vault. Its chest grants two potions and three shards
once. Reach the eastern exit in Prism Sanctum to finish.

Normal doors latch open when their conditions are satisfied. Timed doors close
when the clock expires, except while occupied by a player, crate or living enemy.
Crossing memory can power later stages without holding a timed door open.

Gloves allow heavy pushes. Mirror pedestals turn light toward receivers. Magnetic
pull / repel works up to six tiles, across water but never through walls or into
obstacles or the player. The fourth room's short clock requires a dash.

## Combat, death and reset

Slime has 2 HP and slow pursuit; Bat has 1 HP and periodic movement bursts;
Guardian has 4 HP and a visible 0.7-second attack windup. Enemy navigation respects
terrain, walls, closed doors and crates. Enemies die with a short animation and
leave a one-time healing / shard pickup. Room changes and loading do not respawn
killed enemies.

Damage causes safe knockback, flashing and 1.1 seconds of invulnerability. HP zero
stops movement and actions and opens GAME OVER. Enter / Esc returns to the game
menu without closing the application. A loaded dead run remains GAME OVER.

R restores the room's entrance checkpoint, including health, objects, enemies,
keys and supplies. It reverses rewards acquired in this room, preventing duplicate
claims. Earlier tools remain. Exploration is retained. A revisited room uses its
state at that visit as its new checkpoint.

## Native text and art

Pixel scenery uses integer nearest-neighbor scaling. Bundled DejaVu regular / bold
fonts render directly onto the final output surface with native-size glyph
antialiasing; text is never drawn into the low-resolution world and enlarged.
Modal text replaces the world HUD. Titles and notifications respect panel bounds.
Font notices are in `assets/fonts/DejaVu-LICENSE.txt`.

EnvironmentPainter draws original pixel textures and wall-mounted props. Theme
palettes, materials, sparse floor variants, shadows, light glows, flames, gears and
crystal sparkles distinguish rooms. Tiles and glow surfaces are cached; particles
are bounded. No commercial game assets are used.

## Progress and compatibility

Progress stays in `puzzle_maze/save_v2.json` and its temporary / backup files, all
ignored by Git. Saves include equipment, tools, health, cooldowns, combat, puzzle
snapshots, checkpoints and exploration. Autosave happens every 15 seconds and on
room changes, pauses, deaths and exits. Writes use atomic replacement.

Valid 2.0 progress loads into compact 2.1 coordinates without resetting earned
items or completed rooms. Removed-space positions are moved to safe cells in the
same puzzle region. Reading does not change the source file. Before the first
write over a 2.0 save, its original bytes are preserved as
`save_v2.json.v20.bak`. Missing weapon fields default to Basic Sword; the new
optional vault chest is added safely to old snapshots. Unsupported or damaged
saves fall back to a fresh session without modifying the file during loading.
The original version-one `save.json` remains untouched.

The existing optional `lobby_scene.py` remains inside this package. It now routes
combat / tools and renders text at the host's full output resolution. No host
module was edited. Solo controls match the table; in a two-player session the
starter controls the game: P1 uses WASD, J, E, Space and LShift; P2 uses arrows,
K, Enter, KP0 and RShift. The tutorial and HUD show that participant's controls.
Q / F / H / Tab / R remain shared utility keys. The optional cabinet remains a
free trial without score or ticket payouts.

## OOP structure

- Game / GameScene: scene state, events and display composition, including INTRO
  and TUTORIAL alongside play, pause, map, victory and game over.
- IntroSequence / TutorialCard: timed presentation and one control-guide source.
- Weapon / BasicSword / WEAPONS: equipment, directional reach, damage and timing,
  with a registry for future upgrades.
- Player / TileMap / CollisionManager / Camera: existing movement, health and
  collision core.
- RoomManager / PuzzleManager / PuzzleObject subclasses: JSON maps, factory-based
  entities, compound conditions, inventory, keys and tool puzzles.
- CombatManager / Enemy / Slime / Bat / Guardian / EnemyState: finite encounters,
  movement, windup, damage, death and rewards.
- GameSession / CoordinateTransform / LayoutMigration: persistence, room snapshots
  and safe translation of old progress.
- Exploration / DungeonAtlas: line-of-sight exploration and the actual room graph.
- Renderer / NativeText / RoomTheme / EnvironmentPainter / AudioManager: pixel
  scenery, final-resolution text, cached original art and optional audio.

## Verification

```bash
.venv/bin/python -m unittest discover -s puzzle_maze/tests -v
.venv/bin/python -m puzzle_maze --headless --frames 60
.venv/bin/python -m puzzle_maze --headless --screenshot /tmp/puzzle-maze-21.png
```

Tests cover starter sword / input / single-hit behavior, all eight main rooms via
production movement, push-state solver replay, optical / magnetic / timed puzzles,
combat, onboarding, English text, multiple window sizes, hidden vault rewards,
exploration, death and old-save migration / backup. Legacy fixtures preserve the
original engine regressions. Screenshot review and dummy-driver rendering do not
replace real keyboard, monitor, audio-device and difficulty testing.
