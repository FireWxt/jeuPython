# main_game.py

import pygame
import os
import json
import random
## Import déplacé dans main() pour éviter l'import circulaire
from config import *
from reward import *


# -----------------------
# 1) CONFIG ET CONSTANTES
# -----------------------
pygame.init()

global Q

qtable_filename = "data/q_table.json"
if os.path.exists(qtable_filename):
    with open(qtable_filename, 'r') as f:
        Q = json.load(f)
else:
    Q = {}
# -----------------------
# 3) PATHFINDING
# -----------------------
class Node:
    def __init__(self, x, y, parent=None, g=0, h=0):
        self.x = x
        self.y = y
        self.parent = parent
        self.g = g
        self.h = h
        self.f = g + h

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def find_path(start, goal, grid):
    open_list = []
    closed_list = set()

    start_node = Node(start[0], start[1], None, 0, heuristic(start, goal))
    open_list.append(start_node)

    while open_list:
        open_list.sort(key=lambda node: node.f)
        current_node = open_list.pop(0)
        closed_list.add((current_node.x, current_node.y))

        if (current_node.x, current_node.y) == goal:
            path = []
            while current_node:
                path.append((current_node.x, current_node.y))
                current_node = current_node.parent
            return path[::-1]

        neighbors = [(0,1),(0,-1),(1,0),(-1,0)]
        for dx, dy in neighbors:
            nx, ny = current_node.x + dx, current_node.y + dy
            if 0 <= nx < size and 0 <= ny < size and grid[ny][nx] == 1:
                if (nx, ny) in closed_list:
                    continue
                node = Node(nx, ny, current_node, current_node.g+1, heuristic((nx, ny), goal))
                open_list.append(node)

    return []

# -----------------------
# 4) DEFINITIONS DE CLASSE
# -----------------------
class Unit:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.selected = False
        self.moved = False  # Indicateur de mouvement pour le tour
        self.pv = 2  # Points de vie
        self.attacked_this_turn = False  # Indicateur d'attaque dans ce tour

    def draw(self, screen, units, objectives):
        rect = pygame.Rect(self.x * tile_size, self.y * tile_size, tile_size, tile_size)
        if not self.moved:
            color = PLAYER_COLOR_LIGHT if self.color == PLAYER_COLOR else ENEMY_COLOR_LIGHT
        else:
            color = self.color
        pygame.draw.rect(screen, color, rect)
        
        if self.selected:
            pygame.draw.rect(screen, SELECTED_COLOR, rect, 3)
        
        # Afficher un symbole
        font = pygame.font.SysFont(None, 16)
        symbols = self.get_symbols_on_same_tile(units)
        combined_text = font.render(symbols, True, (255, 255, 255))
        text_width = combined_text.get_width()
        text_x = self.x * tile_size + (tile_size - text_width) // 2
        screen.blit(combined_text, (text_x, self.y * tile_size + 5))

        for obj in objectives:
            if self.x == obj['x'] and self.y == obj['y']:
                pygame.draw.rect(screen, (0, 255, 0), rect, 1)

    def get_symbols_on_same_tile(self, units):
        symbols = [u.get_symbol() for u in units if u.x == self.x and u.y == self.y]
        return ' '.join(symbols)

    def get_symbol(self):
        return "U"

    def can_move(self, x, y):
        # Vérifie si l'unité peut se déplacer dans un rayon de 5
        if 0 <= x < size and 0 <= y < size:
            if abs(self.x - x) <= 1 and abs(self.y - y) <= 1    :
                return True
        return False

    def move(self, x, y):
        self.x = x
        self.y = y
        self.moved = True

    def move_towards_goal(self, goal, grid):
        path = find_path((self.x, self.y), goal, grid)
        if len(path) > 1:
            next_step = path[1]
            self.x, self.y = next_step
            self.moved = True

    def attack(self, target_unit, units, objectives):
        if self.can_move(target_unit.x, target_unit.y):
            dx = target_unit.x - self.x
            dy = target_unit.y - self.y
            old_target_x, old_target_y = target_unit.x, target_unit.y
            new_x, new_y = target_unit.x + dx, target_unit.y + dy

            if target_unit.attacked_this_turn:
                target_unit.pv -= 1
                if target_unit.pv <= 0:
                    units.remove(target_unit)
                    # On peut ensuite se déplacer sur la case vacante
                    self.move(old_target_x, old_target_y)
                    return

        # Tester si la case pour la cible est hors-limites ou occupée par un adversaire
            if not (0 <= new_x < size and 0 <= new_y < size) or any(u.x == new_x and u.y == new_y and u.color != target_unit.color for u in units ):
                # La cible est \"tuée\"
                units.remove(target_unit)
                # L'attaquant prend sa place
                self.move(old_target_x, old_target_y)
            else:
                target_unit.move(new_x, new_y)
                self.move(old_target_x, old_target_y)



    # (Toutes les méthodes draw, can_move, move, move_towards_goal, attack)
    # Idem que tu avais déjà dans ton code.

    def draw(self, screen, units, objectives):
        """Affiche l'unité sur l'écran."""
        rect = pygame.Rect(self.x * tile_size, self.y * tile_size, tile_size, tile_size)
        color = PLAYER_COLOR_LIGHT if self.color == PLAYER_COLOR and not self.moved else ENEMY_COLOR_LIGHT if self.color == ENEMY_COLOR and not self.moved else self.color
        pygame.draw.rect(screen, color, rect)
        if self.selected:
            pygame.draw.rect(screen, SELECTED_COLOR, rect, 3)
        font = pygame.font.SysFont(None, 16)
        symbols = self.get_symbols_on_same_tile(units)
        combined_text = font.render(symbols, True, TEXT_COLOR)
        text_width = combined_text.get_width()
        text_x = self.x * tile_size + (tile_size - text_width) // 2
        screen.blit(combined_text, (text_x, self.y * tile_size + 5))
        if any(self.x == obj['x'] and self.y == obj['y'] for obj in objectives):
            pygame.draw.rect(screen, (0, 255, 0), rect, 1)
