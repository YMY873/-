import pygame
import random
import math
import sys
from typing import Dict, List, Tuple

# 游戏常量配置
WIDTH, HEIGHT = 1000, 800
GRID_COUNT = 22
PLAYER_COLORS = {
    'A': (255, 0, 0), 'B': (0, 255, 0), 'C': (0, 0, 255),
    'D': (255, 255, 0), 'E': (255, 0, 255), 'F': (0, 255, 255),
    'G': (128, 128, 128), 'H': (128, 0, 0), 'I': (0, 128, 0),
    'J': (0, 0, 128), 'K': (128, 128, 0), 'L': (128, 0, 128)
}
PLAYERS = ['G', 'H', 'I', 'J', 'K', 'L']


# 技能系统配置
PLAYER_SKILLS: Dict[str, dict] = {
    'A': {'type': 'position_bonus'},
    'B': {'type': 'double_chance', 'prob': 0.28},
    'C': {'type': 'late_move', 'prob': 0.65},
    'D': {'type': 'elevate', 'prob': 0.4},
    'E': {'type': 'solo_move', 'prob': 0.5},
    'F': {'type': 'dice_2d3'},
    'G': {'type': 'last_move_bonus'},
    'H': {'type': 'first_move_bonus'},
    'I': {'type': 'stack_leader', 'triggered': False},
    'J': {'type': 'stack_dice', 'prob': 0.4, 'dice': (1, 3)},
    'K': {'type': 'catch_up', 'prob': 0.6, 'triggered': False},
    'L': {'type': 'half_chance', 'prob': 0.5}
}

class CircularBoard:
    """环形棋盘核心逻辑"""
    def __init__(self):
        self.reset()

    def reset(self):
        """重置游戏状态"""
        self.positions: List[List[str]] = [[] for _ in range(GRID_COUNT)]
        self.winner: str = None
        self.total_steps: Dict[str, int] = {p: 0 for p in PLAYERS}
        self.active_stacks: Dict[int, List[str]] = {}  # 强制移动的堆叠
        self.skill_states: Dict[str, bool] = {p: False for p in PLAYERS}  # 技能触发状态

    def add_player(self, player: str, position: int):
        """添加玩家到指定位置"""
        self.positions[position].append(player)

    def move_player(self, player: str, steps: int, is_solo: bool = False):
        """处理玩家移动"""
        if self.winner:
            return

        # 强制堆叠移动处理
        if self._handle_forced_stack_move(player, steps):
            return

        # 常规移动逻辑
        current_idx = self.find_player_position(player)
        if current_idx is None:
            return

        self.total_steps[player] += steps
        #if self._check_victory(player):
        #    return

        new_idx = (current_idx + steps) % GRID_COUNT
        self._perform_move(player, current_idx, new_idx, is_solo)
        if new_idx == 0:
            self.winner = player
            return True

        self._check_stack_skills(player, new_idx)
        return False

    def _handle_forced_stack_move(self, player: str, steps: int) -> bool:
        """处理强制堆叠移动"""
        current_idx = self.find_player_position(player)
        if current_idx in self.active_stacks and player in self.active_stacks[current_idx]:
            group = self.active_stacks.pop(current_idx)
            new_idx = (current_idx + steps) % GRID_COUNT

            # 移动整个堆叠
            self.positions[current_idx] = [p for p in self.positions[current_idx] if p not in group]
            self.positions[new_idx].extend(group)

            # 更新步数并检查胜利
            for p in group:
                self.total_steps[p] += steps
                if self._check_victory(p):
                    break
            return True
        return False

    def _perform_move(self, player: str, current_idx: int, new_idx: int, is_solo: bool):
        """执行实际的位置移动"""
        current_stack = self.positions[current_idx]
        player_index = current_stack.index(player)

        move_stack = [player] if is_solo else current_stack[player_index:]
        del current_stack[player_index:player_index + len(move_stack)]
        self.positions[new_idx].extend(move_stack)

    def _check_stack_skills(self, player: str, new_idx: int):
        """检查堆叠相关技能"""
        # I技能触发检测
        if (PLAYER_SKILLS[player]['type'] == 'stack_leader'
            and not self.skill_states[player]
            and len(self.positions[new_idx]) > 1):
            self.active_stacks[new_idx] = self.positions[new_idx].copy()
            self.skill_states[player] = True

    def _check_victory(self, player: str) -> bool:
        idx = self.find_player_position(player)
        if idx == 0:
            self.winner = player
            return True
        return False

    def find_player_position(self, player: str) -> int:
        """查找玩家当前位置"""
        for idx, stack in enumerate(self.positions):
            if player in stack:
                return idx
        return None

    def get_player_stack_size(self, player: str) -> int:
        """获取玩家所在堆叠大小"""
        idx = self.find_player_position(player)
        return len(self.positions[idx]) if idx is not None else 0

    def is_last_place(self, player: str) -> bool:
        """判断是否为最后一名"""
        player_pos = self.find_player_position(player)
        all_pos = [self.find_player_position(p) for p in PLAYERS if p != player]
        return all(p >= player_pos for p in all_pos if p is not None)

