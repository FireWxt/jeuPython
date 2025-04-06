# config.py

tile_size = 30
size = 20
width, height = size * tile_size, size * tile_size
interface_height = 100

PASSABLE_COLOR = (200, 200, 200)
PLAYER_COLOR = (0, 0, 255)
PLAYER_COLOR_LIGHT = (100, 100, 255)
ENEMY_COLOR = (255, 0, 0)
ENEMY_COLOR_LIGHT = (255, 100, 100)
SELECTED_COLOR = (0, 255, 0)
OBJECTIVE_MAJOR_COLOR = (255, 255, 0)
OBJECTIVE_MINOR_COLOR = (255, 215, 0)
BACKGROUND_COLOR = (50, 50, 50)
TEXT_COLOR = (255, 255, 255)
BUTTON_COLOR = (100, 100, 100)
BUTTON_HOVER_COLOR = (150, 150, 150)
def heuristic(a, b):
    """
    Calcule la distance de Manhattan entre les positions 'a' et 'b'.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
