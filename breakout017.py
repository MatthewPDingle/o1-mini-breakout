import pygame
import sys
import random
import math
import numpy as np
import os
import logging

# ========================== Constants ==========================
# Screen Dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Frames Per Second
FPS = 60

# Ball Properties
BALL_SPEED = 6
MAX_SPEED = 15
MAX_BALLS = 10

# Paddle Properties
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 20
PADDLE_SPEED = 7
EXPANDED_WIDTH = 150
SHRUNK_WIDTH = 70
POWERUP_DURATION = 300  # Frames

# Colors
WHITE = (255, 255, 255)        # Default ball color
GREY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)              # Explosive ball color
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (160, 32, 240)
EXPLOSION_COLOR = (255, 100, 0)
SHRINK_COLOR = (0, 255, 255)
SLOW_COLOR = (255, 192, 203)
LASER_COLOR = (255, 0, 255)
EXPLOSIVE_BALL_COLOR = RED    # Use RED for explosive ball

# Power-Up Types
POWERUP_TYPES = ['expand_paddle', 'extra_life', 'multi_ball',
                'shrink_paddle', 'slow_ball', 'laser_paddle', 'explosive_ball']  # Added 'explosive_ball'

# High Score File
HIGH_SCORE_FILE = 'highscore.txt'

# Sound Frequencies
SOUND_FREQUENCIES = {
    'paddle': 440,       # A4
    'brick': 880,        # A5
    'explosion': 150,    # Low frequency
    'wall': 330,         # E4
    'game_over': 220,    # A3
    'powerup': 550,      # C#5
    'laser': 700         # Short laser sound
}

# Maximum Levels
max_levels = 5  # Moved to global scope

# ========================== Logging Configuration ==========================
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info("Initializing Pygame and setting up the game.")

# ========================== Initialize Pygame ==========================
pygame.init()
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

# ========================== Sound Management ==========================
def generate_sound(frequency, duration=0.1, volume=0.5):
    logging.debug(f"Generating sound: frequency={frequency}Hz, duration={duration}s, volume={volume}.")
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    wave = np.sin(2 * math.pi * frequency * t)
    wave = (wave * volume * 32767).astype(np.int16)
    stereo_wave = np.column_stack((wave, wave))
    sound = pygame.sndarray.make_sound(stereo_wave)
    logging.debug("Sound generated successfully.")
    return sound

# Pre-generate and cache sounds
SOUND_EFFECTS = {}
for key, freq in SOUND_FREQUENCIES.items():
    if key == 'explosion':
        SOUND_EFFECTS[key] = generate_sound(freq, duration=0.2, volume=0.7)
    elif key == 'laser':
        SOUND_EFFECTS[key] = generate_sound(freq, duration=0.05, volume=0.3)
    else:
        SOUND_EFFECTS[key] = generate_sound(freq)

# Set initial volume
VOLUME = 0.1
for sound in SOUND_EFFECTS.values():
    sound.set_volume(VOLUME)
logging.debug(f"Initial volume set to {VOLUME * 100}%.")

# ========================== Utility Functions ==========================
def calculate_angle(speed_x, speed_y):
    angle_rad = math.atan2(-speed_y, speed_x)
    angle_deg = math.degrees(angle_rad)
    return round(angle_deg, 2)

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

def draw_text(text, font, color, surface, x, y):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect(center=(x, y))
    surface.blit(text_obj, text_rect)

