import pygame
import sys
import random
import math
import numpy as np
import os

# Initialize Pygame
pygame.init()

# Game Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

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
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Volume Control
VOLUME = 0.1  # Default volume set to 10% (range: 0.0 to 1.0)

# Generate simple beep sounds using numpy
def generate_sound(frequency, duration=0.1, volume=0.5):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    wave = np.sin(2 * math.pi * frequency * t)  # Generate sine wave
    wave = (wave * volume * 32767).astype(np.int16)  # Scale to 16-bit integer
    stereo_wave = np.column_stack((wave, wave))  # Duplicate for stereo
    sound = pygame.sndarray.make_sound(stereo_wave)
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

# Power-Up Types
POWERUP_TYPES = ['expand_paddle', 'extra_life', 'multi_ball']

# High Score File
HIGH_SCORE_FILE = 'highscore.txt'

def load_high_score(filename=HIGH_SCORE_FILE):
    try:
        with open(filename, 'r') as f:
            return int(f.read())
    except:
        return 0

def save_high_score(score, filename=HIGH_SCORE_FILE):
    try:
        with open(filename, 'w') as f:
            f.write(str(score))
    except:
        pass

# Paddle Class
class Paddle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
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
        if not self.expanded:
            self.expanded = True
            self.expand_timer = duration
            self.width *= 1.5
            self.image = pygame.Surface([self.width, self.height])
            self.image.fill(ORANGE)  # Change color to indicate expansion
            self.rect = self.image.get_rect(center=self.rect.center)

    def shrink(self):
        self.expanded = False
        self.width /= 1.5
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect(center=self.rect.center)

# Ball Class
class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y, speed_x=None, speed_y=-4, speed_increment=0):
        super().__init__()
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

    def update(self):
        # Apply speed increment
        if self.speed_increment != 0:
            self.speed_x *= (1 + self.speed_increment)
            self.speed_y *= (1 + self.speed_increment)

        # Store previous position
        self.prev_rect = self.rect.copy()

        self.x += self.speed_x
        self.y += self.speed_y

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

        # Bounce off left and right walls
        if self.rect.left <= 0:
            self.rect.left = 0
            self.speed_x = abs(self.speed_x)
            self.x = float(self.rect.x)
            wall_sound.play()
        if self.rect.right >= SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.speed_x = -abs(self.speed_x)
            self.x = float(self.rect.x)
            wall_sound.play()

        # Bounce off top
        if self.rect.top <= 0:
            self.rect.top = 0
            self.speed_y = abs(self.speed_y)
            self.y = float(self.rect.y)
            wall_sound.play()

        # Ensure speed components do not become zero
        if abs(self.speed_x) < 1:
            self.speed_x = random.choice([-2, 2])
        if abs(self.speed_y) < 1:
            self.speed_y = random.choice([-2, 2])

    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.rect.centerx = x
        self.rect.centery = y
        self.speed_x = random.choice([-4, 4])
        self.speed_y = -4

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
        self.hits -= 1
        if self.hits > 0:
            # Change color based on remaining hits
            color_intensity = int(255 * (self.hits / self.max_hits))
            self.color = (color_intensity, 0, 255 - color_intensity)
            self.image.fill(self.color)
        else:
            self.kill()
            # 20% chance to drop a power-up
            if random.random() < 0.2:
                powerup = PowerUp(self.rect.centerx, self.rect.centery)
                all_powerups.add(powerup)
                all_sprites.add(powerup)
            # 10% chance for explosive brick
            if random.random() < 0.1:
                self.explode()

    def explode(self):
        # Destroy adjacent bricks
        adjacent_bricks = pygame.sprite.spritecollide(self, bricks, False)
        for brick in adjacent_bricks:
            brick.kill()

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

    def update(self):
        self.rect.y += self.speed_y
        # Remove if out of screen
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

# Initialize Sprite Groups
all_sprites = pygame.sprite.Group()
bricks = pygame.sprite.Group()
all_powerups = pygame.sprite.Group()
balls = pygame.sprite.Group()

# Create Bricks
def create_bricks(rows, cols, level=1):
    bricks = pygame.sprite.Group()
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
            elif level >=2 and random.random() < 0.3:
                hits = 2
                color = ORANGE
            else:
                hits = 1
                color = brick_colors[row % len(brick_colors)]
            brick = Brick(x, y, hits, color)
            bricks.add(brick)
    return bricks

# Initialize Level
current_level = 1
max_levels = 5

# Create Initial Bricks
bricks = create_bricks(5, 10, current_level)
all_sprites.add(bricks)

# Create Paddle (Handled Separately)
paddle = Paddle()