class GameLogic:
    """游戏逻辑处理器"""
    @staticmethod
    def apply_pre_skills(player: str, board: CircularBoard, base_steps: int, turn_info: dict) -> int:
        """应用移动前技能"""
        steps = base_steps
        skill = PLAYER_SKILLS[player]

        # 顺序加成技能
        if skill['type'] == 'last_move_bonus' and turn_info['is_last']:
            steps += 2
        elif skill['type'] == 'first_move_bonus' and turn_info['is_first']:
            steps += 2

        # 其他技能处理
        skill_handlers = {
            'position_bonus': lambda: steps + 3 if board.is_last_place(player) else steps,
            'double_chance': lambda: steps * 2 if random.random() < skill['prob'] else steps,
            'solo_move': lambda: steps + (board.get_player_stack_size(player) - 1)
                              if random.random() < skill['prob'] else steps,
            'half_chance': lambda: steps + 1 if random.random() < skill['prob'] else steps,
            'stack_dice': lambda: steps + 2 if (board.get_player_stack_size(player) > 1
                                             and random.random() < skill['prob']) else steps,
            'catch_up': lambda: steps + 2 if (board.skill_states[player]
                                            and random.random() < skill['prob']) else steps
        }

        return skill_handlers.get(skill['type'], lambda: steps)()

    @staticmethod
    def apply_post_skills(player: str, board: CircularBoard):
        """应用移动后技能"""
        skill = PLAYER_SKILLS[player]
        idx = board.find_player_position(player)

        # K技能触发
        if (skill['type'] == 'catch_up'
            and not board.skill_states[player]
            and board.is_last_place(player)):
            board.skill_states[player] = True

        # 提升到堆叠顶部
        if skill['type'] == 'elevate' and idx is not None:
            if random.random() < skill['prob'] and (stack := board.positions[idx]):
                if player in stack:
                    stack.remove(player)
                    stack.append(player)

