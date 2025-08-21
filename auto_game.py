# auto_game.py

import pygame
import random
import time
import os
import json
from config import *
from jeu import Unit, generate_map, generate_units, add_objectives, calculate_scores, draw_map, draw_objectives, draw_scores, draw_victory_message

import csv
from datetime import datetime

# Paramètres
AUTO_MODE = True
NB_PARTIES = 500
PAUSE_BETWEEN_PARTIES = 0.1

# Préparer fichiers
font = pygame.font.SysFont(None, 24)
data_dir = "data"
os.makedirs(data_dir, exist_ok=True)
log_filename = os.path.join(data_dir, f"logs_parties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
qtable_filename = os.path.join(data_dir, "q_table.json")

# Charger Q-table si existante
if os.path.exists(qtable_filename):
    with open(qtable_filename, 'r') as f:
        Q = json.load(f)
else:
    Q = {}

# Initialiser fichier CSV
with open(log_filename, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Partie', 'Tours', 'Score_Joueur', 'Score_Ennemi', 'Gagnant', 'Recompenses', 'Actions_Recompensees'])

# Fonctions utilitaires
def reset_units(units):
    """Réinitialise les flags des unités pour un nouveau tour"""
    for u in units:
        u.moved = False
        u.attacked_this_turn = False
        u.idle_turns = getattr(u, 'idle_turns', 0) + 1

def synthesize_qtable(qtable, min_action_value=0.1, keep_only_best=True, min_state_quality=2):
    """Nettoie la Q-table pour garder uniquement les actions significatives"""
    new_q = {}
    for state, actions in qtable.items():
        filtered = {a: v for a, v in actions.items() if abs(v) >= min_action_value}
        if not filtered:
            continue
        max_val = max(filtered.values())
        if max_val < min_state_quality:
            continue
        if keep_only_best:
            filtered = {a: v for a, v in filtered.items() if v == max_val}
        if filtered:
            new_q[state] = filtered
    return new_q

def get_state(unit, objectives, units):
    """Encode l'état de l'unité en string pour Q-learning"""
    pos = (unit.x, unit.y)
    on_objective = any(unit.x == obj['x'] and unit.y == obj['y'] for obj in objectives)
    close_enemies = sum(1 for u in units if u.color != unit.color and abs(u.x - unit.x) <= 1 and abs(u.y - unit.y) <= 1)
    local_objectives = sum(1 for obj in objectives if abs(obj['x'] - unit.x) <= 1 and abs(obj['y'] - unit.y) <= 1)
    enemies = [u for u in units if u.color != unit.color]
    nearest_enemy_dist = min([abs(u.x - unit.x) + abs(u.y - unit.y) for u in enemies], default=99)
    return f"{unit.x},{unit.y},{int(on_objective)},{close_enemies},{local_objectives},{nearest_enemy_dist}"

def choose_action(state, unit, units):
    """Choisit une action selon Q-table avec exploration"""
    global Q
    directions = [(0,1), (0,-1), (1,0), (-1,0)]
    attackable = [f"ATTACK_{u.x}_{u.y}" for u in units if u.color != unit.color and unit.can_move(u.x, u.y)]
    actions_str = [str(a) for a in directions] + attackable

    if state not in Q:
        Q[state] = {a: 0 for a in actions_str}

    # Exploration
    if random.random() < 0.1:
        return random.choice(actions_str)

    max_value = max(Q[state].values(), default=0)
    best_actions = [a for a in actions_str if Q[state].get(a, float('-inf')) == max_value]

    return random.choice(best_actions) if best_actions else random.choice(actions_str)

def update_q(state, action, reward, new_state, alpha=0.25, gamma=0.95):
    global Q
    action = str(action)
    if new_state not in Q:
        Q[new_state] = {str(a): 0 for a in [(0,1), (0,-1), (1,0), (-1,0)]}
    old_value = Q[state][action]
    future = max(Q[new_state].values())
    Q[state][action] = old_value + alpha * (reward + gamma * future - old_value)

def ai_turn_reward_based(units, objectives, grid, team_color):
    """Tour IA avec récompenses pour Q-learning"""
    global Q
    reward_total = 0
    reward_log = []

    for unit in [u for u in units if u.color == team_color and not u.moved]:
        state = get_state(unit, objectives, units)
        action_str = choose_action(state, unit, units)
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
                update_q(state, action_str, reward, new_state)
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
        update_q(state, action_str, reward, new_state)
        reward_total += reward

    return reward_total, reward_log

def simulate_auto_game():
    pygame.display.set_caption("Jeu IA vs IA")
    screen = pygame.display.set_mode((width, height + interface_height))
    nb_gagnées_score_max = 0
    nb_parties_score_max = 0

    for partie in range(1, NB_PARTIES + 1):
        game_map = generate_map()
        units = generate_units()
        objectives = add_objectives()
        player_score, enemy_score = 0, 0
        victory = False
        turn_count = 0
        total_reward = 0
        actions_rewarded = []

        while not victory:
            for team in [PLAYER_COLOR, ENEMY_COLOR]:
                reward, log = ai_turn_reward_based(units, objectives, game_map, team)
                total_reward += reward
                actions_rewarded.extend(log)
                reset_units(units)
                ps, es = calculate_scores(units, objectives)
                player_score += ps
                enemy_score += es
                turn_count += 1

            if player_score >= 500:
                victory = True
                winner = "Joueur"
            elif enemy_score >= 500:
                victory = True
                winner = "Ennemi"

        with open(log_filename, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([partie, turn_count, player_score, enemy_score, winner, total_reward, '|'.join(actions_rewarded)])

        Q_clean = synthesize_qtable(Q, min_action_value=0.1, keep_only_best=True, min_state_quality=2)
        with open(qtable_filename, 'w') as f:
            json.dump(Q_clean, f)

    pygame.quit()


if __name__ == "__main__":
    simulate_auto_game()