# Create Ball
initial_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
balls.add(initial_ball)
all_sprites.add(initial_ball)

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
            # Reflect the ball
            if ball.prev_rect.bottom <= paddle.rect.top and ball.speed_y > 0:
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
                if ball.speed_x < min_speed_x:
                    ball.speed_x = min_speed_x
                elif ball.speed_x > max_speed_x:
                    ball.speed_x = max_speed_x
                # Ensure y speed is upwards
                ball.speed_y = -abs(ball.speed_y)
                # Reposition ball just above the paddle
                ball.y = float(ball.rect.y)
                paddle_sound.play()

        # Collision with bricks
        hit_bricks = pygame.sprite.spritecollide(ball, bricks, False)
        for brick in hit_bricks:
            # Determine collision side
            if ball.prev_rect.bottom <= brick.rect.top and ball.speed_y > 0:
                ball.rect.bottom = brick.rect.top
                ball.speed_y = -abs(ball.speed_y)
                ball.y = float(ball.rect.y)
            elif ball.prev_rect.top >= brick.rect.bottom and ball.speed_y < 0:
                ball.rect.top = brick.rect.bottom
                ball.speed_y = abs(ball.speed_y)
                ball.y = float(ball.rect.y)
            elif ball.prev_rect.right <= brick.rect.left and ball.speed_x > 0:
                ball.rect.right = brick.rect.left
                ball.speed_x = -abs(ball.speed_x)
                ball.x = float(ball.rect.x)
            elif ball.prev_rect.left >= brick.rect.right and ball.speed_x < 0:
                ball.rect.left = brick.rect.right
                ball.speed_x = abs(ball.speed_x)
                ball.x = float(ball.rect.x)
            else:
                # Fallback
                ball.speed_y *= -1

            brick.hit()
            brick_sound.play()
            score += 10

    # Collision with power-ups
    power_hits = pygame.sprite.spritecollide(paddle, all_powerups, True)
    for power in power_hits:
        apply_powerup(power.power_type)
        powerup_sound.play()

    # Check for ball out of bounds
    for ball in balls.copy():
        if ball.rect.top > SCREEN_HEIGHT:
            ball.kill()
            if len(balls) == 0:
                lives -= 1
                if lives > 0:
                    new_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
                    balls.add(new_ball)
                    all_sprites.add(new_ball)
                else:
                    game_over = True
                    game_over_sound.play()

    # Check for win
    if len(bricks) == 0:
        score += 100  # Bonus for clearing level
        if score > high_score:
            high_score = score
            save_high_score(high_score)
        if current_level < max_levels:
            return True  # Indicate that level has been completed and should start next
        else:
            win = True
            game_over = True
    return False

def apply_powerup(power_type):
    global lives
    if power_type == 'expand_paddle':
        paddle.expand()
    elif power_type == 'extra_life':
        lives += 1
    elif power_type == 'multi_ball':
        new_balls = []
        for ball in balls.copy():
            # Create two new balls with slightly altered speeds
            new_ball1 = Ball(ball.x, ball.y, speed_x=ball.speed_x + 2, speed_y=ball.speed_y, speed_increment=ball.speed_increment)
            new_ball2 = Ball(ball.x, ball.y, speed_x=ball.speed_x - 2, speed_y=ball.speed_y, speed_increment=ball.speed_increment)
            new_balls.extend([new_ball1, new_ball2])
            all_sprites.add(new_ball1, new_ball2)
        balls.add(*new_balls)

def set_volume(new_volume):
    global VOLUME
    VOLUME = new_volume
    for sound in SOUND_EFFECTS:
        sound.set_volume(VOLUME)

def draw_text(text, font, color, surface, x, y):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    text_rect.center = (x, y)
    surface.blit(text_obj, text_rect)

def reset_game():
    global score, lives, game_over, win, current_level, high_score, bricks, all_powerups, all_sprites, paddle, balls, VOLUME

    score = 0
    lives = 3
    game_over = False
    win = False
    current_level = 1

    # Clear all sprite groups
    bricks.empty()
    all_powerups.empty()
    all_sprites.empty()
    balls.empty()

    # Recreate Bricks
    bricks = create_bricks(5, 10, current_level)
    all_sprites.add(bricks)

    # Recreate Paddle
    paddle = Paddle()
    all_sprites.add(paddle)

    # Recreate Ball
    initial_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    balls.add(initial_ball)
    all_sprites.add(initial_ball)

    # Reset Volume to default
    set_volume(0.1)

def main():
    global score, lives, game_over, win, current_level, high_score, bricks, all_powerups, all_sprites, paddle, balls, VOLUME

    paused = False
    running = True
    level_start = False

    while running:
        clock.tick(FPS)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    paused = not paused

        keys = pygame.key.get_pressed()

        # Volume Control
        if keys[pygame.K_UP]:
            new_volume = min(1.0, VOLUME + 0.01)
            if new_volume != VOLUME:
                set_volume(new_volume)
        if keys[pygame.K_DOWN]:
            new_volume = max(0.0, VOLUME - 0.01)
            if new_volume != VOLUME:
                set_volume(new_volume)

        # Handle Level Start
        if level_start:
            draw_text(f"Level {current_level}", large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50)
            draw_text("Press SPACE to Start", font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 10)
            if keys[pygame.K_SPACE]:
                level_start = False
                current_level += 1
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
        elif not paused and not game_over:
            # Update game entities
            paddle.update(keys)
            all_sprites.update()
            completed = handle_collisions()
            if completed:
                level_start = True

        # Drawing
        screen.fill(BLACK)
        all_sprites.draw(screen)
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

        # Draw Power-Ups
        for power in all_powerups:
            screen.blit(power.image, power.rect)

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
                running = False

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
