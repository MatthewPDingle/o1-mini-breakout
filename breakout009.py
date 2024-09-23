import pygame
import sys
import random
import math
import numpy as np
import os
import logging  # Import the logging module

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all levels of log messages
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log to console
    ]
)

logging.info("Initializing Pygame and setting up the game.")

# Initialize Pygame
pygame.init()

# Game Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
MAX_SPEED = 15  # Maximum speed for ball
MAX_BALLS = 10  # Maximum number of balls allowed

# Colors
WHITE = (255, 255, 255)
GREY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (160, 32, 240)

# Screen Setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Breakout Game")
clock = pygame.time.Clock()

# Fonts
font = pygame.font.SysFont("Arial", 24)
large_font = pygame.font.SysFont("Arial", 48)

# Initialize Mixer
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    logging.info("Pygame mixer initialized successfully.")
except pygame.error as e:
    logging.error(f"Failed to initialize Pygame mixer: {e}")

# Volume Control
VOLUME = 0.1  # Default volume set to 10% (range: 0.0 to 1.0)
logging.debug(f"Initial volume set to {VOLUME * 100}%.")

# Helper Function for Angle Calculation
def calculate_angle(speed_x, speed_y):
    angle_rad = math.atan2(-speed_y, speed_x)  # Negative speed_y to account for Pygame's y-axis direction
    angle_deg = math.degrees(angle_rad)
    return round(angle_deg, 2)

# Generate simple beep sounds using numpy
def generate_sound(frequency, duration=0.1, volume=0.5):
    logging.debug(f"Generating sound: frequency={frequency}Hz, duration={duration}s, volume={volume}.")
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    wave = np.sin(2 * math.pi * frequency * t)  # Generate sine wave
    wave = (wave * volume * 32767).astype(np.int16)  # Scale to 16-bit integer
    stereo_wave = np.column_stack((wave, wave))  # Duplicate for stereo
    sound = pygame.sndarray.make_sound(stereo_wave)
    logging.debug("Sound generated successfully.")
    return sound

# Sound Effects
paddle_sound = generate_sound(440)       # A4 note
brick_sound = generate_sound(880)        # A5 note
wall_sound = generate_sound(330)         # E4 note
game_over_sound = generate_sound(220)    # A3 note
powerup_sound = generate_sound(550)      # C#5 note

# List of all sound effects for easy volume management
SOUND_EFFECTS = [paddle_sound, brick_sound, wall_sound, game_over_sound, powerup_sound]

# Set initial volume for all sound effects
for sound in SOUND_EFFECTS:
    sound.set_volume(VOLUME)
logging.debug("Initial volume set for all sound effects.")

# Power-Up Types
POWERUP_TYPES = ['expand_paddle', 'extra_life', 'multi_ball']

# High Score File
HIGH_SCORE_FILE = 'highscore.txt'

def load_high_score(filename=HIGH_SCORE_FILE):
    logging.info(f"Loading high score from {filename}.")
    try:
        with open(filename, 'r') as f:
            high_score = int(f.read())
            logging.info(f"High score loaded: {high_score}.")
            return high_score
    except FileNotFoundError:
        logging.warning(f"{filename} not found. Starting with high score of 0.")
        return 0
    except ValueError:
        logging.error(f"Invalid high score format in {filename}. Resetting to 0.")
        return 0
    except Exception as e:
        logging.error(f"Error loading high score: {e}")
        return 0

def save_high_score(score, filename=HIGH_SCORE_FILE):
    logging.info(f"Saving high score {score} to {filename}.")
    try:
        with open(filename, 'w') as f:
            f.write(str(score))
        logging.info("High score saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save high score: {e}")

