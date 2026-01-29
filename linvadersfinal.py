import arcade
import random
import csv
import os
import math
import datetime
import sqlite3

# константы
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Лицей Invaders"
SPRITE_SCALE = 0.5

# игровые константы
PLAYER_SPEED = 7
BULLET_SPEED = 8
ENEMY_BULLET_SPEED = 5
POWERUP_SPEED = 2
PLAYER_START_LIVES = 3


class PowerUpType:
    # типы улучшений
    SHIELD = 1
    RAPID_FIRE = 2
    EXTRA_LIFE = 3


class DatabaseManager:
    # менеджер базы данных sqlite для хранения рекордов

    def __init__(self, db_name='game_scores.db'):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        # инициализация базы данных
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    lives INTEGER NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            print(f"база данных {self.db_name} инициализирована")
        except Exception as e:
            print(f"ошибка создания базы данных: {e}")

    def save_score(self, player_name, score, level, lives):
        # сохранение результата в базу данных
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scores (player_name, score, level, lives, date)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (player_name, score, level, lives))
            conn.commit()
            conn.close()
            print(f"результат сохранен в бд: {player_name}, {score}, {level}, {lives}")
            return True
        except Exception as e:
            print(f"ошибка сохранения в бд: {e}")
            return False


class Player(arcade.Sprite):
    # класс игрока с управлением и улучшениями

    def __init__(self):
        super().__init__("arcade_resources/assets/images/space_shooter/playerShip1_orange.png", SPRITE_SCALE)
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = 60
        self.lives = PLAYER_START_LIVES
        self.speed = PLAYER_SPEED
        self.shoot_cooldown = 0
        self.shield_active = False
        self.rapid_fire_active = False
        self.powerup_timer = 0

        # для анимации щита
        self.shield_alpha = 0

    def on_update(self, delta_time: float = 1 / 60):
        # обновление игрока
        # ограничение движения
        if self.left < 0:
            self.left = 0
        elif self.right > SCREEN_WIDTH:
            self.right = SCREEN_WIDTH

        # обновление кулдаунов
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        if self.powerup_timer > 0:
            self.powerup_timer -= 1
            # анимация щита
            if self.shield_active:
                self.shield_alpha = int(128 + 127 * math.sin(self.powerup_timer * 0.2))
        else:
            self.shield_active = False
            self.rapid_fire_active = False
            self.shield_alpha = 0


class Bullet(arcade.Sprite):
    # класс пули с физикой

    def __init__(self, x, y, direction=1, is_enemy=False):
        texture = "arcade_resources/assets/images/space_shooter/laserRed01.png" if is_enemy else "arcade_resources/assets/images/space_shooter/laserBlue01.png"
        super().__init__(texture, SPRITE_SCALE * 0.6)
        self.center_x = x
        self.center_y = y
        self.direction = direction
        self.speed = ENEMY_BULLET_SPEED if is_enemy else BULLET_SPEED
        self.is_enemy = is_enemy

    def on_update(self, delta_time: float = 1 / 60):
        # обновление пули
        self.center_y += self.speed * self.direction

        # удаление пули за пределами экрана
        if self.center_y < 0 or self.center_y > SCREEN_HEIGHT:
            self.remove_from_sprite_lists()


class Enemy(arcade.Sprite):
    # класс врага с анимацией

    def __init__(self, x, y, enemy_type, level):
        # используем одну текстуру для всех врагов
        super().__init__("arcade_resources/assets/images/space_shooter/playerShip1_orange.png", SPRITE_SCALE * 0.8)

        # меняем цвет в зависимости от типа врага (анимация)
        colors = [
            arcade.color.GREEN,
            arcade.color.BLUE,
            arcade.color.RED
        ]
        self.color = colors[enemy_type]

        self.center_x = x
        self.center_y = y
        self.enemy_type = enemy_type
        self.health = 1 + enemy_type
        self.base_speed = 1 + enemy_type * 0.3 + level * 0.2
        self.speed = self.base_speed
        self.direction = 1
        self.shoot_cooldown = random.randint(60, 180)
        self.points = (enemy_type + 1) * 10

        # анимация - изменение масштаба (пульсация)
        self.animation_time = random.uniform(0, 3.14)
        self.base_scale = SPRITE_SCALE * 0.8

    def on_update(self, delta_time: float = 1 / 60):
        # обновление врага с анимацией
        # анимация - простая пульсация
        self.animation_time += 0.05
        scale_factor = 1 + 0.1 * abs(math.sin(self.animation_time))
        self.scale = self.base_scale * scale_factor

        # кулдаун стрельбы
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1


