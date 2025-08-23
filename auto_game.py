# auto_game.py

import pygame
import random
import time
import os
import json
from config import *
from jeu import Unit, generate_map, generate_units, add_objectives, calculate_scores, draw_map, draw_objectives, draw_scores, draw_victory_message

AUTO_MODE = True
NB_PARTIES = 500
PAUSE_BETWEEN_PARTIES = 0.1

# Fichiers
import csv
from datetime import datetime

font = pygame.font.SysFont(None, 24)

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

def synthesize_qtable(qtable, min_action_value=0.1, keep_only_best=True, min_state_quality=2):
    """
    Nettoie et sélectionne les comportements efficaces dans la Q-table.

    - Supprime les actions ≈ 0 (bruit)
    - Garde uniquement les états avec au moins une action "positive"
    - Option : ne garder que la meilleure action par état
    """
    new_q = {}

    for state, actions in qtable.items():
        if not actions:
            continue

        # Ne garde que les actions utiles (supprime le bruit)
        filtered = {a: v for a, v in actions.items() if abs(v) >= min_action_value}
        if not filtered:
            continue

        max_val = max(filtered.values())
        if max_val < min_state_quality:
            continue  # Pas un comportement significatif

        if keep_only_best:
            filtered = {a: v for a, v in filtered.items() if v == max_val}

        if filtered:
            new_q[state] = filtered

    return new_q


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
    global Q
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





def update_q(state, action, reward, new_state, alpha=0.25, gamma=0.95):
    global Q
    action = str(action)
    if new_state not in Q:
        Q[new_state] = {str(a): 0 for a in [(0,1), (0,-1), (1,0), (-1,0)]}
    old_value = Q[state][action]
    future = max(Q[new_state].values())
    Q[state][action] = old_value + alpha * (reward + gamma * future - old_value)

def ai_turn_reward_based(units, objectives, grid, team_color):
    global Q
    reward_total = 0
    reward_log = []

    for unit in [u for u in units if u.color == team_color and not u.moved]:
        # État initial
        on_objective_before = any(unit.x == obj['x'] and unit.y == obj['y'] for obj in objectives)
        if not hasattr(unit, 'hold_counter'):
            unit.hold_counter = 0
        if not hasattr(unit, 'on_objective_last_turn'):
            unit.on_objective_last_turn = False

        # Action choisie
        state = get_state(unit, objectives, units)
        action_str = choose_action(state, unit, units)
        reward = 0

        if action_str.startswith("ATTACK"):
            _, x, y = action_str.split("_")
            x, y = int(x), int(y)
            target = next((u for u in units if u.x == x and u.y == y and u.color != unit.color), None)
            if target:
                prev_pv = target.pv
                prev_on_objective = any(target.x == obj['x'] and target.y == obj['y'] for obj in objectives)
                unit.attack(target, units, objectives)
                new_state = get_state(unit, objectives, units)

                if target not in units:
                    reward += 1
                    reward_log.append(f"KILL({unit.x},{unit.y})->({x},{y}):+1")
                elif target.pv < prev_pv:
                    reward += 1
                    reward_log.append(f"DAMAGE({unit.x},{unit.y})->({x},{y}):+1")
                elif prev_on_objective and not any(target.x == obj['x'] and target.y == obj['y'] for obj in objectives):
                    reward += 1
                    reward_log.append(f"PUSH_OFF({unit.x},{unit.y})->({x},{y}):+1")

                update_q(state, action_str, reward, new_state)
                reward_total += reward
                continue  # Corrigé : maintenant bien dans la boucle

        else:
            action = eval(action_str)
            new_x, new_y = unit.x + action[0], unit.y + action[1]
            if 0 <= new_x < size and 0 <= new_y < size:
                if any(u.x == new_x and u.y == new_y for u in units):
                    continue

                if any(obj['x'] == new_x and obj['y'] == new_y for obj in objectives):
                    reward += 8
                    reward_log.append(f"MOVE_OBJ({unit.x},{unit.y})->({new_x},{new_y}):+8")
                    unit.hold_counter = 1
                else:
                    unit.hold_counter = 0

                unit.move(new_x, new_y)

        # MAINTIEN DE POSITION
        on_objective_now = any(unit.x == obj['x'] and unit.y == obj['y'] for obj in objectives)
        if on_objective_now:
            unit.hold_counter += 1
            if unit.hold_counter >= 2:
                reward += 2
                reward_log.append(f"HOLD({unit.x},{unit.y}):+2")
        else:
            unit.hold_counter = 0

        # ABANDON DE POINT
        if unit.on_objective_last_turn and not on_objective_now:
            reward -= 1
            reward_log.append(f"LEAVE_POINT({unit.x},{unit.y}):-1")

        # MàJ mémoire et Q-table
        unit.on_objective_last_turn = on_objective_now
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
        # Affiche le numéro de la partie

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
                for u in units:
                    if u.color == PLAYER_COLOR and any(u.x == o['x'] and u.y == o['y'] for o in objectives):
                        state = get_state(u, objectives, units)
                        for a in Q.get(state, {}):
                            Q[state][a] += 1
            elif enemy_score >= 500:
                victory = True
                message = f"Victoire Ennemi (IA Q-Learning) en {turn_count} tours"
                winner = "Ennemi"
                for u in units:
                    if u.color == PLAYER_COLOR and any(u.x == o['x'] and u.y == o['y'] for o in objectives):
                        state = get_state(u, objectives, units)
                        for a in Q.get(state, {}):
                            Q[state][a] += 1
            elif not any(u.color == PLAYER_COLOR for u in units):
                victory = True
                message = "Victoire Ennemi (plus d'unités joueur)"
                winner = "Ennemi"
            elif not any(u.color == ENEMY_COLOR for u in units):
                victory = True
                message = "Victoire Joueur (plus d'unités ennemies)"
                winner = "Joueur"



            screen.fill((0, 0, 0))
            partie_text = font.render(f"Partie {partie} / {NB_PARTIES}", True, (255, 255, 255))
            screen.blit(partie_text, (20, height + 30))  # en haut à gauche
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

        if nb_parties_score_max > 0:
            pourcentage_gagné = (nb_gagnées_score_max / NB_PARTIES) * 100
        else:
            pourcentage_gagné = 0

        with open(log_filename, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([partie, turn_count, player_score, enemy_score, winner, total_reward, '|'.join(actions_rewarded)])

        if player_score > 499 or enemy_score > 499:
                nb_parties_score_max += 1
                if (player_score > 499 and winner == "Joueur") or (enemy_score > 499 and winner == "Ennemi"):
                    nb_gagnées_score_max += 1

        with open(log_filename, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([])
            writer.writerow(['% Parties Gagnees au score', f"{pourcentage_gagné:.2f}%"])


        Q_clean = synthesize_qtable(Q, min_action_value=0.1, keep_only_best=True, min_state_quality=2)

        with open(qtable_filename, 'w') as f:
            json.dump(Q_clean, f)
            print(f"Q-table synthétisée : {len(Q_clean)} états retenus avec comportement positif.")


    pygame.quit()

if __name__ == "__main__":
    simulate_auto_game()