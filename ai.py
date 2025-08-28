# ai.py — IA (Q-learning) orientée objectifs

from config import *  # size, couleurs, etc. + (éventuellement) constantes de rewards
import random

# -------------------------------------------------
# Valeurs par défaut si non définies dans config.py
# -------------------------------------------------
def _def(name, val):
    globals()[name] = globals().get(name, val)

# Rewards pro-objectifs
_def("OBJ_ENTER", 12.0)      # entrer sur un objectif
_def("OBJ_HOLD", 6.0)        # rester (action (0,0)) sur objectif
_def("OBJ_STAY", 3.0)        # être sur objectif en fin d'action
_def("OBJ_LEAVE", -8.0)      # quitter un objectif

# Combat (abaissé pour ne pas dominer)
_def("DMG_REWARD", 0.2)
_def("KILL_REWARD", 0.4)

# Shaping distance
_def("CLOSER_OBJ", 0.8)
_def("FARTHER_OBJ", -0.8)

# Prior heuristique (pondère Q lors du choix d'action)
_def("PRIOR_BETA", 0.8)

# Gate des attaques au début de partie (0 pour désactiver)
_def("ATTACK_GATING_TURNS", 8)

# Pénalité de temps (pour éviter les parties longues)
_def("TURN_PENALTY_START", 80)
_def("TIME_PENALTY_PER_ACTION", 0.5)
_def("TIME_PENALTY_GROWTH", 0.02)
_def("MAX_TIME_PENALTY", 2.0)

# -------------------------------------------------
# Helpers objectifs
# -------------------------------------------------
def _on_objective_xy(x, y, objectives):
    """True si (x,y) est une case objectif."""
    return any(obj['x'] == x and obj['y'] == y for obj in objectives)

def _nearest_objective_dist(unit, objectives):
    """Distance de Manhattan au plus proche objectif (0 si aucun)."""
    if not objectives:
        return 0
    return min(abs(obj['x'] - unit.x) + abs(obj['y'] - unit.y) for obj in objectives)

# -------------------------------------------------
# Q-learning primitives
# -------------------------------------------------
def choose_action(state, unit, units, Q, eps: float = 0.1, objectives=None, grid=None, turn_count=None):
    """
    Construit l'espace d'actions légal du moment puis sélection ε-greedy
    sur (Q + PRIOR_BETA * prior_heuristique).

    Actions proposées :
      - déplacements: (0,1),(0,-1),(1,0),(-1,0),(0,0)      (0,0) = rester
      - attaques:     "ATTACK_x_y" pour chaque ennemi à portée (can_move)
    """
    # 1) Mouvements légaux
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)]
    move_actions = []
    for dx, dy in directions:
        nx, ny = unit.x + dx, unit.y + dy
        if dx == 0 and dy == 0:
            move_actions.append(str((dx, dy)))  # rester est toujours autorisé
            continue
        if 0 <= nx < size and 0 <= ny < size:
            # si tu as un terrain bloquant, ajoute: and grid[ny][nx] == 1
            if not any(u.x == nx and u.y == ny for u in units):
                move_actions.append(str((dx, dy)))

    # 2) Attaques
    attack_actions = []
    for enemy in (u for u in units if u.color != unit.color):
        if unit.can_move(enemy.x, enemy.y):
            attack_actions.append(f"ATTACK_{enemy.x}_{enemy.y}")

    # Gate des attaques sur les premiers tours si on n'est pas déjà sur obj
    on_obj_now = _on_objective_xy(unit.x, unit.y, objectives or [])
    if turn_count is not None and turn_count < ATTACK_GATING_TURNS and not on_obj_now:
        attack_actions = []

    actions_str = move_actions + attack_actions
    if not actions_str:
        actions_str = [str((0, 0))]

    # 3) Init Q[state] + cases d'action manquantes
    if state not in Q:
        Q[state] = {}
    for a in actions_str:
        if a not in Q[state]:
            Q[state][a] = 0.0

    # 4) Prior heuristique pro-objectifs (faible échelle, additionné à Q)
    prior = {a: 0.0 for a in actions_str}
    prev_dist = _nearest_objective_dist(unit, objectives or [])

    for a in actions_str:
        if a.startswith("ATTACK"):
            # attaques un peu défavorisées sauf si on tient déjà un obj
            prior[a] += (0.2 if on_obj_now else -0.2)
            continue

        dx, dy = eval(a)  # "(dx, dy)"
        nx, ny = unit.x + dx, unit.y + dy

        # rester est très bon si on tient un objectif
        if dx == 0 and dy == 0:
            prior[a] += (OBJ_HOLD / 10.0 if on_obj_now else -0.1)

        entering = _on_objective_xy(nx, ny, objectives or [])
        if entering:
            prior[a] += OBJ_ENTER / 10.0
        if on_obj_now and not entering:
            prior[a] += OBJ_LEAVE / 10.0  # négatif → punit quitter

        new_dist = _nearest_objective_dist(type("P", (), {"x": nx, "y": ny})(), objectives or [])
        if new_dist < prev_dist:
            prior[a] += CLOSER_OBJ / 10.0
        elif new_dist > prev_dist:
            prior[a] += FARTHER_OBJ / 10.0

    # 5) ε-greedy
    if random.random() < eps:
        return random.choice(actions_str)

    def score(a):  # combinaison Q + prior heuristique
        return Q[state][a] + PRIOR_BETA * prior[a]

    best_val = max(score(a) for a in actions_str)
    best = [a for a in actions_str if score(a) == best_val]
    return random.choice(best)

