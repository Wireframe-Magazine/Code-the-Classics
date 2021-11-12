from random import choice, randint, random, shuffle
from enum import Enum
import pygame, pgzero, pgzrun, sys

# Check Python version number. sys.version_info gives version as a tuple, e.g. if (3,7,2,'final',0) for version 3.7.2.
# Unlike many languages, Python can compare two tuples in the same way that you can compare numbers.
if sys.version_info < (3,5):
    print("This game requires at least version 3.5 of Python. Please download it from www.python.org")
    sys.exit()

# Check Pygame Zero version. This is a bit trickier because Pygame Zero only lets us get its version number as a string.
# So we have to split the string into a list, using '.' as the character to split on. We convert each element of the
# version number into an integer - but only if the string contains numbers and nothing else, because it's possible for
# a component of the version to contain letters as well as numbers (e.g. '2.0.dev0')
# We're using a Python feature called list comprehension - this is explained in the Bubble Bobble/Cavern chapter.
pgzero_version = [int(s) if s.isnumeric() else s for s in pgzero.__version__.split('.')]
if pgzero_version < [1,2]:
    print("This game requires at least version 1.2 of Pygame Zero. You have version {0}. Please upgrade using the command 'pip3 install --upgrade pgzero'".format(pgzero.__version__))
    sys.exit()

# Set up constants
WIDTH = 800
HEIGHT = 480
TITLE = "Cavern"

NUM_ROWS = 18
NUM_COLUMNS = 28

LEVEL_X_OFFSET = 50
GRID_BLOCK_SIZE = 25

ANCHOR_CENTRE = ("center", "center")
ANCHOR_CENTRE_BOTTOM = ("center", "bottom")

LEVELS = [ ["XXXXX     XXXXXXXX     XXXXX",
            "","","","",
            "   XXXXXXX        XXXXXXX   ",
            "","","",
            "   XXXXXXXXXXXXXXXXXXXXXX   ",
            "","","",
            "XXXXXXXXX          XXXXXXXXX",
            "","",""],

           ["XXXX    XXXXXXXXXXXX    XXXX",
            "","","","",
            "    XXXXXXXXXXXXXXXXXXXX    ",
            "","","",
            "XXXXXX                XXXXXX",
            "      X              X      ",
            "       X            X       ",
            "        X          X        ",
            "         X        X         ",
            "","",""],

           ["XXXX    XXXX    XXXX    XXXX",
            "","","","",
            "  XXXXXXXX        XXXXXXXX  ",
            "","","",
            "XXXX      XXXXXXXX      XXXX",
            "","","",
            "    XXXXXX        XXXXXX    ",
            "","",""]]

def block(x,y):
    # Is there a level grid block at these coordinates?
    grid_x = (x - LEVEL_X_OFFSET) // GRID_BLOCK_SIZE
    grid_y = y // GRID_BLOCK_SIZE
    if grid_y > 0 and grid_y < NUM_ROWS:
        row = game.grid[grid_y]
        return grid_x >= 0 and grid_x < NUM_COLUMNS and len(row) > 0 and row[grid_x] != " "
    else:
        return False

def sign(x):
    # Returns -1 or 1 depending on whether number is positive or negative
    return -1 if x < 0 else 1

