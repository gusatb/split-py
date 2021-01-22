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


# Not used in this file
class GamePlayer:
    """Represents a player.

    A human playing locally making moves through the UI should use this class as is.
    Extend these functions for AI, remote play, or alternate UI.

    Attributes:
        local_human: Whether to wait for a move through the UI or call get_move.
    """
    def __init__(self, local_human=True):
        self.local_human = local_human

    def choose_color(self, state):
        """Returns whether to choose to play as Red.

        Args:
            state: GameState.
        """
        pass

    def get_move(self, state):
        """Returns a GameMove for the current color.

        Args:
            state: GameState to move in.
        """
        pass

    def update_color_choice(self, choose_red):
        """Makes update to internal state given other players move.

        Args:
            choose_red: Whether the other player chose red.
        """
        pass

    def update_move(self, move):
        """Makes update to internal state given other players move.

        Args:
            move: Move made by other player.
        """
        pass


class GamePoint:
    """Represents a point in space.

    Attributes:
        x: X coordinate.
        y: Y coordinate.
        lines: List of GameLine which have an endpoint at this point.
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.lines = []

    def is_at(self, point):
        """Returns whether or not the given point is at the same location as this."""
        return self.x == point.x and self.y == point.y

    def pair(self):
        """Returns tuple containing x and y coordinates."""
        return self.x, self.y

    def distance(self, point):
        """Returns distance between given point and this."""
        return math.sqrt((self.y - point.y)**2 + (self.x - point.x)**2)

class GameLine:
    """Represents a line segment.

    Attributes:
        endpoints: List of two GamePoints.
        color: Color/Owner of line.
        A: Helper for calculating intersections.
        B: Helper for calculating intersections.
        C: Helper for calculating intersections.
    """
    def __init__(self, p1, p2, color=None, add_self_to_points=False):
        """Creates a GameLine.

        Args:
            p1: GamePoint which is an endpoint of this line.
            p2: GamePoint which is an endpoint of this line.
            color: Color/Owner of line.
            add_self_to_points: Whether to add this line to lines attribute of GamePoints p1, p2.
        """
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
        """Returns tuple of coordinates of the intersection of given line and this, or None if no intersection.

        Args:
            line: Line to calculate intersection with.
        """
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
        """Returns slope of this line."""
        return (self.endpoints[0].y - self.endpoints[1].y) / (self.endpoints[0].x - self.endpoints[1].x + EPSILON)

    def midpoint(self):
        """Returns GamePoint which is the midpoint of this line."""
        return GamePoint((self.endpoints[0].x + self.endpoints[1].x)/2, (self.endpoints[0].y + self.endpoints[1].y)/2)

    def length(self):
        """Returns length of this line."""
        return self.endpoints[0].distance(self.endpoints[1])

    def closest_point(self, point):
        """Returns GamePoint on this line which is closes to given point.

        Args:
            point: Point to find closest point on this line to.
        """
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
        """Returns whether given point is (approximately) on this line."""
        dists = [x.distance(point) for x in self.endpoints]
        return abs(sum(dists) - self.length()) <= 0.01


def atan2(p1, p2):
    """Returns angle between horizontal and the line between the given points.

    Args:
        p1: GamePoint representing one endpoint of line to find angle of.
        p2: GamePoint representing one endpoint of line to find angle of.
    """
    theta = math.atan((p1.y - p2.y)/(p1.x - p2.x + EPSILON))
    if abs(p2.x - p1.x) < EPSILON or p2.x < p1.x:
        theta += math.pi
    return theta

class GameArea:
    """Represents an area (will always be a convex polygon).

    Attributes:
        points: List of points in clockwise or counterclockwise order.
        state: GameState this area exists in.
        color: Color for area
        score: Geometric area of this GameArea.
    """
    def __init__(self, points, state, color=None):
        self.points = points
        self.state = state
        self.color = color
        self.score = self.calculate_score()

    def calculate_score(self):
        """Returns geometric area of this GameArea."""
        points = self.points
        n = len(points)
        term1 = sum([self.points[i].x * self.points[(i+1)%n].y for i in range(n)])
        term2 = sum([self.points[i].y * self.points[(i+1)%n].x for i in range(n)])
        return 0.5 * (term1 - term2)

    def contains(self, point, ignore_lines=[]):
        """Returns whether or not point is within the bounds of this GameArea.

        This function calculates if each bordering point has a clear path to the given point.
        Therefore ignore_lines should include all lines in the area, since they may obstruct
        a clear path to a bordering point.

        Args:
            point: Point to determine.
            ignore_lines: List of lines to ignore.
        """
        for p in self.points:
            if not self.state.clear_path(p, point, ignore_lines):
                return False
        return True


class GameMove:
    """Represents a move in the game.

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


