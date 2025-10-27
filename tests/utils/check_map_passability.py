#!/usr/bin/env python3
"""
Check what the map data says about position (12,12) and surrounding tiles
"""

import subprocess
import time
import requests

cmd = ["python", "-m", "server.app", "--port", "8000", "--load-state", "tests/states/dialog.state"]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    time.sleep(8)
    
    # Get state with map data
    resp = requests.get("http://localhost:8000/state", timeout=2)
    state = resp.json()
    
    print("=" * 70)
    print("MAP DATA AT POSITION (12, 12)")
    print("=" * 70)
    
    pos = state["player"]["position"]
    print(f"\nPlayer position: ({pos['x']}, {pos['y']})")
    print(f"Location: {state['player']['location']}")
    print(f"in_dialog: {state['game']['in_dialog']}")
    print(f"movement_enabled: {state['game']['movement_enabled']}")
    
    # Get map tiles
    if "map" in state and "tiles" in state["map"]:
        tiles = state["map"]["tiles"]
        if tiles and len(tiles) > 14 and len(tiles[0]) > 14:
            print(f"\nMap dimensions: {len(tiles[0])}x{len(tiles)}")
            print("\nTiles around player (showing passability):")
            print("  U = UP (12,11), D = DOWN (12,13), L = LEFT (11,12), R = RIGHT (13,12)")
            print()
            
            # Show 5x5 grid around player
            for dy in range(-2, 3):
                row = []
                for dx in range(-2, 3):
                    x, y = 12 + dx, 12 + dy
                    if 0 <= y < len(tiles) and 0 <= x < len(tiles[0]):
                        tile = tiles[y][x]
                        # tile is [id, behavior, collision, elevation]
                        if len(tile) >= 3:
                            collision = tile[2]
                            if dx == 0 and dy == 0:
                                marker = "P"  # Player
                            elif dx == 0 and dy == -1:
                                marker = "U"  # UP
                            elif dx == 0 and dy == 1:
                                marker = "D"  # DOWN
                            elif dx == -1 and dy == 0:
                                marker = "L"  # LEFT
                            elif dx == 1 and dy == 0:
                                marker = "R"  # RIGHT
                            else:
                                marker = "·"
                            
                            if collision == 0:
                                row.append(f" {marker} ")  # Passable
                            else:
                                row.append(f"[{marker}]")  # Blocked
                        else:
                            row.append(" ? ")
                    else:
                        row.append(" X ")
                print("".join(row))
            
            print("\nLegend: P=Player, U/D/L/R=Directions, [ ]=Blocked, ( )=Passable")
            
            # Check specific tiles
            print("\nTile Details:")
            for direction, (dx, dy) in [("UP", (0, -1)), ("DOWN", (0, 1)), ("LEFT", (-1, 0)), ("RIGHT", (1, 0))]:
                x, y = 12 + dx, 12 + dy
                if 0 <= y < len(tiles) and 0 <= x < len(tiles[0]):
                    tile = tiles[y][x]
                    if len(tile) >= 4:
                        tile_id, behavior, collision, elevation = tile[:4]
                        passable = "✓ PASSABLE" if collision == 0 else "✗ BLOCKED"
                        print(f"  {direction:5} ({x},{y}): collision={collision} {passable}")
    
    print("=" * 70)

finally:
    process.terminate()
    try:
        process.wait(timeout=5)
    except:
        process.kill()