def update_q(state, action, reward, new_state, Q, alpha: float = 0.25, gamma: float = 0.95):
    """
    Mise à jour robuste : crée les clés manquantes pour state/action/new_state.
    Évite les KeyError quand de nouvelles actions apparaissent.
    """
    action = str(action)
    if state not in Q:
        Q[state] = {}
    if action not in Q[state]:
        Q[state][action] = 0.0
    if new_state not in Q:
        Q[new_state] = {}
    old = Q[state][action]
    future = max(Q[new_state].values()) if Q[new_state] else 0.0
    Q[state][action] = old + alpha * (reward + gamma * future - old)

# -------------------------------------------------
# Tour IA avec rewards orientés objectifs
# -------------------------------------------------
def ai_turn_reward_based(units, objectives, grid, team_color, Q, turn_count=None):
    """
    Joue 1 tour complet pour team_color.
    - propose déplacements + rester + attaques
    - rewards : OBJ_ENTER/OBJ_HOLD/OBJ_STAY/OBJ_LEAVE, DMG/KILL abaissés,
      shaping de distance, pénalité de temps optionnelle.
    Retourne: (reward_total, reward_log)
    """
    reward_total = 0.0
    reward_log = []

    for unit in [u for u in units if u.color == team_color and not u.moved]:
        state = get_state(unit, objectives, units)
        prev_on_obj = _on_objective_xy(unit.x, unit.y, objectives)
        prev_dist = _nearest_objective_dist(unit, objectives)

        eps = 0.1 if not prev_on_obj else 0.02  # on explore très peu sur objectif
        action_str = choose_action(
            state, unit, units, Q,
            eps=eps, objectives=objectives, grid=grid, turn_count=turn_count
        )
        if action_str is None:
            unit.moved = True
            continue

        reward = 0.0

        # ---- ATTAQUE ----
        if action_str.startswith("ATTACK"):
            _, x, y = action_str.split("_")
            x, y = int(x), int(y)
            target = next((u for u in units if u.x == x and u.y == y and u.color != unit.color), None)
            if target:
                prev_pv = getattr(target, "pv", getattr(target, "hp", 2))
                unit.attack(target, units, objectives)

                # combat peu récompensé (juste pour signaler la direction)
                if target not in units:
                    reward += KILL_REWARD
                    reward_log.append(f"KILL:+{KILL_REWARD}")
                elif getattr(target, "pv", getattr(target, "hp", 2)) < prev_pv:
                    reward += DMG_REWARD
                    reward_log.append(f"DAMAGE:+{DMG_REWARD}")

                # quitter un objectif pour attaquer est très puni
                now_on_obj = _on_objective_xy(unit.x, unit.y, objectives)
                if prev_on_obj and not now_on_obj:
                    reward += OBJ_LEAVE
                    reward_log.append(f"LEAVE_OBJ:{OBJ_LEAVE}")

        # ---- DEPLACEMENT / RESTER ----
        else:
            dx, dy = eval(action_str)
            nx, ny = unit.x + dx, unit.y + dy

            if dx == 0 and dy == 0:  # rester
                if prev_on_obj:
                    reward += OBJ_HOLD
                    reward_log.append(f"HOLD_OBJ:+{OBJ_HOLD}")
                else:
                    reward -= 0.2  # éviter de camper hors obj
            else:
                if 0 <= nx < size and 0 <= ny < size and not any(u.x == nx and u.y == ny for u in units):
                    entering = _on_objective_xy(nx, ny, objectives)
                    if entering:
                        reward += OBJ_ENTER
                        reward_log.append(f"ENTER_OBJ:+{OBJ_ENTER}")
                    if prev_on_obj and not entering:
                        reward += OBJ_LEAVE
                        reward_log.append(f"LEAVE_OBJ:{OBJ_LEAVE}")
                    unit.move(nx, ny)

        # bonus d'être sur objectif en fin d'action
        if _on_objective_xy(unit.x, unit.y, objectives):
            reward += OBJ_STAY
            reward_log.append(f"ON_OBJ_END:+{OBJ_STAY}")

        # shaping distance vers objectif
        new_dist = _nearest_objective_dist(unit, objectives)
        if new_dist < prev_dist:
            reward += CLOSER_OBJ
            reward_log.append(f"CLOSER_OBJ:+{CLOSER_OBJ}")
        elif new_dist > prev_dist:
            reward += FARTHER_OBJ
            reward_log.append(f"FARTHER_OBJ:{FARTHER_OBJ}")

        # pénalité de temps si trop de tours (pour finir plus vite)
        if turn_count is not None and turn_count >= TURN_PENALTY_START:
            over = turn_count - TURN_PENALTY_START
            extra = min(MAX_TIME_PENALTY, TIME_PENALTY_PER_ACTION * (1 + TIME_PENALTY_GROWTH * over))
            reward -= extra
            reward_log.append(f"TIME_PENALTY:-{extra:.2f}")

        new_state = get_state(unit, objectives, units)
        update_q(state, action_str, reward, new_state, Q)
        reward_total += reward

    return reward_total, reward_log

# -------------------------------------------------
# Etat pour la Q-table (à adapter si besoin)
# -------------------------------------------------
def get_state(unit, objectives, units):
    """
    Encode l'état d'une unité :
      (x, y, on_obj, close_enemies, local_objectives, nearest_enemy_dist)
    Renvoie une string clé pour la Q-table.
    """
    on_objective = _on_objective_xy(unit.x, unit.y, objectives)
    close_enemies = sum(
        1 for u in units
        if u.color != unit.color and abs(u.x - unit.x) <= 1 and abs(u.y - unit.y) <= 1
    )
    local_objectives = sum(
        1 for obj in objectives
        if abs(obj['x'] - unit.x) <= 1 and abs(obj['y'] - unit.y) <= 1
    )
    enemies = [u for u in units if u.color != unit.color]
    nearest_enemy_dist = min(
        [abs(u.x - unit.x) + abs(u.y - unit.y) for u in enemies],
        default=99
    )
    return f"{unit.x},{unit.y},{int(on_objective)},{close_enemies},{local_objectives},{nearest_enemy_dist}"
