# ai_manager.py

from config import *

def find_attackable_player_unit(ai_unit, units):
    """
    Renvoie une unité du joueur que 'ai_unit' peut attaquer
    (ici on considère que 'ai_unit.can_move(x, y)' = portée d'attaque).
    """
    possible_targets = []
    for u in units:
        if u.color == PLAYER_COLOR:
            if ai_unit.can_move(u.x, u.y):
                possible_targets.append(u)
    if not possible_targets:
        return None
    # On choisit la plus proche
    return min(possible_targets, key=lambda p: heuristic((ai_unit.x, ai_unit.y), (p.x, p.y)))


def ai_turn(units, objectives, grid):
    """
    IA qui attaque en priorité si un joueur est à portée,
    sinon contrôle/défend les objectifs majeurs et mineurs.
    """
    major_obj = [obj for obj in objectives if obj['type'] == 'MAJOR']
    minor_objs = [obj for obj in objectives if obj['type'] == 'MINOR']

    def ai_unit_on_objective(obj):
        return any(u.x == obj['x'] and u.y == obj['y'] and u.color == ENEMY_COLOR for u in units)

    def get_closest_free_ai_unit_for(obj):
        free_ai_units = [u for u in units if u.color == ENEMY_COLOR and not u.moved]
        if not free_ai_units:
            return None
        return min(free_ai_units, key=lambda u: heuristic((u.x, u.y), (obj['x'], obj['y'])))

    # PHASE 1 : Attaque
    for unit in units:
        if unit.color == ENEMY_COLOR and not unit.moved:
            target = find_attackable_player_unit(unit, units)
            if target:
                unit.attack(target, units, objectives)
                unit.moved = True  # Action consommée

    # PHASE 2 : Contrôle objectifs
    # Majeur d'abord...
    for obj in major_obj:
        if not ai_unit_on_objective(obj):
            closest_unit = get_closest_free_ai_unit_for(obj)
            if closest_unit:
                closest_unit.move_towards_goal((obj['x'], obj['y']), grid)

    # ...puis mineurs
    for obj in minor_objs:
        if not ai_unit_on_objective(obj):
            closest_unit = get_closest_free_ai_unit_for(obj)
            if closest_unit:
                closest_unit.move_towards_goal((obj['x'], obj['y']), grid)

    # PHASE 3 : Défense / leftover
    leftover_units = [u for u in units if u.color == ENEMY_COLOR and not u.moved]
    if leftover_units:
        for unit in leftover_units:
            if objectives:
                nearest_obj = min(objectives, key=lambda o: heuristic((unit.x, unit.y), (o['x'], o['y'])))
                unit.move_towards_goal((nearest_obj['x'], nearest_obj['y']), grid)
