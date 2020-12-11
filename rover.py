import random
import pyxel

GRAVITY = 1

FPS = 30

spd_miltiplier = 1

ENEMY_PATTERN = [[], ["l"], ["l", "lf"], ["l", "l", "l", "l", "l", "r"], ["l", "l", "lf", "r"], ["lf", "rf"]]

ENEMY_FREQ = [-1, 2, 1.5, 1, 0.7, 0.7]

LEVELUP_TIME = [0.1, 25, 50, 90, 135]

# CHを指定しなくても音を鳴らせる関数
def play_sound(snd):
    is_played = False
    for i in range(4):
        if pyxel.play_pos(i) == -1:
            pyxel.play(i, snd)
            is_played = True
            break
    return is_played

class Player:
    def __init__(self):
        self.x = 112
        self.y = 84
        self.vy = 0
        self.face_right = True
        self.alive = True
        self.onfloor = True
        self.can_jump = False
    
    def update_player(self):
        # Aキーで左に移動 画面外には行けない
        if pyxel.btn(pyxel.KEY_A):
            self.x = max(self.x - 2, 0)
            self.face_right = False # 左を向かせる

        # Dキーで右に移動 画面外には行けない
        if pyxel.btn(pyxel.KEY_D):
            self.x = min(self.x + 2, pyxel.width - 16)
            self.face_right = True # 右を向かせる
        
        # 重力加速度を速度に加算（終端速度6）
        self.vy = min(self.vy + GRAVITY, 6)

        # クリックでジャンプ
        if pyxel.btn(pyxel.MOUSE_LEFT_BUTTON):
            # 接地時
            if self.onfloor and self.can_jump:
                h = max(self.y - pyxel.mouse_y, 8) + 4
                self.vy = - (2 * GRAVITY * h) ** 0.5
                self.onfloor = False
                self.can_jump = False
                play_sound(0)
                play_sound(1)
            # 落下時
            else:
                self.vy = min(self.vy, 1)
        # ボタンを話したらジャンプ可能になる。ボタンを押しっぱなしでジャンプが誤爆する対策
        elif pyxel.btnr(pyxel.MOUSE_LEFT_BUTTON) or pyxel.btnr(pyxel.KEY_F):
            self.can_jump = True
        
        # y方向の移動を反映
        self.y += self.vy

class Enemy:
    def __init__(self, level, h):
        self.to_right = False
        self.is_fast = False
        self.out_of_bound = False
        self.jumped_over = False

        # rが含まれていたら右向き、fが含まれていたら速い
        self.pattern = random.choice(ENEMY_PATTERN[level])
        for char in self.pattern:
            if char == "r": self.to_right = True
            if char == "f": self.is_fast = True

        self.x = -32 if self.to_right else 256
        self.y = 8 + h * 16
        self.speed = 3 if self.is_fast else 2
        self.vx = self.speed if self.to_right else -self.speed

        self.score = 40 if self.is_fast else 25
    
    def update_enemy(self):
        # x座標の更新を反映
        self.x += self.vx

        # 画面外フラグを建てる
        if (
            self.x < -32
            or self.x > pyxel.width + 32
            or self.y < -32
            or self.y > pyxel.height + 32
        ):
            self.out_of_bound = True


