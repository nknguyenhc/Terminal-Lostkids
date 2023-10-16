# Terminal-Lostkids (Python-2L-AET)

This repository contains our team's algorithm submitted to Terminal competition (for APAC region), organised by Correlation One and Citadel.
We were shortlisted to the final round (with 3 other teams) and won third place overall.

For more details about competitions and the game itself please check Correlation One's
[main site](https://terminal.c1games.com/rules). Check out [the playground](https://terminal.c1games.com/playground) to try out the game.

## Manual Play

Check out [the playground](https://terminal.c1games.com/playground).

# Our algorithm

We currently have implemented the followings:

## Python v1

The idea is to use a horizontal wall structure, with 2 entrances into and out of the base on two sides. The idea is that when an opponent mobile unit attempts to reach the edge, the structure maximises the exposure of our turrets on enemy's units, thereby maximising damage on enemy's units. When the entrances are closed, one batch of enemy's scouts is not enough to go through and reach the edge.

We also have a line of walls in front. As our mobile units enters enemy's battle field at the end of the line of walls, the line of walls directs the units' movement.

### Defense

* A pre-defined set of jobs to build.
* Opening and closing the entrances depending on whether the algorithm is attacking and whether the enemy is attacking.
* Track enemy's attack pattern to adjust the mobile point threshold of when the enemy is going to attack.

### Offense

* Accumulate points and attack only when there are enough points.
* If there is a direct path towards an enemy's edge, deploy 1 batch of scouts, otherwise, deploy 3 batches of scouts.
* Count the number of turrets on each side (left, right) of the enemy's battlefield and change side of attack to the side with significantly less turrets.

### Strengths

* Our defense is very effective against one batch of scout spam. This is because we use walls to absorb enemy's scouts.
* Our defense is effective against attacks directed at the middle. This is because such enemy's units are redirected to the side, thereby maximising their exposure to our turrets placed in the middle.
* Our attack is effective against defense using one layer of walls. This is because in such case, we use 3 batches of scouts, which means first two batches would destroy the walls, and the third batch reaches the edge.
* Our attack is effective against defense structure with turrets being spread out with little walls. This is because in that case, we use one batch of scouts so that turrets do not have time to destroy all scouts along the path of traversal.

### Weaknesses

* Our algorithm does not use demolishers. In the case where the enemy maximises exposure of our scouts to turrets and totally block the sides, our algorithm does not manage to score.
* In the case where the enemy spams scouts in at least 2 batches, our structure may not be able to defend.
* Our attack is ineffective against interceptors. This is because our pathing is relatively predictable, hence the enemy can plan interceptors to defend our scout spams.

## Python-2L-AET

Our idea is to use a V-shape defense structure with 2 layers. The idea is to fight against 2-batch scout spams. Attacks are directed towards enemy's edges.

In the case of enemy's redirection at the edge, we initially planned to use demolishers to destroy the walls at the edge, with interceptors as tanks, opening the path for scouts to score. However, we realised that such strategy is not very effective when there are upgraded enemy turrets at the sides, as our demolishers are still destroyed by those turrets before they can open up the walls. In the end, we decided to only use scouts to force open the wall.

On defense on the sides, we use interceptors to stop enemy's scout spam, in the case of enemy spamming multiple batches of scouts.

### Defense

* Two layers of walls in v-shape from one side to another, with pre-defined list of jobs to build.
* Refund weak walls and turrets and replace with new walls and turrets.
* In the case where the enemy spams scouts in multiple batches towards the side, we use interceptor rather than walls to block their attack.
* In the case where the enemy spams scouts in one batch towards the side, we use walls rather than interceptors to block their attack.

### Offense

* In the case where the enemy use walls for redirection, we spam one batch of scouts to force open the wall.
* Otherwise, we spam 2 batches of scouts for attack.

### Strengths

* Our defense is very effective against attacks directed towards the middle, due to the thick layer of defenses in the middle.
* Our structure performs consistently well due to the refund actions, which ensures that our walls can withstand enemy units' damage on movement.
* Our offense is effective against structures using walls to block path towards edges, due to our sheer strength of scouts (boosted up by supports) and our scouts

### Weaknesses

* Our defense opens up the side when we are attacking, which also means it is vulnerable against enemies using same side attack.
* Our offense is at times not effective against redirection with strong reinforcements on the side. We did manage to rank high because not many people use redirection against scout spams.

# Notes

Below are the notes from Correlation One's start kit.

## Algo Development

To test your algo locally, you should use the test_algo_[OS] scripts in the scripts folder. Details on its use is documented in the README.md file in the scripts folder.

For programming documentation of language specific algos, see each language specific README.
For documentation of the game-config or the json format the engine uses to communicate the current game state, see json-docs.html

For advanced users you can install java and run the game engine locally. Java 10 or above is required: [Java Development Kit 10 or above](http://www.oracle.com/technetwork/java/javase/downloads/jdk10-downloads-4416644.html).

All code provided in the starterkit is meant to be used as a starting point, and can be overwritten completely by more advanced players to improve performance or provide additional utility.

## Windows Setup

If you are running Windows, you will need Windows PowerShell installed. This comes pre-installed on Windows 10.
Some windows users might need to run the following PowerShell commands in administrator mode (right-click the
PowerShell icon, and click "run as administrator"):
    
    `Set-ExecutionPolicy Unrestricted`
    
If this doesn't work try this:
    
    `Set-ExecutionPolicy Unrestricted CurrentUser`
    
If that still doesn't work, try these below:
    
    `Set-ExecutionPolicy Bypass`
    `Set-ExecutionPolicy RemoteSigned`
    
And don't forget to run the PowerShell as admin.

## Uploading Algos

Simply select the folder of your algo when prompted on the [Terminal](https://terminal.c1games.com) website. Make sure to select the specific language folder such as "python-algo" do not select the entire starterkit itself.

## Troubleshooting

For detailed troubleshooting help related to both website problems and local development check out [the troubleshooting section](https://terminal.c1games.com/rules#Troubleshooting).

#### Python Requirements

Python algos require Python 3 to run. If you are running Unix (Mac OS or Linux), the command `python3` must run on 
Bash or Terminal. If you are running Windows, the command `py -3` must run on PowerShell.
   
#### Java Requirements

Java algos require the Java Development Kit. Java algos also require [Gradle]
(https://gradle.org/install/) for compilation.
   
## Running Algos

To run your algo locally or on our servers, or to enroll your algo in a competition, please see the [documentation 
for the Terminal command line interface in the scripts directory](https://github.com/correlation-one/AIGamesStarterKit/tree/master/scripts)
