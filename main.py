import pygame, random, math, os, sys

# ---------- Config ----------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.9
GROUND_Y = SCREEN_HEIGHT - 80

PLAYER_SIZE = (48, 64)
PLAYER_SPEED = 5
PLAYER_JUMP_V = -15
SLASH_COOLDOWN = 0.45
SLASH_DURATION = 0.12
SLASH_RANGE = 60
SLASH_WIDTH = 30
DASH_COOLDOWN = 1.5
DASH_SPEED = 15
DASH_DURATION = 0.15

ENEMY_SPAWN_DISTANCE = 400
MAX_ACTIVE_ENEMIES = 12

ASSET_DIR = "assets"
os.makedirs(ASSET_DIR, exist_ok=True)

# ---------- Helpers ----------
def load_image(name, fallback_size=(40,40), col=(255,0,255)):
    path = os.path.join(ASSET_DIR, name)
    if os.path.exists(path):
        return pygame.image.load(path).convert_alpha()
    surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
    surf.fill(col)
    return surf

# ---------- Platforms ----------
class Platform:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = (100, 100, 100)
        self.coin = None

# ---------- Coins ----------
class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.color = (255, 215, 0)
        self.collected = False

    def draw(self, surface, camera_x):
        if not self.collected:
            pygame.draw.circle(surface, self.color, (self.rect.centerx - camera_x, self.rect.centery), self.rect.width//2)

# ---------- Entities ----------
class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.rect = pygame.Rect(x, y, w, h)
        self.vx = 0
        self.vy = 0
        self.on_ground = False

    def update_physics(self, platforms=[]):
        self.vy += GRAVITY
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)

        # Ground collision
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vy = 0
            self.on_ground = True
        else:
            self.on_ground = False

        # Platform collisions
        for plat in platforms:
            if self.vy >= 0 and self.rect.colliderect(plat.rect):
                if self.rect.bottom - self.vy <= plat.rect.top:
                    self.rect.bottom = plat.rect.top
                    self.vy = 0
                    self.on_ground = True

