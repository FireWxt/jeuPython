# auto_game.py

import pygame
import random
import time
import os
import json
from config import *
from jeu import Unit, generate_map, generate_units, add_objectives, calculate_scores, draw_map, draw_objectives, draw_scores, draw_victory_message

AUTO_MODE = True
NB_PARTIES = 50
PAUSE_BETWEEN_PARTIES = 0.01

# Fichiers
import csv
from datetime import datetime

data_dir = "data"
os.makedirs(data_dir, exist_ok=True)
log_filename = os.path.join(data_dir, f"logs_parties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
qtable_filename = os.path.join(data_dir, "q_table.json")

# Initialiser Q-table
if os.path.exists(qtable_filename):
    with open(qtable_filename, 'r') as f:
        Q = json.load(f)
else:
    Q = {}

with open(log_filename, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Partie', 'Tours', 'Score_Joueur', 'Score_Ennemi', 'Gagnant', 'Recompenses', 'Actions_Recompensees'])

def reset_units(units):
    for u in units:
        u.moved = False
        u.attacked_this_turn = False
        if not hasattr(u, 'idle_turns'):
            u.idle_turns = 0
        else:
            u.idle_turns += 1

# IA générique avec apprentissage Q-table

def get_state(unit, objectives, units):
    # 1. Position actuelle
    pos = (unit.x, unit.y)

    # 2. Sur un objectif ?
    on_objective = any(unit.x == obj['x'] and unit.y == obj['y'] for obj in objectives)

    # 3. Ennemis dans le voisinage immédiat (rayon 1)
    close_enemies = sum(
        1 for u in units
        if u.color != unit.color and abs(u.x - unit.x) <= 1 and abs(u.y - unit.y) <= 1
    )

    # 4. Objectifs dans un rayon 1 (local)
    local_objectives = sum(
        1 for obj in objectives
        if abs(obj['x'] - unit.x) <= 1 and abs(obj['y'] - unit.y) <= 1
    )

    # 5. Distance au plus proche ennemi
    enemies = [u for u in units if u.color != unit.color]
    if enemies:
        nearest_enemy_dist = min(abs(u.x - unit.x) + abs(u.y - unit.y) for u in enemies)
    else:
        nearest_enemy_dist = 99  # Aucun ennemi en vue

    # Encodage de l’état sous forme de string
    return f"{unit.x},{unit.y},{int(on_objective)},{close_enemies},{local_objectives},{nearest_enemy_dist}"



def choose_action(state, unit, units):
    directions = [(0,1), (0,-1), (1,0), (-1,0)]
    attackable = [f"ATTACK_{u.x}_{u.y}" for u in units if u.color != unit.color and unit.can_move(u.x, u.y)]
    actions_str = [str(a) for a in directions] + attackable

    # Initialiser l'état si absent
    if state not in Q:
        Q[state] = {}

    # S'assurer que toutes les actions sont bien enregistrées pour cet état
    for a in actions_str:
        if a not in Q[state]:
            Q[state][a] = 0

    # Si aucune action valide, fallback random
    if not Q[state]:
        return random.choice(actions_str)

    # Exploration
    if random.random() < 0.1:
        return random.choice(actions_str)

    max_value = max(Q[state].values(), default=0)
    best_actions = [a for a in actions_str if Q[state].get(a, float('-inf')) == max_value]

    if not best_actions:
        return random.choice(actions_str)

    return random.choice(best_actions)





def update_q(state, action, reward, new_state, alpha=0.3, gamma=0.95):
    action = str(action)
    if new_state not in Q:
        Q[new_state] = {str(a): 0 for a in [(0,1), (0,-1), (1,0), (-1,0)]}
    old_value = Q[state][action]
    future = max(Q[new_state].values())
    Q[state][action] = old_value + alpha * (reward + gamma * future - old_value)

def ai_turn_reward_based(units, objectives, grid, team_color):
    reward_total = 0
    reward_log = []
    for unit in [u for u in units if u.color == team_color and not u.moved]:
        state = get_state(unit, objectives, units)
        
        actions = [(0,1), (0,-1), (1,0), (-1,0)]
        attackable = [f"ATTACK_{u.x}_{u.y}" for u in units if u.color != unit.color and unit.can_move(u.x, u.y)]
        action_str = choose_action(state, unit, units) if 'choose_action' in globals() else str(random.choice(actions))
        
        if action_str.startswith("ATTACK"):
            _, x, y = action_str.split("_")
            x, y = int(x), int(y)
            target = next((u for u in units if u.x == x and u.y == y and u.color != unit.color), None)
            if target:
                prev_pv = target.pv
                prev_on_objective = any(target.x == obj['x'] and target.y == obj['y'] for obj in objectives)
                unit.attack(target, units, objectives)
                new_state = get_state(unit, objectives, units)
                reward = 0
                if target not in units:
                    reward = -3
                    reward_log.append(f"KILL({unit.x},{unit.y})->({x},{y}):-3")
                elif target.pv < prev_pv:
                    reward = 2
                    reward_log.append(f"DAMAGE({unit.x},{unit.y})->({x},{y}):+2")
                elif prev_on_objective and not any(target.x == obj['x'] and target.y == obj['y'] for obj in objectives):
                    reward = 2
                    reward_log.append(f"PUSH_OFF({unit.x},{unit.y})->({x},{y}):+2")
                update_q(state, action_str, reward, new_state)
                reward_total += reward
                continue

        action = eval(action_str) if isinstance(action_str, str) else action_str
        new_x, new_y = unit.x + action[0], unit.y + action[1]
        if 0 <= new_x < size and 0 <= new_y < size:
            if any(u.x == new_x and u.y == new_y for u in units):
                continue
            reward = 0
            if any(obj['x'] == new_x and obj['y'] == new_y for obj in objectives):
                reward = 10
                reward_log.append(f"MOVE_OBJ({unit.x},{unit.y})->({new_x},{new_y}):+10")
                unit.idle_turns = 0
            elif unit.x == new_x and unit.y == new_y and unit.idle_turns >= 1:
                reward = -5
                reward_log.append(f"STAY({unit.x},{unit.y}):-5")

            unit.move(new_x, new_y)
            new_state = get_state(unit, objectives, units)
            update_q(state, action, reward, new_state)
            reward_total += reward
    return reward_total, reward_log


def simulate_auto_game():
    pygame.display.set_caption("Jeu IA vs IA")
    screen = pygame.display.set_mode((width, height + interface_height))

    for partie in range(1, NB_PARTIES + 1):
        print(f"Démarrage de la partie {partie}...")
        game_map = generate_map()
        units = generate_units()
        for u in units:
            u.idle_turns = 0

        objectives = add_objectives()

        player_score, enemy_score = 0, 0
        victory = False
        message = ""
        turn_count = 0
        total_reward = 0
        actions_rewarded = []

        screen.fill((0, 0, 0))
        draw_map(screen, game_map)
        draw_objectives(screen, objectives)
        for u in units:
            u.draw(screen, units, objectives)
        draw_scores(screen, player_score, enemy_score)
        pygame.display.flip()
        time.sleep(0.0001)

        while not victory:
            print(f"Tour {turn_count + 1}")
            reward, log = ai_turn_reward_based(units, objectives, game_map, PLAYER_COLOR)
            total_reward += reward
            actions_rewarded.extend(log)
            reset_units(units)
            ps, es = calculate_scores(units, objectives)
            player_score += ps
            enemy_score += es
            turn_count += 1

            reward, log = ai_turn_reward_based(units, objectives, game_map, ENEMY_COLOR)
            total_reward += reward
            actions_rewarded.extend(log)
            reset_units(units)
            ps, es = calculate_scores(units, objectives)
            player_score += ps
            enemy_score += es
            turn_count += 1

            if player_score >= 500:
                victory = True
                message = f"Victoire Joueur (IA Q-Learning) en {turn_count} tours"
                winner = "Joueur"
            elif enemy_score >= 500:
                victory = True
                message = f"Victoire Ennemi (IA Q-Learning) en {turn_count} tours"
                winner = "Ennemi"
            elif not any(u.color == PLAYER_COLOR for u in units):
                victory = True
                message = "Victoire Ennemi (plus d'unités joueur)"
                winner = "Ennemi"
            elif not any(u.color == ENEMY_COLOR for u in units):
                victory = True
                message = "Victoire Joueur (plus d'unités ennemies)"
                winner = "Joueur"

            screen.fill((0, 0, 0))
            draw_map(screen, game_map)
            draw_objectives(screen, objectives)
            for u in units:
                u.draw(screen, units, objectives)
            draw_scores(screen, player_score, enemy_score)
            pygame.display.flip()
            time.sleep(0.0001)

        print(message)
        draw_victory_message(screen, message)
        pygame.display.flip()
        time.sleep(0.0001)

        with open(log_filename, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([partie, turn_count, player_score, enemy_score, winner, total_reward, '|'.join(actions_rewarded)])

        with open(qtable_filename, 'w') as f:
            json.dump(Q, f)

    pygame.quit()

if __name__ == "__main__":
    simulate_auto_game()
