"""Visual samples follow simulation clocks; no animation changes combat timing."""
from .data import ATTACKS, ROSTER


def attack_phase(name, age, recovery=1):
    attack = ATTACKS[name]
    if age < attack.windup:
        return 'anticipation', max(0, age / attack.windup)
    if age <= attack.windup + attack.active:
        return 'attack', min(1, (age-attack.windup) / attack.active)
    return 'recovery', min(1, (age-attack.windup-attack.active) / (attack.recovery*recovery))


def animation_sample(fighter):
    """Eight crisp poses, with active poses appearing only in the damage window."""
    if not fighter.alive:
        return 'defeated', min(7, int(fighter.defeat_age/.11))
    if fighter.swing:
        swing = fighter.swing
        recovery = ROSTER[fighter.name].recovery if fighter.name in ROSTER else fighter.attack_recovery
        phase, progress = attack_phase(swing.name, swing.age, recovery)
        frame = (min(1, int(progress*2)) if phase == 'anticipation' else
                 2+min(2, int(progress*3)) if phase == 'attack' else 5+min(2, int(progress*3)))
        return swing.name, frame
    if fighter.state in ('hurt', 'knockdown'):
        return fighter.state, min(7, int(fighter.reaction_age/.055))
    if fighter.state == 'dodge':
        return 'dodge', min(7, int((.28-fighter.timer)/.035))
    if fighter.jump > 0:
        return 'airborne', min(7, int(fighter.jump_age/.082))
    state = 'walk' if fighter.state in ('walk', 'approach', 'positioning') else fighter.state
    speed = 13 if fighter.name in ('runner', 'assassin', 'cyber') else 7 if fighter.name in ('bruiser', 'security') else 10
    return state, int(fighter.age*speed) % 8