class CollideActor(Actor):
    def __init__(self, pos, anchor=ANCHOR_CENTRE):
        super().__init__("blank", pos, anchor)

    def move(self, dx, dy, speed):
        new_x, new_y = int(self.x), int(self.y)

        # Movement is done 1 pixel at a time, which ensures we don't get embedded into a wall we're moving towards
        for i in range(speed):
            new_x, new_y = new_x + dx, new_y + dy

            if new_x < 70 or new_x > 730:
                # Collided with edge of level
                return True

            # Normally you don't need brackets surrounding the condition for an if statement (unlike many other
            # languages), but in the case where the condition is split into multiple lines, using brackets removes
            # the need to use the \ symbol at the end of each line.
            # The code below checks to see if we're position we're trying to move into overlaps with a block. We only
            # need to check the direction we're actually moving in. So first, we check to see if we're moving down
            # (dy > 0). If that's the case, we then check to see if the proposed new y coordinate is a multiple of
            # GRID_BLOCK_SIZE. If it is, that means we're directly on top of a place where a block might be. If that's
            # also true, we then check to see if there is actually a block at the given position. If there's a block
            # there, we return True and don't update the object to the new position.
            # For movement to the right, it's the same except we check to ensure that the new x coordinate is a multiple
            # of GRID_BLOCK_SIZE. For moving left, we check to see if the new x coordinate is the last (right-most)
            # pixel of a grid block.
            # Note that we don't check for collisions when the player is moving up.
            if ((dy > 0 and new_y % GRID_BLOCK_SIZE == 0 or
                 dx > 0 and new_x % GRID_BLOCK_SIZE == 0 or
                 dx < 0 and new_x % GRID_BLOCK_SIZE == GRID_BLOCK_SIZE-1)
                and block(new_x, new_y)):
                    return True

            # We only update the object's position if there wasn't a block there.
            self.pos = new_x, new_y

        # Didn't collide with block or edge of level
        return False

