"""Audio diagnostics for Neon Corner Arcade.

    python audio_diagnostics.py            report + play a short test sound and the hub theme
    python audio_diagnostics.py --silent   report only (no sound)
    python audio_diagnostics.py --seconds 6   how long to let the music play (default 4)

It uses the same AudioManager and the same saved settings (saves/audio.json) as the
game, on the real output device (it never selects the dummy driver), and ends with a
verdict that separates: engine failure, missing music files, muted/zero volume, and
(on WSL) a missing libpulse / unreachable WSLg sound server.
"""
import argparse
import ctypes
import logging
import os
import shutil
import sys
import time

import pygame

from audio_manager import AudioManager, MUSIC_FILES
from settings import SAVES_DIR


def wsl_notes():
    notes = []
    if "microsoft" not in (os.uname().release.lower() if hasattr(os, "uname") else ""):
        return notes
    sock = os.environ.get("PULSE_SERVER", "/mnt/wslg/PulseServer").replace("unix:", "")
    notes.append(f"WSL detected. Pulse socket {sock}: {'present' if os.path.exists(sock) else 'MISSING (is WSLg enabled? run `wsl --update` in Windows)'}")
    try:
        ctypes.CDLL("libpulse.so.0")
        notes.append("libpulse.so.0: found")
    except OSError:
        notes.append("libpulse.so.0: NOT INSTALLED -> sudo apt install libpulse0")
    notes.append("Windows side: check the volume mixer, the default output device, and that nothing is muted.")
    return notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--silent", action="store_true", help="report only; play nothing")
    ap.add_argument("--seconds", type=float, default=4.0, help="how long to play the hub theme")
    ap.add_argument("--all", action="store_true", help="also play every room and minigame theme in turn (--seconds each)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="  log: %(levelname)s %(message)s")

    prefs = os.path.join(SAVES_DIR, "audio.json")
    audio = AudioManager(prefs_path=prefs)
    st = audio.status()
    print("== Neon Corner Arcade audio diagnostics ==")
    print(f"SDL_AUDIODRIVER env : {os.environ.get('SDL_AUDIODRIVER') or '(unset: SDL picks)'}")
    print(f"Selected driver     : {st['driver']}")
    print(f"Mixer initialised   : {'YES ' + str(st['mixer']) if st['mixer'] else 'NO'}")
    try:
        from pygame._sdl2 import audio as sdl_audio
        print(f"Output devices      : {sdl_audio.get_audio_device_names(False) or '(none listed)'}")
    except Exception as exc:           # noqa: BLE001 - diagnostic: report, don't hide
        print(f"Output devices      : unavailable ({exc})")
    if st["init_error"]:
        print(f"Init error          : {st['init_error']}")
    print(f"Settings file       : {prefs} ({'exists' if os.path.exists(prefs) else 'absent -> defaults'})")
    print(f"Music volume        : {st['music_volume']:.0%}  (effective {st['effective_music']:.0%})")
    print(f"SFX volume          : {st['sfx_volume']:.0%}  (effective {st['effective_sfx']:.0%})")
    print(f"Muted               : {st['muted']}")
    print(f"Music ducked (pause): {st['duck']:.0%}   watchdog restarts: {st['recoveries']}")
    print(f"Themes              : {', '.join(MUSIC_FILES)}")
    print(f"Missing music files : {st['missing_music'] or 'none'}")
    print(f"Missing SFX files   : {st['missing_sfx'] or 'none'}")
    for line in wsl_notes():
        print("  " + line)

    problems = []
    if not audio.enabled:
        problems.append("AUDIO ENGINE FAILURE: the mixer could not open an output device (see Init error above).")
    if st["missing_music"]:
        problems.append(f"MISSING MUSIC ASSETS: {', '.join(st['missing_music'])} (a quiet synthesized stand-in plays).")
    if st["muted"]:
        problems.append("MUTED in saved settings: press M in the game (or delete saves/audio.json).")
    if st["music_volume"] <= 0.01:
        problems.append("MUSIC VOLUME is 0 in saved settings: press F7 in the game (or delete saves/audio.json).")

    if audio.enabled and not args.silent:
        print("\nPlaying test chord ...")
        audio.test_tone()
        time.sleep(0.9)
        print(f"Playing the hub theme for {args.seconds:g}s (use --seconds 30 to also exercise the device-stall check) ...")
        audio.switch("lobby")
        end = time.time() + args.seconds
        playing = False
        while time.time() < end:
            audio.update(0.05)
            playing = playing or audio.music_playing()
            time.sleep(0.05)
        print(f"Mixer reports music channel busy: {playing}   current track: {audio.theme}")
        st2 = audio.status()
        print(f"Device liveness (silent probe): {st2['device_state']}  last probe {st2['probe_ms']} ms  "
              f"stalls {st2['device_stalls']}  mixer reopens {st2['reopens']}")
        if st2["device_stalls"]:
            problems.append("AUDIO DEVICE STALLS: the sound device stopped consuming samples while the mixer still reported "
                            "playback; the game reopens the mixer to recover. On WSL this is the WSLg audio bridge: run "
                            "'wsl --update', then 'wsl --shutdown' from Windows, and check the Windows output device.")
        if args.all:
            for theme in MUSIC_FILES:
                audio.switch(theme)
                end = time.time() + args.seconds
                while time.time() < end:
                    audio.update(0.05)
                    time.sleep(0.05)
                print(f"  {theme:18s} playing={audio.music_playing()}  file={MUSIC_FILES[theme]}.wav")
        if audio.last_error:
            problems.append(f"PLAYBACK ERROR: {audio.last_error}")
        audio.stop()
        print("\nDid you HEAR the chord and the music? If not, while the mixer reports OK, the problem is\n"
              "OUTPUT ROUTING (wrong default device, Windows volume/mute, WSLg), not the game.")
    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  - " + p)
        return 1
    print("No software problem found." if audio.enabled else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
