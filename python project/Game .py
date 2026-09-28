import json
import random
import time
import os

SAVE_FILE = "savegame.json"
MAX_LEVEL = 100


class Weapon:
    def __init__(self, name, rank, damage, crit_bonus, price, required_level):
        self.name = name
        self.rank = rank
        self.damage = damage
        self.crit_bonus = crit_bonus
        self.price = price
        self.required_level = required_level


class Armor:
    def __init__(self, name, rank, defense, hp_bonus, mana_bonus, crit_resistance, price, required_level):
        self.name = name
        self.rank = rank
        self.defense = defense
        self.hp_bonus = hp_bonus
        self.mana_bonus = mana_bonus
        self.crit_resistance = crit_resistance
        self.price = price
        self.required_level = required_level


class Potion:
    def __init__(self, name, category, heal=0, mana=0, attack=0, defense=0, crit=0, turns=0, price=0):
        self.name = name
        self.category = category
        self.heal = heal
        self.mana = mana
        self.attack = attack
        self.defense = defense
        self.crit = crit
        self.turns = turns
        self.price = price

    def use(self, player):
        old_hp = player.hp
        old_mana = player.mana
        player.hp = min(player.max_hp, player.hp + self.heal)
        player.mana = min(player.max_mana, player.mana + self.mana)
        if self.attack or self.defense or self.crit:
            player.buffs.append({
                "attack": self.attack,
                "defense": self.defense,
                "crit": self.crit,
                "turns": self.turns
            })
        print(f"HP +{player.hp - old_hp}, Mana +{player.mana - old_mana}.")
        if self.attack:
            print(f"Attack +{self.attack} for {self.turns} turns.")
        if self.defense:
            print(f"Defense +{self.defense} for {self.turns} turns.")
        if self.crit:
            print(f"Critical Chance +{self.crit}% for {self.turns} turns.")


class Skill:
    def __init__(self, name, mana_cost, power, effect, unlock_level=1):
        self.name = name
        self.mana_cost = mana_cost
        self.power = power
        self.effect = effect
        self.unlock_level = unlock_level


