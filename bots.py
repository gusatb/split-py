import random
import math
import game



class RandomBot(game.GamePlayer):
    """Randomly playing bot."""

    def __init__(self):
        super(RandomBot, self).__init__(local_human=False)

    def choose_color(self, state):
        """Returns whether to choose to play as Red.

        Chooses randomly.

        Args:
            state: GameState.
        """
        return random.randint(0, 1) == 0


    def _extend_from_point(self, state, point, theta):
        """Returns line and closest intersection from point going in given direction.

        Args:
            point: Point to extend from.
            theta: Angle in radians to extend in.
        """
        farthest_dist = state.width * math.sqrt(2) + 1
        farthest_point = game.GamePoint(point.x + math.cos(theta)*farthest_dist, point.y + math.sin(theta)*farthest_dist)
        created_line = game.GameLine(point, farthest_point)

        other_lines = state.lines[:]

        intersections = [line.intersection(created_line) for line in other_lines]
        line_intersections = list(zip(other_lines, intersections))
        line_intersections = list(filter(lambda x: x[1] is not None, line_intersections))

        if not line_intersections:
            return None, None
        else:
            distances = [point.distance(intersection) for _, intersection in line_intersections]
            min_index = min(enumerate(distances), key=lambda x: x[1])[0]

            temp_line = game.GameLine(line_intersections[min_index][1], point)

            return line_intersections[min_index]

    def get_move(self, state):
        """Returns a GameMove for the current color.

        Chooses random points until it chooses an unscored area. Then chooses
        a random direction and finds the appropriate points.

        Args:
            state: GameState to move in.
        """
        # Randomly choose area
        if state.area_split_line:
            areas = state.get_areas(state.area_split_line, 3-state.next_player)
            return game.GameMove(area=random.choice(areas))

        # Try 100 times to find a legal move
        for _ in range(100):
            # Find point in empty area.
            legal_point = None
            points_tried = 0
            # try up to 1000 points
            while not legal_point and points_tried < 1000:
                x = random.random() * state.width
                y = random.random() * state.width
                point = game.GamePoint(x, y)
                points_tried += 1
                legal_point = point
                for area in state.areas:
                    if area.contains(point):
                        legal_point = None
                        break
            if not legal_point:
                continue

            theta = random.random() * math.pi # Going both directions from this point

            first_line, first_point = self._extend_from_point(state, legal_point, theta)
            second_line, second_point = self._extend_from_point(state, legal_point, theta-math.pi)

            move = game.GameMove(p1=first_point, p1_line=first_line, p2=second_point, p2_line=second_line)

            if not state.is_legal_move(move):
                continue

            return move

        print('Could not find a legal move.')
        return None