# Paddle Class
class Paddle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        logging.debug("Initializing Paddle.")
        self.width = 100
        self.height = 20
        self.color = BLUE
        self.speed = 7
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH / 2
        self.rect.bottom = SCREEN_HEIGHT - 30
        self.expanded = False
        self.expand_timer = 0
        self.moving_left = False
        self.moving_right = False
        logging.debug(f"Paddle initialized at position ({self.rect.centerx}, {self.rect.centery}).")

    def update(self, keys):
        self.moving_left = False
        self.moving_right = False
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
            self.moving_left = True
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
            self.moving_right = True

        # Keep paddle within screen
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

        # Handle paddle expansion timer
        if self.expanded:
            self.expand_timer -= 1
            if self.expand_timer <= 0:
                self.shrink()
            else:
                # Change color to indicate active power-up
                self.image.fill(ORANGE)
        else:
            self.image.fill(self.color)

    def expand(self, duration=300):
        logging.info("Expanding Paddle.")
        if not self.expanded:
            self.expanded = True
            self.expand_timer = duration
            new_width = min(int(self.width * 1.5), SCREEN_WIDTH - 20)  # Ensure paddle doesn't exceed screen
            if new_width != self.width:
                self.width = new_width
                self.image = pygame.Surface([self.width, self.height])
                self.image.fill(ORANGE)  # Change color to indicate expansion
                self.rect = self.image.get_rect(center=self.rect.center)
                logging.debug(f"Paddle expanded to width {self.width}.")

    def shrink(self):
        logging.info("Shrinking Paddle.")
        self.expanded = False
        self.width = 100  # Reset to original width
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect(center=self.rect.center)
        logging.debug(f"Paddle shrunk to width {self.width}.")