class Enemy:
    def __init__(self, name, level, hp, attack, defense, exp, gold, region, skills=None):
        self.name = name
        self.level = level
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.exp = exp
        self.gold = gold
        self.region = region
        self.skills = skills or []
        self.crit_chance = min(25, 5 + level // 10)

    def is_alive(self):
        return self.hp > 0

    def attack_player(self, player):
        damage = max(1, self.attack + random.randint(-2, 3) - player.total_defense())
        if random.randint(1, 100) <= max(1, self.crit_chance - player.armor.crit_resistance if player.armor else self.crit_chance) and not player.defend:
            damage *= 2
            print(f"{self.name} lands a CRITICAL HIT!")
        player.take_damage(damage)


class Boss(Enemy):
    def __init__(self, name, level, hp, attack, defense, exp, gold, region):
        super().__init__(name, level, hp, attack, defense, exp, gold, region,
                         ["special", "heal", "critical"])
        self.turn = 0

    def special_attack(self, player):
        damage = max(1, self.attack * 2 - player.total_defense())
        print(f"{self.name} uses SPECIAL ATTACK!")
        player.take_damage(damage)

    def heal(self):
        amount = min(self.max_hp - self.hp, self.max_hp // 5)
        self.hp += amount
        print(f"{self.name} heals {amount} HP.")


class Player:
    def __init__(self, name, player_class):
        self.name = name
        self.player_class = player_class
        self.level = 1
        self.exp = 0
        self.exp_needed = 100
        self.gold = 100
        self.max_hp, self.max_mana, self.attack, self.defense, self.crit_chance = self.class_stats(player_class)
        self.hp = self.max_hp
        self.mana = self.max_mana
        self.crit_damage = 2.0
        self.weapon = None
        self.armor = None
        self.inventory = []
        self.potions = []
        self.enemies_defeated = 0
        self.bosses_defeated = 0
        self.unlocked_skills = []
        self.unlocked_regions = ["Village"]
        self.buffs = []
        self.passive_levels = []
        self.defend = False
        self.score = 0
        self.start_time = time.time()

    def class_stats(self, player_class):
        stats = {
            "Warrior": (180, 70, 18, 14, 8),
            "Mage": (120, 150, 24, 7, 15),
            "Archer": (140, 110, 20, 10, 22),
            "Assassin": (110, 120, 26, 6, 28)
        }
        return stats[player_class]

    def equip_armor(self, armor):
        if self.armor == armor:
            print("That armor is already equipped.")
            return
        if self.armor:
            self.max_hp -= self.armor.hp_bonus
            self.max_mana -= self.armor.mana_bonus
        self.armor = armor
        self.max_hp += armor.hp_bonus
        self.max_mana += armor.mana_bonus
        self.hp = min(self.hp, self.max_hp)
        self.mana = min(self.mana, self.max_mana)
        print(f"Equipped {armor.name}.")

    def unequip_armor(self):
        if self.armor is None:
            print("No armor equipped.")
            return
        self.max_hp -= self.armor.hp_bonus
        self.max_mana -= self.armor.mana_bonus
        self.hp = min(self.hp, self.max_hp)
        self.mana = min(self.mana, self.max_mana)
        self.armor = None
        print("Armor unequipped.")

    def is_alive(self):
        return self.hp > 0

    def total_attack(self):
        bonus = self.weapon.damage if self.weapon else 0
        bonus += sum(b["attack"] for b in self.buffs)
        bonus += (self.level // 5) * 2
        return self.attack + bonus

    def total_defense(self):
        bonus = self.armor.defense if self.armor else 0
        bonus += sum(b["defense"] for b in self.buffs)
        bonus += self.level // 5
        return self.defense + bonus

    def total_crit(self):
        bonus = self.weapon.crit_bonus if self.weapon else 0
        bonus += sum(b["crit"] for b in self.buffs)
        bonus += (self.level // 10) * 2
        return self.crit_chance + bonus

    def attack_enemy(self, enemy):
        damage = max(1, self.total_attack() - enemy.defense)
        crit_resistance = 0
        if isinstance(enemy, Boss):
            crit_resistance = 5
        if random.randint(1, 100) <= max(1, self.total_crit() - crit_resistance):
            damage = int(damage * self.crit_damage)
            print("CRITICAL HIT!")
        enemy.hp = max(0, enemy.hp - damage)
        print(f"You dealt {damage} damage.")

    def take_damage(self, damage):
        if self.defend:
            damage = max(1, damage // 2)
            print("Defend reduced the damage by 50%.")
        damage = max(1, damage - self.total_defense()) if not self.defend else damage
        self.hp = max(0, self.hp - damage)
        print(f"You received {damage} damage.")
        self.defend = False

    def heal(self):
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + 30 + self.level * 2)
        print(f"You recovered {self.hp - old_hp} HP.")

    def use_skill(self, skill, enemy):
        if self.mana < skill.mana_cost:
            print("Not enough mana.")
            return False
        self.mana -= skill.mana_cost
        if skill.effect == "damage":
            damage = max(1, self.total_attack() + skill.power - enemy.defense)
            enemy.hp = max(0, enemy.hp - damage)
            print(f"{skill.name} dealt {damage} damage.")
        elif skill.effect == "heal":
            old = self.hp
            self.hp = min(self.max_hp, self.hp + skill.power)
            print(f"{skill.name} restored {self.hp - old} HP.")
        elif skill.effect == "mana":
            self.mana = min(self.max_mana, self.mana + skill.power)
            print(f"{skill.name} restored {skill.power} mana.")
        elif skill.effect == "instant":
            if random.randint(1, 100) <= 8:
                enemy.hp = 0
                print(f"{skill.name} defeated the enemy instantly!")
            else:
                damage = max(1, self.total_attack() + skill.power - enemy.defense)
                enemy.hp = max(0, enemy.hp - damage)
                print(f"{skill.name} dealt {damage} damage.")
        return True

    def gain_exp(self, amount):
        self.exp += amount
        print(f"You gained {amount} EXP.")
        while self.level < MAX_LEVEL and self.exp >= self.exp_needed:
            self.exp -= self.exp_needed
            self.level_up()

    def level_up(self):
        self.level += 1
        self.exp_needed = 100 + (self.level - 1) * 50
        self.max_hp += 8
        self.max_mana += 5
        self.attack += 2
        self.defense += 1
        self.hp = self.max_hp
        self.mana = self.max_mana
        print(f"\nLEVEL UP! You reached Level {self.level}.")
        print(f"HP +8 | Mana +5 | Attack +2 | Defense +1")
        if self.level % 5 == 0:
            self.passive_levels.append(self.level)
            self.attack += 2
            self.defense += 1
            print(f"Passive unlocked at Level {self.level}: +2 Attack and +1 Defense.")

        if self.level % 10 == 0:
            self.crit_chance += 2
            print("Passive bonus: +2 Critical Chance.")

    def show_stats(self):
        print("\n========== PLAYER STATS ==========")
        print(f"Name          : {self.name}")
        print(f"Class         : {self.player_class}")
        print(f"Level         : {self.level}")
        print(f"EXP           : {self.exp}/{self.exp_needed}")
        print(f"HP            : {self.hp}/{self.max_hp}")
        print(f"Mana          : {self.mana}/{self.max_mana}")
        print(f"Attack        : {self.total_attack()}")
        print(f"Defense       : {self.total_defense()}")
        print(f"Critical      : {self.total_crit()}%")
        print(f"Critical Dmg  : {self.crit_damage}x")
        print(f"Gold          : {self.gold}")
        print(f"Weapon        : {self.weapon.name if self.weapon else 'None'}")
        print(f"Armor         : {self.armor.name if self.armor else 'None'}")
        print(f"Enemies       : {self.enemies_defeated}")
        print(f"Bosses        : {self.bosses_defeated}")
        print(f"Score         : {self.score}")
        print(f"Regions       : {', '.join(self.unlocked_regions)}")


class Game:
    RANKS = ["Common", "Uncommon", "Rare", "Super Rare", "Epic", "Mythical", "Legendary"]
    REGIONS = ["Village", "Forest", "Cave", "Desert", "Ruins", "Castle", "Volcano", "Frozen Mountain", "Sky Temple", "Demon Realm"]
    BOSS_LEVELS = {10: "Goblin King", 20: "Forest Guardian", 30: "Ancient Golem", 40: "Vampire Lord", 50: "Dragon Rider", 60: "Demon General", 70: "Ice Titan", 80: "Shadow Emperor", 90: "Celestial Dragon", 100: "Ancient Demon King"}

    def __init__(self):
        self.player = None
        self.weapons = self.create_weapons()
        self.armors = self.create_armors()
        self.potions = self.create_potions()
        self.skills = self.create_skills()
        self.enemies = self.create_enemies()
        self.defeated_boss_levels = []

    def create_weapons(self):
        data = [
            ("Wooden Sword", "Common", 5), ("Rusty Axe", "Common", 6), ("Training Bow", "Common", 5),
            ("Hunter's Bow", "Uncommon", 9),
            ("Iron Sword", "Rare", 12), ("Steel Axe", "Rare", 13), ("Long Bow", "Rare", 12),
            ("Crystal Blade", "Super Rare", 20), ("Shadow Dagger", "Super Rare", 21), ("Lightning Bow", "Super Rare", 20),
            ("Flame Sword", "Epic", 30), ("Ice Spear", "Epic", 31), ("Thunder Hammer", "Epic", 32),
            ("Phoenix Blade", "Mythical", 42), ("Demon Slayer", "Mythical", 45), ("Celestial Staff", "Mythical", 43),
            ("Dragon King's Sword", "Legendary", 55), ("Blade of Eternity", "Legendary", 58), ("Bow of the Gods", "Legendary", 57),
            ("Void Reaper", "Legendary", 60), ("Eldoria's Edge", "Legendary", 65)
        ]
        result = []
        for i, (name, rank, damage) in enumerate(data):
            mult = {"Common": 1.0, "Uncommon": 1.1, "Rare": 1.3, "Super Rare": 1.5, "Epic": 1.8, "Mythical": 2.2, "Legendary": 2.8}[rank]
            result.append(Weapon(name, rank, int(damage * mult / 1.5), int({"Common": 0, "Uncommon": 2, "Rare": 5, "Super Rare": 8, "Epic": 12, "Mythical": 18, "Legendary": 25}[rank]), 50 + i * 175, min(100, 1 + i * 4)))
        return result

    def create_armors(self):
        names = ["Leather", "Hunter", "Iron", "Steel", "Shadow", "Crystal", "Flame", "Frost", "Phoenix", "Demon", "Celestial", "Dragon"]
        ranks = ["Common", "Common", "Rare", "Rare", "Super Rare", "Super Rare", "Epic", "Epic", "Mythical", "Mythical", "Legendary", "Legendary"]
        result = []
        for i, name in enumerate(names):
            result.append(Armor(f"{name} Armor Set", ranks[i], 5 + i * 5, 20 + i * 20, 10 + i * 12, i + 2, 60 + i * 220, min(100, 1 + i * 6)))
        return result

    def create_potions(self):
        return [
            Potion("Small Health Potion", "Health", heal=50, price=30), Potion("Medium Health Potion", "Health", heal=100, price=60),
            Potion("Large Health Potion", "Health", heal=250, price=120), Potion("Giant Health Potion", "Health", heal=500, price=250),
            Potion("Ultimate Health Potion", "Health", heal=99999, price=500), Potion("Small Mana Potion", "Mana", mana=30, price=30),
            Potion("Medium Mana Potion", "Mana", mana=75, price=60), Potion("Large Mana Potion", "Mana", mana=150, price=120),
            Potion("Giant Mana Potion", "Mana", mana=300, price=250), Potion("Ultimate Mana Potion", "Mana", mana=99999, price=500),
            Potion("Life-Mana Elixir", "Mixed", heal=150, mana=100, price=250), Potion("Greater Life-Mana Elixir", "Mixed", heal=300, mana=200, price=450),
            Potion("Strength Tonic", "Buff", attack=20, turns=3, price=180), Potion("Iron Skin Tonic", "Buff", defense=20, turns=3, price=180),
            Potion("Critical Tonic", "Buff", crit=15, turns=3, price=220)
        ]

    def create_skills(self):
        return {
            "Warrior": [Skill("Slash", 10, 15, "damage"), Skill("Shield Bash", 20, 25, "damage"), Skill("Rage", 30, 40, "damage", 5), Skill("Earthquake", 50, 70, "damage", 10)],
            "Mage": [Skill("Fireball", 15, 30, "damage"), Skill("Ice Blast", 25, 45, "damage"), Skill("Thunder Strike", 40, 70, "damage", 5), Skill("Meteor", 65, 110, "damage", 10)],
            "Archer": [Skill("Multi Shot", 15, 25, "damage"), Skill("Poison Arrow", 25, 40, "damage"), Skill("Explosive Arrow", 40, 65, "damage", 5), Skill("Sniper Shot", 60, 100, "damage", 10)],
            "Assassin": [Skill("Backstab", 15, 35, "damage"), Skill("Smoke Bomb", 25, 30, "heal"), Skill("Shadow Strike", 40, 70, "damage", 5), Skill("Instant Kill", 80, 100, "instant", 10)]
        }

    def create_enemies(self):
        names = [
            "Goblin", "Wolf", "Slime", "Zombie", "Skeleton", "Orc", "Bandit", "Troll", "Dark Archer", "Giant Spider",
            "Vampire", "Werewolf", "Necromancer", "Ice Golem", "Fire Demon", "Sand Wyrm", "Desert Raider", "Stone Guardian",
            "Dark Knight", "Lava Beast", "Frost Giant", "Sky Serpent", "Temple Guardian", "Demon Hound", "Abyss Walker"
        ]
        result = []
        for i, name in enumerate(names, 1):
            level = min(100, 1 + (i - 1) * 4)
            hp = 45 + level * 8
            attack = 7 + level * 2
            defense = 2 + level
            exp = 25 + level * 5
            gold = 15 + level * 4
            region = self.REGIONS[min(9, (level - 1) // 10)]
            result.append(Enemy(name, level, hp, attack, defense, exp, gold, region))
        return result

    def new_game(self):
        print("\n========== CHARACTER CREATION ==========")
        name = input("Enter Player Name: ").strip() or "Hero"
        classes = {1: "Warrior", 2: "Mage", 3: "Archer", 4: "Assassin"}
        print("\nChoose Your Class")
        for number, name_value in classes.items():
            print(f"{number}. {name_value}")
        choice = self.get_choice(1, 4)
        self.player = Player(name, classes[choice])
        self.player.unlocked_skills = []
        for skill in self.skills[self.player.player_class]:
            if skill.unlock_level <= 1:
                self.player.unlocked_skills.append(skill)
        print("Player created successfully!")

    def get_choice(self, minimum, maximum):
        while True:
            try:
                value = int(input("Choose: "))
                if minimum <= value <= maximum:
                    return value
                print(f"Enter a number from {minimum} to {maximum}.")
            except ValueError:
                print("Please enter a number.")

    def save_game(self):
        if not self.player:
            return
        data = {
            "name": self.player.name,
            "player_class": self.player.player_class,
            "level": self.player.level,
            "exp": self.player.exp,
            "exp_needed": self.player.exp_needed,
            "hp": self.player.hp,
            "max_hp": self.player.max_hp,
            "mana": self.player.mana,
            "max_mana": self.player.max_mana,
            "attack": self.player.attack,
            "defense": self.player.defense,
            "crit_chance": self.player.crit_chance,
            "crit_damage": self.player.crit_damage,
            "gold": self.player.gold,
            "weapon": self.player.weapon.name if self.player.weapon else None,
            "armor": self.player.armor.name if self.player.armor else None,
            "potions": [p.name for p in self.player.potions],
            "inventory": [self.item_name(i) for i in self.player.inventory],
            "enemies_defeated": self.player.enemies_defeated,
            "bosses_defeated": self.player.bosses_defeated,
            "unlocked_regions": self.player.unlocked_regions,
            "defeated_boss_levels": self.defeated_boss_levels,
            "score": self.player.score,
            "buffs": self.player.buffs,
            "elapsed_time": time.time() - self.player.start_time
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        print("Game saved successfully.")

    def load_game(self):
        if not os.path.exists(SAVE_FILE):
            print("No saved game found.")
            return False
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.player = Player(data["name"], data["player_class"])

            for key in [
                "level", "exp", "exp_needed", "hp", "max_hp", "mana", "max_mana",
                "attack", "defense", "crit_chance", "crit_damage", "gold",
                "enemies_defeated", "bosses_defeated", "score"
            ]:
                setattr(self.player, key, data[key])

            self.player.unlocked_regions = data.get("unlocked_regions", ["Village"])
            self.defeated_boss_levels = data.get("defeated_boss_levels", [])
            self.player.buffs = data.get("buffs", [])

            self.player.unlocked_skills = []
            for skill in self.skills[self.player.player_class]:
                if skill.unlock_level <= self.player.level:
                    self.player.unlocked_skills.append(skill)

            weapon_name = data.get("weapon")
            armor_name = data.get("armor")

            self.player.weapon = next((w for w in self.weapons if w.name == weapon_name), None)
            self.player.armor = next((a for a in self.armors if a.name == armor_name), None)

            if self.player.armor:
                self.player.max_hp += self.player.armor.hp_bonus
                self.player.max_mana += self.player.armor.mana_bonus
                self.player.hp = min(self.player.hp, self.player.max_hp)
                self.player.mana = min(self.player.mana, self.player.max_mana)

            self.player.potions = []
            for potion_name in data.get("potions", []):
                source = next((p for p in self.potions if p.name == potion_name), None)
                if source:
                    self.player.potions.append(Potion(source.name, source.category, source.heal, source.mana, source.attack, source.defense, source.crit, source.turns, source.price))

            self.player.inventory = []
            for item_name in data.get("inventory", []):
                item = next((w for w in self.weapons if w.name == item_name), None)
                if item:
                    self.player.inventory.append(item)
                    continue

                item = next((a for a in self.armors if a.name == item_name), None)
                if item:
                    self.player.inventory.append(item)
                    continue

                item = next((p for p in self.potions if p.name == item_name), None)
                if item:
                    self.player.inventory.append(item)
                    continue

                self.player.inventory.append(item_name)

            self.player.start_time = time.time() - data.get("elapsed_time", 0)
            print("Game loaded successfully.")
            return True

        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            print(f"Could not load save: {error}")
            return False

    def item_name(self, item):
        if hasattr(item, "name"):
            return item.name
        return str(item)

    def main_menu(self):
        while True:
            print("\n========================================")
            print("LEGENDS OF THE FORGOTTEN REALM")
            print("========================================")
            print("1. new Game")
            print("2. continue")
            print("3. instructions")
            print("4. exit")
            choice = self.get_choice(1, 4)
            if choice == 1:
                self.new_game()
                return True
            if choice == 2:
                if self.load_game():
                    return True
            elif choice == 3:
                self.instructions()
            else:
                print("goodbye!")
                return False

    def instructions(self):
        print("\n========== INSTRUCTIONS ==========")
        print("Explore regions, defeat enemies, gain EXP, buy equipment, and defeat bosses.")
        print("A boss appears every 10 levels and unlocks the next region when defeated.")
        print("Use Attack, Skills, Heal, Potions, Defend, Inventory, Stats, or Run in battle.")
        print("Save frequently. Reach Level 100 and defeat the Ancient Demon King.")

    def get_region(self):
        index = min(len(self.REGIONS) - 1, max(0, (self.player.level - 1) // 10))
        return self.REGIONS[index]

    def explore(self):
        region = self.get_region()
        if region not in self.player.unlocked_regions:
            print("This region is locked. Defeat the previous boss first.")
            return "continue"
        candidates = [e for e in self.enemies if abs(e.level - self.player.level) <= 12 and e.region == region]
        if not candidates:
            candidates = [e for e in self.enemies if abs(e.level - self.player.level) <= 15]
        template = random.choice(candidates)
        scale = max(1, self.player.level / max(1, template.level))
        enemy = Enemy(template.name, self.player.level, int(template.max_hp * scale), int(template.attack * scale), int(template.defense * scale), int(template.exp * scale), int(template.gold * scale), region)
        print(f"\nYou entered {region}.")
        print(f"A {enemy.name} appeared!")
        return self.battle(enemy)

    def boss_battle(self):
        if self.player.level not in self.BOSS_LEVELS or self.player.level in self.defeated_boss_levels:
            return True
        level = self.player.level
        name = self.BOSS_LEVELS[level]
        boss = Boss(name, level, 500 + level * 45, 25 + level * 3, 8 + level, 500 + level * 15, 500 + level * 20, self.REGIONS[min(9, level // 10)])
        print(f"\n========== BOSS BATTLE: {boss.name} ==========")
        result = self.battle(boss, is_boss=True)
        if result == "win":
            self.defeated_boss_levels.append(level)
            self.player.bosses_defeated += 1
            self.player.score += 1000
            if level < MAX_LEVEL:
                next_region = self.REGIONS[level // 10]
                if next_region not in self.player.unlocked_regions:
                    self.player.unlocked_regions.append(next_region)
                    print(f"Region unlocked: {next_region}")
            return True
        return False

    def battle(self, enemy, is_boss=False):
        battle = Battle(self, enemy, is_boss)
        return battle.start()

    def shop(self):
        while True:
            print("\n========== SHOP ==========")
            print(f"Gold: {self.player.gold}")
            print("1. weapons")
            print("2. armor")
            print("3. potions")
            print("4. sell Items")
            print("5. exit")
            choice = self.get_choice(1, 5)
            if choice == 1:
                self.buy_weapon()
            elif choice == 2:
                self.buy_armor()
            elif choice == 3:
                self.buy_potion()
            elif choice == 4:
                self.sell_item()
            else:
                break

    def buy_weapon(self):
        for i, w in enumerate(self.weapons, 1):
            print(f"{i}. {w.name} [{w.rank}] Damage:{w.damage} Crit+{w.crit_bonus}% Price:{w.price} Lv:{w.required_level}")
        choice = self.get_choice(1, len(self.weapons))
        weapon = self.weapons[choice - 1]
        if self.player.level < weapon.required_level:
            print("Your level is too low.")
        elif self.player.gold < weapon.price:
            print("Not enough gold.")
        else:
            self.player.gold -= weapon.price
            self.player.weapon = weapon
            self.player.inventory.append(weapon)
            print(f"Equipped {weapon.name}.")

    def buy_armor(self):
        for i, a in enumerate(self.armors, 1):
            print(f"{i}. {a.name} [{a.rank}] Def:{a.defense} HP+{a.hp_bonus} Mana+{a.mana_bonus} Price:{a.price} Lv:{a.required_level}")
        choice = self.get_choice(1, len(self.armors))
        armor = self.armors[choice - 1]
        if self.player.level < armor.required_level:
            print("Your level is too low.")
        elif self.player.gold < armor.price:
            print("Not enough gold.")
        else:
            self.player.gold -= armor.price
            self.player.equip_armor(armor)
            self.player.hp = self.player.max_hp
            self.player.mana = self.player.max_mana
            self.player.inventory.append(armor)
            print(f"Equipped {armor.name}.")

    def buy_potion(self):
        for i, p in enumerate(self.potions, 1):
            print(f"{i}. {p.name} [{p.category}] Price:{p.price}")
        choice = self.get_choice(1, len(self.potions))
        potion = self.potions[choice - 1]
        if self.player.gold < potion.price:
            print("Not enough gold.")
        else:
            self.player.gold -= potion.price
            self.player.potions.append(Potion(potion.name, potion.category, potion.heal, potion.mana, potion.attack, potion.defense, potion.crit, potion.turns, potion.price))
            self.player.inventory.append(potion)
            print(f"Bought {potion.name}.")

    def sell_item(self):
        if not self.player.inventory:
            print("Inventory is empty.")
            return
        for i, item in enumerate(self.player.inventory, 1):
            print(f"{i}. {self.item_name(item)}")
        choice = self.get_choice(1, len(self.player.inventory))
        item = self.player.inventory.pop(choice - 1)
        price = max(1, getattr(item, "price", 20) // 2)
        self.player.gold += price
        if item is self.player.weapon:
            self.player.weapon = None
        if item is self.player.armor:
            self.player.unequip_armor()
        print(f"Sold {self.item_name(item)} for {price} gold.")

    def inventory_menu(self):
        print("\n========== INVENTORY ==========")
        print(f"Weapon: {self.player.weapon.name if self.player.weapon else 'None'}")
        print(f"Armor : {self.player.armor.name if self.player.armor else 'None'}")
        print("Potions:")
        if self.player.potions:
            for i, p in enumerate(self.player.potions, 1):
                print(f"{i}. {p.name}")
        else:
            print("None")
        print("Items:")
        for item in self.player.inventory:
            print(f"- {self.item_name(item)}")
        print("\n1. use Potion")
        print("2. unequip Weapon")
        print("3. unequip Armor")
        print("4. drop Item")
        print("5. back")
        choice = self.get_choice(1, 5)
        if choice == 1:
            self.use_potion()
        elif choice == 2:
            self.player.weapon = None
            print("Weapon unequipped.")
        elif choice == 3:
            self.player.unequip_armor()
        elif choice == 4:
            if self.player.inventory:
                for i, item in enumerate(self.player.inventory, 1):
                    print(f"{i}. {self.item_name(item)}")
                index = self.get_choice(1, len(self.player.inventory)) - 1
                item = self.player.inventory.pop(index)
                if item is self.player.weapon:
                    self.player.weapon = None
                if item is self.player.armor:
                    self.player.unequip_armor()
                print(f"Dropped {self.item_name(item)}.")

    def use_potion(self):
        if not self.player.potions:
            print("No potions available.")
            return
        for i, potion in enumerate(self.player.potions, 1):
            print(f"{i}. {potion.name}")
        choice = self.get_choice(1, len(self.player.potions))
        potion = self.player.potions.pop(choice - 1)
        potion.use(self.player)

    def game_loop(self):
        while self.player and self.player.is_alive() and self.player.level <= MAX_LEVEL:
            self.player.unlocked_skills = []
            for skill in self.skills[self.player.player_class]:
                if skill.unlock_level <= self.player.level:
                    self.player.unlocked_skills.append(skill)
            if self.player.level in self.BOSS_LEVELS and self.player.level not in self.defeated_boss_levels:
                if not self.boss_battle():
                    return self.game_over()
            if self.player.level >= MAX_LEVEL and 100 in self.defeated_boss_levels:
                return self.victory_screen()
            print("\n========================================")
            print("       LEGENDS OF THE FORGOTTEN REALM")
            print("========================================")
            print(f"Player: {self.player.name} | Class: {self.player.player_class}")
            print(f"Level: {self.player.level} | HP: {self.player.hp}/{self.player.max_hp} | Mana: {self.player.mana}/{self.player.max_mana}")
            print(f"Gold: {self.player.gold} | Region: {self.get_region()}")
            print("1. explore")
            print("2. playerStats")
            print("3. shop")
            print("4. inventory")
            print("5. saveGame")
            print("6. instructions")
            print("7. exit")
            choice = self.get_choice(1, 7)
            if choice == 1:
                result = self.explore()
                if result == "lose":
                    return self.game_over()
            elif choice == 2:
                self.player.show_stats()
            elif choice == 3:
                self.shop()
            elif choice == 4:
                self.inventory_menu()
            elif choice == 5:
                self.save_game()
            elif choice == 6:
                self.instructions()
            else:
                self.save_game()
                print("Thanks for playing!")
                return

    def game_over(self):
        print("\n==================== GAME OVER ====================")
        print("1. retry")
        print("2. load Save")
        print("3. exit")
        choice = self.get_choice(1, 3)
        if choice == 1:
            self.new_game()
            self.game_loop()
        elif choice == 2:
            if self.load_game():
                self.game_loop()
            else:
                self.new_game()
                self.game_loop()

    def victory_screen(self):
        elapsed = int(time.time() - self.player.start_time)
        print("\n=================================================")
        print("             VICTORY - ELDORIA SAVED")
        print("=================================================")
        print(f"Player Name       : {self.player.name}")
        print(f"Final Level       : {self.player.level}")
        print(f"Total Gold        : {self.player.gold}")
        print(f"Bosses Defeated   : {self.player.bosses_defeated}")
        print(f"Enemies Defeated  : {self.player.enemies_defeated}")
        print(f"Weapons Collected : {sum(isinstance(i, Weapon) for i in self.player.inventory)}")
        print(f"Rare Items Found  : {sum(getattr(i, 'rank', 'Common') != 'Common' for i in self.player.inventory)}")
        print(f"Total Play Time   : {elapsed // 60} min {elapsed % 60} sec")
        print(f"Final Score       : {self.player.score}")
        print("Ancient Demon King defeated. Eldoria is free!")


class Battle:
    def __init__(self, game, enemy, is_boss=False):
        self.game = game
        self.player = game.player
        self.enemy = enemy
        self.is_boss = is_boss
        self.turn = 0

    def start(self):
        print(f"\n========== BATTLE ==========")
        print(f"{self.player.name} VS {self.enemy.name}")
        while self.player.is_alive() and self.enemy.is_alive():
            self.turn += 1
            self.player.defend = False
            print(f"\n--- Turn {self.turn} ---")
            print(f"Your HP: {self.player.hp}/{self.player.max_hp} | Mana: {self.player.mana}/{self.player.max_mana}")
            print(f"{self.enemy.name} HP: {self.enemy.hp}/{self.enemy.max_hp}")
            print("1. attack")
            print("2. skills")
            print("3. heal")
            print("4. use Potion")
            print("5. defend")
            print("6. inventory")
            print("7. view Stats")
            print("8. r7un")
            choice = self.game.get_choice(1, 8)
            player_acted = True
            if choice == 1:
                self.player.attack_enemy(self.enemy)
            elif choice == 2:
                player_acted = self.skill_menu()
            elif choice == 3:
                self.player.heal()
            elif choice == 4:
                self.game.use_potion()
            elif choice == 5:
                self.player.defend = True
                print("You defended this turn. Next incoming damage is reduced by 50%.")
            elif choice == 6:
                self.game.inventory_menu()
            elif choice == 7:
                self.player.show_stats()
            elif choice == 8:
                if self.is_boss:
                    print("You cannot run from a boss!")
                    player_acted = False
                elif random.randint(1, 100) <= 50:
                    print("You escaped!")
                    return "run"
                else:
                    print("Escape failed!")
            if not player_acted:
                continue
            self.decrease_buffs()
            if self.enemy.is_alive():
                self.enemy_turn()
        if self.player.is_alive():
            return self.victory()
        return "lose"



    def skill_menu(self):
        if not self.player.unlocked_skills:
            print("No skills unlocked.")
            return False
        for i, skill in enumerate(self.player.unlocked_skills, 1):
            print(f"{i}. {skill.name} | Mana: {skill.mana_cost} | Unlock: Lv {skill.unlock_level}")
        print(f"{len(self.player.unlocked_skills) + 1}. Back")
        choice = self.game.get_choice(1, len(self.player.unlocked_skills) + 1)
        if choice == len(self.player.unlocked_skills) + 1:
            return False
        return self.player.use_skill(self.player.unlocked_skills[choice - 1], self.enemy)

    def enemy_turn(self):
        if isinstance(self.enemy, Boss):
            if self.turn % 3 == 0:
                self.enemy.special_attack(self.player)
            elif self.enemy.hp < self.enemy.max_hp * 0.3 and random.randint(1, 100) <= 35:
                self.enemy.heal()
            else:
                self.enemy.attack_player(self.player)
        else:
            self.enemy.attack_player(self.player)

    def decrease_buffs(self):
        remaining = []
        for buff in self.player.buffs:
            buff["turns"] -= 1
            if buff["turns"] > 0:
                remaining.append(buff)
        self.player.buffs = remaining

    def victory(self):
        print(f"\nYou defeated {self.enemy.name}!")
        self.player.enemies_defeated += 1
        self.player.gain_exp(self.enemy.exp)
        self.player.gold += self.enemy.gold
        self.player.score += self.enemy.exp + self.enemy.gold
        print(f"EXP +{self.enemy.exp} | Gold +{self.enemy.gold}")
        self.loot_drop(self.is_boss)
        return "win"

    def loot_drop(self, is_boss=False):
        if is_boss:
            roll = random.random() * 100
            if roll < 2:
                rank = "Legendary"
            elif roll < 10:
                rank = "Mythical"
            elif roll < 25:
                rank = "Epic"
            elif roll < 45:
                rank = "Super Rare"
            else:
                rank = "Rare"
            print(f"BOSS REWARD: Guaranteed {rank} or better!")
        else:
            roll = random.random() * 100
            if roll < 0.1:
                rank = "Legendary"
            elif roll < 1.0:
                rank = "Mythical"
            elif roll < 4.0:
                rank = "Epic"
            elif roll < 10.0:
                rank = "Super Rare"
            elif roll < 25.0:
                rank = "Rare"
            elif roll < 50.0:
                rank = "Uncommon"
            else:
                rank = "Common"
        possible_weapons = []
        for weapon in self.game.weapons:
            if weapon.rank == rank and weapon.required_level <= self.player.level:
                possible_weapons.append(weapon)
        possible_armors = []
        for armor in self.game.armors:
            if armor.rank == rank and armor.required_level <= self.player.level:
                possible_armors.append(armor)
        if possible_weapons and (is_boss or random.randint(1, 100) <= 35):
            item = random.choice(possible_weapons)
            self.player.inventory.append(item)
            print(f"LOOT: {item.name} [{item.rank}]")
        elif possible_armors and (is_boss or random.randint(1, 100) <= 35):
            item = random.choice(possible_armors)
            self.player.inventory.append(item)
            print(f"LOOT: {item.name} [{item.rank}]")
        elif random.randint(1, 100) <= (75 if is_boss else 50):
            source = random.choice(self.game.potions)
            potion = Potion(source.name, source.category, source.heal, source.mana, source.attack, source.defense, source.crit, source.turns, source.price)
            self.player.potions.append(potion)
            self.player.inventory.append(potion)
            print(f"LOOT: {potion.name}")
        else:
            materials = ["Iron Ore", "Crystal Shard", "Demon Essence", "Dragon Scale", "Ancient Relic"]
            material = random.choice(materials)
            self.player.inventory.append(material)
            print(f"LOOT: {material}")


def main():
    game = Game()
    if game.main_menu():
        game.game_loop()


if __name__ == "__main__":
    main()