# -----------------------
# 5) MAP, OBJECTIFS, SCORES
# -----------------------
def generate_map():
    return [[1 for _ in range(size)] for _ in range(size)]

def draw_map(screen, game_map):
    for y in range(size):
        for x in range(size):
            color = PASSABLE_COLOR
            rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
            pygame.draw.rect(screen, color, rect)

def generate_units():
    units = []
    player_positions = [(0, i) for i in range(size)]
    enemy_positions = [(size - 1, i) for i in range(size)]
    player_positions = random.sample(player_positions, 5)
    enemy_positions = random.sample(enemy_positions, 5)

    player_units = [Unit(pos[0], pos[1], PLAYER_COLOR) for pos in player_positions]
    enemy_units = [Unit(pos[0], pos[1], ENEMY_COLOR) for pos in enemy_positions]

    units.extend(player_units)
    units.extend(enemy_units)
    return units

def add_objectives():
    objectives = []
    center_x, center_y = size // 2, size // 2

    # 1 majeur
    while True:
        x, y = random.randint(center_x - 3, center_x + 3), random.randint(center_y - 3, center_y + 3)
        if not any(obj['x'] == x and obj['y'] == y for obj in objectives):
            objectives.append({'x': x, 'y': y, 'type': 'MAJOR'})
            break

    # 3 mineurs
    for _ in range(3):
        while True:
            x, y = random.randint(center_x - 5, center_x + 5), random.randint(center_y - 5, center_y + 5)
            if not any(obj['x'] == x and obj['y'] == y for obj in objectives):
                objectives.append({'x': x, 'y': y, 'type': 'MINOR'})
                break

    return objectives

def draw_objectives(screen, objectives):
    for obj in objectives:
        color = OBJECTIVE_MAJOR_COLOR if obj['type'] == 'MAJOR' else OBJECTIVE_MINOR_COLOR
        rect = pygame.Rect(obj['x'] * tile_size, obj['y'] * tile_size, tile_size, tile_size)
        pygame.draw.rect(screen, color, rect)

def calculate_scores(units, objectives):
    player_score = 0
    enemy_score = 0
    for obj in objectives:
        if any(u.x == obj['x'] and u.y == obj['y'] and u.color == PLAYER_COLOR for u in units):
            player_score += 3 if obj['type'] == 'MAJOR' else 1
        elif any(u.x == obj['x'] and u.y == obj['y'] and u.color == ENEMY_COLOR for u in units):
            enemy_score += 3 if obj['type'] == 'MAJOR' else 1
    return player_score, enemy_score

# -----------------------
# 6) BOUCLE PYGAME + LOG.
# -----------------------
def draw_turn_indicator(screen, player_turn):
    font = pygame.font.SysFont(None, 36)
    text = "Joueur" if player_turn else "Ennemi"
    img = font.render(text, True, (255, 255, 255))
    screen.blit(img, (10, 10))