# Ball Class
class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y, speed_x=None, speed_y=-4, speed_increment=0):
        super().__init__()
        logging.debug("Initializing Ball.")
        self.radius = 10
        self.color = RED
        self.image = pygame.Surface([self.radius*2, self.radius*2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect()
        self.x = float(x)
        self.y = float(y)
        self.speed_x = speed_x if speed_x else random.choice([-4, 4])
        self.speed_y = speed_y
        self.prev_rect = self.rect.copy()
        self.speed_increment = speed_increment
        self.speed_increment_applied = False  # Flag to ensure speed_increment is applied only once
        logging.debug(f"Ball initialized at ({self.x}, {self.y}) with speed ({self.speed_x}, {self.speed_y}).")

    def update(self):
        # Apply speed increment only once
        if self.speed_increment != 0 and not self.speed_increment_applied:
            self.speed_x *= (1 + self.speed_increment)
            self.speed_y *= (1 + self.speed_increment)
            # Clamp speed to MAX_SPEED
            self.speed_x = max(-MAX_SPEED, min(self.speed_x, MAX_SPEED))
            self.speed_y = max(-MAX_SPEED, min(self.speed_y, MAX_SPEED))
            logging.debug(f"Ball speed incremented to ({self.speed_x}, {self.speed_y}).")
            self.speed_increment_applied = True

        # Store previous position
        self.prev_rect = self.rect.copy()

        # Move the ball
        self.x += self.speed_x
        self.y += self.speed_y

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

        # Bounce off left and right walls
        if self.rect.left <= 0:
            logging.info("Ball collided with the left wall.")
            angle_before_wall = calculate_angle(self.speed_x, self.speed_y)
            self.rect.left = 0
            self.speed_x = abs(self.speed_x)
            self.x = float(self.rect.x)
            wall_sound.play()
            angle_after_wall = calculate_angle(self.speed_x, self.speed_y)
            logging.info(f"Ball bounced off left wall. Angle changed from {angle_before_wall}° to {angle_after_wall}°.")

        if self.rect.right >= SCREEN_WIDTH:
            logging.info("Ball collided with the right wall.")
            angle_before_wall = calculate_angle(self.speed_x, self.speed_y)
            self.rect.right = SCREEN_WIDTH
            self.speed_x = -abs(self.speed_x)
            self.x = float(self.rect.x)
            wall_sound.play()
            angle_after_wall = calculate_angle(self.speed_x, self.speed_y)
            logging.info(f"Ball bounced off right wall. Angle changed from {angle_before_wall}° to {angle_after_wall}°.")

        # Bounce off top
        if self.rect.top <= 0:
            logging.info("Ball collided with the top wall.")
            angle_before_wall = calculate_angle(self.speed_x, self.speed_y)
            self.rect.top = 0
            self.speed_y = abs(self.speed_y)
            self.y = float(self.rect.y)
            wall_sound.play()
            angle_after_wall = calculate_angle(self.speed_x, self.speed_y)
            logging.info(f"Ball bounced off top wall. Angle changed from {angle_before_wall}° to {angle_after_wall}°.")

        # Clamp speed to MAX_SPEED
        if abs(self.speed_x) > MAX_SPEED:
            self.speed_x = math.copysign(MAX_SPEED, self.speed_x)
            logging.debug(f"Ball speed_x clamped to {self.speed_x}.")
        if abs(self.speed_y) > MAX_SPEED:
            self.speed_y = math.copysign(MAX_SPEED, self.speed_y)
            logging.debug(f"Ball speed_y clamped to {self.speed_y}.")

        # Ensure speed components do not become zero
        MIN_SPEED_X = 2
        if abs(self.speed_x) < MIN_SPEED_X:
            self.speed_x = math.copysign(MIN_SPEED_X, self.speed_x)
            logging.warning(f"Ball speed_x too low. Reset to {self.speed_x}.")

        MIN_SPEED_Y = 2
        if abs(self.speed_y) < MIN_SPEED_Y:
            self.speed_y = math.copysign(MIN_SPEED_Y, self.speed_y)
            logging.warning(f"Ball speed_y too low. Reset to {self.speed_y}.")

    def reset(self, x, y):
        logging.info(f"Resetting Ball to position ({x}, {y}).")
        self.x = float(x)
        self.y = float(y)
        self.rect.centerx = x
        self.rect.centery = y
        self.speed_x = random.choice([-4, 4])
        self.speed_y = -4
        self.speed_increment = 0
        self.speed_increment_applied = False
        logging.debug(f"Ball reset with speed ({self.speed_x}, {self.speed_y}).")

# Brick Class
class Brick(pygame.sprite.Sprite):
    def __init__(self, x, y, hits=1, color=GREEN):
        super().__init__()
        self.width = 60
        self.height = 20
        self.hits = hits
        self.max_hits = hits
        self.color = color
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def hit(self):
        logging.info(f"Brick at ({self.rect.x}, {self.rect.y}) was hit. Remaining hits: {self.hits - 1}.")
        self.hits -= 1
        if self.hits > 0:
            # Change color based on remaining hits
            color_intensity = int(255 * (self.hits / self.max_hits))
            self.color = (color_intensity, 0, 255 - color_intensity)
            self.image.fill(self.color)
            logging.debug(f"Brick color changed to {self.color}.")
        else:
            self.kill()
            logging.info(f"Brick at ({self.rect.x}, {self.rect.y}) destroyed.")
            # 20% chance to drop a power-up
            if random.random() < 0.2:
                powerup = PowerUp(self.rect.centerx, self.rect.centery)
                all_powerups.add(powerup)
                all_sprites.add(powerup)
                logging.debug("Power-up dropped by brick.")
            # 10% chance for explosive brick
            if random.random() < 0.1:
                logging.debug("Brick is explosive. Triggering explosion.")
                self.explode()

    def explode(self):
        # Destroy adjacent bricks
        logging.info(f"Brick at ({self.rect.x}, {self.rect.y}) is exploding adjacent bricks.")
        adjacent_bricks = pygame.sprite.spritecollide(self, bricks, False)
        for brick in adjacent_bricks:
            brick.kill()
            logging.debug(f"Adjacent brick at ({brick.rect.x}, {brick.rect.y}) destroyed by explosion.")
            # 20% chance to drop a power-up from each destroyed adjacent brick
            if random.random() < 0.2:
                powerup = PowerUp(brick.rect.centerx, brick.rect.centery)
                all_powerups.add(powerup)
                all_sprites.add(powerup)
                logging.debug("Power-up dropped by exploded adjacent brick.")
            # 10% chance for further explosions (recursive)
            if random.random() < 0.1:
                logging.debug("Adjacent brick is also explosive. Triggering further explosion.")
                brick.explode()

# Power-Up Class
class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, power_type=None):
        super().__init__()
        self.width = 20
        self.height = 20
        self.power_type = power_type if power_type else random.choice(POWERUP_TYPES)
        self.color = {
            'expand_paddle': ORANGE,
            'extra_life': PURPLE,
            'multi_ball': YELLOW
        }.get(self.power_type, WHITE)
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        self.speed_y = 3
        logging.debug(f"PowerUp '{self.power_type}' created at ({x}, {y}).")

    def update(self):
        self.rect.y += self.speed_y
        # Remove if out of screen
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()
            logging.debug(f"PowerUp '{self.power_type}' removed for moving out of screen.")

# Initialize Sprite Groups
all_sprites = pygame.sprite.Group()
bricks = pygame.sprite.Group()
all_powerups = pygame.sprite.Group()
balls = pygame.sprite.Group()

# Create Bricks
def create_bricks(rows, cols, level=1):
    logging.info(f"Creating bricks: rows={rows}, cols={cols}, level={level}.")
    bricks_group = pygame.sprite.Group()
    brick_colors = [RED, GREEN, YELLOW, ORANGE, PURPLE]
    padding = 5
    offset_x = (SCREEN_WIDTH - (cols * (60 + padding))) / 2
    offset_y = 60
    for row in range(rows):
        for col in range(cols):
            x = offset_x + col * (60 + padding)
            y = offset_y + row * (20 + padding)
            # Determine brick type based on level
            if level >= 3 and random.random() < 0.2:
                hits = 3
                color = PURPLE
            elif level >= 2 and random.random() < 0.3:
                hits = 2
                color = ORANGE
            else:
                hits = 1
                color = brick_colors[row % len(brick_colors)]
            brick = Brick(x, y, hits, color)
            bricks_group.add(brick)
    logging.info(f"{len(bricks_group)} bricks created for level {level}.")
    return bricks_group

# Initialize Level
current_level = 1
max_levels = 5

# Create Initial Bricks
bricks = create_bricks(5, 10, current_level)
all_sprites.add(bricks)
logging.info("Initial bricks added to all_sprites.")

# Create Paddle (Removed from all_sprites)
paddle = Paddle()
# all_sprites.add(paddle)  # Removed to prevent update conflicts
logging.debug("Paddle created but not added to all_sprites.")

# Create Ball
initial_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
balls.add(initial_ball)
all_sprites.add(initial_ball)
logging.debug("Initial ball added to all_sprites and balls group.")

# Game Variables
score = 0
lives = 3
game_over = False
win = False

# Load High Score
high_score = load_high_score()

def handle_collisions():
    global score, lives, game_over, win, current_level, high_score

    for ball in balls:
        # Collision with paddle
        if pygame.sprite.collide_rect(ball, paddle):
            logging.info("Ball collided with Paddle.")
            # Calculate and log the angle before collision
            angle_before_paddle = calculate_angle(ball.speed_x, ball.speed_y)
            logging.debug(f"Ball angle before paddle collision: {angle_before_paddle} degrees.")

            # Calculate overlap to determine collision side
            if ball.speed_y > 0 and ball.prev_rect.bottom <= paddle.rect.top:
                # Reposition the ball just above the paddle
                ball.rect.bottom = paddle.rect.top
                ball.y = float(ball.rect.y)
                # Calculate the hit position (-1 to +1)
                hit_pos = (ball.rect.centerx - paddle.rect.left) / paddle.width  # 0 to 1
                hit_pos = hit_pos * 2 - 1  # -1 to +1
                # Set maximum horizontal speed
                max_speed_x = 7
                ball.speed_x = hit_pos * max_speed_x
                # Incorporate paddle movement
                if paddle.moving_left:
                    ball.speed_x -= 1  # Add to left direction
                elif paddle.moving_right:
                    ball.speed_x += 1  # Add to right direction
                # Clamp speed_x to a range
                min_speed_x = -8
                max_speed_x = 8
                ball.speed_x = max(min_speed_x, min(ball.speed_x, max_speed_x))
                # Ensure y speed is upwards
                ball.speed_y = -abs(ball.speed_y)
                # Reposition ball just above the paddle
                ball.y = float(ball.rect.y)
                paddle_sound.play()

                # Calculate and log the angle after collision
                angle_after_paddle = calculate_angle(ball.speed_x, ball.speed_y)
                logging.info(f"Ball bounced off Paddle. Angle changed from {angle_before_paddle}° to {angle_after_paddle}°.")

                # Log the position on the paddle where the ball bounced
                logging.info(f"Ball bounced at position {round(hit_pos, 2)} on the Paddle.")

        # Collision with bricks
        hit_bricks = pygame.sprite.spritecollide(ball, bricks, False)
        for brick in hit_bricks:
            logging.info(f"Ball collided with Brick at ({brick.rect.x}, {brick.rect.y}).")
            # Calculate and log the angle before collision
            angle_before_brick = calculate_angle(ball.speed_x, ball.speed_y)
            logging.debug(f"Ball angle before brick collision: {angle_before_brick} degrees.")

            # Determine collision side based on overlap
            overlap_x = min(ball.rect.right, brick.rect.right) - max(ball.rect.left, brick.rect.left)
            overlap_y = min(ball.rect.bottom, brick.rect.bottom) - max(ball.rect.top, brick.rect.top)

            if overlap_x < overlap_y:
                # Collision on the left or right side
                if ball.speed_x > 0:
                    # Collided on the left side
                    ball.rect.right = brick.rect.left
                    ball.speed_x = -abs(ball.speed_x)
                    logging.debug("Ball bounced off the left side of the brick.")
                else:
                    # Collided on the right side
                    ball.rect.left = brick.rect.right
                    ball.speed_x = abs(ball.speed_x)
                    logging.debug("Ball bounced off the right side of the brick.")
            else:
                # Collision on the top or bottom
                if ball.speed_y > 0:
                    # Collided on the top
                    ball.rect.bottom = brick.rect.top
                    ball.speed_y = -abs(ball.speed_y)
                    logging.debug("Ball bounced off the top of the brick.")
                else:
                    # Collided on the bottom
                    ball.rect.top = brick.rect.bottom
                    ball.speed_y = abs(ball.speed_y)
                    logging.debug("Ball bounced off the bottom of the brick.")

            # Update ball position after collision
            ball.x = float(ball.rect.x)
            ball.y = float(ball.rect.y)

            brick.hit()
            brick_sound.play()
            score += 10
            logging.info(f"Score increased to {score}.")

            # Calculate and log the angle after collision
            angle_after_brick = calculate_angle(ball.speed_x, ball.speed_y)
            logging.info(f"Ball bounced off Brick. Angle changed from {angle_before_brick}° to {angle_after_brick}°.")

    # Collision with power-ups
    power_hits = pygame.sprite.spritecollide(paddle, all_powerups, True)
    for power in power_hits:
        logging.info(f"Power-up '{power.power_type}' collected.")
        apply_powerup(power.power_type)
        powerup_sound.play()

    # Check for ball out of bounds
    for ball in balls.copy():
        if ball.rect.top > SCREEN_HEIGHT:
            logging.info("Ball went out of bounds.")
            ball.kill()
            logging.debug(f"Ball removed. Remaining balls: {len(balls)}.")
            if len(balls) == 0:
                lives -= 1
                logging.info(f"Lives decreased to {lives}.")
                if lives > 0:
                    new_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
                    balls.add(new_ball)
                    all_sprites.add(new_ball)
                    logging.debug("New ball created after losing a life.")
                else:
                    game_over = True
                    game_over_sound.play()
                    logging.info("Game Over triggered.")

    # Check for win
    if len(bricks) == 0:
        logging.info("All bricks destroyed. Level completed.")
        score += 100  # Bonus for clearing level
        logging.info(f"Score increased by 100 to {score}.")
        if score > high_score:
            high_score = score
            save_high_score(high_score)
            logging.info("New high score achieved!")
        if current_level < max_levels:
            return True  # Indicate that level has been completed and should start next
        else:
            win = True
            game_over = True
            logging.info("Player has won the game!")
    return False

def apply_powerup(power_type):
    global lives
    logging.debug(f"Applying power-up: {power_type}.")
    if power_type == 'expand_paddle':
        paddle.expand()
    elif power_type == 'extra_life':
        lives += 1
        logging.info(f"Extra life granted. Lives: {lives}.")
    elif power_type == 'multi_ball':
        if len(balls) >= MAX_BALLS:
            logging.warning("Maximum number of balls reached. Multi-ball power-up not applied.")
            return
        # Select one ball to duplicate
        ball = random.choice(list(balls))
        new_ball1 = Ball(ball.x, ball.y, speed_x=ball.speed_x + 2, speed_y=ball.speed_y, speed_increment=0)
        new_ball2 = Ball(ball.x, ball.y, speed_x=ball.speed_x - 2, speed_y=ball.speed_y, speed_increment=0)
        all_sprites.add(new_ball1, new_ball2)
        balls.add(new_ball1, new_ball2)
        logging.debug("Multi-ball power-up applied: two new balls created.")
        logging.info(f"Total balls after multi-ball power-up: {len(balls)}.")

def set_volume(new_volume):
    global VOLUME
    VOLUME = new_volume
    for sound in SOUND_EFFECTS:
        sound.set_volume(VOLUME)
    logging.debug(f"Volume set to {VOLUME * 100}%.")

def draw_text(text, font, color, surface, x, y):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    text_rect.center = (x, y)
    surface.blit(text_obj, text_rect)

def reset_game():
    global score, lives, game_over, win, current_level, high_score, bricks, all_powerups, all_sprites, paddle, balls, VOLUME

    logging.info("Resetting game.")
    score = 0
    lives = 3
    game_over = False
    win = False
    current_level = 1

    # Clear all sprite groups except paddle
    bricks.empty()
    all_powerups.empty()
    all_sprites.empty()
    balls.empty()
    logging.debug("All sprite groups cleared.")

    # Recreate Bricks
    bricks = create_bricks(5, 10, current_level)
    all_sprites.add(bricks)
    logging.debug("Bricks recreated and added to all_sprites.")

    # Recreate Paddle
    paddle = Paddle()
    # all_sprites.add(paddle)  # Removed to prevent update conflicts
    logging.debug("Paddle recreated but not added to all_sprites.")

    # Recreate Ball
    initial_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    balls.add(initial_ball)
    all_sprites.add(initial_ball)
    logging.debug("Initial ball recreated and added to all_sprites and balls group.")

    # Reset Volume to default
    set_volume(0.1)
    logging.debug("Volume reset to default.")

def main():
    global score, lives, game_over, win, current_level, high_score, bricks, all_powerups, all_sprites, paddle, balls, VOLUME

    paused = False
    running = True
    level_start = False

    logging.info("Game started.")
    while running:
        clock.tick(FPS)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                logging.info("Quit event received. Exiting game.")
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    paused = not paused
                    logging.info(f"Game {'paused' if paused else 'resumed'} by user.")

        keys = pygame.key.get_pressed()

        # Volume Control
        if keys[pygame.K_UP]:
            new_volume = min(1.0, VOLUME + 0.01)
            if new_volume != VOLUME:
                set_volume(new_volume)
                logging.debug("Volume increased by user.")
        if keys[pygame.K_DOWN]:
            new_volume = max(0.0, VOLUME - 0.01)
            if new_volume != VOLUME:
                set_volume(new_volume)
                logging.debug("Volume decreased by user.")

        # Handle Level Start
        if level_start:
            draw_text(f"Level {current_level}", large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50)
            draw_text("Press SPACE to Start", font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 10)
            if keys[pygame.K_SPACE]:
                level_start = False
                current_level += 1
                logging.info(f"Starting level {current_level}.")
                # Create new bricks for the new level
                new_bricks = create_bricks(5 + current_level, 10, current_level)
                bricks.empty()
                bricks.add(*new_bricks)
                all_sprites.add(new_bricks)
                # Reset balls with increased speed
                for ball in balls.copy():
                    ball.kill()
                new_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, speed_increment=0.1 * current_level)
                balls.add(new_ball)
                all_sprites.add(new_ball)
                logging.debug("New ball created for the new level.")
        elif not paused and not game_over:
            # Update game entities
            paddle.update(keys)  # Update paddle separately
            all_sprites.update()  # Update all other sprites
            completed = handle_collisions()
            if completed:
                level_start = True

        # Drawing
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # Draw Paddle Separately
        screen.blit(paddle.image, paddle.rect)

        # Display Score and Lives
        score_text = font.render(f"Score: {score}", True, WHITE)
        lives_text = font.render(f"Lives: {lives}", True, WHITE)
        level_text = font.render(f"Level: {current_level}", True, WHITE)
        high_score_text = font.render(f"High Score: {high_score}", True, WHITE)
        volume_text = font.render(f"Volume: {int(VOLUME * 100)}%", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(lives_text, (SCREEN_WIDTH - 150, 10))
        screen.blit(level_text, (10, 40))
        screen.blit(high_score_text, (SCREEN_WIDTH - 200, 40))
        screen.blit(volume_text, (10, 70))

        # Draw Power-Ups (already handled by all_sprites.draw)

        # Display Pause Message
        if paused:
            draw_text("PAUSED", large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            draw_text("Press P to Resume", font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50)

        # Level Start Message
        if level_start:
            draw_text(f"Level {current_level}", large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50)
            draw_text("Press SPACE to Start", font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 10)

        # Game Over Message
        if game_over:
            if win:
                message = "CONGRATULATIONS! YOU WIN!"
            else:
                message = "GAME OVER"
            draw_text(message, large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            sub_text = "Press R to Restart or Q to Quit"
            draw_text(sub_text, font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50)

            if keys[pygame.K_r]:
                reset_game()
            if keys[pygame.K_q]:
                logging.info("Quit event received via Q key. Exiting game.")
                running = False

        pygame.display.flip()

    pygame.quit()
    logging.info("Pygame quit. Game terminated.")
    sys.exit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("An unexpected error occurred during the game execution.")
        pygame.quit()
        sys.exit()
