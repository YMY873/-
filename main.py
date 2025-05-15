import pygame
import random
import math
import sys

WIDTH, HEIGHT = 1000, 800
GRID_COUNT = 23
PLAYER_COLORS = {
    'A': (255, 0, 0),
    'B': (0, 255, 0),
    'C': (0, 0, 255),
    'D': (255, 255, 0),
    'E': (255, 0, 255),
    'F': (0, 255, 255)
}
PLAYERS = list(PLAYER_COLORS.keys())
PLAYER_SKILLS = {
    'A': {'type': 'position_bonus'},
    'B': {'type': 'double_chance', 'prob': 0.28},
    'C': {'type': 'late_move', 'prob': 0.65},
    'D': {'type': 'elevate', 'prob': 0.4},
    'E': {'type': 'solo_move', 'prob': 0.5},
    'F': {'type': 'dice_2d3'}
}


class CircularBoard:
    def __init__(self):
        self.reset()

    def reset(self):
        self.positions = [[] for _ in range(GRID_COUNT)]
        self.winner = None
        self.total_steps = {p: 0 for p in PLAYERS}

    def add_player(self, player, position):
        self.positions[position].append(player)

    def move_player(self, player, steps, is_solo=False):
        if self.winner:
            return

        current_idx = self.find_player_position(player)
        if current_idx is None:
            return

        self.total_steps[player] += steps
        if self.total_steps[player] >= GRID_COUNT:
            self.winner = player
            return

        new_idx = (current_idx + steps) % GRID_COUNT
        current_stack = self.positions[current_idx]
        player_index = current_stack.index(player)

        move_stack = [player] if is_solo else current_stack[player_index:]
        del current_stack[player_index:player_index + len(move_stack)]
        self.positions[new_idx].extend(move_stack)

    def find_player_position(self, player):
        for idx, stack in enumerate(self.positions):
            if player in stack:
                return idx
        return None

    def get_player_stack_size(self, player):
        idx = self.find_player_position(player)
        return len(self.positions[idx]) if idx is not None else 0

    def is_last_place(self, player):
        player_pos = self.find_player_position(player)
        all_pos = [self.find_player_position(p) for p in PLAYERS if p != player]
        return all(p >= player_pos for p in all_pos if p is not None)


