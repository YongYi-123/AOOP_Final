# Neon Corner Arcade

A small top-down pixel-art arcade hub with a neon, cat-filled atmosphere. You walk between three connected
rooms (**HOME**, the **ARCADE FLOOR** and the **PRIZE PLAZA**), play arcade cabinets for Tickets, try your luck in
the Lucky Corner, collect prizes and decorate your room. A local cast of cats keeps you company, and the arcade has
a story of its own for players who look closely.

This is a university project for the Advanced Object-Oriented Programming course (NYCU).

## Requirements

* Python 3.10 or newer (developed on 3.12)
* [pygame-ce](https://pyga.me/) 2.5 or newer (the community edition of pygame; do **not** install it alongside
  the original `pygame` package)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Starting the game

```bash
cd arcade_lobby
python main.py
```

The first screen lets you create a profile or continue one. Every profile keeps its own Tokens, Tickets, prizes,
records and story progress. Saves are written to `arcade_lobby/saves/` automatically after each change.

Options: `python main.py --style neon_lofi|lofi|neon` picks a visual style (default `neon_lofi`).

## Controls

| Key | Action |
| --- | --- |
| W A S D / arrow keys | walk, move through menus |
| E / Enter | use, talk, confirm |
| I | open the bag (inventory); pauses inside a minigame |
| Esc | back / close / leave a minigame |
| Q | Quest Log |
| Tab | fold or open the quest tracker |
| T | emote |
| F4 | audio settings |
| F6 / F7, F8 / F9 | music volume down / up, effects volume down / up |
| M | mute |
| F11 or Alt+Enter | fullscreen |

Each minigame shows its own keys on screen.

## What is inside

* **Arcade Floor cabinets:** Retro Racer, Neon Cat Maze, Cat Volleyball, Cat Territory, Starfall Assault,
  Puzzle Maze and Neon Brawl. A play costs Tokens and pays out Tickets.
* **Prize Plaza:** the prize counter, the capsule corner, a claw machine, a showcase of what you have won, and the
  **Lucky Corner** with its bonus games (NEON 21, a coin pusher, pinball and more).
* **Home:** your wardrobe, room decorations, your collection and the daily board with daily challenges and rewards.

There is more to the arcade than its menus show. The story is meant to be discovered, so this README
deliberately says nothing about it.

## For developers

Architecture, save format, the economy, how to add a minigame and how to run the tests are covered in
[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md). Run every test suite with:

```bash
python run_tests.py
```