# ---------- Player ----------
class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, *PLAYER_SIZE)
        self.speed = PLAYER_SPEED
        self.color = (30, 200, 220)
        self.health = 10
        self.facing = 1
        self.slash_cooldown = 0.0
        self.slash_timer = 0.0
        self.dash_cooldown = 0.0
        self.dash_timer = 0.0
        self.score = 0
        self.sprite = load_image("player.png", fallback_size=PLAYER_SIZE, col=self.color)

    def move(self, dx):
        if self.dash_timer <=0: self.vx = dx * self.speed
        if dx != 0: self.facing = 1 if dx > 0 else -1

    def jump(self):
        if self.on_ground:
            self.vy = PLAYER_JUMP_V
            self.on_ground = False

    def slash(self):
        if self.slash_cooldown <= 0:
            self.slash_timer = SLASH_DURATION
            self.slash_cooldown = SLASH_COOLDOWN

    def dash(self):
        if self.dash_cooldown <=0 and self.on_ground:
            self.dash_timer = DASH_DURATION
            self.dash_cooldown = DASH_COOLDOWN
            self.vx = self.facing*DASH_SPEED

    def update(self, dt):
        if self.slash_cooldown >0: self.slash_cooldown -= dt
        if self.slash_timer >0: self.slash_timer -= dt
        if self.dash_cooldown >0: self.dash_cooldown -= dt
        if self.dash_timer >0:
            self.dash_timer -= dt
            if self.dash_timer <=0: self.vx = 0

    def draw(self, surface, camera_x):
        surface.blit(self.sprite, (self.rect.x - camera_x, self.rect.y))
        if self.slash_timer>0:
            sx = self.rect.centerx + self.facing*(self.rect.width//2)
            sy = self.rect.centery
            r = pygame.Rect(0,0,SLASH_RANGE,SLASH_WIDTH)
            if self.facing<0: r.right = sx - camera_x
            else: r.left = sx - camera_x
            r.centery = sy
            pygame.draw.rect(surface,(255,100,100,150), r, 0)

    def slash_hitbox(self):
        if self.slash_timer <=0: return None
        sx = self.rect.centerx + self.facing*(self.rect.width//2)
        sy = self.rect.centery
        if self.facing>0: return pygame.Rect(sx, sy-SLASH_WIDTH//2, SLASH_RANGE, SLASH_WIDTH)
        else: return pygame.Rect(sx - SLASH_RANGE, sy-SLASH_WIDTH//2, SLASH_RANGE, SLASH_WIDTH)

# ---------- Enemy base ----------
class Enemy(Entity):
    def __init__(self, x, y, w=40, h=40):
        super().__init__(x, y, w, h)
        self.hp = 3
        self.speed = 2
        self.damage = 1
        self.color = (200,50,50)
        self.score_value = 10
        self.sprite = None
        self.dead = False

    def update(self, player, dt):
        self.update_ai(player, dt)
        if self.hp <=0: self.dead = True

    def update_ai(self, player, dt):
        if player.rect.x > self.rect.x: self.vx = self.speed
        else: self.vx = -self.speed

    def on_damage(self, amount):
        self.hp -= amount

    def draw(self, surface, camera_x):
        if self.sprite: surface.blit(self.sprite, (self.rect.x - camera_x, self.rect.y))
        else: pygame.draw.rect(surface, self.color, pygame.Rect(self.rect.x-camera_x,self.rect.y,self.rect.width,self.rect.height))

# ---------- Specific Enemies ----------
class Slime(Enemy):
    def __init__(self, x, y):
        super().__init__(x,y,40,28)
        self.hp = 2
        self.speed = 1.2
        self.color = (80,200,80)
        self.score_value = 5
        self.sprite = load_image("slime.png",(40,28),self.color)
        self.jump_cd = 0

    def update_ai(self, player, dt):
        self.vx *=0.9
        self.jump_cd -= dt
        if abs(player.rect.x - self.rect.x)<250 and self.on_ground and self.jump_cd<=0:
            dir = 1 if player.rect.x>self.rect.x else -1
            self.vx = dir*self.speed*2
            self.vy = -9
            self.jump_cd=random.uniform(0.6,1.6)

class Bat(Enemy):
    def __init__(self, x, y):
        super().__init__(x,y,36,28)
        self.hp = 1
        self.speed = 2.4
        self.color = (150,150,255)
        self.fly_range = 60
        self.base_y = y
        self.sprite = load_image("bat.png",(36,28),self.color)
        self.score_value = 8

    def update_ai(self, player, dt):
        dx = player.rect.x - self.rect.x
        self.vx = math.copysign(self.speed, dx) if abs(dx)>10 else 0
        self.rect.y = self.base_y + math.sin(pygame.time.get_ticks()/250.0 + self.rect.x)*self.fly_range

    def update_physics(self, platforms=[]):
        self.rect.x += int(self.vx)

class Archer(Enemy):
    def __init__(self, x, y):
        super().__init__(x,y,40,60)
        self.hp=4
        self.speed=0.6
        self.color=(200,160,80)
        self.sprite = load_image("archer.png",(40,60),self.color)
        self.shoot_cd=random.uniform(1.0,2.5)
        self.score_value=20

    def update_ai(self, player, dt):
        dx = player.rect.x - self.rect.x
        self.vx = 0
        self.shoot_cd -= dt
        if self.shoot_cd<=0:
            self.shoot_cd = random.uniform(1.0,2.5)
            vx = math.copysign(6, dx)
            Game.instance.spawn_projectile(self.rect.centerx, self.rect.centery, vx)

class Minotaur(Enemy):
    def __init__(self, x, y):
        super().__init__(x,y,80,80)
        self.hp = 25
        self.speed = 1.2
        self.damage = 2
        self.color = (180,60,60)
        self.sprite = load_image("minotaur.png",(80,80),self.color)
        self.score_value = 200
        self.charge_cd = 0

    def update_ai(self, player, dt):
        dx = player.rect.x - self.rect.x
        if abs(dx)<300 and self.charge_cd<=0:
            self.vx = math.copysign(self.speed*7, dx)
            self.charge_cd = 2.0
        else:
            self.vx = math.copysign(self.speed, dx)
            self.charge_cd -= dt

# ---------- Projectiles ----------
class Projectile(Entity):
    def __init__(self,x,y,vx,owner=None):
        super().__init__(x,y,10,6)
        self.vx = vx
        self.owner = owner
        self.lifespan = 4.0
        self.damage = 1
        self.color = (255,200,60)

    def update(self, dt):
        self.lifespan -= dt
        self.rect.x += int(self.vx)
        if self.lifespan <=0: return False
        if self.rect.right<Game.instance.camera_x-200 or self.rect.left>Game.instance.camera_x+SCREEN_WIDTH+200:
            return False
        return True

    def draw(self, surface, camera_x):
        pygame.draw.rect(surface, self.color, pygame.Rect(self.rect.x-camera_x,self.rect.y,self.rect.width,self.rect.height))

# ---------- Game ----------
class Game:
    instance = None
    def __init__(self, screen):
        Game.instance = self
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.player = Player(120, GROUND_Y-PLAYER_SIZE[1])
        self.enemies=[]
        self.projectiles=[]
        self.platforms=[]
        self.camera_x = 0
        self.world_time = 0.0
        self.last_spawn_x=0
        self.font = pygame.font.SysFont("consolas",20)
        self.bg_layers = [
            {"speed":0.15,"color":(20,20,40),"rects":self._make_hills(0.15)},
            {"speed":0.4,"color":(30,30,70),"rects":self._make_hills(0.4)},
            {"speed":0.8,"color":(60,60,130),"rects":self._make_hills(0.8)}
        ]
        self.game_over=False

    def _make_hills(self,density):
        rects=[]
        for i in range(200):
            x = i*int(300/density)+random.randint(-60,60)
            h = random.randint(40,140)
            y = GROUND_Y - h - random.randint(0,40)
            w = random.randint(200,400)
            rects.append((x,y,w,h))
        return rects

    def spawn_enemy(self,enemy_cls,x,y):
        e = enemy_cls(x,y)
        self.enemies.append(e)
        return e

    def spawn_projectile(self,x,y,vx):
        self.projectiles.append(Projectile(x,y,vx))

    def procedural_spawn(self):
        px = self.player.rect.x
        # Minotaur spawn more often
        if px>800 and not hasattr(self,"minotaur_spawned"):
            self.minotaur_spawned=True
            spawn_x = px + SCREEN_WIDTH//2
            self.spawn_enemy(Minotaur, spawn_x, GROUND_Y-80)
        if px-self.last_spawn_x>ENEMY_SPAWN_DISTANCE and len(self.enemies)<MAX_ACTIVE_ENEMIES:
            self.last_spawn_x=px
            difficulty = max(1,int(px/800))
            pool=[]
            pool += [Slime]*(5+difficulty*2)
            pool += [Bat]*(3+difficulty)
            pool += [Archer]*(1+difficulty//2)
            cls = random.choice(pool)
            spawn_x = px + SCREEN_WIDTH + random.randint(100,400)
            spawn_y = GROUND_Y - 60
            if cls==Bat: spawn_y = GROUND_Y - random.randint(120,220)
            self.spawn_enemy(cls, spawn_x, spawn_y)

    def procedural_platforms(self):
        px = self.player.rect.x
        if not hasattr(self,"last_platform_x"): 
            self.last_platform_x = 0
            self.last_platform_y = GROUND_Y - 50
        while px + SCREEN_WIDTH > self.last_platform_x + 200:
            w = random.randint(80,160)
            h = 20
            max_up = max(self.last_platform_y - 120, 100)
            max_down = min(self.last_platform_y + 80, GROUND_Y - 50)
            y = random.randint(max_up, max_down)
            x = self.last_platform_x + random.randint(200, 300)
            plat = Platform(x, y, w, h)
            coin = Coin(x + w//2 - 10, y - 20)
            plat.coin = coin
            self.platforms.append(plat)
            self.last_platform_x = x
            self.last_platform_y = y

    def update(self, dt):
        if self.game_over: return
        self.world_time += dt
        keys = pygame.key.get_pressed()
        dx = 0
        if keys[pygame.K_LEFT]: dx=-1
        if keys[pygame.K_RIGHT]: dx=1
        self.player.move(dx)
        if keys[pygame.K_SPACE]: self.player.jump()
        if keys[pygame.K_z]: self.player.slash()
        if keys[pygame.K_x]: self.player.dash()

        self.player.update(dt)
        self.player.update_physics(self.platforms)

        # Enemies
        for e in list(self.enemies):
            e.update(self.player, dt)
            e.update_physics(self.platforms)
            # Slash hit
            hitbox = self.player.slash_hitbox()
            if hitbox and e.rect.colliderect(hitbox):
                e.on_damage(1)
                self.player.score += e.score_value//2
            # Enemy collision with player
            if self.player.rect.colliderect(e.rect):
                self.player.health -= e.damage * dt * 10  # scaled by dt
            if e.dead: self.enemies.remove(e)

        # Projectiles
        for p in list(self.projectiles):
            alive = p.update(dt)
            if alive and p.rect.colliderect(self.player.rect):
                self.player.health -= 1
                self.projectiles.remove(p)
            elif not alive:
                self.projectiles.remove(p)

        # Coins
        for plat in self.platforms:
            if plat.coin and not plat.coin.collected:
                if self.player.rect.colliderect(plat.coin.rect):
                    plat.coin.collected = True
                    self.player.score +=10

        # Procedural
        self.procedural_spawn()
        self.procedural_platforms()

        self.camera_x = self.player.rect.x - SCREEN_WIDTH//3

        # Check for death
        if self.player.health <=0:
            self.game_over=True

    def draw_background(self):
        self.screen.fill((20,20,40))
        for layer in self.bg_layers:
            for x,y,w,h in layer["rects"]:
                pygame.draw.rect(self.screen,layer["color"],pygame.Rect(x-self.camera_x*layer["speed"],y,w,h))
        # Infinite ground
        ground_width = max(SCREEN_WIDTH*10, self.player.rect.x + SCREEN_WIDTH)
        pygame.draw.rect(self.screen,(50,200,70),pygame.Rect(0-self.camera_x,GROUND_Y,ground_width,SCREEN_HEIGHT-GROUND_Y))
        # Platforms
        for plat in self.platforms:
            pygame.draw.rect(self.screen, plat.color, pygame.Rect(plat.rect.x - self.camera_x, plat.rect.y, plat.rect.width, plat.rect.height))
            if plat.coin: plat.coin.draw(self.screen, self.camera_x)

    def draw(self):
        self.draw_background()
        self.player.draw(self.screen,self.camera_x)
        for e in self.enemies: e.draw(self.screen,self.camera_x)
        for p in self.projectiles: p.draw(self.screen,self.camera_x)
        # HUD
        txt = f"HP:{int(self.player.health)} Score:{self.player.score} Dist:{self.player.rect.x//10}"
        surf = self.font.render(txt,True,(255,255,255))
        self.screen.blit(surf,(10,10))
        # Game Over
        if self.game_over:
            go_surf = pygame.font.SysFont("consolas",60).render("GAME OVER",True,(255,0,0))
            self.screen.blit(go_surf,(SCREEN_WIDTH//2 - go_surf.get_width()//2, SCREEN_HEIGHT//2 - 50))

    def run(self):
        running=True
        while running:
            dt = self.clock.tick(FPS)/1000
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: running=False
                if ev.type==pygame.KEYDOWN and self.game_over:
                    if ev.key==pygame.K_r:
                        self.__init__(self.screen)  # restart game
            self.update(dt)
            self.draw()
            pygame.display.flip()

# ---------- Run ----------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
pygame.display.set_caption("Procedural Platformer Fixed With Death")
Game(screen).run()
pygame.quit()
sys.exit()