def draw_end_turn_button(screen):
    font = pygame.font.SysFont(None, 36)
    text = font.render("Terminé", True, (255, 255, 255))
    button_rect = pygame.Rect(width // 2 - 50, height, 100, interface_height - 10)
    pygame.draw.rect(screen, (100, 100, 100), button_rect)
    screen.blit(text, (width // 2 - 50 + 10, height + 10))

def end_turn_button_clicked(mouse_pos):
    x, y = mouse_pos
    button_rect = pygame.Rect(width // 2 - 50, height, 100, interface_height - 10)
    return button_rect.collidepoint(x, y)

def draw_unit_attributes(screen, unit):
    if unit:
        font = pygame.font.SysFont(None, 24)
        pv_text = f"PV: {unit.pv} / 2"
        unit_img = font.render("Unité", True, (255, 255, 255))
        pv_img = font.render(pv_text, True, (255, 255, 255))
        screen.blit(unit_img, (10, height + 10))
        screen.blit(pv_img, (10, height + 40))

def draw_scores(screen, player_score, enemy_score):
    font = pygame.font.SysFont(None, 24)
    player_score_text = f"Score Joueur: {player_score}"
    enemy_score_text = f"Score Ennemi: {enemy_score}"
    player_score_img = font.render(player_score_text, True, (255, 255, 255))
    enemy_score_img = font.render(enemy_score_text, True, (255, 255, 255))
    screen.blit(player_score_img, (10, height + 70))
    screen.blit(enemy_score_img, (width - 150, height + 70))

def draw_victory_message(screen, message):
    font = pygame.font.SysFont(None, 48)
    victory_img = font.render(message, True, (255, 255, 255))
    screen.blit(victory_img, (width // 2 - 100, height // 2 - 24))

def main():
    from auto_game import ai_turn_reward_based
    pygame.display.set_caption("Jeu de stratégie IA")
    screen = pygame.display.set_mode((width, height + interface_height))

    game_map = generate_map()
    units = generate_units()
    objectives = add_objectives()

    selected_unit = None
    player_turn = True
    player_score = 0
    enemy_score = 0
    victory = False
    victory_message = ""

    running = True
    while running:
        if not victory:
            unit_moved = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        unit_moved = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    if end_turn_button_clicked((x, y)):
                        unit_moved = True
                    else:
                        grid_x, grid_y = x // tile_size, y // tile_size
                        if event.button == 1:  # clic gauche
                            possible_units = [
                                u for u in units
                                if u.x == grid_x and u.y == grid_y
                                and not u.moved
                                and ((u.color == PLAYER_COLOR and player_turn) or
                                     (u.color == ENEMY_COLOR and not player_turn))
                            ]
                            if selected_unit in possible_units:
                                current_index = possible_units.index(selected_unit)
                                selected_unit.selected = False
                                selected_unit = possible_units[(current_index+1) % len(possible_units)]
                            else:
                                if selected_unit:
                                    selected_unit.selected = False
                                if possible_units:
                                    selected_unit = possible_units[0]
                            if selected_unit:
                                selected_unit.selected = True
                        elif event.button == 3:  # clic droit => déplacer ou attaquer
                            if selected_unit and ((selected_unit.color == PLAYER_COLOR and player_turn) or
                                                  (selected_unit.color == ENEMY_COLOR and not player_turn)):
                                # attaquer
                                target_unit = [
                                    u for u in units
                                    if u.x == grid_x and u.y == grid_y
                                    and u.color != selected_unit.color
                                ]
                                for cible in target_unit:
                                    selected_unit.attack(cible, units, objectives)

                                # se déplacer
                                if selected_unit.can_move(grid_x, grid_y):
                                    selected_unit.move(grid_x, grid_y)
                                    selected_unit.selected = False
                                    selected_unit = None

            # Fin de tour
            if unit_moved:
                # Réinit
                for u in units:
                    u.moved = False
                    u.attacked_this_turn = False

                if player_turn:
                    # Calcul score
                    p_score_turn, e_score_turn = calculate_scores(units, objectives)
                    player_score += p_score_turn
                    enemy_score += e_score_turn

                    # Appel IA
                    player_turn = False
                    ai_turn_reward_based(units, objectives, game_map, ENEMY_COLOR)

                    # Recalcul score
                    p_score_turn, e_score_turn = calculate_scores(units, objectives)
                    player_score += p_score_turn
                    enemy_score += e_score_turn
                    player_turn = True
                else:
                    player_turn = True

                # Victoire ?
                if player_score >= 500:
                    victory = True
                    victory_message = "Victoire Joueur!"
                elif enemy_score >= 500:
                    victory = True
                    victory_message = "Victoire Ennemi!"
                elif not any(u.color == PLAYER_COLOR for u in units):
                    victory = True
                    victory_message = "Victoire Ennemi!"
                elif not any(u.color == ENEMY_COLOR for u in units):
                    victory = True
                    victory_message = "Victoire Joueur!"

        screen.fill((0,0,0))
        draw_map(screen, game_map)
        draw_objectives(screen, objectives)

        for u in units:
            u.draw(screen, units, objectives)

        draw_turn_indicator(screen, player_turn)
        draw_end_turn_button(screen)
        draw_unit_attributes(screen, selected_unit)
        draw_scores(screen, player_score, enemy_score)

        if victory:
            draw_victory_message(screen, victory_message)
            pygame.display.flip()
            pygame.time.wait(3000)
            running = False

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
