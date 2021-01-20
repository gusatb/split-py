"""Game logic for Split.

Rules:
    Game starts with a square of neutral colored lines.
    (Pie rule for first move?)
    Players take turns drawing line segments of their color with each endpoint touching preexisting lines and not crossing any lines.
    Endpoints of lines cannot be placed on intersections.
    If both endpoints are on lines of the players color, one of the areas is filled with their color (opponents choice).
    A line may not be played if one of the resulting areas is less than the min area limit.
    Player with more area colored wins when no more legal moves remain.
"""

import math


EPSILON = 1e-5


# Game State

class GamePoint:
    """

    Attributes:
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y
        # self.color = color
        self.lines = []

    def is_at(self, point):
        return self.x == point.x and self.y == point.y

    def pair(self):
        return self.x, self.y

    def distance(self, point):
        return math.sqrt((self.y - point.y)**2 + (self.x - point.x)**2)

class GameLine:
    def __init__(self, p1, p2, color=None, add_self_to_points=False):
        self.endpoints = [p1, p2]
        self.color = color
        # Helpers for calculating intersections
        self.A = (p1.y - p2.y)
        self.B = (p2.x - p1.x)
        self.C = -1 * (p1.x*p2.y - p2.x*p1.y)
        if add_self_to_points:
            for ep in self.endpoints:
                assert self not in ep.lines
                ep.lines.append(self)

    def intersection(self, line):
        D  = self.A * line.B - self.B * line.A
        Dx = self.C * line.B - self.B * line.C
        Dy = self.A * line.C - self.C * line.A
        if D != 0:
            x = Dx / D
            y = Dy / D
            intersect_point = GamePoint(x, y)
            if self.contains(intersect_point) and line.contains(intersect_point):
                return intersect_point
        return None

    def slope(self):
        return (self.endpoints[0].y - self.endpoints[1].y) / (self.endpoints[0].x - self.endpoints[1].x + EPSILON)

    def midpoint(self):
        return GamePoint((self.endpoints[0].x + self.endpoints[1].x)/2, (self.endpoints[0].y + self.endpoints[1].y)/2)

    def length(self):
        return self.endpoints[0].distance(self.endpoints[1])

    def closest_point(self, point):
        line_slope = (self.endpoints[0].y - self.endpoints[1].y)/(self.endpoints[0].x - self.endpoints[1].x + EPSILON)
        perp_slope = -1 / (line_slope + EPSILON)

        on_line_x = (perp_slope * point.x - point.y - line_slope * self.endpoints[0].x + self.endpoints[0].y)/(perp_slope - line_slope)
        on_line_y = perp_slope * (on_line_x - point.x) + point.y
        on_line = GamePoint(on_line_x, on_line_y)

        on_line_dists = [ep.distance(on_line) for ep in self.endpoints]
        line_length = self.length()
        if max(on_line_dists) > line_length: # Endpoint is closest
            point_dists = [ep.distance(point) for ep in self.endpoints]
            closest_point = self.endpoints[min(enumerate(point_dists), key=lambda x: x[1])[0]]
            return closest_point
        else:
            return on_line

    def contains(self, point):
        dists = [x.distance(point) for x in self.endpoints]
        return abs(sum(dists) - self.length()) <= 0.01


def fix_tan(p1, p2):
    theta = math.atan((p1.y - p2.y)/(p1.x - p2.x + EPSILON))
    if abs(p2.x - p1.x) < EPSILON or p2.x < p1.x:
        theta += math.pi
    return theta

class Area:
    def __init__(self, points, color=None):
        """Calculates area inside points.

        Args:
            points: List of points in clockwise or counterclockwise order.
            color: Color for area
        """
        self.points = points
        self.color = color
        self.score = self.calculate_score()

    def calculate_score(self):
        points = self.points
        n = len(points)
        term1 = sum([self.points[i].x * self.points[(i+1)%n].y for i in range(n)])
        term2 = sum([self.points[i].y * self.points[(i+1)%n].x for i in range(n)])
        return 0.5 * (term1 - term2)

    def contains(self, point, state, ignore_lines=[]):
        for p in self.points:
            if not clear_path(p, point, state, ignore_lines):
                return False
        return True
        # theta_diffs = []
        # print('cs')
        # for i in range(len(self.points)):
        #     p1 = self.points[i]
        #     p2 = self.points[(i+1)%len(self.points)]
        #     # theta_1 = math.atan((p1.y - point.y) / (p1.x - point.x + EPSILON))
        #     theta_1 = fix_tan(p1, point)
        #     # theta_2 = math.atan((p2.y - point.y) / (p2.x - point.x + EPSILON))
        #     theta_2 = fix_tan(p2, point)
        #     theta_diff = theta_1 - theta_2
        #     theta_diff += 2*math.pi
        #     theta_diff %= 2*math.pi
        #     if theta_diff > math.pi:
        #         theta_diff = 2*math.pi - theta_diff
        #     theta_diffs.append(theta_diff)
        #     print(theta_1, theta_2, theta_diff)
        # print('ce')
        # return sum(theta_diffs) > 2*math.pi - 0.1



class GameState:
    def __init__(self):
        self.width = 10
        self.min_score = 5
        # self.points = [] # Necessary?
        self.areas = [] # Scored and filled areas.
        self.lines = []
        self.next_player = 1
        self.area_split_line = None # If not None, then next turn is area selection
        self.scores = [0, 0]

    def new_game(self):
        p1 = GamePoint(0, 0)
        p2 = GamePoint(0, self.width)
        p3 = GamePoint(self.width, self.width)
        p4 = GamePoint(self.width, 0)
        self.game_area = Area([p1, p2, p3, p4])
        self.lines = [
            GameLine(p1, p2, -1, add_self_to_points=True),
            GameLine(p2, p3, -1, add_self_to_points=True),
            GameLine(p3, p4, -1, add_self_to_points=True),
            GameLine(p4, p1, -1, add_self_to_points=True),
        ]
        self.scores = [0, 0]

    def get_game_area(self):
        return self.game_area

# Make Move

class Move:
    """

    Attributes:
        line_move: Whether or not this move is a new line being placed.
        p1: Endpoint 1 of new line.
        p1_line: Line that will be split by p1 once move is played.
        p2: Endpoint 2 of new line.
        p2_line: Line that will be split by p2 once move is played.
        area: List of points
    """
    def __init__(self, p1=None, p1_line=True, p2=None, p2_line=True, area=None):
        self.line_move = area is None
        self.p1 = p1
        self.p1_line = p1_line
        self.p2 = p2
        self.p2_line = p2_line
        self.area = area


def is_legal_move(move, state):
    if not move.line_move:
        # TODO(gusatb): Add test to ensure points are legal area.
        if not move.area:
            print('Illegal move: Area must be chosen.')
        return move.area
    else:
        if state.area_split_line is not None:
            print('Illegal move: Line move is set and area split is supplied.')
            return False
        if not move.p1 or not move.p2:
            print('Illegal move: Line move must have two points.')
            return False
        # A move is legal if the created line does not cross any other lines,
        # and each point is on a unique line.
        temp_line = GameLine(move.p1, move.p2)
        for line in state.lines:
            # Check if either point already exists
            for ep in line.endpoints:
                if move.p1.is_at(ep) or move.p2.is_at(ep):
                    print('Illegal move: Cannot move on an existing endpoint.')
                    return False
            # Check if points are shared by a line
            if (move.p1_line == line or move.p2_line == line) and temp_line.slope() == line.slope():
                print('Illegal move: Both points are on the same line.')
                return False
            # Check for intersection
            if temp_line.intersection(line) and move.p1_line != line and move.p2_line != line:
                print('Illegal move: Crosses an existing line.')
                return False
        # Check the area the line crosses
        midpoint = temp_line.midpoint()
        for area in state.areas:
            if area.contains(midpoint, state):
                print('Illegal move: Cannot move in scored area.')
                return False
        return True


def clear_path(p1, p2, state, ignore_lines=[]):
    temp_line = GameLine(p1, p2)
    for line in state.lines:
        if line in ignore_lines:
            continue
        if temp_line.intersection(line) and line not in p1.lines and line not in p2.lines:
            return False
    return True

def get_surrounding_area(pos, state):
    """Returns area surrounding point.

    Args:
        split_line: Position.
        state: GameState object.
    """
    # Get all points
    points = set()
    for line in state.lines:
        points.add(line.endpoints[0])
        points.add(line.endpoints[1])
    # Filter to visible points
    middle = pos
    points = list(filter(lambda x: clear_path(middle, x, state), points))
    # Order points
    thetas = []
    for p in points:
        theta = math.atan((p.y - middle.y)/(p.x - middle.x + EPSILON))
        if abs(middle.x - p.x) < EPSILON or middle.x < p.x:
            theta += math.pi
        thetas.append(theta)
    point_thetas = list(zip(points, thetas))
    point_thetas.sort(key=lambda x: x[1])

    points, thetas = list(zip(*point_thetas))

    if len(points) < 3:
        return None

    return Area(points)

def get_areas(split_line, state, color):
    """Returns split areas.

    Args:
        split_line: New line splitting the area into 2.
        state: GameState object.
    """
    # Get all points
    points = set()
    for line in state.lines:
        points.add(line.endpoints[0])
        points.add(line.endpoints[1])
    # Filter to visible points
    middle = split_line.midpoint()
    points = list(filter(lambda x: clear_path(middle, x, state, ignore_lines=[split_line]), points))
    # Order points
    thetas = []
    for p in points:
        theta = math.atan((p.y - middle.y)/(p.x - middle.x + EPSILON))
        if abs(middle.x - p.x) < EPSILON or middle.x < p.x:
            theta += math.pi
        thetas.append(theta)
    point_thetas = list(zip(points, thetas))
    point_thetas.sort(key=lambda x: x[1])

    if len(points) != len(thetas):
        return None
    points, thetas = list(zip(*point_thetas))

    # Split the areas
    split_point_indexes = [points.index(ep) for ep in split_line.endpoints]

    i1 = min(split_point_indexes)
    i2 = max(split_point_indexes)

    area_1 = points[i1:i2+1]
    area_2 = points[0:i1+1] + points[i2:]

    if len(area_1) < 3 or len(area_2) < 3:
        return None

    return Area(area_1, color), Area(area_2, color)


    # Find a line with two visible endpoints
    # first_line = None
    # for line in state.lines:
    #     if clear_path(middle, line.endpoints[0], state) and clear_path(middle, line.endpoints[1], state):
    #         first_line = line
    #         break
    # assert first_line is not None
    # points = [first_line.endpoints[0]]
    # current_point = first_line.endpoints[1]
    # current_line = first_line
    # while current_point != points[0]:
    #     print([x.pair() for x in points])
    #     print('Adding: ', current_point.pair())
    #     assert current_point not in points
    #     points.append(current_point)
    #     # Search other lines for next point
    #     for line in current_point.lines:
    #         if line == current_line:
    #             continue
    #         ep = line.endpoints[1 - line.endpoints.index(current_point)]
    #         if clear_path(middle, ep, state):
    #             current_point = ep
    #             current_line = line
    #             break
    # return points


def split_line(old_line, new_point, state):
    """

    Note: Does not update areas.
    """
    state.lines.remove(old_line)
    new_lines = []
    for ep in old_line.endpoints:
        new_line = GameLine(ep, new_point, color=old_line.color, add_self_to_points=True)
        ep.lines.remove(old_line)
        state.lines.append(new_line)



def make_move(move, state):
    """Make a move and update the state.

    Args:
        move: Move object.
        state: GameState
    """
    assert is_legal_move(move, state)
    if state.area_split_line is not None:
        state.areas.append(move.area)
        state.scores[move.area.color - 1] += move.area.score
        state.area_split_line = None
    else:
        split_line(move.p1_line, move.p1, state)
        split_line(move.p2_line, move.p2, state)
        new_line = GameLine(move.p1, move.p2, color=state.next_player, add_self_to_points=True)
        state.lines.append(new_line)

        # Check for endgame fill
        areas = get_areas(new_line, state, state.next_player)
        total_score = areas[0].score + areas[1].score
        if total_score <= state.min_score:
            state.areas.extend(areas)
            state.scores[state.next_player-1] += total_score
        elif move.p1_line.color == state.next_player and move.p2_line.color == state.next_player:
            state.area_split_line = new_line
        state.next_player = 3 - state.next_player



# Get End State




