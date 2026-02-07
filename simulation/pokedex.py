# simulation/pokedex.py

# Map Internal Gen 3 IDs to readable names and Types
# 0=Normal, 1=Fighting, 2=Flying, 3=Poison, 4=Ground, 5=Rock, 6=Bug, 7=Ghost, 8=Steel
# 9=Mystery, 10=Fire, 11=Water, 12=Grass, 13=Electric, 14=Psychic, 15=Ice, 16=Dragon, 17=Dark

# TYPE CHART (18x18 matrix could go here, or simple dicts)
TYPE_MAP = {
    0: "Normal", 
    1: "Fighting", 
    2: "Flying", 
    3: "Poison", 
    4: "Ground", 
    5: "Rock", 
    6: "Bug", 
    7: "Ghost", 
    8: "Steel", 
    9: "???", 
    10: "Fire", 
    11: "Water", 
    12: "Grass", 
    13: "Electric", 
    14: "Psychic", 
    15: "Ice", 
    16: "Dragon", 
    17: "Dark"
}

# ----------------------------------------------------------------------------------
# SPECIES DATA (Internal Gen 3 ID -> {Name, Types})
# ----------------------------------------------------------------------------------
# NOTE: Gen 3 Internal IDs usually start Gen 3 Pokemon at 277 (Treecko).
# Verified Anchors: Torchic=280, Mudkip=283, Wurmple=290.
SPECIES_DATA = {
    # --- STARTERS ---
    277: {"name": "Treecko",   "types": [12, None]},
    278: {"name": "Grovyle",   "types": [12, None]},
    279: {"name": "Sceptile",  "types": [12, None]},
    
    280: {"name": "Torchic",   "types": [10, None]}, # Verified
    281: {"name": "Combusken", "types": [10, 1]},
    282: {"name": "Blaziken",  "types": [10, 1]},
    
    283: {"name": "Mudkip",    "types": [11, None]}, # Verified
    284: {"name": "Marshtomp", "types": [11, 4]},
    285: {"name": "Swampert",  "types": [11, 4]},

    # --- ROUTE 101 / 102 / 103 (Early Game) ---
    286: {"name": "Poochyena", "types": [17, None]}, # Verified
    287: {"name": "Mightyena", "types": [17, None]},
    288: {"name": "Zigzagoon", "types": [0, None]},  # Verified
    289: {"name": "Linoone",   "types": [0, None]},
    290: {"name": "Wurmple",   "types": [6, None]},  # Verified
    291: {"name": "Silcoon",   "types": [6, None]},
    292: {"name": "Beautifly", "types": [6, 2]},
    293: {"name": "Cascoon",   "types": [6, None]},
    294: {"name": "Dustox",    "types": [6, 3]},
    
    # --- BEST GUESSES (Standard Order) ---
    295: {"name": "Lotad",     "types": [11, 12]},
    296: {"name": "Lombre",    "types": [11, 12]},
    297: {"name": "Ludicolo",  "types": [11, 12]},
    298: {"name": "Seedot",    "types": [12, None]},
    299: {"name": "Nuzleaf",   "types": [12, 17]},
    300: {"name": "Shiftry",   "types": [12, 17]},
    
    301: {"name": "Taillow",   "types": [0, 2]},
    302: {"name": "Swellow",   "types": [0, 2]},
    
    303: {"name": "Wingull",   "types": [11, 2]}, # Standard ID
    304: {"name": "Pelipper",  "types": [11, 2]},
    
    305: {"name": "Ralts",     "types": [14, None]}, # Often 305 or 309 depending on gap
    306: {"name": "Kirlia",    "types": [14, None]},
    307: {"name": "Gardevoir", "types": [14, None]},
    
    # User Reported Drift:
    309: {"name": "Wingull?",  "types": [11, 2]},    # User observed Wingull here
}

# ----------------------------------------------------------------------------------
# MOVE DATA (Move ID -> {Name, Type, Power})
# ----------------------------------------------------------------------------------
MOVES_DATA = {
    # PHYSICAL (Normal)
    1:  {"name": "Pound",        "type": 0,  "power": 40},
    10: {"name": "Scratch",      "type": 0,  "power": 40},
    33: {"name": "Tackle",       "type": 0,  "power": 35},
    98: {"name": "Quick Attack", "type": 0,  "power": 40},
    
    # SPECIAL / ELEMENTAL (Early Game)
    52: {"name": "Ember",        "type": 10, "power": 40},
    55: {"name": "Water Gun",    "type": 11, "power": 40},
    71: {"name": "Absorb",       "type": 12, "power": 20},
    64: {"name": "Peck",         "type": 2,  "power": 35},
    122:{"name": "Lick",         "type": 7,  "power": 20},
    40: {"name": "Poison Sting", "type": 3,  "power": 15},
    310:{"name": "Astonish",     "type": 7,  "power": 30},
    
    # STATUS / NON-DAMAGING
    45: {"name": "Growl",        "type": 0,  "power": 0},
    39: {"name": "Tail Whip",    "type": 0,  "power": 0},
    43: {"name": "Leer",         "type": 0,  "power": 0},
    81: {"name": "String Shot",  "type": 6,  "power": 0},
    106:{"name": "Harden",       "type": 0,  "power": 0},
    103:{"name": "Screech",      "type": 0,  "power": 0},
}

def get_effectiveness(move_type, target_types):
    """
    Calculates Type Effectiveness Multiplier.
    """
    if move_type is None or move_type == 9: return 1.0 # Ignore ??? type
    
    multiplier = 1.0
    for t in target_types:
        if t is None: continue
        
        # --- FIRE (10) ---
        if move_type == 10:
            if t in [12, 6, 15, 8]: multiplier *= 2.0   # Grass, Bug, Ice, Steel
            if t in [10, 11, 5, 16]: multiplier *= 0.5  # Fire, Water, Rock, Dragon
            
        # --- WATER (11) ---
        elif move_type == 11:
            if t in [10, 4, 5]: multiplier *= 2.0       # Fire, Ground, Rock
            if t in [11, 12, 16]: multiplier *= 0.5     # Water, Grass, Dragon
            
        # --- GRASS (12) ---
        elif move_type == 12:
            if t in [11, 4, 5]: multiplier *= 2.0       # Water, Ground, Rock
            if t in [10, 12, 3, 2, 6, 8, 16]: multiplier *= 0.5
            
        # --- NORMAL (0) ---
        elif move_type == 0:
            if t == 5: multiplier *= 0.5 # Rock
            if t == 7: multiplier *= 0.0 # Ghost
            
        # --- FLYING (2) ---
        elif move_type == 2:
            if t in [12, 1, 6]: multiplier *= 2.0       # Grass, Fighting, Bug
            if t in [13, 5, 8]: multiplier *= 0.5
            
    return multiplier