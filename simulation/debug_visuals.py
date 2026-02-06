import time
import gymnasium as gym
import numpy as np
import stable_retro as retro
import pygame
import sys

# Import your existing wrapper from train.py
from train import EmeraldBattleWrapper 

class VisualBattleWrapper(EmeraldBattleWrapper):
    """
    A subclass specifically for visually debugging the macros.
    It takes a Pygame screen object to draw directly to the window.
    """
    def __init__(self, env, screen):
        super().__init__(env)
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)

    def _render_frame(self, unused_obs, info, action_name="Wait"):
        """
        Manually draws the observation to the Pygame window.
        CRITICAL FIX: We ignore 'unused_obs' because it might be the 
        RL feature vector (HP/PP). We fetch the raw screen directly.
        """
        # 1. Check for Quit events (keeps window responsive)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # 2. Fetch the RAW SCREEN from the emulator backend
        # This bypasses the wrapper's observation processing
        raw_screen = self.env.get_screen()

        # 3. Convert (H, W, 3) -> Pygame Surface (W, H, 3)
        surf = pygame.surfarray.make_surface(raw_screen.swapaxes(0, 1))
        
        # 4. Scale up (2x)
        surf = pygame.transform.scale(surf, (480, 320))
        
        # 5. Draw to Screen
        self.screen.blit(surf, (0, 0))
        
        # 6. Draw Debug Overlay
        hp_text = f"HP: {info.get('my_hp', '?')} vs {info.get('enemy_hp', '?')}"
        act_text = f"Action: {action_name}"
        
        # Simple text shadow for readability
        self.screen.blit(self.font.render(hp_text, True, (0, 0, 0)), (12, 12))
        self.screen.blit(self.font.render(hp_text, True, (255, 255, 255)), (10, 10))
        
        self.screen.blit(self.font.render(act_text, True, (0, 0, 0)), (12, 32))
        self.screen.blit(self.font.render(act_text, True, (255, 255, 255)), (10, 30))

        pygame.display.flip()
        
        # 7. Cap Framerate to normal speed (60 FPS)
        self.clock.tick(60)

    def _wait(self, frames):
        """
        Overrides the fast-forward to render frames slowly.
        """
        print(f"   [DEBUG] Waiting {frames} frames (Animation)...")
        no_op = np.zeros(12, dtype=np.int8)
        
        for i in range(frames):
            # We step the internal env to keep time moving
            _, _, _, _, info = self.env.step(no_op)
            self._render_frame(None, info, action_name="Waiting...")

    def _press_button(self, btn_name, hold_frames=4):
        """
        Overrides button press to log and render.
        """
        print(f"   [DEBUG] Pressing Button: {btn_name}")
        
        action_arr = np.zeros(12, dtype=np.int8)
        action_arr[self.btn_indices[btn_name]] = 1
        
        # Hold
        for _ in range(hold_frames):
            _, _, _, _, info = self.env.step(action_arr)
            self._render_frame(None, info, action_name=f"Press {btn_name}")
            
        # Release (Gap)
        no_op = np.zeros(12, dtype=np.int8)
        for _ in range(4):
            _, _, _, _, info = self.env.step(no_op)
            self._render_frame(None, info, action_name="Release")

def main():
    # 1. Setup Pygame Window
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((480, 320))
    pygame.display.set_caption("Pokemon Emerald - Macro Debugger")
    
    # 2. Load Environment
    print("Loading Pokemon Emerald...")
    # render_mode='rgb_array' ensures get_screen() works
    raw_env = retro.make(game='PokemonEmerald-GBA', state='BattleLevel5', render_mode='rgb_array')
    
    # 3. Wrap with Visual Debugger
    env = VisualBattleWrapper(raw_env, screen)
    
    # Reset returns the STATS vector (obs), but we ignore it in _render_frame
    obs, info = env.reset()
    
    # Initial Draw
    env._render_frame(obs, info, "READY")
    
    print("Environment Ready. Starting Battle Loop...")
    print("-" * 50)

    try:
        while True:
            # 4. Interactive Loop
            pygame.event.pump() 
            
            print(f"\n[TURN START] HP: {info.get('my_hp')} vs {info.get('enemy_hp')}")
            print("Select a Move to Test (Focus on Terminal):")
            print("  1: Top-Left  (Move 1)")
            print("  2: Top-Right (Move 2)")
            print("  3: Bot-Left  (Move 3)")
            print("  4: Bot-Right (Move 4)")
            
            try:
                user_input = input(">> Enter 1-4 (or 'q' to quit): ")
                if user_input.lower() == 'q': break
                
                action_idx = int(user_input) - 1
                if action_idx not in [0, 1, 2, 3]: raise ValueError
                
            except ValueError:
                print("Invalid input. Defaulting to Move 1.")
                action_idx = 0

            # 5. Run the Macro Step (This will animate in the window)
            # step() returns the STATS vector, which is fine for RL but we don't draw it.
            obs, reward, terminated, truncated, info = env.step(action_idx)
            
            print(f"[TURN END] Reward: {reward:.2f}")

            if terminated:
                print("\n!!! BATTLE ENDED !!!")
                # Wait a moment to see the result
                env._wait(120) 
                obs, info = env.reset()
                print("Resetting environment...\n")

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        env.close()
        pygame.quit()

if __name__ == "__main__":
    main()