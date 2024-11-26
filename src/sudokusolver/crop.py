"""Crop functions - Functions to crop Surfaces."""

# Programmed by CoolCat467

__title__ = "Crop Functions"
__author__ = "CoolCat467"
__version__ = "0.0.0"

from pygame.color import Color
from pygame.rect import Rect
from pygame.surface import Surface


def crop_color(surface: Surface, color: Color) -> Surface:
    """Crop out color from surface."""
    w, h = surface.get_size()

    surf = surface.copy().convert_alpha()
    surf.fill(Color(0, 0, 0, 0))

    area = Rect(0, 0, 0, 0)
    surf.lock()
    y_inter = False
    x_inter = False
    for y in range(h):
        for x in range(w):
            value = surface.get_at((x, y))
            if value == color:
                if not y_inter:
                    area.top = y
                else:
                    area.bottom = y
                if not x_inter:
                    area.left = x
                else:
                    area.right = x
            else:
                if not y_inter:
                    y_inter = True
                if not x_inter:
                    x_inter = True
                surf.set_at((x, y), value)
    surf.unlock()
    final = Surface(area.size)
    final.blit(surf, (0, 0), area=area)
    return surf


def run() -> None:
    """Run test of module."""


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    run()
