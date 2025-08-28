# config.py

tile_size = 30
size = 20
width, height = size * tile_size, size * tile_size
interface_height = 100

# --- Rewards orientés objectifs ---
OBJ_ENTER = 12.0     # bonus : entrer sur un objectif
OBJ_HOLD  = 6.0      # bonus : rester (action (0,0)) sur un objectif
OBJ_STAY  = 3.0      # bonus : être sur objectif en fin d'action
OBJ_LEAVE = -8.0     # malus : quitter un objectif

DMG_REWARD  = 0.2    # bonus dégât (faible)
KILL_REWARD = 0.4    # bonus kill (faible)

CLOSER_OBJ  = 0.8    # se rapprocher d'un objectif
FARTHER_OBJ = -0.8   # s'en éloigner

# Biais heuristique lors du choix d'action (favorise les objectifs)
PRIOR_BETA = 0.8     # mets 0.0 pour désactiver

# (Optionnel) Gate des attaques au début de partie
ATTACK_GATING_TURNS = 8  # 0 pour désactiver

# (Optionnel) Pénalité de temps si trop de tours (pour finir plus vite)
TURN_PENALTY_START = 80
TIME_PENALTY_PER_ACTION = 0.5
TIME_PENALTY_GROWTH = 0.02
MAX_TIME_PENALTY = 2.0


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
