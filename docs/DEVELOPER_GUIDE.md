# Neon Corner Arcade — Developer Guide

This guide is for the people working on the code. It describes what the code does today. The player-facing
overview is the [README](../README.md).

> **Spoilers.** This guide names the story systems but never their solutions. The step-by-step story test guide
> (with solutions) is [arcade_lobby/MAIN_QUEST_TESTING.md](../arcade_lobby/MAIN_QUEST_TESTING.md). Keep secret
> solutions out of the README, menus, hints and console output.

## 1. Overview

The game is a single-player pygame-ce program. `arcade_lobby/` is the hub: three connected rooms, the profile and
save system, the economy, the story and the small built-in games (Lucky Corner, claw machine, capsules). Each big
Arcade Floor game is its own package at the repository root. It runs inside the hub through a thin adapter scene,
and most of them can also run on their own.

Dependencies: Python 3.10+ and `pygame-ce>=2.5` (see `requirements.txt`). Everything else is the standard
library. Tests use `unittest`.

## 2. Repository layout

| Path | What it is |
| --- | --- |
| `arcade_lobby/` | the hub: `main.py` entry point, rooms, profiles/saves, economy, story, UI kit, audio, built-in games, and the hub's tests (`test_*.py`) |
| `retro_racer/` | RETRO RACER (tests sit next to the code: `retro_racer/test_*.py`) |
| `neon_cat_maze/` | NEON CAT MAZE (cabinet id `puzzle_drop`, kept from the machine it replaced so old saves keep their record) |
| `pixel_volleyball/` | CAT VOLLEYBALL (always against the CPU) |
| `cat_territory/`, `cat_minesweeper/` | CAT TERRITORY (`cat_territory` reuses `cat_minesweeper`'s board and mouse input) |
| `galaxy_defender/` | STARFALL ASSAULT |
| `puzzle_maze/` | PUZZLE MAZE (the Dungeon Maze), with its own saves in `puzzle_maze/profiles/` |
| `neon_brawl/` | NEON BRAWL (draws with the hub's `font` module, so its tests need `arcade_lobby/` on `PYTHONPATH`) |
| `design_preview/` | standalone art studies (Miao Meow's look). Not imported by the game |
| `run_tests.py` | runs every test suite headless |
| `docs/` | this guide |

Generated and personal files are git-ignored: `arcade_lobby/saves/`, `arcade_lobby/save_data.json*`,
`puzzle_maze/profiles/`, `puzzle_maze/save*.json`, `review_screenshots/`, `*.log`, caches.

Each package's own `README`/`*_VERIFICATION.md`/`*_REPORT.md` files are its contributor's notes. Most are in
Chinese and some describe earlier versions. They are kept as written.

## 3. Running

```bash
cd arcade_lobby
python main.py                 # normal start: title, profile select, then HOME
python main.py --debug         # debug helpers in the rooms: F5 +10 Tokens, F6 next day, F7 new daily tasks, F8/F9 test items
```

In a `--debug` build the room's helpers take F5–F9. Outside a room, or without `--debug`, F6–F9 are the volume
keys (`settings.DEBUG_KEYS`, `Game._room_debug_key`).

Developer tools in `arcade_lobby/` all use a **temporary** profile and never open `saves/`:

* `play_story.py <stage>` starts at a chosen point of the main story (`new`, `vending`, `ch1`, `trial01`, `ch2`,
  `routes`, `clues`, `solved`, `trial02`; `--keep` continues the last test save). The debug keys are on.
* `play_trial01.py [--fresh]` opens Trial 01 directly. `play_trial02.py [--fresh] [--round 2|3 [--solved]] [--ending]`
  opens Trial 02 at a chosen point.
* `verify_main_story.py` runs headless from the first quest through Chapter 02 with input bots, and writes screenshots to
  `review_screenshots/main_story/`. It walks Trial 01 with `golden_age_testing.Driver`. `unbeaten_testing.py` is the
  matching Trial 02 driver, and `room_testing.goto_room` jumps between rooms without the wipe.
* `audio_diagnostics.py` checks the sound device; `audio_synth.py` rebuilds the generated music files

[MAIN_QUEST_TESTING.md](../arcade_lobby/MAIN_QUEST_TESTING.md) is the full guide to these tools (with spoilers).
`test_essentials.py` checks that every `play_story` stage, both `play_trial` tools and the debug keys still reach the
state they promise, so a change that breaks a shortcut fails the tests.

## 4. Core architecture

### Game loop and scenes

* `game.Game` owns the window (`display.DisplayManager`, always 4:3 with letterboxing), the low-res canvas
  (`VIEW_W`×`VIEW_H`, upscaled), the `AudioManager`, the `SceneManager` and the current `LocalSession`.
  `Game.step(events, dt)` processes one frame. It is separate from `run()` so tests can drive it.
* `scene_base.SceneManager` is a stack of scenes. Only the top scene gets input and updates. `push`/`pop`/`replace`
  run behind a scanline wipe, and input is ignored during the wipe, so a key cannot pop twice.
* `scene_base.BaseScene` is the scene interface: `on_enter`, `on_exit`, `on_resume`, `on_quit`, `handle_event`,
  `update(dt)`, `draw(surface)`. A scene with `full_resolution = True` draws on the window surface instead of the
  pixel canvas (the embedded 800×600 games do this).

### Rooms

* `room_scene.RoomHub` holds the three rooms (`home_room.HomeRoomScene`, `arcade_floor.ArcadeFloorScene`,
  `prize_plaza.PrizePlazaScene`). It builds each one on its first visit and keeps it afterwards. It also holds what
  the rooms share: the player's body, the wallet HUD, ambience and the `story.StoryDirector`.
* `room_scene.BaseRoomScene` is the shared room behaviour: walking, doorways (`travel` refuses while a wipe or a paid
  game is in flight), the single **modal** (dialogue, panel, bag), the [E] prompt, starting and settling games.
* Room furniture is `room.Prop` → `stations.Station` (anything with an [E] prompt and `interact()`) → the concrete
  stations: `PrizeCounter`, `DailyBoard`, the Lucky Corner cabinets (`LuckyCabinet` subclasses), `VendingMachine`,
  `CapsuleStation`, `ClawStation`, `MiaoMeow` and others. Arcade cabinets are `machine.ArcadeMachine`, built from
  the data in `settings.MACHINES` and laid out by `arcade_layout.py`.

### Input

`controls.ControlScheme` maps keys to **actions** (`up/down/left/right`, `interact`, `menu`, `item`, `pause`,
`confirm`, `emote`). There is one scheme, `SOLO_CONTROLS` (WASD and arrows, E/Enter, I). `input_router.PlayerInput`
turns events into actions and tracks held keys. Hub code and minigame adapters read actions, not key codes.
Window-wide keys (F4, F6–F11, M, Q, Tab) are handled in `Game.step` and `BaseRoomScene.handle_event`.

### Sessions and players

`local_session.LocalSession(profile)` is one play session with exactly one `LocalPlayer` (profile + controls +
`player.HubPlayer` body). The `players`/`profiles`/`avatars` accessors are lists of one, so rooms, story and
minigames share one call path. `session.dispatch(GameEvent(...))` delivers gameplay events (game played, secret
found, trial done, ...) to the profile and to listeners such as the story.

## 5. Profiles and saves

* `player_profile.PlayerProfile` is everything one player owns: the wallet, inventory (`inventory.Inventory`),
  daily tasks/rewards, records, cosmetics, decorations, the story state and lifetime-earnings counters. Its state
  changes only through its methods. Each change is announced to subscribers (`subscribe`, `subscribe_events`) and
  triggers an autosave (`subscribe_save`). `with profile.batch():` groups many changes into one save.
* `profile_manager.ProfileManager` manages any number of profiles under `arcade_lobby/saves/`:
  `profiles.json` (index, `INDEX_VERSION = 2`) plus `profiles/<generated-id>.json` (one file per profile,
  `SAVE_VERSION = 2`). `load_profile` returns one shared instance per id, and `save_profile` refuses any other object, so
  one profile can never overwrite another's file.
* Every JSON save (profiles, the index, audio and display preferences) goes through `save_io.write_json_atomic`:
  a temp file and then an atomic rename. A crash mid-write leaves the old file whole. An unreadable profile file is moved
  aside as `<file>.corrupt`, never deleted.
* Migrations run once and keep the originals: the old single-profile `save_data.json` becomes the first profile
  (kept as `save_data.json.migrated`); a v1 index is copied to `profiles.json.pre-single-player`; old stories and
  lifetime counters are upgraded when they are read.
* `save_lock.SaveLock` stops a second copy of the game from opening the same save folder.

## 6. Economy and rewards

* **Tokens** pay for plays; **Tickets** are the reward currency spent at the prize counter. Starting wallet and
  every price, cap and payout live in `settings.py` (the "economy" section).
* Paying to play: `ArcadeMachine.start_play(profile, use_coupon)` takes the cost (or one Free Play Coupon) and
  returns a `rewards.PlaySession`, or `None` if the player cannot pay. When the minigame scene is popped,
  `BaseRoomScene` settles that session **once** with the scene's `get_result()`. If the game never started, it
  refunds the session instead. A settled session ignores every later call.
* `rewards.RewardBundle` (tokens + tickets + items) is pure data. `RewardService.grant()` delivers it, never raises,
  and reports what happened (`RewardGrantResult`). Unknown items or bad amounts are skipped and logged.
* Lifetime counters: Tickets from Arcade Floor games go through `add_tickets` (counted as *earned*). Lucky Corner and
  claw winnings go through the `award_*` methods (counted as *won*). Refunds and the staff panel go through neither.
  A new payout must use exactly one of these methods. Story milestones read these counters, never the wallet.
* Items are defined once in `item_registry.ITEM_REGISTRY` (ids are stable save keys).

## 7. Minigames

### How a minigame plugs in

1. Subclass `minigame.MinigameScene`. Its constructor takes `(game, machine)`.
2. Read input from `self.input` (actions, see *Input*). Use `self.is_confirm(event, action)` for "OK" presses
   and `self.sound_bus()` to play effects through the hub mixer.
3. Report the outcome: either override `get_reward()` (returns `RewardResult(machine.id, tickets, score)`) or
   override `get_result()` and return a `MiniGameResult` of one `PlayerResult`. `get_result()` must be
   **idempotent**: return the same result however often it is called. Pay the best run of the visit, so restarts
   cannot pay twice.
4. Leave with `self.game.scenes.pop()`, and set a `leaving` flag so no further input is processed.
5. Stop the game's own sounds in `on_exit` and `on_quit`. Pause on `pygame.WINDOWFOCUSLOST`.
6. Register the scene class in `scenes.MINIGAME_SCENES` under the machine's `game_id`, and add the cabinet to
   `settings.MACHINES`. Machines without a registered scene open `MinigamePlaceholderScene`.

### The existing adapters

| Cabinet | Adapter (arcade_lobby) | Package |
| --- | --- | --- |
| RETRO RACER | `retro_racer_scene.RetroRacerScene` | `retro_racer` |
| NEON CAT MAZE | `cat_maze_scene.CatMazeScene` | `neon_cat_maze` |
| CAT VOLLEYBALL | `pixel_volleyball_scene.PixelVolleyballScene` | `pixel_volleyball` |
| CAT TERRITORY | `cat_territory_scene.CatTerritoryScene` | `cat_territory` |
| STARFALL ASSAULT | `galaxy_defender_scene.GalaxyDefenderScene` | `galaxy_defender` |
| PUZZLE MAZE | `puzzle_maze.lobby_scene.PuzzleMazeScene` | `puzzle_maze` |
| NEON BRAWL | `neon_brawl_scene.NeonBrawlScene` | `neon_brawl` |

The adapter owns input mapping, audio routing and settlement. The package owns the rules, drawing and its own
menus. Each package's keys and screens stay its own. The adapters share only the base-class helpers above.

The hub's own small games (Lucky Corner: `chance_scene`, `neon21_scene`, `coin_pusher_scene`, `pinball_scene`;
`claw_scene`; `capsule_ui`) pay through the profile's `award_*` methods with their own daily caps.

## 8. Story

* Quests, chapters, secret items and trials are **data** in `quests.py` (`QUESTS`, `CHAPTERS`, `SECRET_ITEMS`,
  `TRIALS`). `quests.QuestManager` advances them from `GameEvent`s and keeps the state in `PlayerProfile.story`.
* `story.StoryDirector` (one per `RoomHub`) owns the `QuestManager`, Miao Meow's behaviour, the quest UI
  (`quest_ui.py`: tracker, banner, Q log), dialogue (`story_dialogue.py`) and the opening cutscene. Rooms ask it only
  a few things (`update`, `draw_*`, `modal`, `locked`, `toggle_log`, ...).
* Trial rooms are scenes opened from `legacy_terminal.py`: Trial 01 is `golden_age_scene.py` and Trial 02 is
  `unbeaten_scene.py`. Each has a rules module, a content module (text), an art module, a UI module and a `*_testing.py`
  driver for tests. Completing a trial dispatches `secret_trial_done` once and unseals its Memory Fragment flag.
* Content that is **not built yet**: Trial 03 and the final "reopen the arcade" event. Their quests exist as data
  but nothing fires them.
* Treat every hidden interaction, flag and asset as intentional. Before removing something that looks unused, search
  for its string id. Many are reached only through story flags, `getattr` dispatch or the other packages.

## 9. Audio, assets, UI kit

* `audio_manager.AudioManager`: music themes per scene (`Game.music_for`), effect channels, ducking, saved
  volumes (`saves/audio.json`). Sounds are built or loaded once and cached. With no audio device the game stays
  silent instead of crashing.
* `font.get_font()` is the hub's pixel font, with rendered text cached. `ui.py`, `menu_kit.py` and `gfx.py` hold the shared panels,
  text and colour helpers. `settings.Col` is the palette.
* Most art is drawn in code and cached (`@cached`/`lru_cache` helpers in the `*_art.py` modules).
  `arcade_lobby/assets/` holds the music, ambience and cat voice files.

## 10. Running the tests

```bash
python run_tests.py                     # everything: about 300 tests, under a minute
python run_tests.py arcade_lobby        # one or more suites by name
python run_tests.py -j 4 -v             # 4 processes at a time, full output of failures
```

`run_tests.py` uses SDL's dummy video and audio drivers (no window, no sound) and puts the repository root and
`arcade_lobby/` on `PYTHONPATH`. To run one module by hand:

```bash
cd arcade_lobby && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest test_essentials
cd neon_brawl/tests && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=../..:../../arcade_lobby python -m unittest discover
```

Tests create temporary profiles (`tempfile`) or unmanaged in-memory profiles. Never point a test at
`arcade_lobby/saves/` or `puzzle_maze/profiles/`.

The suite is deliberately small: smoke and regression tests for what would hurt most if it broke. The full story is
checked by running `verify_main_story.py`.

| Module | What it guards |
| --- | --- |
| `arcade_lobby/test_essentials.py` | the game starts; doorways; every cabinet opens its real game, charges once and pays once; no charge without Tokens; the `--debug` keys (and the F6–F9 volume-key regression); every `play_story` stage; `play_trial01`/`play_trial02` at each documented point; a trial completes once and unseals one Memory Fragment |
| `arcade_lobby/test_profiles.py` | profile create / load / save, the index, migration of old saves, corrupt and unwritable files |
| `arcade_lobby/test_save_lock.py` | a second copy of the game cannot open the same save folder |
| `arcade_lobby/test_rewards.py` | `RewardService`, `PlaySession` pay-once / refund-once, the room's settlement |
| `arcade_lobby/test_chapters.py` | chapter order, Secret Item and trial gating |
| `arcade_lobby/test_lifetime_earnings.py` | the lifetime counters that open trials (spending never relocks) |
| `arcade_lobby/test_scene_wipe.py` | the scene stack and its transition |
| `arcade_lobby/test_maze45_secret.py` | the Dungeon Maze's Secret Item 03 reaches the story once |
| `<package>/tests/...`, `retro_racer/test_tracks.py` | one core module per game package (rules, model or game flow) |
| `puzzle_maze/tests/test_v45_remaster.py`, `test_migration.py` | Puzzle Maze save migration and its Secret Item 03 discovery (`test_v3_campaign.py` stays because the remaster test reuses it) |

When you fix a serious bug, add one regression test for it to the closest module. Prefer one test that plays the
real flow over many small ones.

## 11. OOP concepts in the project

| Concept | Where to look |
| --- | --- |
| **Encapsulation** | `PlayerProfile` changes its wallet and inventory only through methods (`spend_tokens` refuses when the player cannot pay, `Inventory.add_item` validates). `PlaySession` hides its `_settled` flag, so a play can be paid or refunded only once. |
| **Abstraction** | `BaseScene` and `MinigameScene` are contracts the hub relies on without knowing the game. `ControlScheme` hides key codes behind actions. `GameSoundBus` hides the mixer. |
| **Inheritance** | `BaseScene` → `MinigameScene` → each adapter; `BaseRoomScene` → the three rooms; `Prop` → `Station` → `LuckyCabinet` → `Neon21Station`, `CoinPusherStation`, `PinballStation`, ... |
| **Polymorphism** | `SceneManager` calls `update`/`draw`/`on_exit` on whatever scene is on top. Rooms call `station.interact()` on any station. The room settles any minigame through `get_result()`. |
| **Composition** | `Game` has a `SceneManager`, `AudioManager`, `DisplayManager`, `LocalSession`; `RoomHub` has rooms and a `StoryDirector`; `PlayerProfile` has an `Inventory` and daily managers; each adapter *has* its package's game object instead of inheriting from it. |
| **Adapter pattern** | `*_scene.py` adapters translate hub input, audio and rewards for the independent game packages. |
| **Observer pattern** | `PlayerProfile.subscribe` (HUD, avatar, decorations), `subscribe_save` (autosave), `LocalSession.add_listener` (the story). |
| **Data-driven design** | `settings.MACHINES`, `item_registry.ITEM_REGISTRY` and `quests.QUESTS`: adding a cabinet, an item or a quest is data, not new classes. |
| **Separation of responsibilities** | The game packages work out their own scores and ticket payouts but never touch the wallet or the hub's profile files. The adapters translate. `RewardService` delivers rewards. `ProfileManager` stores profiles. |
