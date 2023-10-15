import gamelib
import random
import math
import warnings
from sys import maxsize
import json
import os


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, REFUND_THRESHOLD_WALL, REFUND_THRESHOLD_TURRET
        global EDGE_BLOCK_LOCATIONS_LEFT, EDGE_BLOCK_LOCATIONS_RIGHT
        global BLOCK_EDGE_ENEMY_MP_THRESHOLD, DEMOLISHER_ENEMY_EDGE_STRENGTH_THRESHOLD, UPGRADE_EDGE_WALL_THRESHOLD
        global ENEMY_EDGE_DEFENSE_LOCATIONS_LEFT, ENEMY_EDGE_DEFENSE_LOCATIONS_RIGHT 
        global DEFENSE_INTERCEPTOR_LOCATION_LEFT, DEFENSE_INTERCEPTOR_LOCATION_RIGHT
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        # for frame analysis
        self.mobile_unit_indices = [3, 4, 5]
        self.costs = {
            3: config["unitInformation"][3]["cost2"],
            4: config["unitInformation"][4]["cost2"],
            5: config["unitInformation"][5]["cost2"],
        }
        MP = 1
        SP = 0

        REFUND_THRESHOLD_WALL = 0.5
        REFUND_THRESHOLD_TURRET = 0.3
        with open(os.path.join(os.path.dirname(__file__), 'defense-order.json'), 'r') as f:
            self.build_order = json.loads(f.read())

        EDGE_BLOCK_LOCATIONS_LEFT = [[0, 13], [1, 13]]
        EDGE_BLOCK_LOCATIONS_RIGHT = [[27, 13], [26, 13]]

        DEFENSE_INTERCEPTOR_LOCATION_LEFT = [4, 9] # TODO: this is not covered by support
        DEFENSE_INTERCEPTOR_LOCATION_RIGHT = [23, 9]

        ENEMY_EDGE_DEFENSE_LOCATIONS_LEFT = [[0, 14], [1, 14], [2, 14], [3, 14], [1, 15], [2, 15], [3, 15], [2, 16]]
        ENEMY_EDGE_DEFENSE_LOCATIONS_RIGHT = [[27, 14], [26, 14], [25, 14], [24, 14], [26, 15], [25, 15], [24, 15], [25, 16]]

        DEMOLISHER_ENEMY_EDGE_STRENGTH_THRESHOLD = 10
        BLOCK_EDGE_ENEMY_MP_THRESHOLD = 12
        UPGRADE_EDGE_WALL_THRESHOLD = 15

        # Important characteristics of a game state, will be parsed in self.parse_game_state()
        self.my_left_edge_blocked = True
        self.my_right_edge_blocked = True
        self.enemy_left_edge_blocked = True
        self.enemy_right_edge_blocked = True
        self.enemy_left_edge_strength = 100
        self.enemy_right_edge_strength = 100
        self.my_MP = 0
        self.enemy_MP = 0
        self.turn_strategy = "defend" # defend, attack_left, attack_right

        self.min_sp_to_save = 0 # at least this amount of SP left in case need to repair for next turn


    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        self.starter_strategy(game_state)

        game_state.submit_turn()


    def starter_strategy(self, game_state):
        self.parse_game_state(game_state)
        self.build_defences(game_state)
        self.execute_turn_strategy(game_state)
        self.evaluate_next_turn_strategy(game_state)


    def parse_game_state(self, game_state):
        self.my_MP = game_state.get_resource(MP, 0)
        self.enemy_MP = game_state.get_resource(MP, 1)
        self.enemy_left_edge_blocked = self.is_enemy_left_edge_blocked(game_state)
        self.enemy_right_edge_blocked = self.is_enemy_right_edge_blocked(game_state)
        self.enemy_left_edge_strength = self.compute_enemy_left_edge_defense_strength(game_state)
        self.enemy_right_edge_strength = self.compute_enemy_right_edge_defense_strength(game_state)
        self.my_left_edge_blocked = self.is_my_left_edge_blocked(game_state)
        self.my_right_edge_blocked = self.is_my_right_edge_blocked(game_state)


    def is_enemy_left_edge_blocked(self, game_state):
        path = game_state.find_path_to_edge([1, 12], game_state.game_map.TOP_RIGHT)
        if len(path) < 10:
            return True
        for i in range(10):
            location = path[i]
            if location[1] < 12:
                return True
        return False


    def is_enemy_right_edge_blocked(self, game_state):
        path = game_state.find_path_to_edge([26, 12], game_state.game_map.TOP_LEFT)
        if len(path) < 10:
            return True
        for i in range(10):
            location = path[i]
            if location[1] < 12:
                return True
        return False
    
    
    def is_enemy_left_edge_misdirecting(self, game_state):
        return not self.enemy_left_edge_blocked and game_state.contains_stationary_unit([0, 14])

    def is_enemy_right_edge_misdirecting(self, game_state):
        return not self.enemy_right_edge_blocked and game_state.contains_stationary_unit([27, 14])


    def is_my_left_edge_blocked(self, game_state):
        for location in EDGE_BLOCK_LOCATIONS_LEFT:
            if not game_state.contains_stationary_unit(location):
                return False
        return True
    

    def is_my_right_edge_blocked(self, game_state):
        for location in EDGE_BLOCK_LOCATIONS_RIGHT:
            if not game_state.contains_stationary_unit(location):
                return False
        return True


    def compute_enemy_left_edge_defense_strength(self, game_state):
        strength = 0
        for location in ENEMY_EDGE_DEFENSE_LOCATIONS_LEFT:
            distance_to_edge = math.dist([0.5, 13], location)
            unit_strength = 0

            unit = game_state.contains_stationary_unit(location)
            if unit and unit.unit_type == TURRET:
                if unit.upgraded:
                    unit_strength = 25 / distance_to_edge
                else:
                    unit_strength = 5 / distance_to_edge
            elif location[1] == 14 and unit and unit.unit_type == WALL:
                if unit.upgraded:
                    unit_strength = 3
                else:
                    unit_strength = 1
            strength += unit_strength
        return strength


    def compute_enemy_right_edge_defense_strength(self, game_state):
        strength = 0
        for location in ENEMY_EDGE_DEFENSE_LOCATIONS_RIGHT:
            distance_to_edge = math.dist([26.5, 13], location)
            unit_strength = 0

            unit = game_state.contains_stationary_unit(location)
            if unit and unit.unit_type == TURRET:
                if unit.upgraded:
                    unit_strength = 25 / distance_to_edge
                else:
                    unit_strength = 5 / distance_to_edge
            elif location[1] == 14 and unit and unit.unit_type == WALL:
                if unit.upgraded:
                    unit_strength = 3
                else:
                    unit_strength = 1
            strength += unit_strength
        return strength


    def build_defences(self, game_state):
        self.block_edge(game_state)
        self.refund_low_health_structures(game_state)
        self.build_default_defences(game_state)


    def block_edge(self, game_state):
        if game_state.turn_number == 0:
            self.block_left_edge(game_state)
            self.block_right_edge(game_state)

        if self.turn_strategy == "defend" and self.enemy_MP >= BLOCK_EDGE_ENEMY_MP_THRESHOLD and not self.my_left_edge_blocked \
                and not self.enemy_left_edge_blocked and not self.my_right_edge_blocked and not self.enemy_right_edge_blocked:
            # situation where both edges are open and enemy is likely to ping scouts
            # do not spawn two groups of interceptors
            # randomly choose one edge to close
            if random.randint(0, 1) == 0:
                self.block_left_edge(game_state)
            else:
                self.block_right_edge(game_state)
            return

        if not self.enemy_left_edge_blocked and not self.my_left_edge_blocked and self.turn_strategy != "attack_left":
            if self.enemy_MP < BLOCK_EDGE_ENEMY_MP_THRESHOLD or self.turn_strategy == "attack_right":
                # close the walls at edge
                self.block_left_edge(game_state)

        if not self.enemy_right_edge_blocked and not self.my_right_edge_blocked and self.turn_strategy != "attack_right":
            if self.enemy_MP < BLOCK_EDGE_ENEMY_MP_THRESHOLD or self.turn_strategy == "attack_left":
                self.block_right_edge(game_state)

    def block_left_edge(self, game_state):
        for location in EDGE_BLOCK_LOCATIONS_LEFT:
            game_state.attempt_spawn(WALL, location)
            if self.enemy_MP > UPGRADE_EDGE_WALL_THRESHOLD:
                game_state.attempt_upgrade(location)
            game_state.attempt_remove(location)
        self.my_left_edge_blocked = True

    def block_right_edge(self, game_state):
        for location in EDGE_BLOCK_LOCATIONS_RIGHT:
            game_state.attempt_spawn(WALL, location)
            if self.enemy_MP > UPGRADE_EDGE_WALL_THRESHOLD:
                game_state.attempt_upgrade(location)
            game_state.attempt_remove(location)
        self.my_right_edge_blocked = True

    def enumerate_friendly_side_locations(self, game_state):
        locations = []
        for x in range(game_state.ARENA_SIZE):
            if x < game_state.HALF_ARENA:
                # 0 - 13
                for y in range(game_state.HALF_ARENA - x - 1, game_state.HALF_ARENA):
                    locations.append([x, y])
            else:
                # 14 - 27
                for y in range(x - 14, game_state.HALF_ARENA):
                    locations.append([x, y])
        return locations


    def refund_low_health_structures(self, game_state):
        for location in self.enumerate_friendly_side_locations(game_state):
            structure = game_state.contains_stationary_unit(location)
            if structure:
                if structure.unit_type == TURRET:
                    if structure.health / structure.max_health < REFUND_THRESHOLD_TURRET:
                        game_state.attempt_remove(location)
                elif structure.unit_type == WALL:
                    if structure.health / structure.max_health < REFUND_THRESHOLD_WALL:
                        game_state.attempt_remove(location)


    def build_default_defences(self, game_state):
        """
        Build and patch defenses
        """
        stop_flag = False

        for job_list in self.build_order:
            if stop_flag:
                break

            for build_job in job_list:
                if build_job["type"] == "spawn":
                    unit = eval(build_job["unit"])
                    location = build_job["location"]
                    if game_state.get_resource(SP) - game_state.type_cost(unit)[0] < self.min_sp_to_save: # not enough structure points
                        stop_flag = True
                        break
                    is_spawned = game_state.attempt_spawn(unit, location)

                elif build_job["type"] == "upgrade":
                    unit = eval(build_job["unit"])
                    location = build_job["location"]
                    if game_state.get_resource(SP) - game_state.type_cost(unit, upgrade=True)[0] < self.min_sp_to_save:
                        stop_flag = True
                        break
                    is_upgraded = game_state.attempt_upgrade(location)


    def execute_turn_strategy(self, game_state):
        if self.turn_strategy == "defend":
            if not self.enemy_left_edge_blocked and not self.my_left_edge_blocked:
                # enemy has high MP and is likely attacking on the left
                self.spawn_interceptor(game_state, DEFENSE_INTERCEPTOR_LOCATION_LEFT, self.choose_number_of_interceptor_based_on_enemy_MP())
            if not self.enemy_right_edge_blocked and not self.my_right_edge_blocked:
                # enemy has high MP and is likely attacking on the right
                self.spawn_interceptor(game_state, DEFENSE_INTERCEPTOR_LOCATION_RIGHT, self.choose_number_of_interceptor_based_on_enemy_MP())
        elif self.turn_strategy == "attack_left":
            if self.is_enemy_left_edge_misdirecting(game_state):
                # demolishers tanked by interceptors to clear misdirection
                self.spawn_interceptor(game_state, [1, 12], self.choose_number_of_tanks_based_on_enemy_edge_strength(self.enemy_left_edge_strength))
                self.spawn_demolisher(game_state, [2, 11], self.choose_number_of_demolishers_based_on_enemy_edge_strength(self.enemy_left_edge_strength))
                self.my_MP = game_state.get_resource(MP, 0)

            elif not self.enemy_left_edge_blocked:
                # need to defend at the same time
                self.spawn_interceptor(game_state, DEFENSE_INTERCEPTOR_LOCATION_LEFT, self.choose_number_of_interceptor_based_on_enemy_MP())
                self.my_MP = game_state.get_resource(MP, 0)
            
            # ping scouts
            first_group_size = self.choose_number_of_scouts_in_first_group_based_on_enemy_edge_strength(self.enemy_left_edge_strength)
            self.ping_scouts(game_state, 4, 1, first_group_size, self.my_MP - first_group_size)
                
        else:
            # attack right
            # clear misdirection if any
            if self.is_enemy_right_edge_misdirecting(game_state):
                self.spawn_interceptor(game_state, [26, 12], self.choose_number_of_tanks_based_on_enemy_edge_strength(self.enemy_right_edge_strength))
                self.spawn_demolisher(game_state, [25, 11], self.choose_number_of_demolishers_based_on_enemy_edge_strength(self.enemy_right_edge_strength))
                self.my_MP = game_state.get_resource(MP, 0)

            elif not self.enemy_right_edge_blocked:
                # need to defend at the same time
                self.spawn_interceptor(game_state, DEFENSE_INTERCEPTOR_LOCATION_RIGHT, self.choose_number_of_interceptor_based_on_enemy_MP())
                self.my_MP = game_state.get_resource(MP, 0)
            
            # ping scouts
            first_group_size = self.choose_number_of_scouts_in_first_group_based_on_enemy_edge_strength(self.enemy_right_edge_strength)
            self.ping_scouts(game_state, 4, 1, first_group_size, self.my_MP - first_group_size)


    def ping_scouts(self, game_state, larger_x, gap, larger_x_size, smaller_x_size):
        # 2 <= larger_x <= 13
        location_larger_x = [larger_x, game_state.HALF_ARENA - larger_x - 1]
        smaller_x = larger_x - gap
        location_smaller_x = [smaller_x, game_state.HALF_ARENA - smaller_x - 1]
        if self.turn_strategy == "attack_left":
            location_larger_x[0] = game_state.ARENA_SIZE - location_larger_x[0] - 1
            location_smaller_x[0] = game_state.ARENA_SIZE - location_smaller_x[0] - 1
        game_state.attempt_spawn(SCOUT, location_larger_x, math.floor(larger_x_size))
        game_state.attempt_spawn(SCOUT, location_smaller_x, math.floor(smaller_x_size))

    def spawn_interceptor(self, game_state, location, number):
        game_state.attempt_spawn(INTERCEPTOR, location, math.floor(number))

    def spawn_demolisher(self, game_state, location, number):
        game_state.attempt_spawn(DEMOLISHER, location, math.floor(number))
        
    def choose_number_of_interceptor_based_on_enemy_MP(self):
        return max(self.enemy_MP / 4, 3) 
    
    def choose_number_of_tanks_based_on_enemy_edge_strength(self, strength):
        return min(2 + math.floor(strength / 10), 5)

    def choose_number_of_demolishers_based_on_enemy_edge_strength(self, strength):
        return min(2 + math.floor(strength / 10), 5)

    def choose_number_of_scouts_in_first_group_based_on_enemy_edge_strength(self, strength):
        return min(5 + math.floor(strength / 7), 10)


    def evaluate_next_turn_strategy(self, game_state):
        self.my_MP = game_state.get_resource(MP, 0)
        if self.my_MP < 10:
            self.turn_strategy = "defend"
        elif self.my_MP > 20 or self.my_MP > self.enemy_MP:
            if self.compute_enemy_left_edge_defense_strength(game_state) > self.compute_enemy_right_edge_defense_strength(game_state):
                self.turn_strategy = "attack_right"
                for location in EDGE_BLOCK_LOCATIONS_RIGHT:
                    game_state.attempt_remove(location)
            else:
                self.turn_strategy = "attack_left"
                for location in EDGE_BLOCK_LOCATIONS_LEFT:
                    game_state.attempt_remove(location)
        else:
            self.turn_strategy = "defend"

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