class GameState:
    """Represents the state of the game.

    Attributes:
        width: Width/Height of the game area.
        min_score: Minimum amount a move can score / Largest unscored area.
        area: List of GameAreas which have already been filled.
        lines: List of all GameLines played in game (including the initial lines).
        next_player: Player to draw a line or choose an area.
        area_split_line: If not None, next move should choose an area on either side of this GameLine.
        scores: Current score for each player.
    """
    def __init__(self):
        self.width = 10
        self.min_score = 5
        self.areas = [] # Scored and filled areas.
        self.lines = []
        self.next_player = 1
        self.area_split_line = None # If not None, then next turn is area selection
        self.scores = [0, 0]

        self.new_game()

    def new_game(self):
        """Reset game."""
        p1 = GamePoint(0, 0)
        p2 = GamePoint(0, self.width)
        p3 = GamePoint(self.width, self.width)
        p4 = GamePoint(self.width, 0)
        self.game_area = GameArea([p1, p2, p3, p4], self)
        self.lines = [
            GameLine(p1, p2, -1, add_self_to_points=True),
            GameLine(p2, p3, -1, add_self_to_points=True),
            GameLine(p3, p4, -1, add_self_to_points=True),
            GameLine(p4, p1, -1, add_self_to_points=True),
        ]
        self.scores = [0, 0]

    def get_game_area(self):
        """Returns GameArea containing the entire playable area."""
        return self.game_area

    def is_legal_move(self, move):
        """Returns whether given move is legal to make.

        Args:
            move: GameMove to determine legality of.
        """
        if not move.line_move:
            # TODO(gusatb): Add test to ensure points are legal area.
            if not move.area:
                print('Illegal move: GameArea must be chosen.')
            return move.area
        else:
            if self.area_split_line is not None:
                print('Illegal move: Line move is set and area split is supplied.')
                return False
            if not move.p1 or not move.p2:
                print('Illegal move: Line move must have two points.')
                return False
            # A move is legal if the created line does not cross any other lines,
            # and each point is on a unique line.
            temp_line = GameLine(move.p1, move.p2)
            for line in self.lines:
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
            for area in self.areas:
                if area.contains(midpoint):
                    print('Illegal move: Cannot move in scored area.')
                    return False
            return True

    def clear_path(self, p1, p2, ignore_lines=[]):
        """Returns whether or not there is a clear path from p1 to p2.

        Every line in this state is checked for an intersection with the line
        between p1 and p2 except line in ignore_lines.

        Args:
            p1: One of the GamePoints to check a clear path between.
            p2: One of the GamePoints to check a clear path between.
            ignore_lines: List of GameLines to ignore.
        """
        temp_line = GameLine(p1, p2)
        for line in self.lines:
            if line in ignore_lines:
                continue
            if temp_line.intersection(line) and line not in p1.lines and line not in p2.lines:
                return False
        return True

    def get_surrounding_area(self, pos):
        """Returns GameArea surrounding point.

        Args:
            pos: GamePoint to get GameArea surrounding.
        """
        # Get all points
        points = set()
        for line in self.lines:
            points.add(line.endpoints[0])
            points.add(line.endpoints[1])
        # Filter to visible points
        middle = pos
        points = list(filter(lambda x: self.clear_path(middle, x), points))
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

        return GameArea(points, self)

    def get_areas(self, split_line, color):
        """Returns two GameAreas on either side of split_line.

        Args:
            split_line: New line splitting the area into 2.
            color: Color of new area.
        """
        # Get all points
        points = set()
        for line in self.lines:
            points.add(line.endpoints[0])
            points.add(line.endpoints[1])
        # Filter to visible points
        middle = split_line.midpoint()
        points = list(filter(lambda x: self.clear_path(middle, x, ignore_lines=[split_line]), points))
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

        return GameArea(area_1, self, color), GameArea(area_2, self, color)


    def split_line(self, old_line, new_point):
        """Split line into two lines.

        Note: Does not update areas.

        Args:
            old_line: GameLine to split.
            new_point: GamePoint on old_line to split.
        """
        self.lines.remove(old_line)
        new_lines = []
        for ep in old_line.endpoints:
            new_line = GameLine(ep, new_point, color=old_line.color, add_self_to_points=True)
            ep.lines.remove(old_line)
            self.lines.append(new_line)

    def make_move(self, move):
        """Make a move and update the state.

        Args:
            move: GameMove object.
        """
        assert self.is_legal_move(move)
        if self.area_split_line is not None:
            # TODO(gusatb): Check legality of area.
            self.areas.append(move.area)
            self.scores[move.area.color - 1] += move.area.score
            self.area_split_line = None
        else:
            self.split_line(move.p1_line, move.p1)
            self.split_line(move.p2_line, move.p2)
            new_line = GameLine(move.p1, move.p2, color=self.next_player, add_self_to_points=True)
            self.lines.append(new_line)

            # Check for endgame fill
            areas = self.get_areas(new_line, self.next_player)
            total_score = areas[0].score + areas[1].score
            if total_score <= self.min_score:
                self.areas.extend(areas)
                self.scores[self.next_player-1] += total_score
            elif move.p1_line.color == self.next_player and move.p2_line.color == self.next_player:
                self.area_split_line = new_line
            self.next_player = 3 - self.next_player

