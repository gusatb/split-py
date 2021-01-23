import pygame
import pygame.freetype  # Import the freetype module.
import game
import math
import bots
import remote_play

# Initializing Pygame
pygame.init()

# Screen
WIDTH = 1000

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Fonts
GAME_FONT = pygame.freetype.SysFont('courier', 20)

EPSILON = game.EPSILON

CIRCLE_SIZE = 5
OUTLINE_SIZE = 2
LINE_WIDTH = 3


class UIState:
    """State of UI including GameState, and move being made.

    Attributes:
        state: GameState.
        click_state: Stage of move being made: 0 - waiting for first point, 1 - waiting for second point, 2 - waiting for area select
        color_to_move: RGB tuple color of player moving.
        first_point: GamePoint of first point in a move.
        first_line: GameLine containing first_point.
        second_point: GamePoint of second point in a move.
        second_line: GameLine containing second_point.
        areas: If not None, tuple of 2 GameAreas to choose between.
        area_choice: GameArea to choose as a move.
        game_area: GameArea containing entire playable area.
        area_cache: List of GameAreas (scored or unscored).
        last_area: Last GameArea mouse was in.
        hover_score: Score of GameArea surrounding mouse position.
        window: Pygame window to draw to.
        zoom: Amount to zoom when drawing to window.
        pan: Amount to pan when drawing window.
        intro_state: Which stage of choosing the game is in: 0 - waiting for first line, 1 - waiting for color choice, 2 - normal game
        players: List of GamePlayer.
    """
    def __init__(self, window, players=[game.GamePlayer(), game.GamePlayer()]):
        self.state = game.GameState()
        self.state.new_game()
        self.click_state = 0
        self.color_to_move = color_translate(self.state.next_player)
        self.first_point = None
        self.first_line = None
        self.second_point = None
        self.second_line = None
        self.areas = None
        self.area_choice = None

        self.game_area = self.state.get_game_area()

        self.area_cache = []
        self.last_area = None
        self.hover_score = 0.0

        self.window = window
        self.zoom = 50
        self.pan = [100, 125]

        self.intro_state = 0
        self.players = players

    def can_draw_fill(self):
        """Returns whether the local player can currently draw a line or choose an area."""
        return self.players[self.state.next_player - 1].local_human and self.intro_state != 1

    def can_choose_color(self):
        """Returns whether the local player can currently choose a color."""
        return self.players[self.state.next_player - 1].local_human and self.intro_state == 1

    def choose_color(self, choose_red):
        """Chooses color.

        Args:
            move: Whether to choose to play as Red.
        """
        assert self.intro_state == 1
        other_player = self.players[2 - self.state.next_player]
        if choose_red:
            p0 = self.players.pop(0)
            self.players.append(p0)
        other_player.update_color_choice(choose_red)
        self.intro_state = 2


    def make_move(self, move):
        """Makes given move.

        Args:
            move: GameMove to make.
        """
        assert self.intro_state != 1
        line_player = self.state.next_player # used to color area choices
        other_player = self.players[2 - self.state.next_player]
        self.state.make_move(move)
        other_player.update_move(move)
        self.color_to_move = color_translate(self.state.next_player)

        if self.intro_state == 0:
            self.intro_state = 1


        if self.players[self.state.next_player - 1].local_human:
            if self.state.area_split_line is None:
                self.click_state = 0
            else:
                self.click_state = 2
                self.areas = self.state.get_areas(self.state.area_split_line, color=line_player)
                self.area_choice = None


    def cancel_move(self):
        """Resets current move state. Does not effect GameState."""
        self.click_state = 2 if self.state.area_split_line else 0
        self.first_point = None
        self.first_line = None
        self.second_point = None
        self.second_line = None
        self.area_choice = None
        self.area_cache = []
        self.last_area = None
        self.hover_score = 0.0

    def draw_polygon(self, color, points):
        """Fills polygon represented by points.

        Args:
            color: RGB tuple color.
            points: Ordered xy tuples representing vertices of polygon to draw.
        """
        points = [self.transform_pair(p) for p in points]
        pygame.draw.polygon(self.window, color, points)

    def draw_line(self, color, p1, p2, size):
        """Draws line between given points.

        Args:
            color: RGB tuple color.
            p1: Endpoint of line segment to draw
            p2: Endpoint of line segment to draw
            size: Width of drawn line segment.
        """
        pair_1 = self.transform_pair(p1)
        pair_2 = self.transform_pair(p2)
        pygame.draw.line(self.window, color, pair_1, pair_2, size)

    def draw_circle(self, color, p1, size, width=0):
        """Draws circle.

        Args:
            color: RGB tuple color.
            p1: Center of circle to draw.
            size: Radius of drawn circle.
            width: Width of circle outline, or 0 to fill.
        """
        pair_1 = self.transform_pair(p1)
        pygame.draw.circle(self.window, color, pair_1, size, width=width)

    def draw_lines(self):
        """Draw all GameLines in GameState."""
        for line in self.state.lines:
            color = color_translate(line.color)
            self.draw_line(color, line.endpoints[0].pair(), line.endpoints[1].pair(), LINE_WIDTH)

    def draw_areas(self):
        """Draw all GameAreas in GameState."""
        for area in self.state.areas:
            color = color_translate(area.color)
            self.draw_polygon(color, [x.pair() for x in area.points])


    def mouse_click(self, pos):
        """Perform mouse click.

        # TODO(gusatb): Describe functionality.

        Args:
            pos: GamePoint representing mouse position.
        """
        self.area_cache = []
        self.last_area = None
        if self.click_state == 0:
            self.click_state = 1
        elif self.click_state == 1:
            # line_player = self.state.next_player
            move = game.GameMove(p1=self.first_point, p1_line=self.first_line, p2=self.second_point, p2_line=self.second_line, area=None)
            self.first_point = None
            self.first_line = None
            self.second_point = None
            self.second_line = None
            if not self.state.is_legal_move(move):
                self.click_state = 0
                return
            self.make_move(move)
        elif self.click_state == 2:
            move = game.GameMove(area=self.area_choice)
            if not self.state.is_legal_move(move):
                return
            self.make_move(move)
            self.area_choice = None
            self.click_state = 0

    def mouse_move(self, pos):
        """Perform mouse move.

        # TODO(gusatb): Describe functionality.

        Args:
            pos: GamePoint representing mouse position.
        """
        if self.game_area.contains(pos, ignore_lines=[l for l in self.state.lines if l.color != -1]):
            if not (self.last_area and self.last_area.contains(pos)):
                found_area = False
                for area in self.area_cache:
                    if area != self.last_area and area.contains(pos):
                        self.last_area = area
                        found_area = True
                        break
                if not found_area:
                    area = self.state.get_surrounding_area(pos)
                    if area:
                        self.last_area = area
                        self.area_cache.append(area)
            if self.last_area:
                self.hover_score = self.last_area.score
        else:
            self.hover_score = 0.0
        if self.click_state == 0:
            closest_points = [line.closest_point(pos) for line in self.state.lines]
            distances = [cp.distance(pos) for cp in closest_points]
            closest_point_index = min(enumerate(distances), key=lambda x: x[1])[0]

            self.first_point = closest_points[closest_point_index]
            self.first_line = self.state.lines[closest_point_index]

        elif self.click_state == 1:
            farthest_dist = self.state.width * math.sqrt(2) + 1
            mouse_theta = game.atan2(self.first_point, pos)
            farthest_point = game.GamePoint(self.first_point.x + math.cos(mouse_theta)*farthest_dist, self.first_point.y + math.sin(mouse_theta)*farthest_dist)
            created_line = game.GameLine(self.first_point, farthest_point)

            other_lines = self.state.lines[:]
            other_lines.remove(self.first_line)

            intersections = [line.intersection(created_line) for line in other_lines]
            line_intersections = list(zip(other_lines, intersections))
            line_intersections = list(filter(lambda x: x[1] is not None, line_intersections))

            if not line_intersections:
                self.second_point = None
                self.second_line = None
            else:
                distances = [self.first_point.distance(intersection) for _, intersection in line_intersections]
                min_index = min(enumerate(distances), key=lambda x: x[1])[0]

                temp_line = game.GameLine(line_intersections[min_index][1], self.first_point)

                midpoint = temp_line.midpoint()
                in_scored_area = False
                for area in self.state.areas:
                    if area.contains(midpoint):
                        in_scored_area = True
                if in_scored_area:
                    self.second_point = None
                    self.second_line = None
                else:
                    self.second_point = line_intersections[min_index][1]
                    self.second_line = line_intersections[min_index][0]
        elif self.click_state == 2:
            if self.areas[0].contains(pos):
                self.area_choice = self.areas[0]
            elif self.areas[1].contains(pos):
                self.area_choice = self.areas[1]
            else:
                self.area_choice = None


    def transform_pair(self, pair):
        """Transforms coordinates of given pair with respect to zoom and pan.

        Args:
            pair: Tuple of coordinates to transform.
        """
        return pair[0] * self.zoom + self.pan[0], pair[1] * self.zoom + self.pan[1]


    def render(self):
        """Render screen."""
        self.window.fill(WHITE)

        GAME_FONT.render_to(self.window, (20, 25), f"P1 Score: {self.state.scores[0]}", (0, 0, 0))
        GAME_FONT.render_to(self.window, (20, 50), f"P2 Score: {self.state.scores[1]}", (0, 0, 0))

        if self.can_choose_color():
            GAME_FONT.render_to(self.window, (20, 75), f"Press 1 to play as Red, Press 2 to play as Blue.", (0, 0, 0))
        else:
            GAME_FONT.render_to(self.window, (20, 75), f"{'Red' if self.state.next_player == 1 else 'Blue'} Player to {'Choose' if self.state.area_split_line else 'Move'}", (0, 0, 0))
            GAME_FONT.render_to(self.window, (20, 100), f"Area Hover Score: {self.hover_score}", (0, 0, 0))


        self.draw_areas()

        if self.area_choice and self.can_draw_fill():
            points = [x.pair() for x in self.area_choice.points]
            self.draw_polygon(color_translate(self.area_choice.color), points)

        self.draw_lines()

        if self.first_point and self.can_draw_fill():
            first_line_color = color_translate(self.first_line.color)
            self.draw_circle(first_line_color, self.first_point.pair(), CIRCLE_SIZE)
            self.draw_circle(self.color_to_move, self.first_point.pair(), CIRCLE_SIZE, width=OUTLINE_SIZE)

        if self.second_point and self.can_draw_fill():
            self.draw_line(self.color_to_move, self.first_point.pair(), self.second_point.pair(), LINE_WIDTH)
            second_line_color = color_translate(self.second_line.color)
            self.draw_circle(second_line_color, self.second_point.pair(), CIRCLE_SIZE)
            self.draw_circle(self.color_to_move, self.second_point.pair(), CIRCLE_SIZE, width=OUTLINE_SIZE)

        pygame.display.update()


