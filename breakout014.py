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
BALL_SPEED = 6  # **New**: Constant total speed magnitude for the ball
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
EXPLOSION_COLOR = (255, 100, 0)  # Color for explosion animation

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
explosion_sound = generate_sound(150, duration=0.2, volume=0.7)  # Lower frequency for explosion
wall_sound = generate_sound(330)         # E4 note
game_over_sound = generate_sound(220)    # A3 note
powerup_sound = generate_sound(550)      # C#5 note

# List of all sound effects for easy volume management
SOUND_EFFECTS = [paddle_sound, brick_sound, explosion_sound, wall_sound, game_over_sound, powerup_sound]

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
        self.speed_x = speed_x if speed_x else random.choice([-BALL_SPEED / math.sqrt(2), BALL_SPEED / math.sqrt(2)])
        self.speed_y = speed_y if speed_y else -BALL_SPEED / math.sqrt(2)
        self.prev_rect = self.rect.copy()
        self.speed_increment = speed_increment
        self.speed_increment_applied = False  # Flag to ensure speed_increment is applied only once
        self.collision_cooldown = 0  # Frames until next collision can be processed
        logging.debug(f"Ball initialized at ({self.x}, {self.y}) with speed ({self.speed_x}, {self.speed_y}).")
        self.normalize_speed()  # Ensure initial speed magnitude is BALL_SPEED

    def normalize_speed(self):
        """Normalize the ball's speed to maintain a constant total speed magnitude."""
        speed = math.hypot(self.speed_x, self.speed_y)
        if speed != 0:
            self.speed_x = (self.speed_x / speed) * BALL_SPEED
            self.speed_y = (self.speed_y / speed) * BALL_SPEED
            logging.debug(f"Ball speed normalized to ({self.speed_x:.2f}, {self.speed_y:.2f}).")

    def update(self):
        # Handle collision cooldown
        if self.collision_cooldown > 0:
            self.collision_cooldown -= 1

        # Apply speed increment only once (if applicable)
        if self.speed_increment != 0 and not self.speed_increment_applied:
            # Instead of scaling speed components, maintain direction and set to new BALL_SPEED
            angle = math.atan2(self.speed_y, self.speed_x)
            BALL_SPEED_NEW = BALL_SPEED * (1 + self.speed_increment)
            self.speed_x = math.cos(angle) * BALL_SPEED_NEW
            self.speed_y = math.sin(angle) * BALL_SPEED_NEW
            logging.debug(f"Ball speed incremented to ({self.speed_x:.2f}, {self.speed_y:.2f}).")
            self.speed_increment_applied = True
            self.normalize_speed()  # Normalize to maintain BALL_SPEED

        # Store previous position
        self.prev_rect = self.rect.copy()

        # Move the ball
        self.x += self.speed_x
        self.y += self.speed_y

        # **Changed**: Use round() instead of int() to prevent the ball from getting stuck
        self.rect.x = round(self.x)
        self.rect.y = round(self.y)

        # Bounce off left and right walls
        if self.rect.left <= 0:
            logging.info("Ball collided with the left wall.")
            angle_before_wall = calculate_angle(self.speed_x, self.speed_y)
            self.rect.left = 0
            self.speed_x = abs(self.speed_x)
            self.x = float(self.rect.x)
            wall_sound.play()
            self.normalize_speed()
            angle_after_wall = calculate_angle(self.speed_x, self.speed_y)
            logging.info(f"Ball bounced off left wall. Angle changed from {angle_before_wall}° to {angle_after_wall}°.")
            # **Additional Fix**: Slightly move the ball away from the wall to prevent immediate re-collision
            self.x += 1  # Move the ball 1 pixel to the right

        if self.rect.right >= SCREEN_WIDTH:
            logging.info("Ball collided with the right wall.")
            angle_before_wall = calculate_angle(self.speed_x, self.speed_y)
            self.rect.right = SCREEN_WIDTH
            self.speed_x = -abs(self.speed_x)
            self.x = float(self.rect.x)
            wall_sound.play()
            self.normalize_speed()
            angle_after_wall = calculate_angle(self.speed_x, self.speed_y)
            logging.info(f"Ball bounced off right wall. Angle changed from {angle_before_wall}° to {angle_after_wall}°.")
            # **Additional Fix**: Slightly move the ball away from the wall to prevent immediate re-collision
            self.x -= 1  # Move the ball 1 pixel to the left

        # Bounce off top
        if self.rect.top <= 0:
            logging.info("Ball collided with the top wall.")
            angle_before_wall = calculate_angle(self.speed_x, self.speed_y)
            self.rect.top = 0
            self.speed_y = abs(self.speed_y)
            self.y = float(self.rect.y)
            wall_sound.play()
            self.normalize_speed()
            angle_after_wall = calculate_angle(self.speed_x, self.speed_y)
            logging.info(f"Ball bounced off top wall. Angle changed from {angle_before_wall}° to {angle_after_wall}°.")
            # **Additional Fix**: Slightly move the ball away from the wall to prevent immediate re-collision
            self.y += 1  # Move the ball 1 pixel downward

        # **Removed**: Clamp speed to MAX_SPEED
        # **Removed**: Ensure speed components do not become zero

    def reset(self, x, y):
        logging.info(f"Resetting Ball to position ({x}, {y}).")
        self.x = float(x)
        self.y = float(y)
        self.rect.centerx = x
        self.rect.centery = y
        self.speed_x = random.choice([-BALL_SPEED / math.sqrt(2), BALL_SPEED / math.sqrt(2)])
        self.speed_y = -BALL_SPEED / math.sqrt(2)
        self.speed_increment = 0
        self.speed_increment_applied = False
        self.collision_cooldown = 0
        self.normalize_speed()
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
            # Play explosion sound if brick is explosive
            if hasattr(self, 'explosive') and self.explosive:
                explosion_sound.play()
            else:
                brick_sound.play()
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
                # Instead of exploding immediately, mark for explosion after collision handling
                bricks_to_explode.append(self)

    def explode(self):
        # Destroy adjacent bricks and create explosion animation
        logging.info(f"Brick at ({self.rect.x}, {self.rect.y}) is exploding adjacent bricks.")
        explosion_sound.play()
        explosion = Explosion(self.rect.centerx, self.rect.centery)
        all_sprites.add(explosion)
        # Define a range to check for adjacent bricks (e.g., surrounding area)
        explosion_range = 70  # Adjust as needed
        adjacent_bricks = [brick for brick in bricks if brick != self and
                           abs(brick.rect.x - self.rect.x) < explosion_range and
                           abs(brick.rect.y - self.rect.y) < explosion_range]
        for brick in adjacent_bricks:
            if brick in bricks_to_explode:
                continue  # Prevent recursive explosion in the same loop
            brick.kill()
            logging.debug(f"Adjacent brick at ({brick.rect.x}, {brick.rect.y}) destroyed by explosion.")
            # Play appropriate sound based on whether the brick is explosive
            if hasattr(brick, 'explosive') and brick.explosive:
                explosion_sound.play()
                # Mark for further explosion
                bricks_to_explode.append(brick)
            else:
                brick_sound.play()
            # 20% chance to drop a power-up from each destroyed adjacent brick
            if random.random() < 0.2:
                powerup = PowerUp(brick.rect.centerx, brick.rect.centery)
                all_powerups.add(powerup)
                all_sprites.add(powerup)
                logging.debug("Power-up dropped by exploded adjacent brick.")
            # 10% chance for further explosions (recursive)
            if random.random() < 0.1 and not hasattr(brick, 'explosive'):
                logging.debug("Adjacent brick is also explosive. Triggering further explosion.")
                bricks_to_explode.append(brick)

