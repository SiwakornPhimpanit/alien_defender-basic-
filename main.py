"""Alien Defender — run with python main.py."""
import json
import math
import os
from pathlib import Path
import random
import sys
import pygame
from storage import SHIPS, atomic_write, load_game

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'AlienDefender'
WIDTH, HEIGHT = 960, 640
CYAN, WHITE, MUTED = (75, 224, 255), (232, 241, 255), (143, 163, 194)

class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('ALIEN DEFENDER | Galactic Patrol')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.big = pygame.font.Font(None, 66)
        self.small = pygame.font.Font(None, 22)
        self.running = True
        self.state = 'menu'
        self.previous = 'menu'
        self.ship = 'Falcon'
        self.settings = {'music': 0.35, 'sfx': 0.6, 'difficulty': 'Normal'}
        try:
            saved = json.loads((DATA / 'settings.json').read_text(encoding='utf-8'))
            for key in ('music', 'sfx'):
                value = saved.get(key)
                if type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1:
                    self.settings[key] = value
            if saved.get('difficulty') in ('Easy', 'Normal', 'Hard'):
                self.settings['difficulty'] = saved['difficulty']
        except (OSError, ValueError, AttributeError):
            pass
        self.sounds = {}
        if pygame.mixer.get_init():
            for name in ('shoot', 'explosion', 'hit'):
                try:
                    self.sounds[name] = pygame.mixer.Sound(str(ROOT / 'assets' / (name + '.wav')))
                except (pygame.error, OSError):
                    pass
            try:
                pygame.mixer.music.load(str(ROOT / 'assets/music.wav'))
                pygame.mixer.music.play(-1)
            except (pygame.error, OSError):
                pass
        self.apply_audio()
        self.stars = [[random.randrange(WIDTH), random.randrange(HEIGHT), random.uniform(20, 85)] for _ in range(100)]
        self.buttons = []
        self.notice = ''
        self.notice_time = 0
        self.has_game = False

    def apply_audio(self):
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(self.settings['music'])
            for sound in self.sounds.values():
                sound.set_volume(self.settings['sfx'])

    def sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    def tell(self, message):
        self.notice, self.notice_time = message, 4

    def start(self, data=None):
        self.ship = data['ship'] if data else self.ship
        self.x, self.y = (data['x'], data['y']) if data else (480, 550)
        self.hp = data['hp'] if data else SHIPS[self.ship][1]
        self.score, self.wave = (data['score'], data['wave']) if data else (0, 1)
        self.bullets, self.enemy_bullets, self.aliens, self.particles = [], [], [], []
        self.cooldown, self.invincible = 0, 1.5
        self.has_game = True
        self.spawn_wave()
        self.state = 'play'

    def spawn_wave(self):
        self.aliens = []
        for row in range(min(5, 2 + self.wave // 3)):
            for col in range(8):
                self.aliens.append({'x': 130 + col * 95, 'y': 105 + row * 52, 'hp': 1 + self.wave // 5, 'phase': random.random() * 6})
        self.wave_time = 0
        self.enemy_timer = 0.7

    def save(self):
        if not self.has_game or self.hp <= 0:
            self.tell('Start a game before saving.')
            return
        try:
            atomic_write(DATA / 'save.json', {'version': 1, 'ship': self.ship, 'x': self.x, 'y': self.y, 'hp': self.hp, 'score': self.score, 'wave': self.wave})
            self.tell('Game saved. Loading restarts the current wave.')
        except OSError:
            self.tell('Cannot write save file. Check folder permissions.')

    def load(self):
        try:
            self.start(load_game(DATA / 'save.json'))
            self.tell('Game loaded — current wave restarted.')
        except FileNotFoundError:
            self.tell('No saved game yet.')
        except (OSError, ValueError, TypeError):
            self.tell('Cannot load: save file is invalid or unreadable.')

    def text(self, text, x, y, color=WHITE, font=None, center=False):
        surface = (font or self.font).render(text, True, color)
        self.screen.blit(surface, surface.get_rect(center=(x, y)) if center else (x, y))

    def button(self, label, rect, action):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, (29, 65, 91) if hover else (16, 31, 54), rect, border_radius=10)
        pygame.draw.rect(self.screen, CYAN if hover else (48, 77, 108), rect, 2, border_radius=10)
        self.text(label, *rect.center, center=True)
        self.buttons.append((rect, action))

    def draw_ship(self, x, y, ship, scale=1):
        color = {'Falcon': CYAN, 'Titan': (255, 181, 73), 'Swift': (190, 135, 255)}[ship]
        points = [(0, -25), (21, 21), (8, 15), (0, 22), (-8, 15), (-21, 21)]
        pygame.draw.polygon(self.screen, color, [(x + a * scale, y + b * scale) for a, b in points])
        pygame.draw.polygon(self.screen, WHITE, [(x, y-13*scale), (x+5*scale, y+8*scale), (x-5*scale, y+8*scale)])
        pygame.draw.polygon(self.screen, (255, 120, 65), [(x-6*scale, y+23*scale), (x, y+random.randint(30, 42)*scale), (x+6*scale, y+23*scale)])

    def burst(self, x, y, color):
        for _ in range(18):
            self.particles.append([x, y, random.uniform(-140, 140), random.uniform(-140, 140), 0.6, color])

    def update_play(self, dt):
        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP])
        length = max(1, math.hypot(dx, dy))
        speed, _, delay = SHIPS[self.ship]
        self.x = max(25, min(935, self.x + dx / length * speed * dt))
        self.y = max(350, min(600, self.y + dy / length * speed * dt))
        self.cooldown -= dt
        self.invincible -= dt
        if keys[pygame.K_SPACE] and self.cooldown <= 0:
            self.bullets.append([self.x, self.y - 28])
            self.cooldown = delay
            self.sound('shoot')
        self.wave_time += dt
        factor = {'Easy': 0.7, 'Normal': 1, 'Hard': 1.4}[self.settings['difficulty']]
        for alien in self.aliens:
            alien['x'] += math.sin(self.wave_time * 1.5 + alien['phase']) * 24 * dt
            alien['y'] += (7 + self.wave * 1.2) * factor * dt
        self.enemy_timer -= dt
        if self.aliens and self.enemy_timer <= 0:
            source = random.choice(self.aliens)
            self.enemy_bullets.append([source['x'], source['y'] + 15])
            self.enemy_timer = max(0.16, 0.9 - self.wave * 0.035) / factor
        for bullet in self.bullets[:]:
            bullet[1] -= 570 * dt
            if bullet[1] < 0:
                self.bullets.remove(bullet)
                continue
            for alien in self.aliens[:]:
                if abs(bullet[0]-alien['x']) < 24 and abs(bullet[1]-alien['y']) < 20:
                    self.bullets.remove(bullet)
                    alien['hp'] -= 1
                    if alien['hp'] <= 0:
                        self.aliens.remove(alien)
                        self.score += 100
                        self.burst(alien['x'], alien['y'], (115, 255, 156))
                        self.sound('explosion')
                    break
        for bullet in self.enemy_bullets[:]:
            bullet[1] += (210 + self.wave * 9) * factor * dt
            if bullet[1] > HEIGHT:
                self.enemy_bullets.remove(bullet)
            elif abs(bullet[0]-self.x) < 20 and abs(bullet[1]-self.y) < 24:
                self.enemy_bullets.remove(bullet)
                self.damage(20)
        for alien in self.aliens[:]:
            if alien['y'] > 615 or (abs(alien['x']-self.x) < 35 and abs(alien['y']-self.y) < 35):
                self.aliens.remove(alien)
                self.damage(30)
        for particle in self.particles[:]:
            particle[0] += particle[2] * dt
            particle[1] += particle[3] * dt
            particle[4] -= dt
            if particle[4] <= 0:
                self.particles.remove(particle)
        if self.hp <= 0:
            self.state = 'over'
        elif not self.aliens:
            self.wave += 1
            self.hp = min(SHIPS[self.ship][1], self.hp + 15)
            self.enemy_bullets.clear()
            self.spawn_wave()

    def damage(self, amount):
        if self.invincible <= 0:
            self.hp = max(0, self.hp - amount)
            self.invincible = 0.8
            self.sound('hit')
            self.burst(self.x, self.y, (255, 100, 100))

    def change_setting(self, key):
        if key == 'difficulty':
            options = ['Easy', 'Normal', 'Hard']
            self.settings[key] = options[(options.index(self.settings[key])+1) % 3]
        else:
            self.settings[key] = round((self.settings[key] + 0.25) % 1.25, 2)
            self.settings[key] = min(1, self.settings[key])
        self.apply_audio()
        try:
            atomic_write(DATA / 'settings.json', self.settings)
        except OSError:
            self.tell('Settings applied, but could not save to disk.')

    def draw(self):
        self.screen.fill((5, 10, 24))
        for x, y, speed in self.stars:
            pygame.draw.circle(self.screen, (75, 100, 140), (int(x), int(y)), 1 if speed < 60 else 2)
        self.buttons = []
        if self.state in ('play', 'pause', 'over'):
            for alien in self.aliens:
                x, y = int(alien['x']), int(alien['y'])
                pygame.draw.ellipse(self.screen, (111, 237, 148), (x-22, y-15, 44, 30))
                for side in (-1, 1):
                    pygame.draw.circle(self.screen, (8, 24, 34), (x+side*9, y-2), 5)
                    pygame.draw.line(self.screen, (111, 237, 148), (x+side*12, y-10), (x+side*23, y-24), 3)
            for x, y in self.bullets:
                pygame.draw.line(self.screen, CYAN, (x, y), (x, y+17), 4)
            for x, y in self.enemy_bullets:
                pygame.draw.circle(self.screen, (255, 100, 130), (int(x), int(y)), 5)
            for x, y, _, _, life, color in self.particles:
                pygame.draw.circle(self.screen, color, (int(x), int(y)), max(1, int(life*6)))
            if self.invincible <= 0 or int(pygame.time.get_ticks()/100) % 2:
                self.draw_ship(self.x, self.y, self.ship)
            pygame.draw.rect(self.screen, (10, 19, 37), (0, 0, WIDTH, 62))
            self.text(f'SCORE {self.score:06d}     WAVE {self.wave}     {self.ship.upper()}', 24, 20)
            self.text(f'HP {self.hp}', 625, 20, CYAN)
            self.button('Pause', (810, 10, 120, 40), lambda: setattr(self, 'state', 'pause'))
        if self.state in ('pause', 'over'):
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((3, 8, 20, 220))
            self.screen.blit(overlay, (0, 0))
            self.buttons = []
            self.text('PAUSED' if self.state == 'pause' else 'MISSION OVER', 480, 145, CYAN, self.big, True)
            if self.state == 'pause':
                self.button('Resume', (330, 215, 300, 48), lambda: setattr(self, 'state', 'play'))
                self.button('Save Game', (330, 275, 300, 48), self.save)
            else:
                self.text(f'Final score: {self.score}  |  Wave {self.wave}', 480, 215, center=True)
                self.button('New Start', (330, 275, 300, 48), lambda: setattr(self, 'state', 'select'))
            self.button('Settings', (330, 335, 300, 48), self.open_settings)
            self.button('Main Menu', (330, 395, 300, 48), lambda: setattr(self, 'state', 'menu'))
        elif self.state == 'menu':
            self.text('GALACTIC PATROL', 480, 90, MUTED, self.small, True)
            self.text('ALIEN DEFENDER', 480, 150, CYAN, self.big, True)
            for i, (label, action) in enumerate([
                ('New Start', lambda: setattr(self, 'state', 'select')),
                ('Save Game', self.save), ('Load Game', self.load),
                ('Settings', self.open_settings), ('Quit', lambda: setattr(self, 'running', False))]):
                self.button(label, (330, 240+i*58, 300, 46), action)
            if self.has_game and self.hp > 0:
                self.button('Continue', (680, 240, 170, 46), lambda: setattr(self, 'state', 'play'))
            self.text('WASD / Arrows: move    SPACE: fire    ESC: pause', 480, 570, MUTED, self.small, True)
        elif self.state == 'select':
            self.text('CHOOSE YOUR SHIP', 480, 100, CYAN, self.big, True)
            for index, (name, (speed, hp, delay)) in enumerate(SHIPS.items()):
                x = 65 + index*300
                pygame.draw.rect(self.screen, (16, 28, 49), (x, 180, 270, 300), border_radius=14)
                self.draw_ship(x+135, 260, name, 1.8)
                self.text(name.upper(), x+135, 340, CYAN, center=True)
                self.text(f'HP {hp}  |  Speed {speed}', x+135, 380, center=True)
                self.text(f'Fire rate {1/delay:.1f}/sec', x+135, 410, MUTED, center=True)
                self.button('Select', (x+45, 435, 180, 40), lambda n=name: self.choose(n))
            self.button('Back', (380, 535, 200, 45), lambda: setattr(self, 'state', 'menu'))
        elif self.state == 'settings':
            self.text('SETTINGS', 480, 120, CYAN, self.big, True)
            for index, key in enumerate(('music', 'sfx', 'difficulty')):
                value = self.settings[key]
                label = f'{key.upper()}: {int(value*100)}%' if key != 'difficulty' else f'DIFFICULTY: {value}'
                self.button(label, (280, 235+index*70, 400, 50), lambda k=key: self.change_setting(k))
            self.text('Click a setting to cycle its value. Changes save automatically.', 480, 470, MUTED, self.small, True)
            self.button('Back', (380, 530, 200, 45), lambda: setattr(self, 'state', self.previous))
        if self.notice_time > 0:
            pygame.draw.rect(self.screen, (28, 54, 75), (0, 606, WIDTH, 34))
            self.text(self.notice, 480, 623, WHITE, self.small, True)

    def choose(self, name):
        self.ship = name
        self.start()

    def open_settings(self):
        self.previous = self.state
        self.state = 'settings'

    def run(self, smoke=False):
        frames = 0
        while self.running:
            dt = min(self.clock.tick(60)/1000, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == 'play': self.state = 'pause'
                        elif self.state == 'pause': self.state = 'play'
                        elif self.state == 'settings': self.state = self.previous
                        elif self.state == 'select': self.state = 'menu'
                    elif event.key == pygame.K_F5 and self.state in ('play', 'pause'): self.save()
                    elif event.key == pygame.K_F9: self.load()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in self.buttons[:]:
                        if rect.collidepoint(event.pos):
                            action()
                            break
            for star in self.stars:
                star[1] = (star[1]+star[2]*dt) % HEIGHT
            self.notice_time = max(0, self.notice_time-dt)
            if self.state == 'play': self.update_play(dt)
            self.draw()
            pygame.display.flip()
            frames += 1
            if smoke and frames >= 8: self.running = False
        pygame.quit()

if __name__ == '__main__':
    Game().run('--smoke-test' in sys.argv)