def color_translate(color_id):
    """Returns RGB tuple representing GameLine color.

    Args:
        color_id: GameLine color to translate.
    """
    if color_id == -1:
        return BLACK
    elif color_id == 1:
        return RED
    elif color_id == 2:
        return BLUE

def main():
    window = pygame.display.set_mode((WIDTH, WIDTH))
    pygame.display.set_caption("Split")

    opponent = 'remote' # bot/local/remote

    if opponent == 'remote':
        ui_state = UIState(window, players=[remote_play.RemotePlayer('127.0.0.1'), game.GamePlayer()])
        if ui_state.players[0].client_id == 0:
            temp_p = ui_state.players.pop(0)
            ui_state.players.append(temp_p)
    else:
        opponent_player = bots.RandomBot() if opponent == 'bot' else game.GamePlayer()
        # TODO: Shuffle players.
        ui_state = UIState(window, players=[opponent_player, game.GamePlayer()])


    run = True

    while run:

        current_player = ui_state.players[ui_state.state.next_player - 1]
        other_player = ui_state.players[2 - ui_state.state.next_player]
        if not current_player.local_human:
            if ui_state.intro_state == 1:
                choice = current_player.choose_color(ui_state.state)
                ui_state.choose_color(choice)
                other_player.update_color_choice(choice)
            else:
                move = current_player.get_move(ui_state.state)
                ui_state.make_move(move)
                other_player.update_move(move)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()

            # Reverse transform mouse
            mouse_position = pygame.mouse.get_pos()
            mouse_position = game.GamePoint((mouse_position[0]-ui_state.pan[0])/ui_state.zoom, (mouse_position[1]-ui_state.pan[1])/ui_state.zoom)

            if ui_state.can_draw_fill():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        ui_state.zoom *= 1.5
                    elif event.button == 5:
                        ui_state.zoom /= 1.5
                    elif event.button == 3:
                        ui_state.cancel_move()
                    else:
                        ui_state.mouse_click(mouse_position)
                if event.type == pygame.MOUSEMOTION:
                    ui_state.mouse_move(mouse_position)
        keys = pygame.key.get_pressed()  #checking pressed keys
        if keys[pygame.K_w]:
            ui_state.pan[1] += 1
        if keys[pygame.K_a]:
            ui_state.pan[0] += 1
        if keys[pygame.K_s]:
            ui_state.pan[1] -= 1
        if keys[pygame.K_d]:
            ui_state.pan[0] -= 1
        if ui_state.can_choose_color():
            if keys[pygame.K_1]:
                ui_state.choose_color(True)
            if keys[pygame.K_2]:
                ui_state.choose_color(False)

        ui_state.render()


if __name__ == '__main__':
    main()
