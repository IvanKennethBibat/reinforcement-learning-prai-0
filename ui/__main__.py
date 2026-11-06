"""Play the game: ``python -m ui``."""
import pygame

from ui.arena import HEIGHT, WIDTH
from ui.game import Game

FPS = 60


def read_movement():
    keys = pygame.key.get_pressed()
    return (
        (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a]),
        (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w]),
    )


def main():
    pygame.init()
    pygame.display.set_caption("Pipkin's Meadow")
    window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    clock = pygame.time.Clock()
    game = Game()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            else:
                game.handle_event(event)
        game.update(dt, read_movement())
        game.draw(window)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
