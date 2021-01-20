import pygame
import pygame.freetype  # Import the freetype module.
import game
import math

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
# GAME_FONT = pygame.freetype.Font("your_font.ttf", 24)

EPSILON = game.EPSILON

CIRCLE_SIZE = 5
OUTLINE_SIZE = 2
LINE_WIDTH = 3


class UIState:
    def __init__(self):
        self.state = game.GameState()
        self.state.new_game()
        self.click_state = 0 # 0 - waiting for first point, 1 - waiting for second point, 2 - waiting for area select
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

        self.zoom = 50
        self.pan = [100, 125]


def color_translate(color_id):
    if color_id == -1:
        return BLACK
    elif color_id == 1:
        return RED
    elif color_id == 2:
        return BLUE


def draw_polygon(win, color, points, ui_state):
    points = [transform_pair(p, ui_state) for p in points]
    pygame.draw.polygon(win, color, points)


def draw_line(win, color, p1, p2, size, ui_state):
    pair_1 = transform_pair(p1, ui_state)
    pair_2 = transform_pair(p2, ui_state)
    pygame.draw.line(win, color, pair_1, pair_2, size)


def draw_circle(win, color, p1, size, ui_state, width=0):
    pair_1 = transform_pair(p1, ui_state)
    pygame.draw.circle(win, color, pair_1, size, width=width)


def draw_lines(win, ui_state):
    for line in ui_state.state.lines:
        color = color_translate(line.color)
        draw_line(win, color, line.endpoints[0].pair(), line.endpoints[1].pair(), LINE_WIDTH, ui_state)


def draw_areas(win, ui_state):
    for area in ui_state.state.areas:
        color = color_translate(area.color)
        draw_polygon(win, color, [x.pair() for x in area.points], ui_state)


def mouse_click(pos, ui_state):
    ui_state.area_cache = []
    ui_state.last_area = None
    if ui_state.click_state == 0:
        ui_state.click_state = 1
    elif ui_state.click_state == 1:
        line_player = ui_state.state.next_player
        move = game.Move(p1=ui_state.first_point, p1_line=ui_state.first_line, p2=ui_state.second_point, p2_line=ui_state.second_line, area=None)
        ui_state.first_point = None
        ui_state.first_line = None
        ui_state.second_point = None
        ui_state.second_line = None
        if not game.is_legal_move(move, ui_state.state):
            ui_state.click_state = 0
            return
        game.make_move(move, ui_state.state)
        if ui_state.state.area_split_line is None:
            ui_state.click_state = 0
            ui_state.color_to_move = color_translate(ui_state.state.next_player)
        else:
            ui_state.click_state = 2
            ui_state.areas = game.get_areas(ui_state.state.area_split_line, ui_state.state, color=line_player)
            ui_state.area_choice = None
    elif ui_state.click_state == 2:
        move = game.Move(area=ui_state.area_choice)
        if not game.is_legal_move(move, ui_state.state):
            return
        game.make_move(move, ui_state.state)
        ui_state.area_choice = None
        ui_state.color_to_move = color_translate(ui_state.state.next_player)
        ui_state.click_state = 0


def mouse_move(pos, ui_state):
    if ui_state.game_area.contains(pos, ui_state.state, ignore_lines=[l for l in ui_state.state.lines if l.color != -1]):
        if not (ui_state.last_area and ui_state.last_area.contains(pos, ui_state.state)):
            found_area = False
            for area in ui_state.area_cache:
                if area != ui_state.last_area and area.contains(pos, ui_state.state):
                    ui_state.last_area = area
                    found_area = True
                    break
            if not found_area:
                area = game.get_surrounding_area(pos, ui_state.state)
                if area:
                    print(f'Calculated surrounding area: {len(area.points)}')
                    ui_state.last_area = area
                    ui_state.area_cache.append(area)
                else:
                    print(f'No area found')
            else:
                print('found area in cache')
        if ui_state.last_area:
            ui_state.hover_score = ui_state.last_area.score
    else:
        ui_state.hover_score = 0.0
    if ui_state.click_state == 0:
        closest_points = [line.closest_point(pos) for line in ui_state.state.lines]
        distances = [cp.distance(pos) for cp in closest_points]
        closest_point_index = min(enumerate(distances), key=lambda x: x[1])[0]

        ui_state.first_point = closest_points[closest_point_index]
        ui_state.first_line = ui_state.state.lines[closest_point_index]

    elif ui_state.click_state == 1:
        farthest_dist = ui_state.state.width * math.sqrt(2) + 1
        mouse_theta = math.atan((ui_state.first_point.y - pos.y)/(ui_state.first_point.x - pos.x + EPSILON))
        if abs(pos.x - ui_state.first_point.x) < EPSILON or pos.x < ui_state.first_point.x:
            mouse_theta += math.pi
        farthest_point = game.GamePoint(ui_state.first_point.x + math.cos(mouse_theta)*farthest_dist, ui_state.first_point.y + math.sin(mouse_theta)*farthest_dist)
        created_line = game.GameLine(ui_state.first_point, farthest_point)

        other_lines = ui_state.state.lines[:]
        other_lines.remove(ui_state.first_line)

        intersections = [line.intersection(created_line) for line in other_lines]
        line_intersections = list(zip(other_lines, intersections))
        line_intersections = list(filter(lambda x: x[1] is not None, line_intersections))



        if not line_intersections:
            ui_state.second_point = None
            ui_state.second_line = None
        else:
            distances = [ui_state.first_point.distance(intersection) for _, intersection in line_intersections]
            min_index = min(enumerate(distances), key=lambda x: x[1])[0]

            temp_line = game.GameLine(line_intersections[min_index][1], ui_state.first_point)

            midpoint = temp_line.midpoint()
            in_scored_area = False
            for area in ui_state.state.areas:
                if area.contains(midpoint, ui_state.state):
                    in_scored_area = True
            if in_scored_area:
                ui_state.second_point = None
                ui_state.second_line = None
            else:
                ui_state.second_point = line_intersections[min_index][1]
                ui_state.second_line = line_intersections[min_index][0]
    elif ui_state.click_state == 2:
        if ui_state.areas[0].contains(pos, ui_state.state):
            ui_state.area_choice = ui_state.areas[0]
        elif ui_state.areas[1].contains(pos, ui_state.state):
            ui_state.area_choice = ui_state.areas[1]
        else:
            ui_state.area_choice = None




        # other_lines = ui_state.state.lines[:]
        # other_lines.remove(ui_state.first_line)
        # closest_points = [line.closest_point(pos) for line in other_lines]
        # distances = [cp.distance(pos) for cp in closest_points]
        # cp_line = list(zip(closest_points, other_lines, distances))
        # cp_line.sort(key=lambda x: x[2])
        #
        # for closest_point, line, _ in cp_line:
        #     created_line = game.GameLine(ui_state.first_point, closest_point, ui_state.state.next_player)
        #     found_coll = False
        #     # Check for collisions
        #     for coll_line in other_lines:
        #         if coll_line == line:
        #             continue
        #         if created_line.intersection(coll_line):
        #             found_coll = True
        #             break
        #     if not found_coll:
        #         break
        #
        # ui_state.second_point = closest_point
        # ui_state.second_line = line