class GameVisualization:
    def __init__(self, speed=2):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.font = pygame.font.Font(None, 24)
        self.board = CircularBoard()
        self.clock = pygame.time.Clock()
        self.grid_positions = self.calculate_positions()
        self.speed = speed
        self.win_counts = {p: 0 for p in PLAYERS}
        self.total_games = 0
        self.initial_order = []  # 存储初始随机顺序

    def calculate_positions(self):
        positions = []
        radius = min(WIDTH, HEIGHT) * 0.4
        center = (WIDTH // 2, HEIGHT // 2)
        for i in range(GRID_COUNT):
            angle = 2 * math.pi * i / GRID_COUNT
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            positions.append((x, y))
        return positions

    def draw_board(self):
        self.screen.fill((255, 255, 255))
        for idx, (x, y) in enumerate(self.grid_positions):
            text = self.font.render(str(idx), True, (0, 0, 0))
            self.screen.blit(text, (x - 10, y - 10))
            players = self.board.positions[idx]
            for i, player in enumerate(players):
                color = PLAYER_COLORS[player]
                pos = (x + i * 15, y + i * 15)
                pygame.draw.circle(self.screen, color, pos, 10)
                text = self.font.render(player, True, (0, 0, 0))
                self.screen.blit(text, (pos[0] - 5, pos[1] - 8))

        stats = " | ".join([f"{k}:{v}" for k, v in self.win_counts.items()])
        stat_text = self.font.render(f"Total Games: {self.total_games}  {stats}", True, (0, 0, 0))
        self.screen.blit(stat_text, (20, HEIGHT - 40))
        speed_text = self.font.render(f"Speed: {self.speed} (Up/Down Arrow)", True, (0, 0, 0))
        self.screen.blit(speed_text, (20, 20))
        pygame.display.flip()

    def initialize_players(self):
        self.board.positions = [[] for _ in range(GRID_COUNT)]
        self.board.add_player('A', 0)
        self.board.add_player('C', 22)
        self.board.add_player('B', 22)
        self.board.add_player('E', 21)
        self.board.add_player('D', 21)
        self.board.add_player('F', 20)

    def process_turn(self, player):
        dice = self.roll_dice(player)
        steps = self.apply_pre_skills(player, dice)
        is_solo = self.check_solo_move(player)
        self.board.move_player(player, steps, is_solo)
        self.apply_post_skills(player)
        self.update_display()

    def roll_dice(self, player):
        if PLAYER_SKILLS[player]['type'] == 'dice_2d3':
            return random.randint(2, 3)
        return random.randint(1, 3)

    def apply_pre_skills(self, player, base_steps):
        steps = base_steps
        skill = PLAYER_SKILLS[player]
        if skill['type'] == 'position_bonus' and self.board.is_last_place(player):
            steps += 3
        elif skill['type'] == 'double_chance' and random.random() < skill['prob']:
            steps *= 2
        elif skill['type'] == 'solo_move' and random.random() < skill['prob']:
            stack_size = self.board.get_player_stack_size(player)
            steps += (stack_size - 1)
        return steps

    def check_solo_move(self, player):
        return (PLAYER_SKILLS[player]['type'] == 'solo_move'
                and random.random() < PLAYER_SKILLS[player]['prob'])

    def apply_post_skills(self, player):
        skill = PLAYER_SKILLS[player]
        if skill['type'] == 'elevate' and random.random() < skill['prob']:
            idx = self.board.find_player_position(player)
            if idx is not None:
                stack = self.board.positions[idx]
                if player in stack:
                    stack.remove(player)
                    stack.append(player)

    def adjust_move_order(self, base_order):
        ordered = list(base_order)
        for i in range(len(base_order)):
            p = base_order[i]
            if p == 'C' and PLAYER_SKILLS[p]['type'] == 'late_move':
                idx = self.board.find_player_position(p)
                if idx is not None:
                    stack = self.board.positions[idx]
                    if stack.index(p) > 0 and random.random() < 0.65:
                        ordered.append(ordered.pop(i))
                        break  # 每个回合只调整一次
        return ordered

    def run_game(self):
        self.board.reset()
        self.initialize_players()
        # 生成第一回合的随机顺序
        self.initial_order = random.sample(PLAYERS, len(PLAYERS))

        while not self.board.winner:
            # 使用初始顺序的副本进行调整
            current_order = self.adjust_move_order(self.initial_order.copy())
            for player in current_order:
                if self.board.winner:
                    break
                self.process_turn(player)
                self.update_display()

        if self.board.winner:
            self.win_counts[self.board.winner] += 1
            self.total_games += 1

    def update_display(self):
        self.draw_board()
        pygame.display.flip()
        pygame.time.delay(int(500 / self.speed))

    def show_winner_message(self):
        if self.board.winner:
            victory_font = pygame.font.Font(None, 72)
            text = victory_font.render(f"Winner: {self.board.winner}!",
                                       True, PLAYER_COLORS[self.board.winner])
            self.screen.blit(text, (WIDTH // 2 - 150, HEIGHT // 2))
            pygame.display.flip()
            pygame.time.delay(int(1000 / self.speed))

    def auto_simulate(self, max_games=1000):
        running = True
        while running and self.total_games < max_games:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.speed = min(5, self.speed + 1)
                    elif event.key == pygame.K_DOWN:
                        self.speed = max(1, self.speed - 1)

            self.run_game()
            self.show_winner_message()

        pygame.quit()


if __name__ == "__main__":
    game = GameVisualization(speed=2)
    game.auto_simulate(max_games=100)