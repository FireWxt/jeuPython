# reward_defensive.py
from config import size, heuristic

def compute_reward(unit, action_str, old_state, new_state, objectives, units):
    """
    IA défensive : maintien de position sur objectif jusqu'à ce qu'une menace soit détectée.
    """
    reward = 0
    reason = ""

    # Détection des ennemis à proximité
    enemies = [u for u in units if u.color != unit.color]
    threat_detected = any(heuristic((unit.x, unit.y), (e.x, e.y)) <= 1 for e in enemies)

    # Maintien sur objectif
    on_objective = any(unit.x == obj['x'] and unit.y == obj['y'] for obj in objectives)
    if on_objective:
        unit.hold_counter = getattr(unit, "hold_counter", 0) + 1
        reward += 5
        reason = f"HOLD({unit.x},{unit.y}):+5"
        if not threat_detected:
            return reward, reason

    # Action d'attaque
    if action_str.startswith("ATTACK") and threat_detected:
        _, x, y = action_str.split("_")
        x, y = int(x), int(y)
        target = next((u for u in units if u.x == x and u.y == y and u.color != unit.color), None)
        if target:
            if target.pv <= 0 or target not in units:
                reward += 5
                reason = f"KILL({unit.x},{unit.y})->({x},{y}):+5"
            else:
                reward += 2
                reason = f"DAMAGE({unit.x},{unit.y})->({x},{y}):+2"

    # Déplacement
    elif not action_str.startswith("ATTACK"):
        action = eval(action_str)
        new_x, new_y = unit.x + action[0], unit.y + action[1]
        if 0 <= new_x < size and 0 <= new_y < size:
            # Se rapprocher d'une menace
            if threat_detected and enemies:
                nearest_enemy = min(enemies, key=lambda e: heuristic((unit.x, unit.y), (e.x, e.y)))
                dist_before = heuristic((unit.x, unit.y), (nearest_enemy.x, nearest_enemy.y))
                dist_after = heuristic((new_x, new_y), (nearest_enemy.x, nearest_enemy.y))
                if dist_after < dist_before:
                    reward += 1
                    reason = f"MOVE_TOWARDS_THREAT({unit.x},{unit.y})->({new_x},{new_y}):+1"
            # Se rapprocher d'un objectif
            if not on_objective and objectives:
                nearest_obj = min(objectives, key=lambda o: heuristic((unit.x, unit.y), (o['x'], o['y'])))
                dist_before = heuristic((unit.x, unit.y), (nearest_obj['x'], nearest_obj['y']))
                dist_after = heuristic((new_x, new_y), (nearest_obj['x'], nearest_obj['y']))
                if dist_after < dist_before:
                    reward += 1
                    reason = f"MOVE_CLOSER_OBJ({unit.x},{unit.y})->({new_x},{new_y}):+1"

    # Abandon d’objectif
    if getattr(unit, "on_objective_last_turn", False) and not on_objective:
        reward -= 3
        reason = f"LEAVE_POINT({unit.x},{unit.y}):-3"

    return reward, reason