# ========================== Game Classes ==========================
class Paddle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        logging.debug("Initializing Paddle.")
        self.original_width = PADDLE_WIDTH
        self.width = self.original_width
        self.height = PADDLE_HEIGHT
        self.color = BLUE
        self.original_color = BLUE
        self.speed = PADDLE_SPEED
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect(centerx=SCREEN_WIDTH / 2, bottom=SCREEN_HEIGHT - 30)
        self.active_powerups = {}
        self.moving_left = False
        self.moving_right = False
        logging.debug(f"Paddle initialized at position ({self.rect.centerx}, {self.rect.centery}).")

    def update(self, keys):
        self.moving_left = keys[pygame.K_LEFT]
        self.moving_right = keys[pygame.K_RIGHT]

        if self.moving_left:
            self.rect.x -= self.speed
        if self.moving_right:
            self.rect.x += self.speed

        # Keep paddle within screen
        self.rect.left = max(self.rect.left, 0)
        self.rect.right = min(self.rect.right, SCREEN_WIDTH)

        # Update active power-ups
        expired_powerups = []
        for power, timer in self.active_powerups.items():
            self.active_powerups[power] -= 1
            if self.active_powerups[power] <= 0:
                expired_powerups.append(power)

        for power in expired_powerups:
            self.deactivate_powerup(power)

    def activate_powerup(self, power_type, duration=POWERUP_DURATION):
        logging.info(f"Activating power-up: {power_type}.")
        self.active_powerups[power_type] = duration
        if power_type == 'expand_paddle':
            self.width = min(EXPANDED_WIDTH, SCREEN_WIDTH - 20)
            self.image = pygame.Surface([self.width, self.height])
            self.image.fill(ORANGE)
            self.rect = self.image.get_rect(center=self.rect.center)
            logging.debug(f"Paddle expanded to width {self.width}.")
        elif power_type == 'shrink_paddle':
            self.width = max(SHRUNK_WIDTH, 50)
            self.image = pygame.Surface([self.width, self.height])
            self.image.fill(SHRINK_COLOR)
            self.rect = self.image.get_rect(center=self.rect.center)
            logging.debug(f"Paddle shrunk to width {self.width}.")
        elif power_type == 'laser_paddle':
            self.original_color = self.color
            self.color = LASER_COLOR
            self.image.fill(self.color)
            logging.debug("Laser Paddle activated.")
        elif power_type == 'explosive_ball':
            # No paddle modification required; handled in Ball class
            logging.debug("Explosive Ball power-up activated.")

    def deactivate_powerup(self, power_type):
        logging.info(f"Deactivating power-up: {power_type}.")
        del self.active_powerups[power_type]
        if power_type in ['expand_paddle', 'shrink_paddle']:
            self.width = self.original_width
            self.image = pygame.Surface([self.width, self.height])
            self.image.fill(self.original_color)
            self.rect = self.image.get_rect(center=self.rect.center)
            logging.debug(f"Paddle restored to original width {self.width}.")
        elif power_type == 'laser_paddle':
            self.color = self.original_color
            self.image.fill(self.color)
            logging.debug("Laser Paddle deactivated.")

    def shoot_laser(self):
        if 'laser_paddle' in self.active_powerups:
            laser = Laser(self.rect.centerx, self.rect.top)
            all_sprites.add(laser)
            lasers.add(laser)
            SOUND_EFFECTS['laser'].play()
            logging.debug("Laser shot from Paddle.")

    def center_paddle(self):
        self.rect.centerx = SCREEN_WIDTH / 2
        self.rect.bottom = SCREEN_HEIGHT - 30
        logging.debug(f"Paddle centered at ({self.rect.centerx}, {self.rect.centery}).")

