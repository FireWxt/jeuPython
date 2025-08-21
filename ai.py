from config import *
import random


def find_attackable_player_unit(ai_unit, units):
    """
    Renvoie une unité du joueur que 'ai_unit' peut attaquer.
    Amélioration : On choisit en priorité l'ennemi le plus faible (peu de HP),
    puis le plus proche.
    """
    possible_targets = []
    for u in units:
        if u.color == PLAYER_COLOR:
            if ai_unit.can_move(u.x, u.y):  # portée d'attaque
                possible_targets.append(u)
    if not possible_targets:
        return None
    # Tri par (HP, distance)
    return min(
        possible_targets,
        key=lambda p: (p.hp, heuristic((ai_unit.x, ai_unit.y), (p.x, p.y)))
    )


def ai_turn(units, objectives, grid):
    """
    IA améliorée :
    1. Attaque en priorité si un joueur est à portée.
    2. Si l'unité est faible, elle se replie.
    3. Sinon, elle tente de contrôler les objectifs (majeurs > mineurs).
    4. Défense : au moins une unité garde chaque objectif.
    5. Les unités restantes se regroupent.
    6. Un peu d'aléa pour éviter un comportement trop prévisible.
    """

    def ai_unit_on_objective(obj):
        # Amélioration : on retourne la liste des défenseurs IA sur l'objectif
        return [u for u in units if u.x == obj['x'] and u.y == obj['y'] and u.color == ENEMY_COLOR]

    def get_closest_free_ai_unit_for(obj):
        free_ai_units = [u for u in units if u.color == ENEMY_COLOR and not u.moved]
        if not free_ai_units:
            return None
        return min(free_ai_units, key=lambda u: heuristic((u.x, u.y), (obj['x'], obj['y'])))

    def objective_value(obj):
        # Amélioration : donner une valeur plus forte aux objectifs majeurs
        return 10 if obj['type'] == 'MAJOR' else 5


    # PHASE 1 : Attaque
    
    for unit in units:
        if unit.color == ENEMY_COLOR and not unit.moved:

            # Amélioration : retraite si unité trop faible
            if unit.hp <= 1:
                nearest_obj = min(objectives, key=lambda o: heuristic((unit.x, unit.y), (o['x'], o['y'])))
                unit.move_towards_goal((nearest_obj['x'], nearest_obj['y']), grid)
                unit.moved = True
                continue


            target = find_attackable_player_unit(unit, units)
            if target:
                unit.attack(target, units, objectives)
                unit.moved = True

    
    # PHASE 2 : Contrôle des objectifs

    for obj in sorted(objectives, key=objective_value, reverse=True):
        defenders = ai_unit_on_objective(obj)
        if not defenders:  # objectif libre
            closest_unit = get_closest_free_ai_unit_for(obj)
            if closest_unit:
                closest_unit.move_towards_goal((obj['x'], obj['y']), grid)
                closest_unit.moved = True
        else:
            # Amélioration : une unité reste en défense
            defenders[0].moved = True

    
    # PHASE 3 : Défense / leftover
    
    leftover_units = [u for u in units if u.color == ENEMY_COLOR and not u.moved]
    if leftover_units:
        # Amélioration : point de rassemblement = moyenne des positions
        avg_x = sum(u.x for u in leftover_units) // len(leftover_units)
        avg_y = sum(u.y for u in leftover_units) // len(leftover_units)
        rally_point = (avg_x, avg_y)

        for unit in leftover_units:
            # Amélioration : petit facteur d'aléa (20% de chance de se déplacer ailleurs)
            if random.random() < 0.2:
                rand_pos = (unit.x + random.choice([-1, 1]), unit.y + random.choice([-1, 1]))
                unit.move_towards_goal(rand_pos, grid)
            else:
                unit.move_towards_goal(rally_point, grid)
            unit.moved = True
