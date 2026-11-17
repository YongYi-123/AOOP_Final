# Pixel character and combat polish verification

The final artwork is drawn on a new 32×32 grid and displayed with nearest-neighbor 2× scaling, including bosses. NOVA retains cyan hair, headphones and scarf; fast, normal, heavy and boss silhouettes have separate hair, clothing and equipment. No background files, controls, save schema, hitboxes, attack damage, attack timing or ticket rules changed.

Arms use two rigid three-pixel bones. Eight visual samples follow each attack's actual windup, active interval and character-specific recovery. Anticipation never displays an active pose. New visual feedback includes tiny star impacts, short punch crescents, heavy ground arcs, cyan special rings, dodge ghosts, jump dust, squeezed hurt eyes, floor-anchored tumbles and combo labels. Existing 45ms hit-stop is preserved. Powerful hits add a 120ms arena-only shake of one or two pixels; HUD and control text remain fixed.

The requested balance change is isolated to boss entry: continuing after wave 2 now grants 65 HP instead of 35, capped at maximum health. Ordinary checkpoints still grant 35 HP. This applies to all three stages and cannot be claimed twice by repeating `advance()`.

## Automated results

95 tests passed: 78 Brawl tests (including 13 new polish tests) and 17 Lobby integration tests. These cover ordinary-input campaign completion for all three characters, stage and boss progression, controls, payment and settlement, recovery and invulnerability, attack-window sampling, fixed bone lengths, all fighter poses and both facings, canvas containment, alpha preservation, cached-sprite immutability, effect clipping and lifetime, stable HUD during shake, and boss-entry healing boundaries.

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m unittest neon_brawl.tests.test_combat neon_brawl.tests.test_evolution neon_brawl.tests.test_environment_expansion neon_brawl.tests.test_street_life neon_brawl.tests.test_research_complex neon_brawl.tests.test_character_polish test_neon_brawl -q
```

`git diff --check` passed.

## Render verification and limits

Ran the actual `BrawlGame` drawing and keyboard/update flow with SDL's dummy video driver. Inspected character/outfit sheets, NOVA's eight-frame pose sheet, staged punch and special encounters, and boss warning/attack/recovery screenshots. These are offscreen visual checks and automated inputs, not a human desktop playthrough. The standalone preview window is provided but was not manually played.

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_combat
PYTHONPATH=arcade_lobby:. .venv/bin/python -m neon_brawl.review_combat --play
```

Output: `/tmp/brawl-combat-review`. The final staged render benchmark averaged 1.07ms per native 400×300 frame across 240 frames on this environment; this excludes real display presentation and is not a gameplay FPS measurement. The preview starts at character selection with NOVA highlighted and does not load saves, charge tokens or award tickets. For production integration, launch `.venv/bin/python arcade_lobby/main.py` and enter NEON BRAWL from the left island of ARCADE FLOOR.