class PowerUp(arcade.Sprite):
    # класс улучшения с анимацией

    def __init__(self, x, y):
        textures = {
            PowerUpType.SHIELD: "arcade_resources/assets/images/items/star.png",
            PowerUpType.RAPID_FIRE: "arcade_resources/assets/images/items/gemBlue.png",
            PowerUpType.EXTRA_LIFE: "arcade_resources/assets/images/items/coinGold.png"
        }
        self.powerup_type = random.choice([PowerUpType.SHIELD, PowerUpType.RAPID_FIRE, PowerUpType.EXTRA_LIFE])
        super().__init__(textures[self.powerup_type], SPRITE_SCALE * 0.4)
        self.center_x = x
        self.center_y = y
        self.speed = POWERUP_SPEED
        self.animation_time = 0

    def on_update(self, delta_time: float = 1 / 60):
        # обновление улучшения с анимацией
        self.center_y -= self.speed

        # анимация - вращение
        self.animation_time += 0.1
        self.angle = math.sin(self.animation_time) * 30

        if self.center_y < 0:
            self.remove_from_sprite_lists()


class Particle:
    # система частиц - простая частица для эффектов взрыва

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.lifetime = random.uniform(0.3, 0.8)
        self.max_lifetime = self.lifetime
        self.size = random.uniform(2, 5)
        # цвет как кортеж rgb
        self.color = random.choice([
            (255, 255, 0),  # желтый
            (255, 165, 0),  # оранжевый
            (255, 0, 0)  # красный
        ])

    def update(self, delta_time):
        # обновление частицы
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= delta_time

    def draw(self):
        # отрисовка частицы с прозрачностью
        # не рисуем мертвые частицы
        if self.lifetime <= 0:
            return

        alpha = int(255 * (self.lifetime / self.max_lifetime))
        alpha = max(0, min(255, alpha))  # гарантия диапазона [0, 255]
        color = (self.color[0], self.color[1], self.color[2], alpha)
        arcade.draw_circle_filled(self.x, self.y, self.size, color)

    def is_alive(self):
        # проверка жива ли частица
        return self.lifetime > 0


class ParticleSystem:
    # система частиц для визуализации взрывов

    def __init__(self):
        self.particles = []

    def emit(self, x, y, count=20):
        # создание частиц в точке взрыва
        for _ in range(count):
            self.particles.append(Particle(x, y))

    def update(self, delta_time):
        # обновление всех частиц
        self.particles = [p for p in self.particles if p.is_alive()]
        for particle in self.particles:
            particle.update(delta_time)

    def draw(self):
        # отрисовка всех частиц
        for particle in self.particles:
            particle.draw()


