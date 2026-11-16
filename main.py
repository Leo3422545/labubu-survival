import argparse
import asyncio
import queue
import random
import threading
from pathlib import Path
import pygame

W, H = 1100, 700
EVENTS = queue.Queue(maxsize=5000)
ROOT = Path(__file__).resolve().parent

def emit(*args):
    try:
        EVENTS.put_nowait(args)
    except queue.Full:
        pass

def live_worker(username):
    try:
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import ConnectEvent, DisconnectEvent, GiftEvent, CommentEvent, LikeEvent, FollowEvent
        client = TikTokLiveClient(unique_id=username.lstrip("@"))

        @client.on(ConnectEvent)
        async def connected(event):
            emit("status", "CONECTADO")

        @client.on(DisconnectEvent)
        async def disconnected(event):
            emit("status", "DESCONECTADO")

        @client.on(CommentEvent)
        async def comment(event):
            emit("comment", getattr(event.user, "nickname", "Viewer"), str(event.comment).lower().strip())

        @client.on(LikeEvent)
        async def like(event):
            emit("like", max(1, int(getattr(event, "count", 1) or 1)))

        @client.on(FollowEvent)
        async def follow(event):
            emit("follow", getattr(event.user, "nickname", "Viewer"))

        @client.on(GiftEvent)
        async def gift(event):
            if getattr(event, "streaking", False):
                return
            emit("gift", getattr(event.user, "nickname", "Viewer"), str(getattr(event.gift, "name", "presente")), max(1, int(getattr(event, "repeat_count", 1) or 1)))

        asyncio.run(client.start())
    except Exception as exc:
        emit("status", "Erro TikTok: " + str(exc)[:80])

