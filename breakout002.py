import pygame
import sys
import random
import math
import numpy as np

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

# Power-Up Types
POWERUP_TYPES = ['expand_paddle', 'extra_life', 'multi_ball']

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

    def update(self, keys):
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed

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

    def expand(self, duration=300):
        if not self.expanded:
            self.expanded = True
            self.expand_timer = duration
            self.width *= 1.5
            self.image = pygame.Surface([self.width, self.height])
            self.image.fill(self.color)
            self.rect = self.image.get_rect(center=self.rect.center)

    def shrink(self):
        self.expanded = False
        self.width /= 1.5
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect(center=self.rect.center)

# Ball Class
class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y, speed_x=None, speed_y=-4):
        super().__init__()
        self.radius = 10
        self.color = RED
        self.image = pygame.Surface([self.radius*2, self.radius*2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        self.speed_x = speed_x if speed_x else random.choice([-4, 4])
        self.speed_y = speed_y
        self.prev_rect = self.rect.copy()

    def update(self):
        # Store previous position
        self.prev_rect = self.rect.copy()

        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

        # Bounce off left and right walls
        if self.rect.left <= 0:
            self.rect.left = 0
            self.speed_x = abs(self.speed_x)
            wall_sound.play()
        if self.rect.right >= SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.speed_x = -abs(self.speed_x)
            wall_sound.play()

        # Bounce off top
        if self.rect.top <= 0:
            self.rect.top = 0
            self.speed_y = abs(self.speed_y)
            wall_sound.play()

    def reset(self, x, y):
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

# High Score
high_score = 0

def handle_collisions():
    global score, lives, game_over, win, current_level, high_score

    for ball in balls:
        # Collision with paddle
        if pygame.sprite.collide_rect(ball, paddle):
            # Reflect the ball
            # Determine collision side
            if ball.prev_rect.bottom <= paddle.rect.top and ball.speed_y > 0:
                ball.rect.bottom = paddle.rect.top
                ball.speed_y = -abs(ball.speed_y)

                # Adjust ball's horizontal speed based on collision point
                hit_pos = (ball.rect.centerx - paddle.rect.left) / paddle.width
                ball.speed_x = (hit_pos - 0.5) * 8  # Range from -4 to +4

                paddle_sound.play()

        # Collision with bricks
        hit_bricks = pygame.sprite.spritecollide(ball, bricks, False)
        for brick in hit_bricks:
            # Determine collision side
            if ball.prev_rect.bottom <= brick.rect.top and ball.speed_y > 0:
                ball.rect.bottom = brick.rect.top
                ball.speed_y = -abs(ball.speed_y)
            elif ball.prev_rect.top >= brick.rect.bottom and ball.speed_y < 0:
                ball.rect.top = brick.rect.bottom
                ball.speed_y = abs(ball.speed_y)
            elif ball.prev_rect.right <= brick.rect.left and ball.speed_x > 0:
                ball.rect.right = brick.rect.left
                ball.speed_x = -abs(ball.speed_x)
            elif ball.prev_rect.left >= brick.rect.right and ball.speed_x < 0:
                ball.rect.left = brick.rect.right
                ball.speed_x = abs(ball.speed_x)
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
        if current_level < max_levels:
            current_level += 1
            new_bricks = create_bricks(5 + current_level, 10, current_level)
            bricks.empty()
            bricks.add(*new_bricks)
            all_sprites.add(new_bricks)
            # Reset balls
            for ball in balls.copy():
                ball.kill()
            new_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            balls.add(new_ball)
            all_sprites.add(new_ball)
        else:
            win = True
            game_over = True

def apply_powerup(power_type):
    global lives
    if power_type == 'expand_paddle':
        paddle.expand()
    elif power_type == 'extra_life':
        lives += 1
    elif power_type == 'multi_ball':
        new_balls = []
        for ball in balls.copy():
            new_ball1 = Ball(ball.rect.centerx, ball.rect.centery, speed_x=ball.speed_x + 2, speed_y=ball.speed_y)
            new_ball2 = Ball(ball.rect.centerx, ball.rect.centery, speed_x=ball.speed_x - 2, speed_y=ball.speed_y)
            new_balls.extend([new_ball1, new_ball2])
            all_sprites.add(new_ball1, new_ball2)
        balls.add(*new_balls)

def draw_text(text, font, color, surface, x, y):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    text_rect.center = (x, y)
    surface.blit(text_obj, text_rect)

def reset_game():
    global score, lives, game_over, win, current_level, high_score, bricks, all_powerups, all_sprites, paddle, balls

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

    # Recreate Ball
    initial_ball = Ball(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    balls.add(initial_ball)
    all_sprites.add(initial_ball)

def main():
    global score, lives, game_over, win, current_level, high_score, bricks, all_powerups, all_sprites, paddle, balls

    running = True
    while running:
        clock.tick(FPS)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()

        if not game_over:
            paddle.update(keys)
            all_sprites.update()
            handle_collisions()

        # Drawing
        screen.fill(BLACK)
        all_sprites.draw(screen)
        screen.blit(paddle.image, paddle.rect)  # Draw paddle separately

        # Display Score and Lives
        score_text = font.render(f"Score: {score}", True, WHITE)
        lives_text = font.render(f"Lives: {lives}", True, WHITE)
        level_text = font.render(f"Level: {current_level}", True, WHITE)
        high_score_text = font.render(f"High Score: {high_score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(lives_text, (SCREEN_WIDTH - 150, 10))
        screen.blit(level_text, (10, 40))
        screen.blit(high_score_text, (SCREEN_WIDTH - 200, 40))

        # Draw Power-Ups
        for power in all_powerups:
            screen.blit(power.image, power.rect)

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