# Explosion Animation Class
class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y, max_radius=50, color=EXPLOSION_COLOR, duration=30):
        super().__init__()
        self.x = x
        self.y = y
        self.max_radius = max_radius
        self.current_radius = 10
        self.color = color
        self.duration = duration  # Frames the explosion lasts
        self.frame = 0
        self.image = pygame.Surface((self.max_radius*2, self.max_radius*2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def update(self):
        if self.frame < self.duration:
            # Calculate incremental radius and fading
            self.current_radius += (self.max_radius - self.current_radius) / (self.duration - self.frame)
            # Clear the previous image
            self.image.fill((0, 0, 0, 0))
            # Draw the expanding circle with fading effect
            alpha = max(255 - int((255 / self.duration) * self.frame), 0)
            explosion_color = self.color + (alpha,)
            pygame.draw.circle(self.image, explosion_color, (self.max_radius, self.max_radius), int(self.current_radius))
            self.frame += 1
        else:
            self.kill()

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
                explosive = False
            elif level >= 2 and random.random() < 0.3:
                hits = 2
                color = ORANGE
                explosive = True  # Make some bricks explosive
            else:
                hits = 1
                color = brick_colors[row % len(brick_colors)]
                explosive = False
            brick = Brick(x, y, hits, color)
            brick.explosive = explosive  # Add explosive attribute
            bricks_group.add(brick)
    logging.info(f"{len(bricks_group)} bricks created for level {level}.")
    return bricks_group

# Initialize Level
current_level = 1
max_levels = 5

# Create Paddle (Removed from all_sprites)
paddle = Paddle()
# all_sprites.add(paddle)  # Removed to prevent update conflicts
logging.debug("Paddle created but not added to all_sprites.")

# Game Variables
score = 0
lives = 3
game_over = False
win = False

# Load High Score
high_score = load_high_score()

# List to keep track of bricks that need to explode after collision handling
bricks_to_explode = []

def handle_collisions():
    global score, lives, game_over, win, current_level, high_score

    # Reset bricks_to_explode list
    global bricks_to_explode
    bricks_to_explode = []

    for ball in balls:
        # Skip collision handling if ball is in collision cooldown
        if ball.collision_cooldown > 0:
            continue

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
                ball.speed_y = -abs(ball.speed_y)
                ball.y = float(ball.rect.y)
                # Calculate the hit position (-1 to +1)
                hit_pos = (ball.rect.centerx - paddle.rect.left) / paddle.width  # 0 to 1
                hit_pos = hit_pos * 2 - 1  # -1 to +1
                # Set horizontal speed based on hit position
                max_speed_x = BALL_SPEED * 0.8  # Adjust as needed
                ball.speed_x = hit_pos * max_speed_x
                # Incorporate paddle movement
                if paddle.moving_left:
                    ball.speed_x -= 1  # Add to left direction
                elif paddle.moving_right:
                    ball.speed_x += 1  # Add to right direction
                # Clamp speed_x to a range
                min_speed_x = -BALL_SPEED
                max_speed_x = BALL_SPEED
                ball.speed_x = max(min_speed_x, min(ball.speed_x, max_speed_x))
                # Normalize speed to maintain total speed
                ball.normalize_speed()
                # Reposition ball just above the paddle
                ball.y = float(ball.rect.y)
                paddle_sound.play()

                # Calculate and log the angle after collision
                angle_after_paddle = calculate_angle(ball.speed_x, ball.speed_y)
                logging.info(f"Ball bounced off Paddle. Angle changed from {angle_before_paddle}° to {angle_after_paddle}°.")

                # Log the position on the paddle where the ball bounced
                logging.info(f"Ball bounced at position {round(hit_pos, 2)} on the Paddle.")

                # Set collision cooldown
                ball.collision_cooldown = 5  # Prevent immediate re-collision

        # Collision with bricks
        hit_bricks = pygame.sprite.spritecollide(ball, bricks, False)
        if hit_bricks:
            # Process only the first collision to prevent multiple updates
            brick = hit_bricks[0]
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
            score += 10
            logging.info(f"Score increased to {score}.")

            # Normalize speed to maintain total speed
            ball.normalize_speed()

            # Calculate and log the angle after collision
            angle_after_brick = calculate_angle(ball.speed_x, ball.speed_y)
            logging.info(f"Ball bounced off Brick. Angle changed from {angle_before_brick}° to {angle_after_brick}°.")

            # Set collision cooldown
            ball.collision_cooldown = 5  # Prevent immediate re-collision

def apply_explosions():
    """Process all bricks marked for explosion after collision handling."""
    global bricks_to_explode
    while bricks_to_explode:
        brick = bricks_to_explode.pop(0)
        brick.explode()

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
        # Create two new balls with slight speed variations
        angle = math.atan2(ball.speed_y, ball.speed_x)
        speed_variation = math.radians(15)  # 15 degrees variation
        speed = math.hypot(ball.speed_x, ball.speed_y)
        new_angle1 = angle + speed_variation
        new_angle2 = angle - speed_variation
        new_speed_x1 = speed * math.cos(new_angle1)
        new_speed_y1 = speed * math.sin(new_angle1)
        new_speed_x2 = speed * math.cos(new_angle2)
        new_speed_y2 = speed * math.sin(new_angle2)
        new_ball1 = Ball(ball.x, ball.y, speed_x=new_speed_x1, speed_y=new_speed_y1)
        new_ball2 = Ball(ball.x, ball.y, speed_x=new_speed_x2, speed_y=new_speed_y2)
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

def draw_text(text, font_obj, color, surface, x, y):
    text_obj = font_obj.render(text, True, color)
    text_rect = text_obj.get_rect()
    text_rect.center = (x, y)
    surface.blit(text_obj, text_rect)

def reset_game():
    global score, lives, game_over, win, current_level, high_score, bricks, all_powerups, all_sprites, paddle, balls, VOLUME, level_start

    logging.info("Resetting game.")
    score = 0
    lives = 3
    game_over = False
    win = False
    current_level = 1
    level_start = True  # Start the first level in paused state

    # Clear all sprite groups except paddle
    bricks.empty()
    all_powerups.empty()
    all_sprites.empty()
    balls.empty()
    logging.debug("All sprite groups cleared.")

    # Recreate Paddle
    paddle = Paddle()
    # all_sprites.add(paddle)  # Removed to prevent update conflicts
    logging.debug("Paddle recreated but not added to all_sprites.")

    # Reset Volume to default
    set_volume(0.1)
    logging.debug("Volume reset to default.")

def main():
    global score, lives, game_over, win, current_level, high_score, bricks, all_powerups, all_sprites, paddle, balls, VOLUME, level_start

    level_start = True  # Start the first level in paused state
    running = True
    paused = False

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
                logging.info(f"Starting level {current_level}.")
                # Create new bricks for the current level
                new_bricks = create_bricks(5, 10, current_level)
                bricks.empty()
                bricks.add(*new_bricks)
                all_sprites.add(new_bricks)
                # Reset balls with increased speed (handled by normalization)
                for ball in balls.copy():
                    ball.kill()
                new_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, speed_increment=0.1 * current_level)
                balls.add(new_ball)
                all_sprites.add(new_ball)
                logging.debug("New ball created for the new level.")
        elif not game_over:
            # Update game entities only if not paused
            if not paused:
                paddle.update(keys)  # Update paddle separately
                all_sprites.update()  # Update all other sprites
                handle_collisions()
                apply_explosions()
                # Collision with power-ups
                power_hits = pygame.sprite.spritecollide(paddle, all_powerups, True)
                for power in power_hits:
                    logging.info(f"Power-up '{power.power_type}' collected.")
                    apply_powerup(power.power_type)
                    powerup_sound.play()

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
                        current_level += 1
                        level_start = True
                        logging.info(f"Proceeding to level {current_level}.")
                    else:
                        win = True
                        game_over = True
                        logging.info("Player has won the game!")

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