# def display_message(content):
#     pygame.time.delay(500)
#     win.fill(WHITE)
#     end_text = END_FONT.render(content, 1, BLACK)
#     win.blit(end_text, ((WIDTH - end_text.get_width()) // 2, (WIDTH - end_text.get_height()) // 2))
#     pygame.display.update()
#     pygame.time.delay(3000)


def transform_pair(pair, ui_state):
    return pair[0] * ui_state.zoom + ui_state.pan[0], pair[1] * ui_state.zoom + ui_state.pan[1]


def render(win, ui_state):
    win.fill(WHITE)

    GAME_FONT.render_to(win, (20, 25), f"P1 Score: {ui_state.state.scores[0]}", (0, 0, 0))
    GAME_FONT.render_to(win, (20, 50), f"P2 Score: {ui_state.state.scores[1]}", (0, 0, 0))
    GAME_FONT.render_to(win, (20, 75), f"Player {ui_state.state.next_player} to {'choose' if ui_state.state.area_split_line else 'move'}", (0, 0, 0))
    GAME_FONT.render_to(win, (20, 100), f"Area hover score: {ui_state.hover_score}", (0, 0, 0))

    draw_areas(win, ui_state)

    if ui_state.area_choice:
        points = [x.pair() for x in ui_state.area_choice.points]
        draw_polygon(win, ui_state.color_to_move, points, ui_state)

    draw_lines(win, ui_state)

    if ui_state.first_point:
        first_line_color = color_translate(ui_state.first_line.color)
        draw_circle(win, first_line_color, ui_state.first_point.pair(), CIRCLE_SIZE, ui_state)
        draw_circle(win, ui_state.color_to_move, ui_state.first_point.pair(), CIRCLE_SIZE, ui_state, width=OUTLINE_SIZE)

    if ui_state.second_point:
        draw_line(win, ui_state.color_to_move, ui_state.first_point.pair(), ui_state.second_point.pair(), LINE_WIDTH, ui_state)
        second_line_color = color_translate(ui_state.second_line.color)
        draw_circle(win, second_line_color, ui_state.second_point.pair(), CIRCLE_SIZE, ui_state)
        draw_circle(win, ui_state.color_to_move, ui_state.second_point.pair(), CIRCLE_SIZE, ui_state, width=OUTLINE_SIZE)


    # # Drawing X's and O's
    # for image in images:
    #     x, y, IMAGE = image
    #     win.blit(IMAGE, (x - IMAGE.get_width() // 2, y - IMAGE.get_height() // 2))

    pygame.display.update()

# class UIState:
#     def __init__(self):
#         self.state = game.GameState()
#         self.state.new_game()
#         self.click_state = 0 # 0 - waiting for first point, 1 - waiting for second point, 2 - waiting for area select
#         self.color_to_move = RED
#         self.first_point = None

def main():
    win = pygame.display.set_mode((WIDTH, WIDTH))
    pygame.display.set_caption("Split")

    ui_state = UIState()

    run = True

    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()

            # Reverse transform mouse
            mouse_position = pygame.mouse.get_pos()
            mouse_position = game.GamePoint((mouse_position[0]-ui_state.pan[0])/ui_state.zoom, (mouse_position[1]-ui_state.pan[1])/ui_state.zoom)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    ui_state.zoom *= 1.5
                elif event.button == 5:
                    ui_state.zoom /= 1.5
                else:
                    mouse_click(mouse_position, ui_state)
            if event.type == pygame.MOUSEMOTION:
                mouse_move(mouse_position, ui_state)
        keys = pygame.key.get_pressed()  #checking pressed keys
        if keys[pygame.K_w]:
            ui_state.pan[1] += 1
        if keys[pygame.K_a]:
            ui_state.pan[0] += 1
        if keys[pygame.K_s]:
            ui_state.pan[1] -= 1
        if keys[pygame.K_d]:
            ui_state.pan[0] -= 1

        render(win, ui_state)


while True:
    if __name__ == '__main__':
        main()
