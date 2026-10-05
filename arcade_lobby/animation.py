"""Tiny frame-animation system shared by the player, the cat and the machines.

Frames can be anything (usually Surfaces, sometimes plain indices); the
classes here only handle timing, so no sprite class re-implements it.
"""


class Animation:
    """A list of frames played at a fixed rate, looping or one-shot."""

    def __init__(self, frames, frame_duration=0.1, loop=True):
        self.frames = list(frames)
        self.frame_duration = frame_duration
        self.loop = loop
        self.reset()

    def reset(self):
        self.time = 0.0
        self.current_frame = 0
        self.finished = False

    def update(self, dt):
        if self.finished:
            return
        self.time += dt
        while self.time >= self.frame_duration:
            self.time -= self.frame_duration
            if self.current_frame + 1 < len(self.frames):
                self.current_frame += 1
            elif self.loop:
                self.current_frame = 0
            else:
                self.finished = True
                self.time = 0.0
                break

    @property
    def image(self):
        return self.frames[self.current_frame]


class AnimationController:
    """Owns a set of named animations and plays one at a time."""

    def __init__(self, animations, start):
        self.animations = animations
        self.name = start
        self.current = animations[start]

    def play(self, name, sync=False):
        """Switch animation. With sync=True the frame/time carry over, so e.g.
        turning while walking doesn't restart the walk cycle."""
        if name == self.name:
            return
        old = self.current
        self.name = name
        self.current = self.animations[name]
        self.current.reset()
        if sync:
            self.current.current_frame = old.current_frame % len(self.current.frames)
            self.current.time = old.time

    def update(self, dt):
        self.current.update(dt)

    @property
    def image(self):
        return self.current.image

    @property
    def frame_index(self):
        return self.current.current_frame


class AnimatedSprite:
    """Base class for anything with a main AnimationController."""

    def __init__(self, animations, start):
        self.anim = AnimationController(animations, start)

    @property
    def image(self):
        return self.anim.image

    # Draw passes used by the room scene (override as needed)
    def draw_under(self, surf):
        """Drawn on the floor before any sprites (shadows, reflections)."""

    def draw_glow(self, surf):
        """Drawn additively after the room lighting (neon halos)."""
