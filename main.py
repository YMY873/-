import random
from collections import defaultdict

GRID_COUNT = 23
PLAYERS = ['卡卡罗', '柯莱塔', '长离', '今夕', '椿', '守岸人']
PLAYER_SKILLS = {
    '卡卡罗': {'type': 'position_bonus'},
    '柯莱塔': {'type': 'double_chance', 'prob': 0.28},
    '长离': {'type': 'late_move', 'prob': 0.65},
    '今夕': {'type': 'elevate', 'prob': 0.4},
    '椿': {'type': 'solo_move', 'prob': 0.5},
    '守岸人': {'type': 'dice_2d3'}
}


class CircularBoard:
    def __init__(self):
        self.reset()

    def reset(self):
        self.positions = [[] for _ in range(GRID_COUNT)]
        self.winner = None
        self.total_steps = defaultdict(int)

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
        return len(self.positions[idx]) if idx else 0

    def is_last_place(self, player):
        player_pos = self.find_player_position(player)
        all_pos = [self.find_player_position(p) for p in PLAYERS if p != player]
        return all(p >= player_pos for p in all_pos if p is not None)


class GameSimulator:
    def __init__(self):
        self.board = CircularBoard()
        self.win_counts = defaultdict(int)
        self.initial_order = []

    def initialize_players(self):
        self.board.positions = [[] for _ in range(GRID_COUNT)]
        self.board.add_player('卡卡罗', 0)
        self.board.add_player('长离', 22)
        self.board.add_player('柯莱塔', 22)
        self.board.add_player('椿', 21)
        self.board.add_player('今夕', 21)
        self.board.add_player('守岸人', 20)

    def process_turn(self, player):
        dice = self.roll_dice(player)
        steps = self.apply_pre_skills(player, dice)
        is_solo = self.check_solo_move(player)
        self.board.move_player(player, steps, is_solo)
        self.apply_post_skills(player)

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
            if p == '长离' and PLAYER_SKILLS[p]['type'] == 'late_move':
                idx = self.board.find_player_position(p)
                if idx is not None:
                    stack = self.board.positions[idx]
                    if stack.index(p) > 0 and random.random() < 0.65:
                        ordered.append(ordered.pop(i))
                        break
        return ordered

    def run_game(self):
        self.board.reset()
        self.initialize_players()
        self.initial_order = random.sample(PLAYERS, len(PLAYERS))

        while not self.board.winner:
            current_order = self.adjust_move_order(self.initial_order.copy())
            for player in current_order:
                if self.board.winner:
                    break
                self.process_turn(player)

        if self.board.winner:
            self.win_counts[self.board.winner] += 1
        return self.board.winner

    def simulate(self, times=100000):
        for _ in range(times):
            self.run_game()

        print("模拟结果（按胜率排序）：")
        print("=" * 40)
        total = sum(self.win_counts.values())
        for player in sorted(PLAYERS, key=lambda x: -self.win_counts[x]):
            wins = self.win_counts[player]
            print(f"{player}: {wins:>6} 胜 | 胜率 {wins / total * 100:>5.2f}% | 平均每 {total / wins:.1f} 局获胜一次")

        print("\n技能说明：")
        print("-" * 40)
        for p in PLAYERS:
            desc = {
                'position_bonus': '当处于最后位置时+3步',
                'double_chance': '28%概率移动步数×2',
                'late_move': '65%概率在本回合最后行动',
                'elevate': '40%概率升至同格棋子顶部',
                'solo_move': '50%概率单独移动并获得(n-1)步加成',
                'dice_2d3': '固定掷出2-3步骰子'
            }[PLAYER_SKILLS[p]['type']]
            print(f"{p}: {desc}")


if __name__ == "__main__":
    print("开始模拟100,000局游戏...")
    random.seed(2023)  # 固定随机种子确保结果可复现
    simulator = GameSimulator()
    simulator.simulate(100000)