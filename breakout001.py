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

# Screen Setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Breakout Game")
clock = pygame.time.Clock()

# Fonts
font = pygame.font.SysFont("Arial", 24)

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

# Simple beep sounds
paddle_sound = generate_sound(440)      # A4 note
brick_sound = generate_sound(880)       # A5 note
wall_sound = generate_sound(330)        # E4 note
game_over_sound = generate_sound(220)   # A3 note

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

# Ball Class
class Ball(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.radius = 10
        self.color = RED
        self.image = pygame.Surface([self.radius*2, self.radius*2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH / 2
        self.rect.centery = SCREEN_HEIGHT / 2
        self.speed_x = random.choice([-4, 4])
        self.speed_y = -4

    def update(self):
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

        # Bounce off left and right walls
        if self.rect.left <= 0:
            self.speed_x = abs(self.speed_x)
            wall_sound.play()
        if self.rect.right >= SCREEN_WIDTH:
            self.speed_x = -abs(self.speed_x)
            wall_sound.play()

        # Bounce off top
        if self.rect.top <= 0:
            self.speed_y = abs(self.speed_y)
            wall_sound.play()

    def reset(self):
        self.rect.centerx = SCREEN_WIDTH / 2
        self.rect.centery = SCREEN_HEIGHT / 2
        self.speed_x = random.choice([-4, 4])
        self.speed_y = -4

# Brick Class
class Brick(pygame.sprite.Sprite):
    def __init__(self, x, y, color=GREEN):
        super().__init__()
        self.width = 60
        self.height = 20
        self.color = color
        self.image = pygame.Surface([self.width, self.height])
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# Game Setup
def create_bricks(rows, cols):
    bricks = pygame.sprite.Group()
    brick_colors = [RED, GREEN, YELLOW, GREY]
    padding = 5
    offset_x = (SCREEN_WIDTH - (cols * (60 + padding))) / 2
    offset_y = 60
    for row in range(rows):
        for col in range(cols):
            x = offset_x + col * (60 + padding)
            y = offset_y + row * (20 + padding)
            color = brick_colors[row % len(brick_colors)]
            brick = Brick(x, y, color)
            bricks.add(brick)
    return bricks

def main():
    # Sprite Groups
    all_sprites = pygame.sprite.Group()
    bricks = create_bricks(5, 10)
    all_sprites.add(bricks)

    paddle = Paddle()
    all_sprites.add(paddle)

    ball = Ball()
    all_sprites.add(ball)

    # Game Variables
    score = 0
    lives = 3
    game_over = False
    win = False

    running = True
    while running:
        clock.tick(FPS)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        paddle.update(keys)

        if not game_over:
            ball.update()

            # Collision with paddle
            if ball.rect.colliderect(paddle.rect):
                ball.speed_y = -abs(ball.speed_y)
                # Adjust ball's horizontal speed based on where it hit the paddle
                hit_pos = (ball.rect.centerx - paddle.rect.left) / paddle.width
                ball.speed_x = (hit_pos - 0.5) * 8  # Adjust for direction
                paddle_sound.play()

            # Collision with bricks
            hit_bricks = pygame.sprite.spritecollide(ball, bricks, True)
            if hit_bricks:
                ball.speed_y *= -1
                brick_sound.play()
                score += 10

            # Check for loss of life
            if ball.rect.top > SCREEN_HEIGHT:
                lives -= 1
                if lives > 0:
                    ball.reset()
                else:
                    game_over = True
                    game_over_sound.play()

            # Check for win
            if len(bricks) == 0:
                win = True
                game_over = True

        # Drawing
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # Display Score and Lives
        score_text = font.render(f"Score: {score}", True, WHITE)
        lives_text = font.render(f"Lives: {lives}", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(lives_text, (SCREEN_WIDTH - 100, 10))

        # Game Over Message
        if game_over:
            if win:
                message = "YOU WIN!"
            else:
                message = "GAME OVER"
            game_over_text = font.render(message, True, WHITE)
            screen.blit(game_over_text, (SCREEN_WIDTH / 2 - game_over_text.get_width() / 2, SCREEN_HEIGHT / 2))
            sub_text = font.render("Press R to Restart or Q to Quit", True, WHITE)
            screen.blit(sub_text, (SCREEN_WIDTH / 2 - sub_text.get_width() / 2, SCREEN_HEIGHT / 2 + 40))

            if keys[pygame.K_r]:
                main()  # Restart the game
                return
            if keys[pygame.K_q]:
                running = False

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
