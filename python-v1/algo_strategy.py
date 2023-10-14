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

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
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

        with open(os.path.join(os.path.dirname(__file__), 'defense-order.json'), 'r') as f:
            self.build_order = json.loads(f.read())
        
        with open(os.path.join(os.path.dirname(__file__), 'no-obstruction.json'), 'r') as f:
            self.no_obstruction_locations = json.loads(f.read())

        self.blockages = [None, None] # the wall positions that are used to block path of scout spam
        self.enemy_rush_threshold = 7
        self.should_attack_left = True
        self.hole_exists = True

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
        
        self.find_hole(game_state)
        self.build_defences(game_state)
        self.spawn_scouts(game_state)
        self.remove_blockages(game_state)
    
    def find_hole(self, game_state):
        if not self.hole_exists:
            return

        if self.should_attack_left:
            path = game_state.find_path_to_edge([14, 0])
            final_location = path[len(path) - 1]
            if final_location[1] - final_location[0] != 14 and final_location[1] >= 13:
                self.hole_exists = False
        
        else:
            path = game_state.find_path_to_edge([13, 0])
            final_location = path[len(path) - 1]
            if final_location[0] + final_location[1] != 41 and final_location[1] >= 13:
                self.hole_exists = False

    # should spawn interceptors if enemy is likely to attack
    #? spawn interceptors to cover scouts / self destruct / clear enemy scouts
    # two layers in the middle
    # replace bad walls
    # how to defend edge???
    # may need a specific strategy to defend edge, detect enemy trying to attack edge, remove structure and put interceptor
    # interceptor deals 20 damage, turret 5, scout health 25
    # idea: if enemy blocks edge, then don't build edge structure
    #       if enemy clears edge and doesn't have many MP, block edge
    #       if enemy clears edge and has many MP, initiate edge defense
    # edge defense against 2 groups of scouts: don't build structure, use interceptor + turret to kill the scouts
    def build_defences(self, game_state):
        is_covered_up = self.cover_up(game_state)
        self.build_default_defences(game_state, is_covered_up.count(False))
        self.cover_up(game_state, is_covered_up)
    
    # should allow more openings for attack
    def remove_blockages(self, game_state):
        if self.is_attacking_next_turn(game_state):
            location = self.blockages[1 if self.should_attack_left else 0]
            if location:
                game_state.attempt_remove(location)
                self.blockages[1 if self.should_attack_left else 0] = None
        
        for location in self.no_obstruction_locations:
            location = location if self.should_attack_left else [27 - location[0], location[1]]
            game_state.attempt_remove(location)
    
    # demolisher + scouts to attack edge -> not as good as 2 groups of scouts
    # demolisher to clear enemy structures -> only works when there's no turret?
    # upgraded turrect can kill 1 demolisher in each frame, strategise in defense

    def spawn_scouts(self, game_state):
        if self.is_attacking(game_state):
            if self.should_attack_left:
                if self.blockages[1]:
                    return
            else:
                if self.blockages[0]:
                    return

            if self.hole_exists:
                game_state.attempt_spawn(SCOUT, [14, 0] if self.should_attack_left else [13, 0], math.floor(game_state.get_resource(MP)))
            else:
                game_state.attempt_spawn(SCOUT, [16, 2] if self.should_attack_left else [11, 2], 6)
                game_state.attempt_spawn(SCOUT, [15, 1] if self.should_attack_left else [12, 1], 4)
                game_state.attempt_spawn(SCOUT, [14, 0] if self.should_attack_left else [13, 0], math.floor(game_state.get_resource(MP)))
    
    def is_enemy_likely_to_attack(self, game_state):
        return game_state.get_resource(MP, player_index=1) >= self.enemy_rush_threshold # assuming that cost of scout is 1
    
    def is_attacking(self, game_state):
        return game_state.get_resource(MP) >= 14
    
    def is_attacking_next_turn(self, game_state):
        return game_state.get_resource(MP) >= 9
    
    def cover_up(self, game_state, is_covered_up=[False, False]):
        """
        Cover up both entries into the base.
        Can safely assume that there are enough structure points to spawn 2 walls
        """
        result = []
        if not is_covered_up[0] and not (self.blockages[0] and game_state.contains_stationary_unit(self.blockages[0])) \
                and (self.is_enemy_likely_to_attack(game_state) and not self.is_attacking(game_state) if not self.should_attack_left else True):
            bottom_x_i = 4
            while game_state.contains_stationary_unit([bottom_x_i, 11]) and game_state.contains_stationary_unit([bottom_x_i - 2, 13]):
                bottom_x_i += 1
            spawn_position = [bottom_x_i - 2, 12]
            can_spawn = bottom_x_i != 4 and not game_state.contains_stationary_unit(spawn_position)
            if can_spawn:
                game_state.attempt_spawn(WALL, spawn_position)
                self.blockages[0] = spawn_position
            result.append(can_spawn)
        else:
            result.append(True)
        
        if not is_covered_up[1] and not (self.blockages[1] and game_state.contains_stationary_unit(self.blockages[1])) \
                and (self.is_enemy_likely_to_attack(game_state) and not self.is_attacking(game_state) if self.should_attack_left else True):
            bottom_x_i = 23
            while game_state.contains_stationary_unit([bottom_x_i, 11]) and game_state.contains_stationary_unit([bottom_x_i + 2, 13]):
                bottom_x_i -= 1
            spawn_position = [bottom_x_i + 2, 12]
            can_spawn = bottom_x_i != 23 and not game_state.contains_stationary_unit(spawn_position)
            if can_spawn:
                game_state.attempt_spawn(WALL, spawn_position)
                self.blockages[1] = spawn_position
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
                location = location if self.should_attack_left else [27 - location[0], location[1]]
                if game_state.get_resource(SP) < game_state.type_cost(unit)[0] + patch_cost: # not enough structure points
                    break
                is_spawned = game_state.attempt_spawn(unit, location)
            
            elif build_job["type"] == "upgrade":
                unit = eval(build_job["unit"])
                location = build_job["location"]
                location = location if self.should_attack_left else [27 - location[0], location[1]]
                if game_state.get_resource(SP) < game_state.type_cost(unit, upgrade=True)[0] + patch_cost:
                    break
                is_upgraded = game_state.attempt_upgrade(location)

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        state = json.loads(turn_string)
        if state["turnInfo"][0] == 1:
            if state["turnInfo"][2] == 0:
                # analyse enemy turret structure
                left_count = 0
                right_count = 0
                for turret in state["p2Units"][2]:
                    if turret[0] < 14:
                        left_count += 1
                    else:
                        right_count += 1
                if left_count >= 4 or right_count >= 4:
                    new_should_attack_left = right_count - left_count > 1
                    if new_should_attack_left != self.should_attack_left:
                        self.hole_exists = True # refresh insights about hole when switching side of attack
                    self.should_attack_left = new_should_attack_left
            
                # get the number of MPs that the opponent is using to spawn units, and adjust accordingly
                new_threshold = min(
                    self.enemy_rush_threshold, 
                    sum(map(
                        lambda spawn_action: self.costs[spawn_action[1]],
                        filter(
                            lambda spawn_action: spawn_action[3] == 2 and spawn_action[1] in self.mobile_unit_indices, 
                            state["events"]["spawn"],
                        ),
                    )),
                )
                if new_threshold > 0:
                    self.enemy_rush_threshold = new_threshold


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