class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y, speed_x=None, speed_y=-4, speed_increment=0):
        super().__init__()
        logging.debug("Initializing Ball.")
        self.radius = 10
        self.color = WHITE  # Default color is white
        self.explosive = False  # Indicates if the ball is explosive
        self.original_color = self.color
        self.image = pygame.Surface([self.radius*2, self.radius*2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect(center=(x, y))
        self.x = float(x)
        self.y = float(y)
        self.speed_increment = speed_increment
        self.speed_increment_applied = False
        self.slow_effect = False
        self.speed_multiplier = 1.0
        self.speed_x = speed_x if speed_x else random.choice([-BALL_SPEED / math.sqrt(2), BALL_SPEED / math.sqrt(2)])
        self.speed_y = speed_y if speed_y else -BALL_SPEED / math.sqrt(2)
        self.prev_rect = self.rect.copy()
        self.collided = False  # Flag to prevent multiple collisions per frame
        self.normalize_speed()
        logging.debug(f"Ball initialized at ({self.x}, {self.y}) with speed ({self.speed_x}, {self.speed_y}).")

    def normalize_speed(self):
        speed = math.hypot(self.speed_x, self.speed_y)
        if speed != 0:
            self.speed_x = (self.speed_x / speed) * BALL_SPEED * self.speed_multiplier
            self.speed_y = (self.speed_y / speed) * BALL_SPEED * self.speed_multiplier
            # Log only if speed has changed significantly
            if hasattr(self, 'previous_speed'):
                if not math.isclose(speed, math.hypot(self.previous_speed[0], self.previous_speed[1]), abs_tol=0.1):
                    logging.debug(f"Ball speed normalized to ({self.speed_x:.2f}, {self.speed_y:.2f}).")
            else:
                logging.debug(f"Ball speed normalized to ({self.speed_x:.2f}, {self.speed_y:.2f}).")
            self.previous_speed = (self.speed_x, self.speed_y)

    def update(self):
        if self.speed_increment != 0 and not self.speed_increment_applied:
            angle = math.atan2(self.speed_y, self.speed_x)
            BALL_SPEED_NEW = BALL_SPEED * (1 + self.speed_increment)
            self.speed_x = math.cos(angle) * BALL_SPEED_NEW
            self.speed_y = math.sin(angle) * BALL_SPEED_NEW
            self.speed_increment_applied = True
            self.normalize_speed()
            logging.debug(f"Ball speed incremented to ({self.speed_x:.2f}, {self.speed_y:.2f}).")

        if self.slow_effect:
            self.speed_multiplier = 0.7
            self.normalize_speed()

        self.prev_rect = self.rect.copy()
        self.x += self.speed_x
        self.y += self.speed_y
        self.rect.x = round(self.x)
        self.rect.y = round(self.y)

        # Collision with walls
        if self.rect.left <= 0:
            logging.info("Ball collided with the left wall.")
            SOUND_EFFECTS['wall'].play()
            self.speed_x = abs(self.speed_x)
            self.x = self.rect.x + 1
            self.normalize_speed()
            logging.info(f"Ball bounced off left wall. New speed: ({self.speed_x:.2f}, {self.speed_y:.2f}).")

        if self.rect.right >= SCREEN_WIDTH:
            logging.info("Ball collided with the right wall.")
            SOUND_EFFECTS['wall'].play()
            self.speed_x = -abs(self.speed_x)
            self.x = self.rect.x - 1
            self.normalize_speed()
            logging.info(f"Ball bounced off right wall. New speed: ({self.speed_x:.2f}, {self.speed_y:.2f}).")

        if self.rect.top <= 0:
            logging.info("Ball collided with the top wall.")
            SOUND_EFFECTS['wall'].play()
            self.speed_y = abs(self.speed_y)
            self.y = self.rect.y + 1
            self.normalize_speed()
            logging.info(f"Ball bounced off top wall. New speed: ({self.speed_x:.2f}, {self.speed_y:.2f}).")

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
        self.slow_effect = False
        self.speed_multiplier = 1.0
        self.collided = False
        self.explosive = False  # Reset explosive state
        self.color = self.original_color  # Reset color
        self.image.fill((0, 0, 0, 0))  # Clear the image
        pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
        self.normalize_speed()
        logging.debug(f"Ball reset with speed ({self.speed_x}, {self.speed_y}).")

    def apply_slow(self, duration=POWERUP_DURATION):
        if not self.slow_effect:
            logging.info("Applying slow ball effect.")
            self.slow_effect = True
            self.speed_multiplier = 0.7
            self.normalize_speed()

    def remove_slow(self):
        if self.slow_effect:
            logging.info("Removing slow ball effect.")
            self.slow_effect = False
            self.speed_multiplier = 1.0
            self.normalize_speed()

    def make_explosive(self):
        if not self.explosive:
            self.explosive = True
            self.color = EXPLOSIVE_BALL_COLOR  # Change color to red
            self.image.fill((0, 0, 0, 0))      # Clear the image
            pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
            logging.debug("Ball is now explosive.")

    def revert_to_regular(self):
        if self.explosive:
            self.explosive = False
            self.color = self.original_color
            self.image.fill((0, 0, 0, 0))      # Clear the image
            pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
            logging.debug("Ball reverted to regular state.")

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
        self.rect = self.image.get_rect(topleft=(x, y))

    def hit(self):
        logging.info(f"Brick at ({self.rect.x}, {self.rect.y}) was hit. Remaining hits: {self.hits - 1}.")
        self.hits -= 1
        if self.hits > 0:
            color_intensity = int(255 * (self.hits / self.max_hits))
            self.color = (color_intensity, 0, 255 - color_intensity)
            self.image.fill(self.color)
            logging.debug(f"Brick color changed to {self.color}.")
        else:
            SOUND_EFFECTS['brick'].play()
            self.kill()
            logging.info(f"Brick at ({self.rect.x}, {self.rect.y}) destroyed.")
            # Drop power-up with 20% chance
            if random.random() < 0.2:
                powerup = PowerUp(self.rect.centerx, self.rect.centery)
                all_powerups.add(powerup)
                all_sprites.add(powerup)
                logging.debug("Power-up dropped by brick.")

class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y, max_radius=100, color=EXPLOSION_COLOR, duration=30):
        super().__init__()
        self.x = x
        self.y = y
        self.max_radius = max_radius  # Set blast radius to 100 pixels
        self.current_radius = 10
        self.color = color
        self.duration = duration
        self.frame = 0
        self.image = pygame.Surface((self.max_radius*2, self.max_radius*2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(self.x, self.y))
        all_sprites.add(self)
        logging.debug(f"Explosion created at ({self.x}, {self.y}).")

    def update(self):
        if self.frame < self.duration:
            growth_rate = (self.max_radius - self.current_radius) / (self.duration - self.frame)
            self.current_radius += growth_rate
            self.image.fill((0, 0, 0, 0))
            alpha = max(255 - int((255 / self.duration) * self.frame), 0)
            # Ensure alpha is within valid range
            alpha = max(min(alpha, 255), 0)
            explosion_color = self.color + (alpha,)
            pygame.draw.circle(self.image, explosion_color, (self.max_radius, self.max_radius), int(self.current_radius))
            self.frame += 1
        else:
            self.kill()

class Laser(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.width = 4
        self.height = 20
        self.color = YELLOW
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect(centerx=x, bottom=y)
        self.speed_y = -10
        logging.debug(f"Laser created at ({x}, {y}).")

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0:
            self.kill()
            logging.debug("Laser removed for moving out of screen.")

class PowerUp(pygame.sprite.Sprite):
    COLOR_MAPPING = {
        'expand_paddle': ORANGE,
        'extra_life': PURPLE,
        'multi_ball': YELLOW,
        'shrink_paddle': SHRINK_COLOR,
        'slow_ball': SLOW_COLOR,
        'laser_paddle': LASER_COLOR,
        'explosive_ball': EXPLOSIVE_BALL_COLOR  # Added explosive_ball color
    }

    def __init__(self, x, y, power_type=None):
        super().__init__()
        self.width = 20
        self.height = 20
        self.power_type = power_type if power_type else random.choice(POWERUP_TYPES)
        self.color = self.COLOR_MAPPING.get(self.power_type, WHITE)
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed_y = 3
        logging.debug(f"PowerUp '{self.power_type}' created at ({x}, {y}).")

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()
            logging.debug(f"PowerUp '{self.power_type}' removed for moving out of screen.")

class PowerUpMessage(pygame.sprite.Sprite):
    def __init__(self, text, duration=60, position=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100), color=WHITE):
        super().__init__()
        self.duration = duration
        self.frame = 0
        self.font = pygame.font.SysFont("Arial", 24)
        self.text = text
        self.color = color
        self.image = self.font.render(self.text, True, self.color)
        self.image = self.image.convert_alpha()
        self.rect = self.image.get_rect(center=position)
        self.alpha = 255
        self.velocity_y = 1
        all_sprites.add(self)
        logging.debug(f"PowerUpMessage '{self.text}' created at {position}.")

    def update(self):
        if self.frame < self.duration:
            self.rect.y += self.velocity_y
            fade_factor = 255 * (1 - self.frame / self.duration)
            self.image.set_alpha(int(fade_factor))
            self.frame += 1
        else:
            self.kill()

# ========================== Sprite Groups ==========================
all_sprites = pygame.sprite.Group()
bricks = pygame.sprite.Group()
all_powerups = pygame.sprite.Group()
balls = pygame.sprite.Group()
lasers = pygame.sprite.Group()
messages = pygame.sprite.Group()

# ========================== Brick Creation ==========================
def create_bricks(rows, cols, level=1):
    logging.info(f"Creating bricks: rows={rows}, cols={cols}, level={level}.")
    padding = 5
    offset_x = (SCREEN_WIDTH - (cols * (60 + padding))) / 2
    offset_y = 60
    for row in range(rows):
        for col in range(cols):
            x = offset_x + col * (60 + padding)
            y = offset_y + row * (20 + padding)
            # Simplified brick creation without explosive bricks
            hits = 1
            color = [RED, GREEN, YELLOW, ORANGE, PURPLE][row % 5]
            brick = Brick(x, y, hits, color)
            bricks.add(brick)
            all_sprites.add(brick)
    logging.info(f"{len(bricks)} bricks created for level {level}.")

# ========================== Game Management Functions ==========================
def clear_active_powerups():
    logging.debug("Clearing all active power-ups.")
    # Deactivate paddle power-ups
    for power in list(paddle.active_powerups.keys()):
        paddle.deactivate_powerup(power)
    # Deactivate ball power-ups
    for ball in balls:
        if ball.explosive:
            ball.revert_to_regular()

def apply_powerup(power_type):
    global lives
    logging.debug(f"Applying power-up: {power_type}.")
    instant_powerups = ['extra_life', 'multi_ball']
    if power_type not in instant_powerups:
        clear_active_powerups()
    if power_type == 'expand_paddle':
        paddle.activate_powerup('expand_paddle')
    elif power_type == 'extra_life':
        lives += 1
        logging.info(f"Extra life granted. Lives: {lives}.")
    elif power_type == 'multi_ball':
        if len(balls) >= MAX_BALLS:
            logging.warning("Maximum number of balls reached. Multi-ball power-up not applied.")
            return
        ball = random.choice(list(balls))
        angle = math.atan2(ball.speed_y, ball.speed_x)
        speed_variation = math.radians(15)
        speed = math.hypot(ball.speed_x, ball.speed_y)
        new_angle1 = angle + speed_variation
        new_angle2 = angle - speed_variation
        new_speed_x1 = speed * math.cos(new_angle1)
        new_speed_y1 = speed * math.sin(new_angle1)
        new_speed_x2 = speed * math.cos(new_angle2)
        new_speed_y2 = speed * math.sin(new_angle2)
        new_ball1 = Ball(ball.x, ball.y, speed_x=new_speed_x1, speed_y=new_speed_y1)
        new_ball2 = Ball(ball.x, ball.y, speed_x=new_speed_x2, speed_y=new_speed_y2)
        balls.add(new_ball1, new_ball2)
        all_sprites.add(new_ball1, new_ball2)
        logging.debug("Multi-ball power-up applied: two new balls created.")
        logging.info(f"Total balls after multi-ball power-up: {len(balls)}.")
    elif power_type == 'shrink_paddle':
        paddle.activate_powerup('shrink_paddle')
    elif power_type == 'slow_ball':
        for ball in balls:
            ball.apply_slow()
    elif power_type == 'laser_paddle':
        paddle.activate_powerup('laser_paddle')
    elif power_type == 'explosive_ball':
        # Make all existing balls explosive
        for ball in balls:
            ball.make_explosive()
    else:
        logging.warning(f"Unknown power-up type: {power_type}.")

def set_volume(new_volume):
    global VOLUME
    VOLUME = new_volume
    for sound in SOUND_EFFECTS.values():
        sound.set_volume(VOLUME)
    logging.debug(f"Volume set to {VOLUME * 100}%.")

def reset_game():
    global score, lives, game_over, win, current_level

    logging.info("Resetting game.")
    score = 0
    lives = 3
    game_over = False
    win = False
    current_level = 1
    level_start = True

    # Clear all sprite groups except paddle
    bricks.empty()
    all_powerups.empty()
    lasers.empty()
    messages.empty()
    all_sprites.empty()
    balls.empty()

    # Recreate Paddle
    global paddle
    paddle = Paddle()
    # Removed adding paddle to all_sprites

    # Reset Volume
    set_volume(0.1)
    logging.debug("Volume reset to default.")

def change_background(level):
    level_colors = [
        BLACK,
        (10, 10, 50),
        (50, 10, 10),
        (10, 50, 10),
        (50, 50, 10),
        (10, 50, 50)
    ]
    color = level_colors[level % len(level_colors)]
    screen.fill(color)

# ========================== Collision Handling ==========================
def handle_collisions():
    global score, lives, game_over, win, current_level, high_score

    level_completed = False  # Flag to indicate level completion

    for ball in balls:
        ball.collided = False  # Reset collision flag at the start of handling

        # Collision with paddle
        if pygame.sprite.collide_rect(ball, paddle):
            if not ball.collided:
                logging.info("Ball collided with Paddle.")
                angle_before_paddle = calculate_angle(ball.speed_x, ball.speed_y)
                logging.debug(f"Ball angle before paddle collision: {angle_before_paddle} degrees.")

                if ball.speed_y > 0 and ball.prev_rect.bottom <= paddle.rect.top:
                    ball.rect.bottom = paddle.rect.top
                    ball.speed_y = -abs(ball.speed_y)
                    ball.y = float(ball.rect.y)
                    hit_pos = (ball.rect.centerx - paddle.rect.left) / paddle.width
                    hit_pos = hit_pos * 2 - 1
                    max_speed_x = BALL_SPEED * 0.8
                    ball.speed_x = hit_pos * max_speed_x

                    if paddle.moving_left:
                        ball.speed_x -= 1
                    elif paddle.moving_right:
                        ball.speed_x += 1

                    ball.speed_x = max(-BALL_SPEED, min(ball.speed_x, BALL_SPEED))
                    ball.normalize_speed()
                    ball.y = float(ball.rect.y)
                    SOUND_EFFECTS['paddle'].play()

                    angle_after_paddle = calculate_angle(ball.speed_x, ball.speed_y)
                    logging.info(f"Ball bounced off Paddle. Angle changed from {angle_before_paddle}° to {angle_after_paddle}°.")
                    logging.info(f"Ball bounced at position {round(hit_pos, 2)} on the Paddle.")

                    ball.collided = True  # Set collision flag

        # Collision with bricks
        hit_bricks = pygame.sprite.spritecollide(ball, bricks, False)
        if hit_bricks and not ball.collided:
            # Process only the first collision to prevent multiple bounces
            brick = hit_bricks[0]
            logging.info(f"Ball collided with Brick at ({brick.rect.x}, {brick.rect.y}).")
            angle_before_brick = calculate_angle(ball.speed_x, ball.speed_y)
            logging.debug(f"Ball angle before brick collision: {angle_before_brick} degrees.")

            overlap_x = min(ball.rect.right, brick.rect.right) - max(ball.rect.left, brick.rect.left)
            overlap_y = min(ball.rect.bottom, brick.rect.bottom) - max(ball.rect.top, brick.rect.top)

            if overlap_x < overlap_y:
                if ball.speed_x > 0:
                    ball.rect.right = brick.rect.left
                    ball.speed_x = -abs(ball.speed_x)
                else:
                    ball.rect.left = brick.rect.right
                    ball.speed_x = abs(ball.speed_x)
            else:
                if ball.speed_y > 0:
                    ball.rect.bottom = brick.rect.top
                    ball.speed_y = -abs(ball.speed_y)
                else:
                    ball.rect.top = brick.rect.bottom
                    ball.speed_y = abs(ball.speed_y)

            ball.x = float(ball.rect.x)
            ball.y = float(ball.rect.y)

            brick.hit()
            score += 10
            logging.info(f"Score increased to {score}.")
            ball.normalize_speed()

            angle_after_brick = calculate_angle(ball.speed_x, ball.speed_y)
            logging.info(f"Ball bounced off Brick. Angle changed from {angle_before_brick}° to {angle_after_brick}°.")
            logging.info(f"Brick at ({brick.rect.x}, {brick.rect.y}) was hit. Remaining hits: {brick.hits}.")

            ball.collided = True  # Set collision flag

            # Check if the ball is explosive
            if ball.explosive:
                # Create an explosion at the collision point
                Explosion(ball.rect.centerx, ball.rect.centery)
                # Destroy bricks within the explosion radius (100 pixels)
                explosion_radius = 100
                for other_brick in bricks.copy():
                    distance = math.hypot(other_brick.rect.centerx - ball.rect.centerx,
                                          other_brick.rect.centery - ball.rect.centery)
                    if distance <= explosion_radius:
                        other_brick.kill()
                        score += 10
                        logging.info(f"Brick at ({other_brick.rect.x}, {other_brick.rect.y}) destroyed by explosion. Score: {score}.")
                # Revert the ball to regular state
                ball.revert_to_regular()

        # Collision with power-ups
        collected_powerups = pygame.sprite.spritecollide(paddle, all_powerups, True)
        for power in collected_powerups:
            logging.info(f"Power-up '{power.power_type}' collected at ({power.rect.x}, {power.rect.y}).")
            apply_powerup(power.power_type)
            SOUND_EFFECTS['powerup'].play()

            display_text = {
                'expand_paddle': "Expanded Paddle!",
                'extra_life': "Extra Life!",
                'multi_ball': "Multi-Ball!",
                'shrink_paddle': "Shrunk Paddle!",
                'slow_ball': "Slowed Ball!",
                'laser_paddle': "Laser Paddle!",
                'explosive_ball': "Explosive Ball!"  # Added explosive_ball message
            }.get(power.power_type, "Power-Up!")

            if messages:
                lowest_y = max(msg.rect.y for msg in messages)
                new_y = lowest_y + 30
                new_y = min(new_y, SCREEN_HEIGHT - 30)
            else:
                new_y = SCREEN_HEIGHT / 2 + 100

            message_position = (SCREEN_WIDTH / 2, new_y)
            message = PowerUpMessage(text=display_text, position=message_position)
            logging.debug(f"Power-up message '{display_text}' displayed at position {message_position}.")

        # Collision with lasers
        laser_hits = pygame.sprite.groupcollide(lasers, bricks, True, False)
        for laser, hit_bricks in laser_hits.items():
            for brick in hit_bricks:
                logging.info(f"Laser collided with Brick at ({brick.rect.x}, {brick.rect.y}).")
                brick.hit()
                score += 15
                logging.info(f"Score increased to {score}.")

        # Check for balls out of bounds
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
                        # Center the paddle when a new ball is created
                        paddle.center_paddle()
                    else:
                        game_over = True
                        SOUND_EFFECTS['game_over'].play()
                        logging.info("Game Over triggered.")

        # Check for win
        if len(bricks) == 0:
            logging.info("All bricks destroyed. Level completed.")
            score += 100
            logging.info(f"Score increased by 100 to {score}.")
            if score > high_score:
                high_score = score
                save_high_score(high_score)
                logging.info("New high score achieved!")
            if current_level < max_levels:
                level_completed = True
            else:
                win = True
                game_over = True
                logging.info("Player has won the game!")

            return level_completed  # Indicate level completion

# ========================== Main Game Function ==========================
def main():
    global score, lives, game_over, win, current_level, high_score

    high_score = load_high_score()
    current_level = 1
    score = 0
    lives = 3
    game_over = False
    win = False
    level_start = True

    # Create Paddle
    global paddle
    paddle = Paddle()
    # Removed adding paddle to all_sprites

    running = True
    paused = False

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
                elif event.key == pygame.K_SPACE and 'laser_paddle' in paddle.active_powerups:
                    paddle.shoot_laser()

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

        # Level Start
        if level_start:
            change_background(current_level)
            draw_text(f"Level {current_level}", large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50)
            draw_text("Press SPACE to Start", font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 10)
            if keys[pygame.K_SPACE]:
                level_start = False
                logging.info(f"Starting level {current_level}.")
                clear_active_powerups()
                create_bricks(5 + current_level, 10, current_level)
                # Reset balls
                for ball in balls.copy():
                    ball.kill()
                new_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, speed_increment=0.1 * current_level)
                balls.add(new_ball)
                all_sprites.add(new_ball)
                logging.debug("New ball created for the new level.")
                # Center the paddle at the start of the level
                paddle.center_paddle()
        elif not game_over:
            if not paused:
                paddle.update(keys)
                all_sprites.update()
                messages.update()
                collision_result = handle_collisions()  # Call once and store the result
                if collision_result:
                    level_start = True
                    if current_level < max_levels:
                        current_level += 1
                        logging.info(f"Proceeding to level {current_level}.")
                    else:
                        win = True
                        game_over = True
                        logging.info("All levels completed. Player wins!")

        # Drawing
        if not level_start:
            change_background(current_level)

        all_sprites.draw(screen)
        messages.draw(screen)
        screen.blit(paddle.image, paddle.rect)  # Draw paddle separately

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

        # Display Pause Message
        if paused:
            draw_text("PAUSED", large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            draw_text("Press P to Resume", font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50)

        # Game Over Message
        if game_over:
            message = "CONGRATULATIONS! YOU WIN!" if win else "GAME OVER"
            draw_text(message, large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            sub_text = "Press R to Restart or Q to Quit"
            draw_text(sub_text, font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50)

            if keys[pygame.K_r]:
                reset_game()
                level_start = True
            if keys[pygame.K_q]:
                logging.info("Quit event received via Q key. Exiting game.")
                running = False

        pygame.display.flip()

    pygame.quit()
    logging.info("Pygame quit. Game terminated.")
    sys.exit()

# ========================== Entry Point ==========================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("An unexpected error occurred during the game execution.")
        pygame.quit()
        sys.exit()
