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
        global ENEMY_EDGE_DEFENSE_LOCATIONS_LEFT, ENEMY_EDGE_DEFENSE_LOCATIONS_RIGHT 
        global ATTACK_DEMOLISHER_LOCATION_LEFT, ATTACK_DEMOLISHER_LOCATION_RIGHT
        global DEFENSE_INTERCEPTOR_LOCATION_LEFT, DEFENSE_INTERCEPTOR_LOCATION_RIGHT
        global ATTACK_LEFT_SCOUT_FIRST_GROUP_LOCATION, ATTACK_LEFT_SCOUT_SECOND_GROUP_LOCATION
        global ATTACK_RIGHT_SCOUT_FIRST_GROUP_LOCATION, ATTACK_RIGHT_SCOUT_SECOND_GROUP_LOCATION
        global ATTACK_LEFT_REMOVE_WALL_LOCATION, ATTACK_RIGHT_REMOVE_WALL_LOCATION
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0

        REFUND_THRESHOLD_WALL = 0.7
        REFUND_THRESHOLD_TURRET = 0.5
        with open(os.path.join(os.path.dirname(__file__), 'defense-order.json'), 'r') as f:
            self.build_order = json.loads(f.read())

        ENEMY_EDGE_DEFENSE_LOCATIONS_LEFT = [[0, 14], [1, 14], [2, 14], [3, 14], [4, 14], [1, 15], [2, 15], [3, 15], [2, 16], [3, 16]]
        ENEMY_EDGE_DEFENSE_LOCATIONS_RIGHT = [[27, 14], [26, 14], [25, 14], [24, 14], [23, 14], [26, 15], [25, 15], [24, 15], [25, 16], [24, 16]]

        ATTACK_DEMOLISHER_LOCATION_LEFT = [6, 7]
        ATTACK_DEMOLISHER_LOCATION_RIGHT = [21, 7]
        DEFENSE_INTERCEPTOR_LOCATION_LEFT = [7, 6]
        DEFENSE_INTERCEPTOR_LOCATION_RIGHT = [20, 6]
        ATTACK_LEFT_SCOUT_FIRST_GROUP_LOCATION = [14, 0]
        ATTACK_LEFT_SCOUT_SECOND_GROUP_LOCATION = [21, 7]
        ATTACK_RIGHT_SCOUT_FIRST_GROUP_LOCATION = [13, 0]
        ATTACK_RIGHT_SCOUT_SECOND_GROUP_LOCATION = [8, 5]
        ATTACK_LEFT_REMOVE_WALL_LOCATION = [6, 7]
        ATTACK_RIGHT_REMOVE_WALL_LOCATION = [21, 8]

        # Important characteristics of a game state, will be parsed in self.parse_game_state()
        self.enemy_left_edge_strength = 100
        self.enemy_right_edge_strength = 100
        self.enemy_left_edge_blocked = True
        self.enemy_left_edge_blocked = True
        self.enemy_left_edge_misdirecting = False
        self.enemy_left_edge_misdirecting = False
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
        self.enemy_left_edge_misdirecting = self.is_enemy_left_edge_misdirecting(game_state)
        self.enemy_right_edge_misdirecting = self.is_enemy_right_edge_misdirecting(game_state)
        self.enemy_left_edge_strength = self.compute_enemy_left_edge_defense_strength(game_state)
        self.enemy_right_edge_strength = self.compute_enemy_right_edge_defense_strength(game_state)


    def is_enemy_left_edge_misdirecting(self, game_state):
        return not self.enemy_left_edge_blocked and game_state.contains_stationary_unit([0, 14])

    def is_enemy_right_edge_misdirecting(self, game_state):
        return not self.enemy_right_edge_blocked and game_state.contains_stationary_unit([27, 14])


    def is_enemy_left_edge_blocked(self, game_state):
        path = game_state.find_path_to_edge([1, 13], game_state.game_map.TOP_RIGHT)
        if len(path) < 10:
            return True
        for i in range(10):
            location = path[i]
            if location[1] < 13:
                return True
        return False


    def is_enemy_right_edge_blocked(self, game_state):
        path = game_state.find_path_to_edge([26, 13], game_state.game_map.TOP_LEFT)
        if len(path) < 10:
            return True
        for i in range(10):
            location = path[i]
            if location[1] < 13:
                return True
        return False


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
        self.refund_low_health_structures(game_state)
        self.build_default_defences(game_state)


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
                    if self.turn_strategy == "attack_left" and location == ATTACK_LEFT_REMOVE_WALL_LOCATION:
                        continue
                    if self.turn_strategy == "attack_right" and location == ATTACK_RIGHT_REMOVE_WALL_LOCATION:
                        continue
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
            pass
        elif self.turn_strategy == "attack_left":
            if self.enemy_left_edge_misdirecting:
                # demolisher to clear misdirection
                self.spawn_demolisher(game_state, ATTACK_DEMOLISHER_LOCATION_LEFT, 
                                      self.choose_number_of_demolishers_based_on_enemy_edge_strength(self.enemy_left_edge_strength))
                self.my_MP = game_state.get_resource(MP, 0)

            elif not self.enemy_left_edge_blocked:
                # need to defend using interceptor
                self.spawn_interceptor(game_state, DEFENSE_INTERCEPTOR_LOCATION_LEFT, self.choose_number_of_interceptor_based_on_enemy_MP())
                self.my_MP = game_state.get_resource(MP, 0)
            
            # ping scouts
            first_group_size = self.choose_number_of_scouts_in_first_group_based_on_enemy_edge_strength(self.enemy_left_edge_strength)
            self.spawn_scouts(game_state, ATTACK_LEFT_SCOUT_FIRST_GROUP_LOCATION, first_group_size)
            second_group_size = self.my_MP - first_group_size
            self.spawn_scouts(game_state, ATTACK_LEFT_SCOUT_SECOND_GROUP_LOCATION, second_group_size)
                
        else:
            # attack right
            if self.enemy_right_edge_misdirecting:
                # demolisher to clear misdirection
                self.spawn_demolisher(game_state, ATTACK_DEMOLISHER_LOCATION_RIGHT, 
                                      self.choose_number_of_demolishers_based_on_enemy_edge_strength(self.enemy_right_edge_strength))
                self.my_MP = game_state.get_resource(MP, 0)

            elif not self.enemy_right_edge_blocked:
                # need to defend using interceptor
                self.spawn_interceptor(game_state, DEFENSE_INTERCEPTOR_LOCATION_RIGHT, self.choose_number_of_interceptor_based_on_enemy_MP())
                self.my_MP = game_state.get_resource(MP, 0)
            
            # ping scouts
            first_group_size = self.choose_number_of_scouts_in_first_group_based_on_enemy_edge_strength(self.enemy_right_edge_strength)
            self.spawn_scouts(game_state, ATTACK_RIGHT_SCOUT_FIRST_GROUP_LOCATION, first_group_size)
            second_group_size = self.my_MP - first_group_size
            self.spawn_scouts(game_state, ATTACK_RIGHT_SCOUT_SECOND_GROUP_LOCATION, second_group_size)


    def spawn_interceptor(self, game_state, location, number):
        game_state.attempt_spawn(INTERCEPTOR, location, math.floor(number))
        
    def choose_number_of_interceptor_based_on_enemy_MP(self):
        return max(self.enemy_MP / 5, 2) 

    def spawn_scouts(self, game_state, location, number):
        game_state.attempt_spawn(SCOUT, location, math.floor(number))

    def spawn_demolisher(self, game_state, location, number):
        game_state.attempt_spawn(DEMOLISHER, location, math.floor(number))

    def choose_number_of_scouts_in_first_group_based_on_enemy_edge_strength(self, strength):
        return min(5 + math.floor(strength / 7), 10)
    
    def choose_number_of_demolishers_based_on_enemy_edge_strength(self, strength):
        return min(3 + math.floor(strength / 10), 5)


    def evaluate_next_turn_strategy(self, game_state):
        self.my_MP = game_state.get_resource(MP, 0)
        if self.my_MP < 10:
            self.turn_strategy = "defend"
        elif self.my_MP > 20 or self.my_MP > self.enemy_MP:
            if self.compute_enemy_left_edge_defense_strength(game_state) > self.compute_enemy_right_edge_defense_strength(game_state):
                self.turn_strategy = "attack_right"
                game_state.attempt_remove(ATTACK_RIGHT_REMOVE_WALL_LOCATION)
            else:
                self.turn_strategy = "attack_left"
                game_state.attempt_remove(ATTACK_LEFT_REMOVE_WALL_LOCATION)
        else:
            self.turn_strategy = "defend"


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
