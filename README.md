# Reinforcement-Learning-PRAI-0
This is a PyGame app to demonstrate a working reinforcement learning NPC in a turn-based battle with Dynamic Difficulty Adjustment (DDA), similar to Final Fantasy 7, or Pokemon games.

The NPC is trained with tabular Q-learning. Difficulty is adjusted by choosing opponents from a pool of different strengths.

## Installation
With [uv](https://docs.astral.sh/uv/) (recommended), from the repository root:
```bash
uv sync                      # creates .venv with the exact versions in uv.lock
uv run pytest -q             # optional: runs the test suite
uv run python -m ui          # plays the game
```
Without uv, use Python 3.13 and `pip install -r requirements.txt`, then run the same commands without `uv run`. The trained Q-tables are committed in `checkpoints/`, so the game runs without retraining.

## Requirements
python v3.13.*
```text

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


## RL formulation
**State** (`battle/state.py`, 3072 states): the NPC's HP and mana, the opponent's HP and mana (each in 4 buckets), the opponent's last move (5 moves or none) and whether the NPC is honed. The game shows both fighters' HP and mana to the human player as well, so the NPC observes the same things a player does, and nothing hidden.

**Actions:** the five moves below. Moves the NPC can't afford are masked out.

**Reward** (`battle/env.py`): +1 for a win, -1 for a loss, 0 for a draw, plus potential-based shaping F = γΦ(s') − Φ(s), where Φ is the NPC's HP lead / 100 and Φ = 0 when the fight ends (Ng, Harada and Russell, 1999). The shaping rewards every turn that improves the NPC's position, heals included, and its discounted total over a fight is zero, so it speeds up learning without changing the best policy. An earlier reward paid 0.01 × damage traded each turn. It ignored heals, and in one of three seeds the agent learned to run down the 30-turn clock while ahead, because a timeout kept the damage it had already been paid for. `experiments/m3_ablation.py` compares the two rewards and two state changes (cost-aligned mana buckets and a late-fight clock flag), and `results/m3_ablation.json` has its results. Neither state change helped, so the state was kept as it is.

**Algorithm and hyperparameters:** tabular Q-learning (`agents/q_learning.py`) with α = 0.1 and γ = 0.95. ε decays linearly from 1.0 to 0.05 over the first 80% of 40,000 training episodes. Every experiment uses seeds 0, 1 and 2 for training, and reports results across all three.

## Training and DDA
Run these in order to regenerate every checkpoint and result:
```bash
uv run python -m experiments.train_pool       # trains the NPC over seeds 0-2 (about 30 s)
uv run python -m experiments.dda_simulation   # simulated players with and without DDA
uv run python -m experiments.plot_results     # draws the figures into results/
uv run python -m experiments.generalisation   # specialist vs mixed training (about 70 s)
uv run python -m experiments.tier_rules       # compares epsilon, rank and tolerance tier rules
uv run python -m experiments.m3_ablation pbrs # one reward/state variant; also base, mana5, clock, all
```
The NPC is trained against a random mix of the random, scripted and expert bots, so it doesn't overfit to one opponent. Q-tables are saved to `checkpoints/npc_seed{0,1,2}.npy`. All training and evaluation results come from simulated players (bots), not people.

**Opponent pool:** six tiers from one trained Q-table. Each tier makes a random legal move with probability 1.0, 0.8, 0.6, 0.4, 0.2 or 0.0, and otherwise plays greedily, so tier 0 is easiest. `results/tier_ladder.csv` shows player scores rising steadily as tiers get easier, on every seed and for every simulated player.

**DDA** (`agents/dda.py`): the indicator is the player's score over their last 10 fights (win 1, draw 0.5, loss 0). The target is 40-60%. The mechanism moves one tier harder above the band and one easier below it, after at least 3 fights and at most once every 3 fights. It checks after every fight, but changing the tier every fight overshoots: the 10-fight score lags behind a change, and in simulation the share of fights in the band fell from 67/52/45% to 60/37/32% (novice/intermediate/skilled). `results/dda_summary.csv` and `results/dda_adaptation.png` compare DDA with a fixed middle tier for three simulated players, over 30 runs each.

**In the game:** every foe, the boss included, is played by the seed 0 agent at exactly the tier DDA picks. One DDA director follows the player across the whole session. After each fight, press **R** to rematch, so a player can fill the 10-fight window. Every fight counts towards DDA, rematches included. A DDA badge is always on screen, at the top right of the map and under the turn counter in battle. It shows the current tier as pips and the player's win rate over the last 10 fights (win 1, draw 0.5), which is green inside the 40-60% target band and orange outside it. When DDA changes the tier, the next fight opens with a "DIFFICULTY UP" or "DIFFICULTY DOWN" notice. So the adaptation is visible in play without F1, and the player is told about it. Without `checkpoints/npc_seed0.npy`, the slimes fall back to the scripted bots.

**Interpretability:** press **F1** in game for a debug overlay. In battle, it shows the agent's state, its Q-value for each legal move, the move it picked and whether that move was greedy or a deliberate random one, plus the DDA tier and score. On the map, it shows the DDA tier and score. `results/q_policy_map.png` maps the learned greedy move across HP and mana situations, averaged over the states the agent actually visited (about two thirds of the table).

## Playing
```bash
uv run python -m ui
```
Arrow keys or WASD to walk and to pick a move, Enter or Space to confirm. Number keys 1-5 and the mouse also work in battle. Esc quits.

You play Pipkin, a small black cat clearing slimes out of a sunny valley. You start in the village, with roads out to the western meadow, the island court and the old ruins, and you can take them in any order. Back paths link the three areas, and two side areas are there to explore. Sheep graze and wander around the map, and hop away if you get too close. Slimes bounce around their own patch of the map. Foes start a fight when you get close, and beating all three slimes opens the Great Hall to the north, where Vesper waits. Every fight starts at full HP and mana, matching how the agents are trained. Foes and their policies are set in `ui/encounters.py`, and the level is a text map in `ui/assets/level.txt`.

To change the level, run `uv run python -m ui.editor` and paint with the mouse. Left click paints, right click picks up a tile, the arrow keys or WASD scroll, Ctrl+S saves and Ctrl+Z undoes. It won't save a level that can't be finished, such as one with a slime walled off.

Character art lives in sprite sheets in `ui/assets`, which you can edit in any pixel editor as long as the frame grid stays the same. `uv run python -m ui.bake_sprites` regenerates them from the drawing code and overwrites hand edits, so commit edited sheets first.

Pipkin's moves are Attack, Swipe, Sharpen Claws, Block and Heal. These are Pipkin's names for the engine's moves. Pipkin plays by exactly the same rules as the foes and the simulated players, so the training and DDA results describe the game a person plays.

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

## Hyperparameters
- Epsilon (ε)
    - Determines the balance between exploitation of known 'good' moves over exploration of new unseen moves.
    - A value of 0 (never explore new actions, always exploit) to 1 (acts randomly each step).
- Alpha (α)
    - Determines the learning-rate of the agent at each training step, adjusting weights in response to the error in each step.
    - A value of 0 (it learns nothing from new experiences) to 1 (Overwrites old knowledge with the latest experience).
- Gamma (γ)
    - The discount factor, determines the value of rewards now vs. future rewards to the agent.
    - A value of 0 (immediate rewards only) to 1 (Later/Immediate rewards matter the same to the agent).