class Level:
    # несколько уровней - класс управления уровнями с увеличивающейся сложностью

    def __init__(self, level_number):
        self.level_number = level_number
        self.enemies_per_row = min(8 + level_number, 12)
        self.enemy_rows = min(3 + level_number, 7)
        self.enemy_speed_multiplier = 1 + (level_number - 1) * 0.15

    def spawn_enemies(self):
        # генерация врагов для уровня (больше с каждым уровнем)
        enemies = arcade.SpriteList()

        start_x = 100
        start_y = SCREEN_HEIGHT - 150
        spacing_x = (SCREEN_WIDTH - 200) / self.enemies_per_row
        spacing_y = 60

        for row in range(self.enemy_rows):
            # тип врага зависит от ряда
            enemy_type = min(row // 2, 2)

            for col in range(self.enemies_per_row):
                x = start_x + col * spacing_x
                y = start_y - row * spacing_y
                enemy = Enemy(x, y, enemy_type, self.level_number)
                enemies.append(enemy)

        return enemies


class GameView(arcade.View):
    # основной класс игры с камерой

    def __init__(self):
        super().__init__()

        # спрайты
        self.player_sprite = None
        self.player_list = None
        self.bullet_list = None
        self.enemy_bullet_list = None
        self.enemy_list = None
        self.powerup_list = None

        # игровые переменные (подсчет результатов)
        self.score = 0
        self.level = None
        self.current_level = 1

        # управление врагами
        self.enemy_direction = 1
        self.enemy_move_down = False

        # камера - используем смещение для эффекта тряски
        self.camera_shake = 0
        self.camera_x = 0
        self.camera_y = 0

        # физический движок - arcade для обработки физики
        self.physics_engine = None

        # система частиц для взрывов
        self.particle_system = ParticleSystem()

        # звуки
        self.shoot_sound = None
        self.explosion_sound = None
        self.powerup_sound = None
        self.level_complete_sound = None
        self.hit_sound = None

        # управление
        self.left_pressed = False
        self.right_pressed = False

        # менеджер базы данных
        self.db_manager = DatabaseManager()

        # имя игрока
        self.player_name = "Player"

        arcade.set_background_color(arcade.color.BLACK)

    def setup(self):
        # инициализация игры

        # физический движок arcade
        self.physics_engine = None  # в этой игре не используется сложная физика движка

        # спрайты
        self.player_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.enemy_bullet_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.powerup_list = arcade.SpriteList()

        # игрок
        self.player_sprite = Player()
        self.player_list.append(self.player_sprite)

        # несколько уровней
        self.level = Level(self.current_level)
        self.enemy_list = self.level.spawn_enemies()

        # звуки
        try:
            self.shoot_sound = arcade.load_sound("arcade_resources/assets/sounds/hurt1.wav")
            self.explosion_sound = arcade.load_sound("arcade_resources/assets/sounds/explosion1.wav")
            self.powerup_sound = arcade.load_sound("arcade_resources/assets/sounds/coin1.wav")
            self.level_complete_sound = arcade.load_sound("arcade_resources/assets/sounds/upgrade1.wav")
            self.hit_sound = arcade.load_sound("arcade_resources/assets/sounds/hit1.wav")
        except Exception as e:
            print(f"не удалось загрузить звуки: {e}")

    def on_show_view(self):
        # вызывается при показе view (стартовое окно переключается сюда)
        self.setup()

    def on_draw(self):
        # отрисовка с камерой
        self.clear()

        # проверка что игрок существует
        if self.player_sprite is None:
            return

        # камера - применяем смещение для эффекта тряски при попадании
        if self.camera_shake > 0:
            self.camera_x = random.uniform(-self.camera_shake, self.camera_shake)
            self.camera_y = random.uniform(-self.camera_shake, self.camera_shake)
            self.camera_shake -= 0.5
        else:
            self.camera_x = 0
            self.camera_y = 0

        # спрайты
        self.player_list.draw()
        self.bullet_list.draw()
        self.enemy_bullet_list.draw()
        self.enemy_list.draw()
        self.powerup_list.draw()

        # система частиц
        self.particle_system.draw()

        # отрисовка щита игрока (анимация)
        if self.player_sprite.shield_active:
            arcade.draw_circle_outline(
                self.player_sprite.center_x,
                self.player_sprite.center_y,
                40,
                (0, 255, 255, self.player_sprite.shield_alpha),
                3
            )

        # подсчет и вывод результатов
        arcade.draw_text(f"очки: {self.score}", 10, SCREEN_HEIGHT - 30,
                         arcade.color.WHITE, 20, bold=True)
        arcade.draw_text(f"уровень: {self.current_level}", 10, SCREEN_HEIGHT - 60,
                         arcade.color.WHITE, 20, bold=True)
        arcade.draw_text(f"жизни: {self.player_sprite.lives}", 10, SCREEN_HEIGHT - 90,
                         arcade.color.WHITE, 20, bold=True)
        arcade.draw_text(f"игрок: {self.player_name}", 10, SCREEN_HEIGHT - 120,
                         arcade.color.YELLOW, 16, bold=True)

        # активные улучшения
        if self.player_sprite.shield_active:
            arcade.draw_text("щит", SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30,
                             arcade.color.CYAN, 16, bold=True)
        if self.player_sprite.rapid_fire_active:
            arcade.draw_text("быстрая стрельба", SCREEN_WIDTH - 200, SCREEN_HEIGHT - 60,
                             arcade.color.YELLOW, 16, bold=True)

    def on_update(self, delta_time):
        # обновление логики игры

        # проверка что игрок существует
        if self.player_sprite is None:
            return

        # управление игроком
        if self.left_pressed:
            self.player_sprite.center_x -= self.player_sprite.speed
        if self.right_pressed:
            self.player_sprite.center_x += self.player_sprite.speed

        # обновление спрайтов
        for sprite in self.player_list:
            sprite.on_update(delta_time)
        for sprite in self.bullet_list:
            sprite.on_update(delta_time)
        for sprite in self.enemy_bullet_list:
            sprite.on_update(delta_time)
        for sprite in self.enemy_list:
            sprite.on_update(delta_time)
        for sprite in self.powerup_list:
            sprite.on_update(delta_time)

        # система частиц
        self.particle_system.update(delta_time)

        # логика врагов
        self.update_enemies()

        # collide - проверка столкновений
        self.check_collisions()

        # несколько уровней - переход на следующий уровень
        if len(self.enemy_list) == 0:
            self.level_complete()

        # финальное окно - переход при поражении
        if self.player_sprite.lives <= 0:
            self.game_over()

    def update_enemies(self):
        # обновление поведения врагов

        if len(self.enemy_list) == 0:
            return

        # проверка границ
        move_down = False
        for enemy in self.enemy_list:
            enemy.center_x += enemy.speed * self.enemy_direction

            if (self.enemy_direction == 1 and enemy.right >= SCREEN_WIDTH - 50) or \
                    (self.enemy_direction == -1 and enemy.left <= 50):
                move_down = True

        # опускание вниз и смена направления
        if move_down:
            self.enemy_direction *= -1
            for enemy in self.enemy_list:
                enemy.center_y -= 30
                enemy.speed *= 1.05  # ускорение с каждым рядом

        # стрельба врагов
        for enemy in self.enemy_list:
            if enemy.enemy_type >= 1 and enemy.shoot_cooldown <= 0:
                if random.random() < 0.005 * self.current_level:
                    bullet = Bullet(enemy.center_x, enemy.center_y, -1, is_enemy=True)
                    self.enemy_bullet_list.append(bullet)
                    enemy.shoot_cooldown = random.randint(60, 180)

        # проверка достижения нижней границы
        for enemy in self.enemy_list:
            if enemy.center_y < 100:
                self.player_sprite.lives = 0  # мгновенное поражение

    def check_collisions(self):
        # collide - проверка всех столкновений

        # проверка что игрок существует
        if self.player_sprite is None:
            return

        # пули игрока vs враги
        for bullet in self.bullet_list:
            hit_list = arcade.check_for_collision_with_list(bullet, self.enemy_list)

            if hit_list:
                bullet.remove_from_sprite_lists()

                for enemy in hit_list:
                    enemy.health -= 1

                    if enemy.health <= 0:
                        # подсчет результатов
                        self.score += enemy.points
                        # система частиц - создание взрыва
                        self.create_explosion(enemy.center_x, enemy.center_y)
                        enemy.remove_from_sprite_lists()

                        # звук взрыва
                        if self.explosion_sound:
                            arcade.play_sound(self.explosion_sound, volume=0.3)

                        # случайное появление улучшения
                        if random.random() < 0.15:
                            powerup = PowerUp(enemy.center_x, enemy.center_y)
                            self.powerup_list.append(powerup)
                    else:
                        # звук попадания
                        if self.hit_sound:
                            arcade.play_sound(self.hit_sound, volume=0.2)

        # пули врагов vs игрок
        hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.enemy_bullet_list)

        if hit_list and not self.player_sprite.shield_active:
            for bullet in hit_list:
                bullet.remove_from_sprite_lists()

            self.player_sprite.lives -= 1
            # система частиц - взрыв при попадании
            self.create_explosion(self.player_sprite.center_x, self.player_sprite.center_y)
            # камера - эффект тряски
            self.camera_shake = 5

            # звук
            if self.explosion_sound:
                arcade.play_sound(self.explosion_sound, volume=0.5)
        elif hit_list and self.player_sprite.shield_active:
            # щит поглощает удар
            for bullet in hit_list:
                bullet.remove_from_sprite_lists()
            if self.hit_sound:
                arcade.play_sound(self.hit_sound, volume=0.3)

        # игрок vs улучшения
        hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.powerup_list)

        for powerup in hit_list:
            self.apply_powerup(powerup.powerup_type)
            powerup.remove_from_sprite_lists()

            # звук подбора улучшения
            if self.powerup_sound:
                arcade.play_sound(self.powerup_sound, volume=0.5)

    def apply_powerup(self, powerup_type):
        # применение улучшения

        if powerup_type == PowerUpType.SHIELD:
            self.player_sprite.shield_active = True
            self.player_sprite.powerup_timer = 300  # 5 секунд
        elif powerup_type == PowerUpType.RAPID_FIRE:
            self.player_sprite.rapid_fire_active = True
            self.player_sprite.powerup_timer = 300
        elif powerup_type == PowerUpType.EXTRA_LIFE:
            self.player_sprite.lives += 1

    def create_explosion(self, x, y):
        # система частиц - создание эффекта взрыва
        self.particle_system.emit(x, y, 30)

    def shoot_bullet(self):
        # стрельба игрока

        # проверка что игрок существует
        if self.player_sprite is None:
            return

        cooldown = 10 if not self.player_sprite.rapid_fire_active else 3

        if self.player_sprite.shoot_cooldown <= 0:
            bullet = Bullet(self.player_sprite.center_x, self.player_sprite.center_y + 20)
            self.bullet_list.append(bullet)
            self.player_sprite.shoot_cooldown = cooldown

            # звук стрельбы
            if self.shoot_sound:
                arcade.play_sound(self.shoot_sound, volume=0.2)

    def level_complete(self):
        # несколько уровней - завершение уровня и переход на следующий

        self.current_level += 1
        self.level = Level(self.current_level)
        self.enemy_list = self.level.spawn_enemies()
        self.enemy_direction = 1

        # звук завершения уровня
        if self.level_complete_sound:
            arcade.play_sound(self.level_complete_sound)

    def game_over(self):
        # финальное окно - окончание игры

        # сохранение результатов во все форматы
        self.save_score_all_formats()

        game_over_view = GameOverView(
            self.score,
            self.current_level,
            self.player_sprite.lives if self.player_sprite else 0,
            self.player_name
        )
        self.window.show_view(game_over_view)

    def save_score_all_formats(self):
        # хранение данных - сохранение результата во все форматы

        lives = self.player_sprite.lives if self.player_sprite else 0

        # сохранение в sqlite базу данных
        try:
            success = self.db_manager.save_score(self.player_name, self.score,
                                                 self.current_level, lives)
            if success:
                print("успешно сохранено в бд")
            else:
                print("ошибка сохранения в бд")
        except Exception as e:
            print(f"ошибка при вызове сохранения в бд: {e}")

        # сохранение в csv файл
        file_exists = os.path.isfile('highscores.csv')
        try:
            with open('highscores.csv', 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Player', 'Score', 'Level', 'Lives', 'Date'])
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([self.player_name, self.score, self.current_level,
                                 lives, timestamp])
            print(f"результат сохранен в csv: {self.player_name}, {self.score}")
        except Exception as e:
            print(f"ошибка сохранения в csv: {e}")

        # сохранение в txt файл
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open('game_results.txt', 'a', encoding='utf-8') as f:
                f.write(f"дата: {timestamp}\n")
                f.write(f"игрок: {self.player_name}\n")
                f.write(f"очки: {self.score}\n")
                f.write(f"уровень: {self.current_level}\n")
                f.write(f"жизни: {lives}\n")
                f.write("-" * 40 + "\n\n")
            print(f"результат сохранен в txt: {self.player_name}, {self.score}")
        except Exception as e:
            print(f"ошибка сохранения в txt: {e}")

    def on_key_press(self, key, modifiers):
        # обработка нажатий клавиш
        if key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.D:
            self.right_pressed = True

    def on_key_release(self, key, modifiers):
        # обработка отпускания клавиш
        if key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.D:
            self.right_pressed = False

    def on_mouse_press(self, x, y, button, modifiers):
        # обработка нажатий мыши
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.shoot_bullet()


class MenuView(arcade.View):
    # стартовое окно - меню игры

    def __init__(self):
        super().__init__()
        self.player_name = "Player"
        self.caps_lock = False  # режим caps lock
        self.shift_pressed = False  # нажат ли shift

    def on_show_view(self):
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        self.clear()

        # заголовок
        arcade.draw_text("лицей invaders", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
                         arcade.color.GREEN, font_size=50, anchor_x="center", bold=True)

        # текущее имя игрока
        arcade.draw_text(f"имя игрока: {self.player_name}", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 160,
                         arcade.color.YELLOW, font_size=24, anchor_x="center", bold=True)

        # инструкции по вводу имени
        instructions = []
        instructions.append("используйте клавиши для ввода имени:")
        instructions.append("a-z - буквы, 0-9 - цифры, space - пробел")
        instructions.append("backspace - удалить, caps lock/c - регистр")
        instructions.append("shift - временный регистр")

        y_pos = SCREEN_HEIGHT - 210
        for i, text in enumerate(instructions):
            arcade.draw_text(text, SCREEN_WIDTH // 2, y_pos,
                             arcade.color.LIGHT_GRAY, font_size=16, anchor_x="center")
            y_pos -= 30

        # режим caps lock
        caps_status = "вкл" if self.caps_lock else "выкл"
        caps_color = arcade.color.GREEN if self.caps_lock else arcade.color.RED
        arcade.draw_text(f"caps lock: {caps_status}", SCREEN_WIDTH // 2, y_pos,
                         caps_color, font_size=16, anchor_x="center", bold=True)
        y_pos -= 40

        # инструкции управления в игре
        arcade.draw_text("управление в игре:", SCREEN_WIDTH // 2, y_pos,
                         arcade.color.YELLOW, font_size=24, anchor_x="center", bold=True)
        y_pos -= 40

        arcade.draw_text("a/d - движение влево/вправо", SCREEN_WIDTH // 2, y_pos,
                         arcade.color.WHITE, font_size=18, anchor_x="center")
        y_pos -= 40

        arcade.draw_text("лкм - стрельба", SCREEN_WIDTH // 2, y_pos,
                         arcade.color.WHITE, font_size=18, anchor_x="center")
        y_pos -= 50

        # типы улучшений
        arcade.draw_text("улучшения:", SCREEN_WIDTH // 2, y_pos,
                         arcade.color.CYAN, font_size=20, anchor_x="center", bold=True)
        y_pos -= 40

        arcade.draw_text("⭐ щит (временная защита)", SCREEN_WIDTH // 2, y_pos,
                         arcade.color.WHITE, font_size=16, anchor_x="center")
        y_pos -= 30

        arcade.draw_text("💎 быстрая стрельба", SCREEN_WIDTH // 2, y_pos,
                         arcade.color.WHITE, font_size=16, anchor_x="center")
        y_pos -= 30

        arcade.draw_text("🪙 дополнительная жизнь", SCREEN_WIDTH // 2, y_pos,
                         arcade.color.WHITE, font_size=16, anchor_x="center")
        y_pos -= 50

        # кнопки управления в меню
        arcade.draw_text("нажмите enter для начала игры", SCREEN_WIDTH // 2, y_pos,
                         arcade.color.YELLOW, font_size=24, anchor_x="center", bold=True)

    def on_key_press(self, key, modifiers):
        # отслеживание shift
        if key == arcade.key.LSHIFT or key == arcade.key.RSHIFT:
            self.shift_pressed = True

        # управление в меню - изменение имени
        if key == arcade.key.BACKSPACE:
            if len(self.player_name) > 0:
                self.player_name = self.player_name[:-1]

        elif key == arcade.key.ENTER:
            # запуск игры с текущим именем
            game_view = GameView()
            game_view.player_name = self.player_name
            self.window.show_view(game_view)

        # переключение caps lock
        elif key == arcade.key.CAPSLOCK or key == arcade.key.C:
            self.caps_lock = not self.caps_lock

        # пробел
        elif key == arcade.key.SPACE:
            if len(self.player_name) < 20:  # ограничение длины имени
                self.player_name += " "

        # цифры 0-9 (верхний ряд клавиатуры)
        elif arcade.key.KEY_0 <= key <= arcade.key.KEY_9:
            if len(self.player_name) < 20:
                # получаем цифру из кода клавиши
                # KEY_0 = 48, KEY_1 = 49, и т.д.
                digit = chr(key)
                self.player_name += digit

        # цифры на цифровой клавиатуре (numpad)
        elif arcade.key.NUM_0 <= key <= arcade.key.NUM_9:
            if len(self.player_name) < 20:
                # преобразуем код клавиши в цифру
                # NUM_0 = 256, NUM_1 = 257, и т.д.
                digit = str(key - arcade.key.NUM_0)
                self.player_name += digit

        # обработка ввода букв для имени (a-z)
        elif arcade.key.A <= key <= arcade.key.Z:
            if len(self.player_name) < 20:
                char = chr(key)

                # логика определения регистра
                if self.shift_pressed:
                    # shift нажат - инвертируем регистр
                    if self.caps_lock:
                        self.player_name += char.lower()
                    else:
                        self.player_name += char.upper()
                else:
                    # shift не нажат
                    if self.caps_lock:
                        self.player_name += char.upper()
                    else:
                        self.player_name += char.lower()

    def on_key_release(self, key, modifiers):
        # отслеживание отпускания shift
        if key == arcade.key.LSHIFT or key == arcade.key.RSHIFT:
            self.shift_pressed = False


class GameOverView(arcade.View):
    # финальное окно - экран окончания игры с результатами

    def __init__(self, score, level, lives, player_name="Player"):
        super().__init__()
        self.score = score
        self.level = level
        self.lives = lives
        self.player_name = player_name

    def on_show_view(self):
        arcade.set_background_color(arcade.color.DARK_RED)

    def on_draw(self):
        self.clear()

        # заголовок
        arcade.draw_text("игра окончена", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
                         arcade.color.WHITE, font_size=50, anchor_x="center", bold=True)

        # итоговые результаты
        arcade.draw_text("итоговые результаты:", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 180,
                         arcade.color.YELLOW, font_size=28, anchor_x="center", bold=True)

        arcade.draw_text(f"игрок: {self.player_name}", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 240,
                         arcade.color.YELLOW, font_size=26, anchor_x="center")

        arcade.draw_text(f"очки: {self.score}", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 290,
                         arcade.color.WHITE, font_size=32, anchor_x="center")

        arcade.draw_text(f"достигнут уровень: {self.level}", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 340,
                         arcade.color.WHITE, font_size=28, anchor_x="center")

        arcade.draw_text(f"оставшиеся жизни: {self.lives}", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 390,
                         arcade.color.WHITE, font_size=28, anchor_x="center")

        # оценка производительности
        if self.score > 500:
            performance = "отличная игра!"
            color = arcade.color.GOLD
        elif self.score > 300:
            performance = "хорошая игра!"
            color = arcade.color.SILVER
        elif self.score > 100:
            performance = "неплохо!"
            color = arcade.color.BRONZE
        else:
            performance = "попробуйте еще!"
            color = arcade.color.GRAY

        arcade.draw_text(performance, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 450,
                         color, font_size=24, anchor_x="center", bold=True)

        # информация о сохранении
        arcade.draw_text("результат сохранен в базу данных и файлы",
                         SCREEN_WIDTH // 2, SCREEN_HEIGHT - 510,
                         arcade.color.LIGHT_GREEN, font_size=18, anchor_x="center")

        # кнопки управления
        arcade.draw_text("нажмите r для новой игры", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 570,
                         arcade.color.GREEN, font_size=24, anchor_x="center", bold=True)

        arcade.draw_text("нажмите esc для выхода в меню", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 620,
                         arcade.color.GRAY, font_size=20, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.R:
            # рестарт игры
            game_view = GameView()
            game_view.player_name = self.player_name
            self.window.show_view(game_view)
        elif key == arcade.key.ESCAPE:
            # возврат в меню
            menu_view = MenuView()
            self.window.show_view(menu_view)


def main():
    # главная функция запуска игры

    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    menu_view = MenuView()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
