"""Rebuild original chiptune stems with the arcade's offline synthesizer.
Run from repository root: PYTHONPATH=arcade_lobby .venv/bin/python -m neon_brawl.build_audio
"""
from pathlib import Path
from audio_synth import Mix, hz, write_wav

def build():
    output=Path(__file__).resolve().parents[1]/'arcade_lobby/assets/music'
    for stage,(root,bpm) in enumerate(((45,112),(42,124),(44,136),(40,148))):
        beat=60/bpm; m=Mix(beat*32)
        for step in range(128):
            t=step*beat/4; chord=(0,0,5,7)[step//32]
            bass=root+chord+(12 if step%4==2 else 0)
            if step%2==0: m.note(t,beat*.35,hz(bass),'tri',.24)
            arp=(0,7,12,15,19,12,7,3)[step%8]
            m.note(t,beat*.16,hz(root+24+chord+arp),'p12',.045)
            if step%4==0: m.kick(t,.16)
            if step%8==4: m.noise(t,.10,.13,decay=27,seed=step+31)
            m.noise(t,.035,.035,decay=85,seed=step)
            if step%8==0:
                melody=(12,15,19,22,19,15,14,7,12,19,24,22,19,15,14,10)[step//8]
                m.note(t,beat*.8,hz(root+24+melody),'p25',.075,vibrato=5)
        write_wav(str(output/f'neon_brawl_{stage}.wav'),m.finish(rms=-18,lowpass=.18))
if __name__=='__main__': build()
