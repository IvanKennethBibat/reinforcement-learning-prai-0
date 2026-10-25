# Reinforcement-Learning-PRAI-0
This is Assignment 1 of MSc Module: Principles of Artificial Intelligence. This is a PyGame desktop app to demonstrate a working reinforcement learning NPC in a turn-based battle with Dynamic Difficulty Adjustment (DDA), similar to Final Fantasy 7, or Pokemon games.

Q-learning is used as the primary algorithm, then further experiments with other algorithms will be tried and tested.

## Requirements
```text
python v3.14.*

gymnasium==1.4.0
matplotlib==3.11.2
numpy==2.5.4
pygame-ce==2.5.8
```

## Tech Stack
- gymnasium 
    - Provides the interface for developing and comparing reinforcement learning algorithms by providing a standard API to communicate between the RL agent and the environment.
- numpy
    - Python library used for storing the Q-table as an array of states x actions, performs the Q-learning updates and seed generator for reproducibility
- pygame-ce
    - Renders the battle screen, inputs and game loop.
    - Actively-maintained version of the original pygame library.
- matplotlib
    - Creates the visualisation of the RL model training pipeline: learning curves, baseline comparisons, Q-table heatmaps, and adaptation plots.

## Moves
Both players will have the same moveset and same base stats:

- Base Stats
    - 100 HP
    - 30 Mana

- Movesets
    - Attack
        - 12 max damage, 0 Mana cost.
    - Firebolt
        - 25 max damage, 10 mana cost.
    - Hone
        - Next Attack/Firebolt does 200% damage, 5 mana cost.
    - Heal
        - Gain 20 HP, 8 mana cost.  
    - Defend
        - Reduce Damage taken by 50%, gain 5 mana at end-of-turn.
 
## Game Rules
- Mana and HP cannot exceed 30 and 100 respectively, and cannot go below 0.
- Defend, then Heal has priority before other moves. Other moves are made simulateneously.
- Hone spends a turn to increase the next Attack/Firebolt, this must be done the following turn or the Hone effect is wasted. Hone does not stack.
- Draw after 30 turns have been made to prevent infinite loops.
- Win if the opponent's HP drops to 0. If both hit 0 in the same turn, it's a draw.
- Moves requiring mana that the player does not have will be unavailable.
- Moves from both players are made before any actions are completed.
- Damage is determined by the max damage multiplied by a random integer between 85-100, divided by 100, then rounded down, like in the pokemon games.