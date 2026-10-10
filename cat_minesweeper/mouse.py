"""Convert window pixels to the 400x300 canvas used by both launch modes."""


class MineMouseInput:
    @staticmethod
    def canvas_position(point, screen_size):
        width, height = screen_size
        return (int(point[0] * 400 / width), int(point[1] * 300 / height))
