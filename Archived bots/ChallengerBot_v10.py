import hlt
from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move
from itertools import groupby
import math
import os

MAX_STRENGTH = 255


def get_best_individual_move(square, available_directions={NORTH, EAST, SOUTH, WEST}):
    if len(available_directions) == 0 or square.strength <= 5 * square.production:
        return Move(square, STILL)

    if len(available_directions) > 1:
        best_opportunity_direction = max(available_directions,
                                         key=lambda direction: direction_opportunity(square, direction))
    else:
        best_opportunity_direction = list(available_directions)[0]

    target_square = game_map.get_target(square, best_opportunity_direction)

    if is_move_possible(square, target_square):
        return Move(square, best_opportunity_direction)
    else:
        return Move(square, STILL)


def is_direction_possible(source_square, direction):
    return is_move_possible(source_square, game_map.get_target(source_square, direction))


def is_move_possible(source_square, target_square):
    if target_square.owner == myID:
        return True
    if target_square.owner == unowned_id:
        return source_square.strength > target_square.strength
    else:
        return source_square.strength >= target_square.strength


def direction_opportunity(square, direction):
    return still_opportunity(square) if direction == STILL else move_opportunity(square, direction)


def still_opportunity(square):
    return square_opportunity(square.strength, square.production)


def square_opportunity(strength, production):
    normalized_strength = (strength + 1) / (MAX_STRENGTH + 1)
    normalized_production = (production + 1) / (MAX_PRODUCTION + 1)
    opportunity = normalized_production / normalized_strength
    return opportunity


def move_opportunity(square, direction):
    """
    :return: a float that represents the opportunity of moving to `direction` from `square`
    """
    opportunity = 0
    current_weight = 1
    decay_factor = math.exp(-1 / 2.0)
    total_weight = 0
    current_square = square

    for i in range(game_map.width):
        neighbor = game_map.get_target(current_square, direction)
        if neighbor.owner != myID:
            opportunity += square_opportunity(neighbor.strength, neighbor.production) * current_weight
        current_square = neighbor
        total_weight += current_weight
        current_weight *= decay_factor
    return opportunity / total_weight


def get_unowned_id():
    """
    :return: the id of unowned squares
    """
    owners = [square.owner for square in game_map]
    max_owner_id = myID
    max_owner_count = 0
    for owner_id, owners in groupby(owners, lambda x: x):
        n = len(list(owners))
        if n > max_owner_count:
            max_owner_count = n
            max_owner_id = owner_id
    return max_owner_id


def get_best_collective_moves():
    """
    Compute the best collective moves by processing the stack of best individual moves and re-affecting
    self-destructive moves, i.e. moves that have a cumulative strength > MAX_STRENGTH.
    :return: a list of moves that are collectively optimized
    """

    # TODO: Replace dictionary with matrix here
    targets = {}
    squares_stack = [{'square': square, 'available_directions': {NORTH, EAST, SOUTH, WEST}} for square in game_map if
                     square.owner == myID]

    while len(squares_stack) > 0:
        squares_stack_item = squares_stack.pop()
        square = squares_stack_item['square']
        available_directions = squares_stack_item['available_directions']
        move = get_best_individual_move(square, available_directions)
        target = game_map.get_target(square, move.direction)
        target_key = "{},{}".format(target.x, target.y)
        if target_key not in targets:
            targets[target_key] = [{'move': move, 'available_directions': available_directions}]
        else:
            existing_moves = targets[target_key]
            cumulated_moves = existing_moves + [{'move': move, 'available_directions': available_directions}]
            if sum([m['move'].square.strength for m in cumulated_moves]) <= MAX_STRENGTH * 1.2:
                targets[target_key] = existing_moves + [{'move': move, 'available_directions': available_directions}]
            else:
                if move.direction == STILL:
                    targets[target_key] = [{'move': move, 'available_directions': {}}]
                    for existing_move in existing_moves:
                        directions = existing_move['available_directions']
                        directions.remove(existing_move['move'].direction)
                        squares_stack.append(
                            {'square': existing_move['move'].square, 'available_directions': directions})
                else:
                    # sorting existing moves by decreasing strength
                    cumulated_moves.sort(
                        key=lambda item: -1000 if item['move'].direction == STILL else -item['move'].square.strength)
                    total_strength = 0
                    top_moves = []
                    for mv in cumulated_moves:
                        strength = mv['move'].square.strength
                        if total_strength + strength <= 255:
                            total_strength += strength
                            top_moves.append(mv)
                        else:
                            directions = mv['available_directions']
                            directions.remove(mv['move'].direction)
                            squares_stack.append({'square': mv['move'].square, 'available_directions': directions})
                    targets[target_key] = top_moves

    moves = [target_move['move'] for target_moves in targets.values() for target_move in target_moves]
    return moves


myID, game_map = hlt.get_init()
productions = [sq.production for sq in game_map]
MAX_PRODUCTION = max(productions)
unowned_id = get_unowned_id()
bot_name = os.path.basename(__file__).split('.')[0]
hlt.send_init(bot_name)

while True:
    game_map.get_frame()
    hlt.send_frame(get_best_collective_moves())