class Orb(CollideActor):
    MAX_TIMER = 250

    def __init__(self, pos, dir_x):
        super().__init__(pos)

        # Orbs are initially blown horizontally, then start floating upwards
        self.direction_x = dir_x
        self.floating = False
        self.trapped_enemy_type = None      # Number representing which type of enemy is trapped in this bubble
        self.timer = -1
        self.blown_frames = 6  # Number of frames during which we will be pushed horizontally

    def hit_test(self, bolt):
        # Check for collision with a bolt
        collided = self.collidepoint(bolt.pos)
        if collided:
            self.timer = Orb.MAX_TIMER - 1
        return collided

    def update(self):
        self.timer += 1

        if self.floating:
            # Float upwards
            self.move(0, -1, randint(1, 2))
        else:
            # Move horizontally
            if self.move(self.direction_x, 0, 4):
                # If we hit a block, start floating
                self.floating = True

        if self.timer == self.blown_frames:
            self.floating = True
        elif self.timer >= Orb.MAX_TIMER or self.y <= -40:
            # Pop if our lifetime has run out or if we have gone off the top of the screen
            game.pops.append(Pop(self.pos, 1))
            if self.trapped_enemy_type != None:
                # trapped_enemy_type is either zero or one. A value of one means there's a chance of creating a
                # powerup such as an extra life or extra health
                game.fruits.append(Fruit(self.pos, self.trapped_enemy_type))
            game.play_sound("pop", 4)

        if self.timer < 9:
            # Orb grows to full size over the course of 9 frames - the animation frame updating every 3 frames
            self.image = "orb" + str(self.timer // 3)
        else:
            if self.trapped_enemy_type != None:
                self.image = "trap" + str(self.trapped_enemy_type) + str((self.timer // 4) % 8)
            else:
                self.image = "orb" + str(3 + (((self.timer - 9) // 8) % 4))

class Bolt(CollideActor):
    SPEED = 7

    def __init__(self, pos, dir_x):
        super().__init__(pos)

        self.direction_x = dir_x
        self.active = True

    def update(self):
        # Move horizontally and check to see if we've collided with a block
        if self.move(self.direction_x, 0, Bolt.SPEED):
            # Collided
            self.active = False
        else:
            # We didn't collide with a block - check to see if we collided with an orb or the player
            for obj in game.orbs + [game.player]:
                if obj and obj.hit_test(self):
                    self.active = False
                    break

        direction_idx = "1" if self.direction_x > 0 else "0"
        anim_frame = str((game.timer // 4) % 2)
        self.image = "bolt" + direction_idx + anim_frame

class Pop(Actor):
    def __init__(self, pos, type):
        super().__init__("blank", pos)

        self.type = type
        self.timer = -1

    def update(self):
        self.timer += 1
        self.image = "pop" + str(self.type) + str(self.timer // 2)

class GravityActor(CollideActor):
    MAX_FALL_SPEED = 10

    def __init__(self, pos):
        super().__init__(pos, ANCHOR_CENTRE_BOTTOM)

        self.vel_y = 0
        self.landed = False

    def update(self, detect=True):
        # Apply gravity, without going over the maximum fall speed
        self.vel_y = min(self.vel_y + 1, GravityActor.MAX_FALL_SPEED)

        # The detect parameter indicates whether we should check for collisions with blocks as we fall. Normally we
        # want this to be the case - hence why this parameter is optional, and is True by default. If the player is
        # in the process of losing a life, however, we want them to just fall out of the level, so False is passed
        # in this case.
        if detect:
            # Move vertically in the appropriate direction, at the appropriate speed
            if self.move(0, sign(self.vel_y), abs(self.vel_y)):
                # If move returned True, we must have landed on a block.
                # Note that move doesn't apply any collision detection when the player is moving up - only down
                self.vel_y = 0
                self.landed = True

            if self.top >= HEIGHT:
                # Fallen off bottom - reappear at top
                self.y = 1
        else:
            # Collision detection disabled - just update the Y coordinate without any further checks
            self.y += self.vel_y

# Class for pickups including fruit, extra health and extra life
class Fruit(GravityActor):
    APPLE = 0
    RASPBERRY = 1
    LEMON = 2
    EXTRA_HEALTH = 3
    EXTRA_LIFE = 4

    def __init__(self, pos, trapped_enemy_type=0):
        super().__init__(pos)

        # Choose which type of fruit we're going to be.
        if trapped_enemy_type == Robot.TYPE_NORMAL:
            self.type = choice([Fruit.APPLE, Fruit.RASPBERRY, Fruit.LEMON])
        else:
            # If trapped_enemy_type is 1, it means this fruit came from bursting an orb containing the more dangerous type
            # of enemy. In this case there is a chance of getting an extra help or extra life power up
            # We create a list containing the possible types of fruit, in proportions based on the probability we want
            # each type of fruit to be chosen
            types = 10 * [Fruit.APPLE, Fruit.RASPBERRY, Fruit.LEMON]    # Each of these appear in the list 10 times
            types += 9 * [Fruit.EXTRA_HEALTH]                           # This appears 9 times
            types += [Fruit.EXTRA_LIFE]                                 # This only appears once
            self.type = choice(types)                                   # Randomly choose one from the list

        self.time_to_live = 500 # Counts down to zero

    def update(self):
        super().update()

        # Does the player exist, and are they colliding with us?
        if game.player and game.player.collidepoint(self.center):
            if self.type == Fruit.EXTRA_HEALTH:
                game.player.health = min(3, game.player.health + 1)
                game.play_sound("bonus")
            elif self.type == Fruit.EXTRA_LIFE:
                game.player.lives += 1
                game.play_sound("bonus")
            else:
                game.player.score += (self.type + 1) * 100
                game.play_sound("score")

            self.time_to_live = 0   # Disappear
        else:
            self.time_to_live -= 1

        if self.time_to_live <= 0:
            # Create 'pop' animation
            game.pops.append(Pop((self.x, self.y - 27), 0))

        anim_frame = str([0, 1, 2, 1][(game.timer // 6) % 4])
        self.image = "fruit" + str(self.type) + anim_frame

class Player(GravityActor):
    def __init__(self):
        # Call constructor of parent class. Initial pos is 0,0 but reset is always called straight afterwards which
        # will set the actual starting position.
        super().__init__((0, 0))

        self.lives = 2
        self.score = 0

    def reset(self):
        self.pos = (WIDTH / 2, 100)
        self.vel_y = 0
        self.direction_x = 1            # -1 = left, 1 = right
        self.fire_timer = 0
        self.hurt_timer = 100   # Invulnerable for this many frames
        self.health = 3
        self.blowing_orb = None

    def hit_test(self, other):
        # Check for collision between player and bolt - called from Bolt.update. Also check hurt_timer - after being hurt,
        # there is a period during which the player cannot be hurt again
        if self.collidepoint(other.pos) and self.hurt_timer < 0:
            # Player loses 1 health, is knocked in the direction the bolt had been moving, and can't be hurt again
            # for a while
            self.hurt_timer = 200
            self.health -= 1
            self.vel_y = -12
            self.landed = False
            self.direction_x = other.direction_x
            if self.health > 0:
                game.play_sound("ouch", 4)
            else:
                game.play_sound("die")
            return True
        else:
            return False

    def update(self):
        # Call GravityActor.update - parameter is whether we want to perform collision detection as we fall. If health
        # is zero, we want the player to just fall out of the level
        super().update(self.health > 0)

        self.fire_timer -= 1
        self.hurt_timer -= 1

        if self.landed:
            # Hurt timer starts at 200, but drops to 100 once the player has landed
            self.hurt_timer = min(self.hurt_timer, 100)

        if self.hurt_timer > 100:
            # We've just been hurt. Either carry out the sideways motion from being knocked by a bolt, or if health is
            # zero, we're dropping out of the level, so check for our sprite reaching a certain Y coordinate before
            # reducing our lives count and responding the player. We check for the Y coordinate being the screen height
            # plus 50%, rather than simply the screen height, because the former effectively gives us a short delay
            # before the player respawns.
            if self.health > 0:
                self.move(self.direction_x, 0, 4)
            else:
                if self.top >= HEIGHT*1.5:
                    self.lives -= 1
                    self.reset()
        else:
            # We're not hurt
            # Get keyboard input. dx represents the direction the player is facing
            dx = 0
            if keyboard.left:
                dx = -1
            elif keyboard.right:
                dx = 1

            if dx != 0:
                self.direction_x = dx

                # If we haven't just fired an orb, carry out horizontal movement
                if self.fire_timer < 10:
                    self.move(dx, 0, 4)

            # Do we need to create a new orb? Space must have been pressed and released, the minimum time between
            # orbs must have passed, and there is a limit of 5 orbs.
            if space_pressed() and self.fire_timer <= 0 and len(game.orbs) < 5:
                # x position will be 38 pixels in front of the player position, while ensuring it is within the
                # bounds of the level
                x = min(730, max(70, self.x + self.direction_x * 38))
                y = self.y - 35
                self.blowing_orb = Orb((x,y), self.direction_x)
                game.orbs.append(self.blowing_orb)
                game.play_sound("blow", 4)
                self.fire_timer = 20

            if keyboard.up and self.vel_y == 0 and self.landed:
                # Jump
                self.vel_y = -16
                self.landed = False
                game.play_sound("jump")

        # Holding down space causes the current orb (if there is one) to be blown further
        if keyboard.space:
            if self.blowing_orb:
                # Increase blown distance up to a maximum of 120
                self.blowing_orb.blown_frames += 4
                if self.blowing_orb.blown_frames >= 120:
                    # Can't be blown any further
                    self.blowing_orb = None
        else:
            # If we let go of space, we relinquish control over the current orb - it can't be blown any further
            self.blowing_orb = None

        # Set sprite image. If we're currently hurt, the sprite will flash on and off on alternate frames.
        self.image = "blank"
        if self.hurt_timer <= 0 or self.hurt_timer % 2 == 1:
            dir_index = "1" if self.direction_x > 0 else "0"
            if self.hurt_timer > 100:
                if self.health > 0:
                    self.image = "recoil" + dir_index
                else:
                    self.image = "fall" + str((game.timer // 4) % 2)
            elif self.fire_timer > 0:
                self.image = "blow" + dir_index
            elif dx == 0:
                self.image = "still"
            else:
                self.image = "run" + dir_index + str((game.timer // 8) % 4)

class Robot(GravityActor):
    TYPE_NORMAL = 0
    TYPE_AGGRESSIVE = 1

    def __init__(self, pos, type):
        super().__init__(pos)

        self.type = type

        self.speed = randint(1, 3)
        self.direction_x = 1
        self.alive = True

        self.change_dir_timer = 0
        self.fire_timer = 100

    def update(self):
        super().update()

        self.change_dir_timer -= 1
        self.fire_timer += 1

        # Move in current direction - turn around if we hit a wall
        if self.move(self.direction_x, 0, self.speed):
            self.change_dir_timer = 0

        if self.change_dir_timer <= 0:
            # Randomly choose a direction to move in
            # If there's a player, there's a two thirds chance that we'll move towards them
            directions = [-1, 1]
            if game.player:
                directions.append(sign(game.player.x - self.x))
            self.direction_x = choice(directions)
            self.change_dir_timer = randint(100, 250)

        # The more powerful type of robot can deliberately shoot at orbs - turning to face them if necessary
        if self.type == Robot.TYPE_AGGRESSIVE and self.fire_timer >= 24:
            # Go through all orbs to see if any can be shot at
            for orb in game.orbs:
                # The orb must be at our height, and within 200 pixels on the x axis
                if orb.y >= self.top and orb.y < self.bottom and abs(orb.x - self.x) < 200:
                    self.direction_x = sign(orb.x - self.x)
                    self.fire_timer = 0
                    break

        # Check to see if we can fire at player
        if self.fire_timer >= 12:
            # Random chance of firing each frame. Likelihood increases 10 times if player is at the same height as us
            fire_probability = game.fire_probability()
            if game.player and self.top < game.player.bottom and self.bottom > game.player.top:
                fire_probability *= 10
            if random() < fire_probability:
                self.fire_timer = 0
                game.play_sound("laser", 4)

        elif self.fire_timer == 8:
            #  Once the fire timer has been set to 0, it will count up - frame 8 of the animation is when the actual bolt is fired
            game.bolts.append(Bolt((self.x + self.direction_x * 20, self.y - 38), self.direction_x))

        # Am I colliding with an orb? If so, become trapped by it
        for orb in game.orbs:
            if orb.trapped_enemy_type == None and self.collidepoint(orb.center):
                self.alive = False
                orb.floating = True
                orb.trapped_enemy_type = self.type
                game.play_sound("trap", 4)
                break

        # Choose and set sprite image
        direction_idx = "1" if self.direction_x > 0 else "0"
        image = "robot" + str(self.type) + direction_idx
        if self.fire_timer < 12:
            image += str(5 + (self.fire_timer // 4))
        else:
            image += str(1 + ((game.timer // 4) % 4))
        self.image = image


class Game:
    def __init__(self, player=None):
        self.player = player
        self.level_colour = -1
        self.level = -1

        self.next_level()

    def fire_probability(self):
        # Likelihood per frame of each robot firing a bolt - they fire more often on higher levels
        return 0.001 + (0.0001 * min(100, self.level))

    def max_enemies(self):
        # Maximum number of enemies on-screen at once - increases as you progress through the levels
        return min((self.level + 6) // 2, 8)

    def next_level(self):
        self.level_colour = (self.level_colour + 1) % 4
        self.level += 1

        # Set up grid
        self.grid = LEVELS[self.level % len(LEVELS)]

        # The last row is a copy of the first row
        # Note that we don't do 'self.grid.append(self.grid[0])'. That would alter the original data in the LEVELS list
        # Instead, what this line does is create a brand new list, which is distinct from the list in LEVELS, and
        # consists of the level data plus the first row of the level. It's also interesting to note that you can't
        # do 'self.grid += [self.grid[0]]', because that's equivalent to using append.
        # As an alternative, we could have copied the list on the line below '# Set up grid', by writing
        # 'self.grid = list(LEVELS...', then used append or += on the line below.
        self.grid = self.grid + [self.grid[0]]

        self.timer = -1

        if self.player:
            self.player.reset()

        self.fruits = []
        self.bolts = []
        self.enemies = []
        self.pops = []
        self.orbs = []

        # At the start of each level we create a list of pending enemies - enemies to be created as the level plays out.
        # When this list is empty, we have no more enemies left to create, and the level will end once we have destroyed
        # all enemies currently on-screen. Each element of the list will be either 0 or 1, where 0 corresponds to
        # a standard enemy, and 1 is a more powerful enemy.
        # First we work out how many total enemies and how many of each type to create
        num_enemies = 10 + self.level
        num_strong_enemies = 1 + int(self.level / 1.5)
        num_weak_enemies = num_enemies - num_strong_enemies

        # Then we create the list of pending enemies, using Python's ability to create a list by multiplying a list
        # by a number, and by adding two lists together. The resulting list will consist of a series of copies of
        # the number 1 (the number depending on the value of num_strong_enemies), followed by a series of copies of
        # the number zero, based on num_weak_enemies.
        self.pending_enemies = num_strong_enemies * [Robot.TYPE_AGGRESSIVE] + num_weak_enemies * [Robot.TYPE_NORMAL]

        # Finally we shuffle the list so that the order is randomised (using Python's random.shuffle function)
        shuffle(self.pending_enemies)

        self.play_sound("level", 1)

    def get_robot_spawn_x(self):
        # Find a spawn location for a robot, by checking the top row of the grid for empty spots
        # Start by choosing a random grid column
        r = randint(0, NUM_COLUMNS-1)

        for i in range(NUM_COLUMNS):
            # Keep looking at successive columns (wrapping round if we go off the right-hand side) until
            # we find one where the top grid column is unoccupied
            grid_x = (r+i) % NUM_COLUMNS
            if self.grid[0][grid_x] == ' ':
                return GRID_BLOCK_SIZE * grid_x + LEVEL_X_OFFSET + 12

        # If we failed to find an opening in the top grid row (shouldn't ever happen), just spawn the enemy
        # in the centre of the screen
        return WIDTH/2

    def update(self):
        self.timer += 1

        # Update all objects
        for obj in self.fruits + self.bolts + self.enemies + self.pops + [self.player] + self.orbs:
            if obj:
                obj.update()

        # Use list comprehensions to remove objects which are no longer wanted from the lists. For example, we recreate
        # self.fruits such that it contains all existing fruits except those whose time_to_live counter has reached zero
        self.fruits = [f for f in self.fruits if f.time_to_live > 0]
        self.bolts = [b for b in self.bolts if b.active]
        self.enemies = [e for e in self.enemies if e.alive]
        self.pops = [p for p in self.pops if p.timer < 12]
        self.orbs = [o for o in self.orbs if o.timer < 250 and o.y > -40]

        # Every 100 frames, create a random fruit (unless there are no remaining enemies on this level)
        if self.timer % 100 == 0 and len(self.pending_enemies + self.enemies) > 0:
            # Create fruit at random position
            self.fruits.append(Fruit((randint(70, 730), randint(75, 400))))

        # Every 81 frames, if there is at least 1 pending enemy, and the number of active enemies is below the current
        # level's maximum enemies, create a robot
        if self.timer % 81 == 0 and len(self.pending_enemies) > 0 and len(self.enemies) < self.max_enemies():
            # Retrieve and remove the last element from the pending enemies list
            robot_type = self.pending_enemies.pop()
            pos = (self.get_robot_spawn_x(), -30)
            self.enemies.append(Robot(pos, robot_type))

        # End level if there are no enemies remaining to be created, no existing enemies, no fruit, no popping orbs,
        # and no orbs containing trapped enemies. (We don't want to include orbs which don't contain trapped enemies,
        # as the level would never end if the player kept firing new orbs)
        if len(self.pending_enemies + self.fruits + self.enemies + self.pops) == 0:
            if len([orb for orb in self.orbs if orb.trapped_enemy_type != None]) == 0:
                self.next_level()

    def draw(self):
        # Draw appropriate background for this level
        screen.blit("bg%d" % self.level_colour, (0, 0))

        block_sprite = "block" + str(self.level % 4)

        # Display blocks
        for row_y in range(NUM_ROWS):
            row = self.grid[row_y]
            if len(row) > 0:
                # Initial offset - large blocks at edge of level are 50 pixels wide
                x = LEVEL_X_OFFSET
                for block in row:
                    if block != ' ':
                        screen.blit(block_sprite, (x, row_y * GRID_BLOCK_SIZE))
                    x += GRID_BLOCK_SIZE

        # Draw all objects
        all_objs = self.fruits + self.bolts + self.enemies + self.pops + self.orbs
        all_objs.append(self.player)
        for obj in all_objs:
            if obj:
                obj.draw()

    def play_sound(self, name, count=1):
        # Some sounds have multiple varieties. If count > 1, we'll randomly choose one from those
        # We don't play any sounds if there is no player (e.g. if we're on the menu)
        if self.player:
            try:
                # Pygame Zero allows you to write things like 'sounds.explosion.play()'
                # This automatically loads and plays a file named 'explosion.wav' (or .ogg) from the sounds folder (if
                # such a file exists)
                # But what if you have files named 'explosion0.ogg' to 'explosion5.ogg' and want to randomly choose
                # one of them to play? You can generate a string such as 'explosion3', but to use such a string
                # to access an attribute of Pygame Zero's sounds object, we must use Python's built-in function getattr
                sound = getattr(sounds, name + str(randint(0, count - 1)))
                sound.play()
            except Exception as e:
                # If no such sound file exists, print the name
                print(e)

# Widths of the letters A to Z in the font images
CHAR_WIDTH = [27, 26, 25, 26, 25, 25, 26, 25, 12, 26, 26, 25, 33, 25, 26,
              25, 27, 26, 26, 25, 26, 26, 38, 25, 25, 25]

def char_width(char):
    # Return width of given character. For characters other than the letters A to Z (i.e. space, and the digits 0 to 9),
    # the width of the letter A is returned. ord gives the ASCII/Unicode code for the given character.
    index = max(0, ord(char) - 65)
    return CHAR_WIDTH[index]

def draw_text(text, y, x=None):
    if x == None:
        # If no X pos specified, draw text in centre of the screen - must first work out total width of text
        x = (WIDTH - sum([char_width(c) for c in text])) // 2

    for char in text:
        screen.blit("font0"+str(ord(char)), (x, y))
        x += char_width(char)

IMAGE_WIDTH = {"life":44, "plus":40, "health":40}

def draw_status():
    # Display score, right-justified at edge of screen
    number_width = CHAR_WIDTH[0]
    s = str(game.player.score)
    draw_text(s, 451, WIDTH - 2 - (number_width * len(s)))

    # Display level number
    draw_text("LEVEL " + str(game.level + 1), 451)

    # Display lives and health
    # We only display a maximum of two lives - if there are more than two, a plus symbol is displayed
    lives_health = ["life"] * min(2, game.player.lives)
    if game.player.lives > 2:
        lives_health.append("plus")
    if game.player.lives >= 0:
        lives_health += ["health"] * game.player.health

    x = 0
    for image in lives_health:
        screen.blit(image, (x, 450))
        x += IMAGE_WIDTH[image]

# Is the space bar currently being pressed down?
space_down = False

# Has the space bar just been pressed? i.e. gone from not being pressed, to being pressed
def space_pressed():
    global space_down
    if keyboard.space:
        if space_down:
            # Space was down previous frame, and is still down
            return False
        else:
            # Space wasn't down previous frame, but now is
            space_down = True
            return True
    else:
        space_down = False
        return False

# Pygame Zero calls the update and draw functions each frame

class State(Enum):
    MENU = 1
    PLAY = 2
    GAME_OVER = 3


def update():
    global state, game

    if state == State.MENU:
        if space_pressed():
            # Switch to play state, and create a new Game object, passing it a new Player object to use
            state = State.PLAY
            game = Game(Player())
        else:
            game.update()

    elif state == State.PLAY:
        if game.player.lives < 0:
            game.play_sound("over")
            state = State.GAME_OVER
        else:
            game.update()

    elif state == State.GAME_OVER:
        if space_pressed():
            # Switch to menu state, and create a new game object without a player
            state = State.MENU
            game = Game()

def draw():
    game.draw()

    if state == State.MENU:
        # Draw title screen
        screen.blit("title", (0, 0))

        # Draw "Press SPACE" animation, which has 10 frames numbered 0 to 9
        # The first part gives us a number between 0 and 159, based on the game timer
        # Dividing by 4 means we go to a new animation frame every 4 frames
        # We enclose this calculation in the min function, with the other argument being 9, which results in the
        # animation staying on frame 9 for three quarters of the time. Adding 40 to the game timer is done to alter
        # which stage the animation is at when the game first starts
        anim_frame = min(((game.timer + 40) % 160) // 4, 9)
        screen.blit("space" + str(anim_frame), (130, 280))

    elif state == State.PLAY:
        draw_status()

    elif state == State.GAME_OVER:
        draw_status()
        # Display "Game Over" image
        screen.blit("over", (0, 0))

# Set up sound system and start music
try:
    pygame.mixer.quit()
    pygame.mixer.init(44100, -16, 2, 1024)

    music.play("theme")
    music.set_volume(0.3)
except:
    # If an error occurs, just ignore it
    pass



# Set the initial game state
state = State.MENU

# Create a new Game object, without a Player object
game = Game()

pgzrun.go()
