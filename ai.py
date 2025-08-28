# ai.py
from config import *  # size, couleurs, etc.
import random

def get_state(unit, objectives, units):
    pos = (unit.x, unit.y)
    on_objective = any(unit.x == obj['x'] and unit.y == obj['y'] for obj in objectives)
    close_enemies = sum(1 for u in units if u.color != unit.color and abs(u.x - unit.x) <= 1 and abs(u.y - unit.y) <= 1)
    local_objectives = sum(1 for obj in objectives if abs(obj['x'] - unit.x) <= 1 and abs(obj['y'] - unit.y) <= 1)
    enemies = [u for u in units if u.color != unit.color]
    nearest_enemy_dist = min([abs(u.x - unit.x) + abs(u.y - unit.y) for u in enemies], default=99)
    return f"{unit.x},{unit.y},{int(on_objective)},{close_enemies},{local_objectives},{nearest_enemy_dist}"

def choose_action(state, unit, units, Q):
    directions = [(0,1), (0,-1), (1,0), (-1,0)]
    attackable = [f"ATTACK_{u.x}_{u.y}" for u in units if u.color != unit.color and unit.can_move(u.x, u.y)]
    actions_str = [str(a) for a in directions] + attackable

    if state not in Q:
        Q[state] = {a: 0 for a in actions_str}

    if random.random() < 0.1:  # exploration
        return random.choice(actions_str)

    max_value = max(Q[state].values(), default=0)
    best_actions = [a for a in actions_str if Q[state].get(a, float('-inf')) == max_value]
    return random.choice(best_actions) if best_actions else random.choice(actions_str)

def update_q(state, action, reward, new_state, Q, alpha=0.25, gamma=0.95):
    action = str(action)
    if new_state not in Q:
        Q[new_state] = {str(a): 0 for a in [(0,1), (0,-1), (1,0), (-1,0)]}
    old_value = Q[state][action]
    future = max(Q[new_state].values())
    Q[state][action] = old_value + alpha * (reward + gamma * future - old_value)

def ai_turn_reward_based(units, objectives, grid, team_color, Q):
    reward_total = 0
    reward_log = []

    for unit in [u for u in units if u.color == team_color and not u.moved]:
        state = get_state(unit, objectives, units)
        action_str = choose_action(state, unit, units, Q)
        reward = 0

        if action_str.startswith("ATTACK"):
            _, x, y = action_str.split("_")
            x, y = int(x), int(y)
            target = next((u for u in units if u.x == x and u.y == y and u.color != unit.color), None)
            if target:
                prev_pv = target.pv
                unit.attack(target, units, objectives)
                new_state = get_state(unit, objectives, units)
                if target not in units:
                    reward += 1
                    reward_log.append(f"KILL({unit.x},{unit.y})->({x},{y}):+1")
                elif target.pv < prev_pv:
                    reward += 1
                    reward_log.append(f"DAMAGE({unit.x},{unit.y})->({x},{y}):+1")
                update_q(state, action_str, reward, new_state, Q)
                reward_total += reward
                continue
        else:
            action = eval(action_str)
            new_x, new_y = unit.x + action[0], unit.y + action[1]
            if 0 <= new_x < size and 0 <= new_y < size:
                if not any(u.x == new_x and u.y == new_y for u in units):
                    if any(obj['x'] == new_x and obj['y'] == new_y for obj in objectives):
                        reward += 8
                        reward_log.append(f"MOVE_OBJ({unit.x},{unit.y})->({new_x},{new_y}):+8")
                    unit.move(new_x, new_y)

        on_objective_now = any(unit.x == obj['x'] and unit.y == obj['y'] for obj in objectives)
        if on_objective_now:
            reward += 2
            reward_log.append(f"HOLD({unit.x},{unit.y}):+2")

        new_state = get_state(unit, objectives, units)
        update_q(state, action_str, reward, new_state, Q)
        reward_total += reward

    return reward_total, reward_log
