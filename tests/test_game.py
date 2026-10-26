import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import atomic_write, load_game
from main import Game
import pygame

class StorageTests(unittest.TestCase):
    def test_round_trip_and_reject_corrupt_data(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / 'save.json'
            data = dict(version=1, ship='Falcon', x=480, y=550, hp=80, score=300, wave=2)
            atomic_write(path, data)
            self.assertEqual(load_game(path), data)
            for key, value in [('hp', -1), ('ship', 'unknown'), ('x', float('nan')), ('score', True), ('wave', 1.5)]:
                with self.subTest(key=key):
                    atomic_write(path, {**data, key: value})
                    with self.assertRaises(ValueError): load_game(path)
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError): load_game(path)

class GameTests(unittest.TestCase):
    def test_ships_combat_wave_and_render(self):
        game = Game()
        try:
            for ship in ('Falcon', 'Titan', 'Swift'):
                game.choose(ship)
                self.assertEqual(game.ship, ship)
                alien = game.aliens[0]
                game.bullets = [[alien['x'], alien['y'] + 5]]
                game.update_play(0.001)
                self.assertEqual(game.score, 100)
                game.aliens.clear()
                game.update_play(0.001)
                self.assertEqual(game.wave, 2)
                self.assertTrue(game.aliens)
            for state in ('menu', 'select', 'play', 'pause', 'over', 'settings'):
                game.state = state
                game.draw()
            game.invincible = 0
            game.damage(1000)
            game.state = 'play'
            game.update_play(0.001)
            self.assertEqual(game.state, 'over')
        finally:
            pygame.quit()

if __name__ == '__main__':
    unittest.main()