class GameVisualization:
    """游戏可视化系统"""
    def __init__(self, speed=2):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.font = pygame.font.Font(None, 24)
        self.board = CircularBoard()
        self.clock = pygame.time.Clock()
        self.grid_positions = self._calculate_positions()
        self.speed = speed
        self.win_counts = {p: 0 for p in PLAYERS}
        self.total_games = 0
        self.current_turn_order = []

    def _calculate_positions(self) -> List[Tuple[float, float]]:
        """计算棋盘网格坐标"""
        radius = min(WIDTH, HEIGHT) * 0.4
        center = (WIDTH // 2, HEIGHT // 2)
        return [
            (
                center[0] + radius * math.cos(2 * math.pi * i / GRID_COUNT),
                center[1] + radius * math.sin(2 * math.pi * i / GRID_COUNT)
            )
            for i in range(GRID_COUNT)
        ]

    def draw_board(self):
        """绘制游戏界面"""
        self.screen.fill((255, 255, 255))

        # 绘制网格和玩家
        for idx, (x, y) in enumerate(self.grid_positions):
            # 网格编号
            text = self.font.render(str(idx), True, (0, 0, 0))
            self.screen.blit(text, (x - 10, y - 10))

            # 玩家棋子
            players = self.board.positions[idx]
            for i, player in enumerate(players):
                color = PLAYER_COLORS[player]
                pos = (x + i * 15, y + i * 15)
                pygame.draw.circle(self.screen, color, pos, 10)
                text = self.font.render(player, True, (0, 0, 0))
                self.screen.blit(text, (pos[0] - 5, pos[1] - 8))

            # 强制堆叠标记
            if idx in self.board.active_stacks:
                pygame.draw.rect(self.screen, (255, 0, 0), (x - 15, y - 15, 30, 30), 2)

        # 统计信息
        stats = " | ".join(f"{k}:{v}" for k, v in self.win_counts.items())
        stat_text = self.font.render(f"Total Games: {self.total_games}  {stats}", True, (0, 0, 0))
        self.screen.blit(stat_text, (20, HEIGHT - 40))

        # 速度显示
        speed_text = self.font.render(f"Speed: {self.speed} (Up/Down Arrow)", True, (0, 0, 0))
        self.screen.blit(speed_text, (20, 20))

        pygame.display.flip()

    def initialize_players(self, base_order):
        self.board.positions = [[] for _ in range(GRID_COUNT)]
        initial_pos = 1  # 固定初始位置为1

    # 仅保留G-L玩家并按逆序添加形成正确堆叠
        for player in reversed(base_order):  # 逆序遍历确保最后行动者位于堆叠底部
            if player in PLAYERS:  # 双重保险确保仅包含目标玩家
                self.board.add_player(player, initial_pos)



    def process_turn(self, player: str, turn_info: dict):
        """处理单个玩家回合"""
        # 骰子判定
        dice = self._roll_dice(player)

        # 技能处理
        steps = GameLogic.apply_pre_skills(player, self.board, dice, turn_info)
        is_solo = self._check_solo_move(player)

        # 执行移动
        self.board.move_player(player, steps, is_solo)
        GameLogic.apply_post_skills(player, self.board)

        self.update_display()

    def _roll_dice(self, player: str) -> int:
        """投掷骰子"""
        skill = PLAYER_SKILLS[player]
        if skill['type'] == 'dice_2d3':
            return random.randint(2, 3)
        if skill['type'] == 'stack_dice':
            return random.choice(skill['dice'])
        return random.randint(1, 3)

    def _check_solo_move(self, player: str) -> bool:
        """检查是否触发单走"""
        skill = PLAYER_SKILLS[player]
        return skill['type'] == 'solo_move' and random.random() < skill['prob']

    def adjust_move_order(self, base_order: List[str]) -> List[str]:
        """调整移动顺序（处理C的延迟移动）"""
        ordered = list(base_order)
        for i, p in enumerate(base_order):
            if p == 'C' and PLAYER_SKILLS[p]['type'] == 'late_move':
                idx = self.board.find_player_position(p)
                if idx is not None and self.board.positions[idx].index(p) > 0:
                    if random.random() < 0.65:
                        ordered.append(ordered.pop(i))
                        break  # 每个回合只调整一次
        return ordered

    def run_game(self):
        self.board.reset()
        base_order = random.sample(PLAYERS, len(PLAYERS))  # 生成随机顺序
        current_order = self.adjust_move_order(base_order)
        self.current_turn_order = current_order
        self.initialize_players(base_order)  # 使用生成的顺序初始化


        while not self.board.winner:
            base_order = random.sample(PLAYERS, len(PLAYERS))
            current_order = self.adjust_move_order(base_order)
            self.current_turn_order = current_order

            for i, player in enumerate(current_order):
                if self.board.winner:
                    break

                turn_info = {
                    'is_first': i == 0,
                    'is_last': i == len(current_order)-1
                }
                self.process_turn(player, turn_info)
                self.update_display()

        if self.board.winner:
            self.win_counts[self.board.winner] += 1
            self.total_games += 1

    def update_display(self):
        """更新显示"""
        self.draw_board()
        pygame.display.flip()
        pygame.time.delay(int(500 / self.speed))

    def auto_simulate(self, max_games=1000):
        """自动模拟多局游戏"""
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
            self._show_winner_message()

        pygame.quit()

    def _show_winner_message(self):
        """显示胜利信息"""
        if winner := self.board.winner:
            victory_font = pygame.font.Font(None, 72)
            text = victory_font.render(f"Winner: {winner}!", True, PLAYER_COLORS[winner])
            self.screen.blit(text, (WIDTH//2-150, HEIGHT//2))
            pygame.display.flip()
            pygame.time.delay(int(1000/self.speed))

if __name__ == "__main__":
    game = GameVisualization(speed=2)
    game.auto_simulate(max_games=100)

