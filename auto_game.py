# auto_game.py — version corrigée (plus d'import circulaire)

import os
import json
import csv
from datetime import datetime
import time

import pygame

from config import *  # tile_size, size, width, height, interface_height, couleurs, etc.

# On importe désormais l'IA depuis ai.py (et non plus depuis ce fichier)
from ai import ai_turn_reward_based

# Les outils de génération/affichage et classes proviennent de jeu.py
from jeu import (
    Unit,
    generate_map, generate_units, add_objectives,
    calculate_scores, draw_map, draw_objectives, draw_scores, draw_victory_message
)

# -----------------------
# Paramètres d'entraînement auto
# -----------------------
AUTO_MODE = True
NB_PARTIES = 500
PAUSE_BETWEEN_PARTIES = 0.1  # secondes entre parties (si tu veux voir)

# -----------------------
# Préparation fichiers
# -----------------------
data_dir = "data"
os.makedirs(data_dir, exist_ok=True)
log_filename = os.path.join(data_dir, f"logs_parties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
qtable_filename = os.path.join(data_dir, "q_table.json")

# -----------------------
# Q-table
# -----------------------
if os.path.exists(qtable_filename):
    with open(qtable_filename, "r") as f:
        Q = json.load(f)
else:
    Q = {}

# -----------------------
# Utilitaires auto
# -----------------------
def reset_units(units):
    """Réinitialise les flags des unités pour un nouveau tour."""
    for u in units:
        u.moved = False
        u.attacked_this_turn = False
        u.idle_turns = getattr(u, "idle_turns", 0) + 1

def synthesize_qtable(qtable, min_action_value=0.1, keep_only_best=True, min_state_quality=2):
    """
    Nettoie la Q-table pour garder uniquement les actions significatives.
    """
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

# -----------------------
# Simulation auto (IA vs IA)
# -----------------------
def simulate_auto_game():
    pygame.init()
    pygame.display.set_caption("Jeu IA vs IA")
    screen = pygame.display.set_mode((width, height + interface_height))

    # Init CSV de logs
    with open(log_filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Partie", "Tours", "Score_Joueur", "Score_Ennemi",
            "Gagnant", "Recompenses", "Actions_Recompensees"
        ])

    nb_gagnees_score_max = 0
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

        # Boucle de partie (IA rouge vs IA bleue)
        while not victory:
            for team in [PLAYER_COLOR, ENEMY_COLOR]:
                # ✨ APPEL IA (maintenant importée depuis ai.py) et passage de Q
                reward, log = ai_turn_reward_based(units, objectives, game_map, team, Q)
                total_reward += reward
                actions_rewarded.extend(log)

                # fin de tour : reset des flags + scores
                reset_units(units)
                ps, es = calculate_scores(units, objectives)
                player_score += ps
                enemy_score += es
                turn_count += 1

            # Conditions de victoire
            if player_score >= 500:
                victory = True
                winner = "Joueur"
            elif enemy_score >= 500:
                victory = True
                winner = "Ennemi"
            elif not any(u.color == PLAYER_COLOR for u in units):
                victory = True
                winner = "Ennemi"
            elif not any(u.color == ENEMY_COLOR for u in units):
                victory = True
                winner = "Joueur"

        # Log CSV
        with open(log_filename, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                partie, turn_count, player_score, enemy_score,
                winner, total_reward, "|".join(actions_rewarded)
            ])

        # Nettoyage + sauvegarde Q-table
        Q_clean = synthesize_qtable(Q, min_action_value=0.1, keep_only_best=True, min_state_quality=2)
        with open(qtable_filename, "w") as f:
            json.dump(Q_clean, f)

        # Petite pause si tu veux visualiser (optionnel)
        if PAUSE_BETWEEN_PARTIES:
            time.sleep(PAUSE_BETWEEN_PARTIES)

    pygame.quit()

if __name__ == "__main__":
    simulate_auto_game()