class Game:
    def __init__(self, username):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Labubu Survival - TikTokLive")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20)
        self.big = pygame.font.SysFont("arial", 48, bold=True)
        self.sprites = {}
        for name in ("front", "back", "left", "right"):
            path = ROOT / "assets" / ("labubu_" + name + ".png")
            if path.exists():
                image = pygame.image.load(str(path)).convert_alpha()
                self.sprites[name] = pygame.transform.smoothscale(image, (105, 105))
        self.status = "OFFLINE"
        self.messages = []
        self.running = True
        self.reset()
        if username:
            threading.Thread(target=live_worker, args=(username,), daemon=True).start()

    def reset(self):
        self.player = pygame.Vector2(W / 2, H / 2)
        self.hp, self.score, self.elapsed, self.likes = 100, 0, 0, 0
        self.enemies, self.guards = [], []
        self.spawn_cd = self.attack_cd = self.hurt_cd = self.dash_cd = 0
        self.face = "front"
        self.live_move = pygame.Vector2()
        self.live_move_cd = 0
        self.over = self.paused = False

    def note(self, message):
        self.messages.append([str(message)[:80], 5])
        self.messages = self.messages[-7:]
        print("[JOGO]", message)

    def spawn(self, count=1):
        for _ in range(min(25, count)):
            side = random.randrange(4)
            x = random.randint(0, W) if side % 2 == 0 else (-25 if side == 1 else W + 25)
            y = (-25 if side == 0 else H + 25) if side % 2 == 0 else random.randint(0, H)
            self.enemies.append({"p": pygame.Vector2(x, y), "speed": random.uniform(65, 110), "hp": 1})

    def blast(self, radius=230, damage=2):
        for enemy in self.enemies[:]:
            if self.player.distance_to(enemy["p"]) < radius:
                enemy["hp"] -= damage
                if enemy["hp"] <= 0:
                    self.enemies.remove(enemy)
                    self.score += 10
        self.note("Explosao!")

    def handle(self, event):
        kind, *values = event
        if kind == "status":
            self.status = values[0]
            self.note(self.status)
        elif kind == "like":
            self.likes += values[0]
            while self.likes >= 25:
                self.likes -= 25
                self.blast(180, 1)
        elif kind == "follow":
            self.guards.append({"p": self.player.copy(), "ttl": 15, "cd": 0})
            self.note(values[0] + " virou guardiao!")
        elif kind == "comment":
            user, command = values
            directions = {"cima": (0, -1), "baixo": (0, 1), "esquerda": (-1, 0), "direita": (1, 0)}
            if command in directions:
                self.live_move = pygame.Vector2(directions[command])
                self.live_move_cd = 1.5
            elif command == "bomba":
                self.blast()
            elif command == "curar":
                self.hp = min(100, self.hp + 20)
                self.note(user + " curou Labubu")
            elif command == "escudo":
                self.hurt_cd = max(self.hurt_cd, 5)
                self.note(user + " ativou escudo")
            elif command == "monstro":
                self.spawn(3)
        elif kind == "gift":
            user, name, amount = values
            amount = min(amount, 20)
            lower = name.lower()
            if "rose" in lower or "rosa" in lower:
                self.hp = min(100, self.hp + 3 * amount)
                self.note(user + " enviou " + name + " (cura)")
            elif any(word in lower for word in ("lion", "leão", "universe", "universo")):
                self.blast(400, 5)
                self.hurt_cd = max(self.hurt_cd, 5)
            else:
                self.spawn(min(15, amount + 2))
                self.note(user + " enviou " + name)

    def update(self, dt):
        if self.paused or self.over:
            return
        self.elapsed += dt
        self.spawn_cd -= dt
        self.attack_cd -= dt
        self.hurt_cd = max(0, self.hurt_cd - dt)
        self.dash_cd = max(0, self.dash_cd - dt)
        self.live_move_cd = max(0, self.live_move_cd - dt)
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        )
        if self.live_move_cd > 0:
            move += self.live_move
        if move.length_squared():
            move = move.normalize()
            self.player += move * 265 * dt
            self.face = ("right" if move.x > 0 else "left") if abs(move.x) > abs(move.y) else ("front" if move.y > 0 else "back")
        self.player.x = max(35, min(W - 35, self.player.x))
        self.player.y = max(45, min(H - 35, self.player.y))
        if self.spawn_cd <= 0:
            self.spawn(1 + min(4, int(self.elapsed // 85)))
            self.spawn_cd = max(.3, 1.45 - self.elapsed * .003)
        if self.attack_cd <= 0 and self.enemies:
            enemy = min(self.enemies, key=lambda e: self.player.distance_to(e["p"]))
            if self.player.distance_to(enemy["p"]) < 125:
                enemy["hp"] -= 1
                self.attack_cd = .35
                if enemy["hp"] <= 0:
                    self.enemies.remove(enemy)
                    self.score += 10
        for enemy in self.enemies[:]:
            delta = self.player - enemy["p"]
            if delta.length_squared():
                enemy["p"] += delta.normalize() * enemy["speed"] * dt
            if self.player.distance_to(enemy["p"]) < 37:
                if self.hurt_cd <= 0:
                    self.hp -= 10
                    self.hurt_cd = .7
                self.enemies.remove(enemy)
                if self.hp <= 0:
                    self.hp = 0
                    self.over = True
        for guard in self.guards[:]:
            guard["ttl"] -= dt
            guard["cd"] -= dt
            if guard["ttl"] <= 0:
                self.guards.remove(guard)
                continue
            if self.enemies:
                enemy = min(self.enemies, key=lambda e: guard["p"].distance_to(e["p"]))
                direction = enemy["p"] - guard["p"]
                if direction.length_squared():
                    guard["p"] += direction.normalize() * 180 * dt
                if direction.length() < 35 and guard["cd"] <= 0:
                    enemy["hp"] -= 1
                    guard["cd"] = .5
                    if enemy["hp"] <= 0:
                        self.enemies.remove(enemy)
                        self.score += 15
        for message in self.messages[:]:
            message[1] -= dt
            if message[1] <= 0:
                self.messages.remove(message)

    def draw(self):
        self.screen.fill((13, 18, 30))
        for x in range(0, W, 50):
            pygame.draw.line(self.screen, (24, 32, 48), (x, 0), (x, H))
        for y in range(0, H, 50):
            pygame.draw.line(self.screen, (24, 32, 48), (0, y), (W, y))
        for enemy in self.enemies:
            p = enemy["p"]
            pygame.draw.circle(self.screen, (240, 78, 96), (int(p.x), int(p.y)), 15)
        for guard in self.guards:
            pygame.draw.circle(self.screen, (180, 120, 255), (int(guard["p"].x), int(guard["p"].y)), 13)
        img = self.sprites.get(self.face)
        if img:
            self.screen.blit(img, img.get_rect(center=(int(self.player.x), int(self.player.y - 14))))
        else:
            pygame.draw.circle(self.screen, (90, 170, 255), (int(self.player.x), int(self.player.y)), 20)
        if self.hurt_cd > 0:
            pygame.draw.circle(self.screen, (130, 200, 255), (int(self.player.x), int(self.player.y)), 42, 2)
        pygame.draw.rect(self.screen, (55, 60, 70), (20, 18, 230, 20), border_radius=6)
        pygame.draw.rect(self.screen, (70, 215, 125) if self.hp > 30 else (240, 70, 80), (20, 18, int(230 * self.hp / 100), 20), border_radius=6)
        def label(text, x, y, color=(235, 240, 250)):
            self.screen.blit(self.font.render(str(text), True, color), (x, y))
        label("LABUBU HP: " + str(self.hp), 20, 46)
        label("PONTOS: " + str(self.score), 20, 76)
        label("TEMPO: " + str(int(self.elapsed)) + "s", 20, 106)
        label("LIKES: " + str(self.likes) + "/25", 20, 136)
        label("GUARDIOES: " + str(len(self.guards)), 20, 166)
        label("TIKTOK: " + self.status[:35], W - 350, 20)
        label("Chat: bomba / curar / escudo / monstro", W - 350, 50)
        y = H - 30
        for message, _ in reversed(self.messages):
            label(message, 20, y)
            y -= 25
        if self.over or self.paused:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 175))
            self.screen.blit(veil, (0, 0))
            title = self.big.render("FIM DE JOGO" if self.over else "PAUSADO", True, (255, 255, 255))
            self.screen.blit(title, title.get_rect(center=(W // 2, H // 2)))
            if self.over:
                label("ENTER para reiniciar", W // 2 - 100, H // 2 + 45)
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(.05, self.clock.tick(60) / 1000)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                    elif event.key == pygame.K_RETURN and self.over:
                        self.reset()
                    elif event.key == pygame.K_SPACE and self.dash_cd <= 0 and not self.over and not self.paused:
                        keys = pygame.key.get_pressed()
                        direction = pygame.Vector2(int(keys[pygame.K_d]) - int(keys[pygame.K_a]), int(keys[pygame.K_s]) - int(keys[pygame.K_w]))
                        if not direction.length_squared():
                            direction = pygame.Vector2(0, -1)
                        self.player += direction.normalize() * 115
                        self.player.x = max(35, min(W - 35, self.player.x))
                        self.player.y = max(45, min(H - 35, self.player.y))
                        self.dash_cd = 2
                        self.hurt_cd = max(self.hurt_cd, .4)
            for _ in range(100):
                try:
                    self.handle(EVENTS.get_nowait())
                except queue.Empty:
                    break
            self.update(dt)
            self.draw()
        pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="")
    args = parser.parse_args()
    Game(args.username).run()
