### Required Steps to Obtain Stone Badge

### I. SPLIT 01 - Title Screen, Naming, and Moving Van

1.  **Title Screen & Intro**
    * MILESTONE: GAME_RUNNING
    * INTERACT: with Title Screen (Press A)
    * DIALOG: Professor Birch intro cutscene
    * SPECIAL: Select gender
    * SPECIAL: Select name
    * MILESTONE: PLAYER_NAME_SET
    * DIALOG: with professor Birch
    * MILESTONE: INTRO_CUTSCENE_COMPLETE

2.  **Truck Ride & House Intro**
    * NAVIGATE: to exit of moving van (8, 1, MOVING_VAN)
    * MILESTONE: LITTLEROOT_TOWN
    * DIALOG: with Mom (1F, after truck)
    * MILESTONE: PLAYER_HOUSE_ENTERED

### II. SPLIT 02 - Player's House & Rival's House

3.  **Set the Clock (Player's House)**
    * DIALOG: with Mom (PLAYERS_HOUSE_1F)
    * NAVIGATE: to stairs (8, 2, PLAYERS_HOUSE_1F)
    * MILESTONE: PLAYER_BEDROOM
    * NAVIGATE: to clock (5, 1, PLAYERS_HOUSE_2F)
    * INTERACT: with clock (5, 1, PLAYERS_HOUSE_2F)
    * DIALOG: with Mom (2F, after clock)
    * NAVIGATE: to stairs (8, 2, PLAYERS_HOUSE_2F)
    * DIALOG: with Mom (1F, after clock)
    * NAVIGATE: to exit (4, 7, PLAYERS_HOUSE_1F)

4.  **Visit Rival (May's House)**
    * NAVIGATE: to May's house (14, 8, LITTLEROOT_TOWN)
    * MILESTONE: RIVAL_HOUSE
    * DIALOG: with May's mother (MAYS_HOUSE_1F)
    * NAVIGATE: to stairs (2, 2, MAYS_HOUSE_1F)
    * MILESTONE: RIVAL_BEDROOM
    * NAVIGATE: to Pokéball (5, 4, MAYS_HOUSE_2F)
    * INTERACT: with Pokéball to trigger May (5, 4, MAYS_HOUSE_2F)
    * DIALOG: with May (MAYS_HOUSE_2F)
    * NAVIGATE: to stairs (1, 1, MAYS_HOUSE_2F)
    * DIALOG: with May (MAYS_HOUSE_1F, after coming downstairs)
    * NAVIGATE: to exit (2, 9, MAYS_HOUSE_1F)

5.  **Leave Town**
    * NAVIGATE: to north of town (11, 1, LITTLEROOT_TOWN)
    * DIALOG: with NPC (11, 1, LITTLEROOT_TOWN)

6.  **Birch Rescue (Route 101)**
    * NAVIGATE: to Route 101 (triggers Birch cutscene)
    * MILESTONE: ROUTE_101
    * NAVIGATE: to Birch's bag (7, 14, ROUTE_101)
    * INTERACT: with Birch's bag (7, 14, ROUTE_101)
    * SPECIAL: Starter Selection menu (confirm first Pokémon)
    * MILESTONE: STARTER_CHOSEN
    * BATTLE: with wild Poochyena (ROUTE_101)

7.  **Return to Lab**
    * MILESTONE: BIRCH_LAB_VISITED
    * DIALOG: with Birch (BIRCHS_LAB)
    * INTERACT: with Nickname screen (decline nickname)
    * NAVIGATE: to exit Birch's Lab (6, 13, BIRCHS_LAB)

### III. SPLIT 03 - Defeat rival and talk to Birch
8. Travel from Littleroot Town to Oldale to Route 103 (9,3, route 103)
    * NAVIGATE: from littleroot Town to Route 101
    * NAVIGATE: from Route 101 to Oldale
    * MILESTONE: OLDALE_TOWN
    * NAVIGATE: from Oldale to Route 103
    * MILESTONE: ROUTE_103
    * INTERACT: Interact with your Rival (9,3, ROUTE_103) 
    * BATTLE: with rival at (9, 3, ROUTE_103)
    * NAVIGATE: to poke center (6, 16, OLDALE TOWN)
    * INTERACT: Interact with poke center (7, 3, OLDALE TOWN POKEMON CENTER 1F)
    * NAVIGATE: out of poke center (7, 9, OLDALE TOWN POKEMON CENTER 1F)
    * NAVIGATE: to ROUTE 103 (8, 19, OLDALE TOWN)
    * DIALOG: auto dialog with may on way south to birch
    
9. Navigate from Route 103 to Oldale to Littleroot Town
    * NAVIGATE: to Birch Lab (7,16, Littleroot Town)
    * DIALOG: With Birch 
    * MILESTONE: RECEIVED_POKEDEX
    * NAVIGATE: out of Birch lab (6,13, BIRCH LAB)

### IV. SPLIT 04 - Travel to Petalburg City, Talk to Dad, and Help Wally
10. Travel to Petalburg City via Route 102
    * NAVIGATE: TO (10,9 LittleRoot Town)
    * DIALOG: auto-dialog with mom
    * NAVIGATE: TO ROUTE101 
    * NAVIGATE: TO OLDALE_TOWN
    * NAVIGATE to ROUTE_102 (0, 11, Oldale Town)
    * MILESTONE: ROUTE_102
    * BATTLE AT (33,15, ROUTE_102)
    * NAVIGATE TO (25, 14, ROUTE_102)
    * BATTLE AT (25, 14, ROUTE_102)
    * NAVIGATE TO (19, 7, ROUTE_102)
    * BATTLE AT (19, 7, ROUTE_102)
    * NAVIGATE TO PETLABURG_CITY (0, 8, ROUTE_102)
    * MILESTONE: PETALBURG_CITY
    
11. Assist Wally in catching a Pokémon
    * NAVIGATE: TO Petalburg Gym (15, 8 PETALBURG CITY)
    * INTERACT: with dad (15, 9, PETALBURG CITY GYM) <-- SHOULD THIS BE (4,107)?>
    * MILESTONE: DAD_FIRST_MEETING
    * DIALOG: Wally tutorial cinematic 
    * MILESTONE: GYM_EXPLANATION
    * NAVIGATE: out of gym (4, 112)

### V. SPLIT 05 - Proceed to Rustboro City via Route 104 (WEST) and Petalburg Woods
12. ROUTE 104 SOUTH -> PETALBURG WOODS
    * NAVIGATE: to (4, 12, PETALBURG CITY)
    * DIALOG: automatic dialog with team aqua when leaving 
    * NAVIGATE: to route 104 south
    * NAVIGATE: TO PETALBURG_WOODS
        - AVOID BATTLE AT (11, 43, ROUTE_103) -- avoid due to full restore
    * MILESTONE: PETALBURG_WOODS

13. PETALBURG WOODS -> ROUTE 104 NORTH
    * NAVIGATE: TO (9, 32, PETALBURG WOODS)
    * BATTLE AT (9, 32, PETALBURG WOODS)
    * NAVIGATE: TO (26, 23, PETALBURG WOODS)
    * DIALOG AT (26, 23, PETALBURG WOODS)
    * BATTLE AT (26, 23, PETALBURG WOODS)
    * DIALOG AT (26, 23, PETALBURG WOODS)
    * MILESTONE: TEAM_AQUA_GRUNT_DEFEATED
    * NAVIGATE TO (7, 14, PETALBURG WOODS)
    * BATTLE AT (7, 14, PETALBURG WOODS)
    * NAVIGATE TO ROUTE 104
    * MILESTONE: ROUTE_104_NORTH

14. ROUTE 104 -> RUSTBORO CITY
    * NAVIGATE TO (19, 25, ROUTE104)
    * BATTLE AT (19, 25, ROUTE104)
    * NAVIGATE TO RUSTBORO_CITY
        - AVOID BATTLE AT (24, 24, ROUTE104) -- avoid due to shroomish
    * MILESTONE: RUSTBORO_CITY

### VI. SPLIT 06 - Enter Gym and defeat roxanne
15. Rustoboro city -> RUSTBORO CITY GYM (27, 19, RUSTBORO CITY)
    * NAVIGATE: TO RUSTBORO CITY POKEMON CENTER (16, 38, RUSTBORO CITY)
    * NAVIGATE: TO (7, 3 RUSTBORO CITY POKEMON CENTER 1F)
    * INTERACT: with nurse at (7, 3, RUSTBORO CITY POKEMON CENTER 1F)
    * NAVIGATE: TO (7, 9 RUSTBORO CITY POKEMON CENTER 1F)
    * NAVIGATE: TO RUSTBORO CITY GYM (27, 19, RUSTBORO CITY)
    * MILESTONE: RUSTBORO_GYM_ENTERED

16. RUSTBORO CITY GYM
    * NAVIGATE: TO (1,16, RUSTBORO CITY GYM)
    * NAVIGATE: TO (2,10, RUSTBORO CITY GYM)
    * NAVIGATE: TO (2,9, RUSTBORO CITY GYM)
    * BATTLE: AT (2,9, RUSTBORO CITY GYM)
    * NAVIGATE: TO (5, 2 RUSTBORO CITY GYM)
    * INTERACT: with roxanne at (5, 2 RUSTBORO CITY GYM)
    * MILESTONE: ROXANNE_DEFEATED
    * MILESTONE: FIRST_GYM_COMPLETE
    * MILESTONE: STONE_BADGE
