import gamelib
import random
import math
import warnings
from sys import maxsize
import json


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
        # seed = random.randrange(maxsize)
        # random.seed(seed)
        # gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup

        with open('python-v1/defense-order.json', 'r') as f:
            self.build_order = json.loads(f.read())
            gamelib.debug_write("Game insights loaded successfully")

        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))

        self.starter_strategy(game_state)
        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        gamelib.debug_write("Resources left: {}".format(game_state.get_resource(SP)))
        
        self.build_defences(game_state)

    def build_defences(self, game_state):
        # Check if there is a need to patch. Balance between preventing scout cannon and threat
        need_to_patch = self.is_enemy_likely_to_attack(game_state) and not self.is_attacking(game_state)
        is_covered_up = [True, True]
        if need_to_patch:
            is_covered_up = self.cover_up(game_state)

        self.build_default_defences(game_state, is_covered_up.count(False))

        self.cover_up(game_state, is_covered_up)
    
    def is_enemy_likely_to_attack(self, game_state):
        return game_state.get_resource(MP, player_index=1) >= 7
    
    def is_attacking(self, game_state):
        return game_state.get_resource(MP) >= 14
    
    def cover_up(self, game_state, is_covered_up=[False, False]):
        """
        Cover up both entries into the base.
        Can safely assume that there are enough structure points to spawn 2 walls
        """
        result = []
        if not is_covered_up[0]:
            bottom_x_i = 4
            while game_state.contains_stationary_unit([bottom_x_i, 11]) and game_state.contains_stationary_unit([bottom_x_i - 2, 13]):
                bottom_x_i += 1
            spawn_position = [bottom_x_i - 2, 12]
            can_spawn = bottom_x_i != 4 and not game_state.contains_stationary_unit(spawn_position)
            if can_spawn:
                game_state.attempt_spawn(WALL, spawn_position)
                gamelib.debug_write("Spawned blocking WALL at {}".format(spawn_position))
            result.append(can_spawn)
        else:
            result.append(True)
        
        if not is_covered_up[1]:
            bottom_x_i = 23
            while game_state.contains_stationary_unit([bottom_x_i, 11]) and game_state.contains_stationary_unit([bottom_x_i + 2, 13]):
                bottom_x_i -= 1
            spawn_position = [bottom_x_i + 2, 12]
            can_spawn = bottom_x_i != 23 and not game_state.contains_stationary_unit(spawn_position)
            if can_spawn:
                game_state.attempt_spawn(WALL, spawn_position)
                gamelib.debug_write("Spawned blocking WALL at {}".format(spawn_position))
            result.append(can_spawn)
        else:
            result.append(True)
        
        return result
    
    def build_default_defences(self, game_state, patch_cost):
        """
        Build and patch defenses
        """
        for build_job in self.build_order:
            if build_job["type"] == "spawn":
                unit = eval(build_job["unit"])
                location = build_job["location"]
                if game_state.get_resource(SP) < game_state.type_cost(unit)[0] + patch_cost: # not enough structure points
                    break
                is_spawned = game_state.attempt_spawn(unit, location)
                if is_spawned: gamelib.debug_write("Spawned {} at {}".format(build_job["unit"], location))
            
            else if build_job["type"] == "upgrade":
                unit = eval(build_job["unit"])
                location = build_job["location"]
                if game_state.get_resource(SP) < game_state.type_cost(unit, upgrade=True)[0] + patch_cost:
                    break
                is_upgraded = game_state.attempt_upgrade(unit, location)
                if is_upgraded: gamelib.debug_write("Spawned {} at {}".format(build_job["unit"], location))

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