class App:
    def __init__(self):
        pyxel.init(240, 135, fps=FPS, caption="Rover", fullscreen=True)

        pyxel.load("assets/assets.pyxres")

        self.game_status = 0 # 0:Title 1:Gameplay 2:Result
        self.hiscore = 0

        pyxel.run(self.update, self.draw)
    
    def game_init(self, hiscore=0):
        self.time = 0
        self.score = 0
        self.level = 0
        self.score_each_level = []
        self.is_gameover = False

        self.last_jumpoversnd = 0
        self.mouse_released = False
        self.time_levelup = -999
        self.time_gameover = -999

        self.p = Player()

        self.floor = (16, 100)
        self.e = []

    def update(self):
        # タイトル画面
        if self.game_status == 0:
            # クリックかFキーで開始
            if pyxel.btn(pyxel.MOUSE_LEFT_BUTTON) or pyxel.btn(pyxel.KEY_F):
                self.game_status = 1
                self.game_init()
                # Fキーで開始するとLEVEL FOURから始まる
                if pyxel.btn(pyxel.KEY_F):
                    self.time = 2690
                    self.level = 3
        
        # ゲームプレイ画面
        elif self.game_status == 1:

            # プレイヤー生存時のみ更新を行う
            if self.p.alive:

                # プレイヤーの更新
                self.p.update_player()
                
                # 敵の更新
                for e in self.e:
                    e.update_enemy()

                    # 飛び越え判定
                    if (
                        not e.jumped_over
                        and e.y > self.p.y 
                        and e.x - 8 < self.p.x 
                        and e.x > self.p.x
                    ):
                        self.score += e.score
                        e.jumped_over = True
                        if self.time - self.last_jumpoversnd >= 2:
                            play_sound(3)
                            self.last_jumpoversnd = self.time

                    # 早いやつは当たり判定がちょっとちっちゃい
                    fast_mod = 1 if e.is_fast else 0

                    # 当たり判定
                    if (
                        e.x + 8 - fast_mod > self.p.x + 6
                        and e.x + fast_mod < self.p.x + 12
                        and e.y + 8 - fast_mod > self.p.y + 6
                        and e.y + fast_mod < self.p.y + 12
                    ):
                        self.gameover()

                    # 画面外に出ていったやつを削除
                    if e.out_of_bound:
                        del e
                
                self.update_floor(*self.floor)

                self.time += 1

                if self.level > 0 and self.time - self.time_levelup > 120 and self.time % (32 // (self.level ** 2)) == 0:
                    self.score += 1
                
                if self.time - self.time_levelup == 60:
                    play_sound(6)
                    play_sound(5)

                
                # 障害物の生成
                if (
                    self.level > 0
                    and self.time - self.time_levelup > 150
                    and (self.level == 5
                        or LEVELUP_TIME[self.level] * FPS - self.time > 90)
                    and self.time % (ENEMY_FREQ[self.level] * FPS) == 0
                ):
                    for h in random.sample(range(8), self.level):
                        if self.level <= 2 and h >= 6:
                            h = 5
                        if h < 6:
                            self.e.append(Enemy(self.level, h))

                #for i, v in enumerate(self.floor):
                #    self.floor[i] = self.update_floor(*v)
                
                # 所定の時間を超えたらレベルアップ
                if self.level < 5 and self.time == LEVELUP_TIME[self.level] * FPS:
                    self.next_level()

                # 落ちたらゲームオーバー
                if self.p.y > pyxel.height:
                    self.gameover()
            
            else:
                if pyxel.btn(pyxel.MOUSE_LEFT_BUTTON):
                    if self.mouse_released and self.time_gameover == -999:
                        self.time_gameover = pyxel.frame_count
                        self.step = 0
                        self.time_last_step = pyxel.frame_count + 45
                        self.countup_start_step = [None for _ in range(20)]
                        self.hiscore_sound_flag = True
                        self.mouse_released = False
                else:
                    self.mouse_released = True
                
                if pyxel.frame_count - self.time_gameover == 20:
                    self.game_status = 2
        
        # リザルト画面
        elif self.game_status == 2:
            if pyxel.btn(pyxel.MOUSE_LEFT_BUTTON) or pyxel.btn(pyxel.KEY_F):
                if self.mouse_released:
                    self.game_status = 1
                    del self.p
                    for e in self.e:
                        del e
                    if self.score > self.hiscore:
                        self.hiscore = self.score
                    self.game_init()
                    # Fキーで開始するとLEVEL FOURから始まる
                    if pyxel.btn(pyxel.KEY_F):
                        self.time = 2690
                        self.level = 3
            else:
                self.mouse_released = True



    def update_floor(self, x, y):
        if (
            self.p.x + 12 >= x
            and self.p.x <= x + 204
            and self.p.y + 16 >= y
            and self.p.y <= y + 8
            and self.p.vy > 0
        ):
            self.p.onfloor = True
            self.p.vy = 0
            self.p.y = y - 16
            
        else:
            self.p.onfloor = False

        return x, y

    def next_level(self):
        self.time_levelup = self.time
        # LEVEL FOURから始めた時のために、配列の長さが足りていなかったら0埋めしておく
        if len(self.score_each_level) < self.level:
            self.score_each_level = [0 for _ in range(self.level)]
        self.score_each_level.append(self.score - sum(self.score_each_level))
        self.level += 1
    
    def gameover(self):
        self.p.alive = False
        self.is_gameover = True
        play_sound(8)
        self.next_level()

    # 数字を画像で表示する関数（スコア表示用）
    def display_number_by_image(self, number, x, y, img, u, v, w, h, align="left", spacing=2, key=0):
        if align == "left": # 左揃え
            left_x = x
        elif align == "center": # 中央揃え
            left_x = int(x + spacing // 2 - len(str(number)) * (w + spacing) // 2)
        elif align == "right": # 右揃え
            left_x = x + spacing - len(str(number)) * (w + spacing)

        for i, char in enumerate(str(number)):
            pyxel.blt(left_x + i * (w + spacing), y, img, u + int(char) * w, v, w, h, key)

    def draw(self):
        # 黒色で塗りつぶす。
        pyxel.cls(0)

        # タイトル画面
        if self.game_status == 0:
            # タイトルロゴ
            pyxel.blt(100, 60, 0, 208, 0, 40, 16, 0)

            # CLICK TO START
            pyxel.blt(79, 100, 0, 0, 216, 82, 5, 0)
        
        # ゲームプレイ画面
        elif self.game_status == 1:
            # マウスの高さに灰色で線を表示
            pyxel.line(0, pyxel.mouse_y, pyxel.width, pyxel.mouse_y, 13)

            # "SCORE" の文字表示
            pyxel.blt(103, 5, 0, 80, 24, 34, 8, 0)
            
            # スコアの数字表示
            self.display_number_by_image(self.score, 120, 16, 0, 16, 16, 6, 16, "center")

            # ハイスコア表示
            if self.hiscore != 0:
                pyxel.blt(5, 8, 0, 0, 232, 43, 5, 0)
                self.display_number_by_image(self.hiscore, 75, 8, 0, 0, 240, 5, 5, align="right", spacing=1)

            time_from_last_levelup = self.time - self.time_levelup
            # レベル表示
            if (
                time_from_last_levelup > 60
                and time_from_last_levelup < 150
                and (time_from_last_levelup % 10 < 5
                    or time_from_last_levelup < 90
                )
            ):
                img_w = [0, 64, 65, 80, 72, 72]
                img_x = max(240 - (time_from_last_levelup - 60) ** 2, 120 - img_w[self.level] // 2)
                pyxel.blt(img_x, 108, 0, 0, 64 + self.level * 16, img_w[self.level], 16, 0)
            
            # 障害物の表示
            for e in self.e:
                pyxel.blt(e.x, e.y, 0, 8 if e.is_fast else 0, 16, 8, 8, 15)

            # ゆか
            pyxel.rect(16, 100, 208, 3, 7)

            # プレイヤー描画
            pyxel.blt(
                self.p.x,
                self.p.y,
                0,
                16 if self.p.face_right else 0, # 向いている方向でテクスチャを変える
                32 if self.p.vy > 0 else 48, # 落下中は落下テクスチャ
                16,
                16,
                1,
            )

            # ゲームオーバー時の幕
            if self.time_gameover > 0:
                pyxel.rect(0, 0, min((pyxel.frame_count - self.time_gameover) ** 2, pyxel.width), pyxel.height, 13)
                pyxel.rect(0, 0, min((max(pyxel.frame_count - self.time_gameover - 4, 0)) ** 2, pyxel.width), pyxel.height, 0)
                # 2枚目の幕と同時にゲームオーバーの文字を出現させる
                if (pyxel.frame_count - self.time_gameover - 4) ** 2 >= 88:
                    pyxel.blt(88, 60, 0, 80, 0, min((pyxel.frame_count - self.time_gameover - 4) ** 2 - 88, 64), 16, 1)

        else:
            # GAMEOVERの文字
            pyxel.blt(88, max(min(60 - 0.6 * (pyxel.frame_count - self.time_gameover - 48) * abs(pyxel.frame_count - self.time_gameover - 48), 60), 8), 0, 80, 0, 64, 16, 1)
            
            if pyxel.frame_count - self.time_last_step > 15:
                self.step += 1
                self.time_last_step = pyxel.frame_count

            if self.step >= 1:
                # 各ステージのスコア
                for i, scr in enumerate(self.score_each_level[1:]):
                    if self.step > i:
                        pyxel.blt(68, 32 + i * 8, 0, 0, 160 + i * 5, 80, 5, 0)
                        self.display_number_by_image(self.countup(scr, i), 173, 32 + i * 8, 0, 0, 192, 5, 5, align="right", spacing=1)
                
                if self.step > (self.level - 1):
                    pyxel.line(68, 32 + (self.level - 1) * 8, 172, 32 + (self.level - 1) * 8, 13)
            
            # SCOREの文字
            if self.step > self.level:
                pyxel.blt(68, 32 + self.level * 8 - 7, 0, 80, 24, 34, 8, 0)

            # 合計スコア
            if self.step > self.level + 1:
                self.display_number_by_image(self.countup(self.score, self.level + 1), 173, 32 + self.level * 8 - 4, 0, 16, 16, 6, 16, "right")
            
            # ハイスコア
            if self.hiscore != 0 and self.score > self.hiscore:
                if self.step > self.level + 2:
                    pyxel.blt(68, 32 + self.level * 8 + 7, 0, 0, 200, 64, 5, 0)
                    # チカチカは目に悪いので不採用
                    #pyxel.blt(68, 32 + self.level * 8 + 7, 0, 0, 200 + 5 * (pyxel.frame_count // 2 % 3), 64, 5, 0)
                    if self.hiscore_sound_flag:
                        play_sound(6)
                        play_sound(5)
                        self.hiscore_sound_flag = False
                
                if self.step > self.level + 3:
                    # CLICK TO RETRY
                    pyxel.blt(79, 112, 0, 0, 224, 82, 5, 0)
            else:
                if self.step > self.level + 2:
                    # CLICK TO RETRY
                    pyxel.blt(79, 112, 0, 0, 224, 82, 5, 0)
    
    def countup(self, num, id, duration=30):
        current = 0

        if not self.countup_start_step[id]:
            self.countup_start_step[id] = -1 if num == 0 else pyxel.frame_count
            play_sound(9)
            current = 0

        else:
            if pyxel.frame_count - self.countup_start_step[id] >= duration:
                if pyxel.frame_count - self.countup_start_step[id] == duration:
                    play_sound(9)
                current = num
            else:
                if num * (pyxel.frame_count - self.countup_start_step[id]) // duration - num * (pyxel.frame_count - self.countup_start_step[id] - 1) // duration:
                    play_sound(9)
                self.time_last_step = pyxel.frame_count
                current = num * (pyxel.frame_count - self.countup_start_step[id]) // duration
            
        

        return current
        

App()
