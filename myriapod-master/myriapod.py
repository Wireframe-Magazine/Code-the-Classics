import pgzero, pgzrun, pygame, sys
from random import choice, randint, random
from enum import Enum

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

WIDTH = 480
HEIGHT = 800
TITLE = "Myriapod"

DEBUG_TEST_RANDOM_POSITIONS = False

# Pygame Zero allows you to access and change sprite positions based on various
# anchor points
CENTRE_ANCHOR = ("center", "center")

num_grid_rows = 25
num_grid_cols = 14

# Convert a position in pixel units to a position in grid units. In this game, a grid square is 32 pixels.
def pos2cell(x, y):
    return ((int(x)-16)//32, int(y)//32)

# Convert grid cell position to pixel coordinates, with a given offset
def cell2pos(cell_x, cell_y, x_offset=0, y_offset=0):
    # If the requested offset is zero, returns the centre of the requested cell, hence the +16. In the case of the
    # X axis, there's a 16 pixel border at the left and right of the screen, hence +16 becomes +32.
    return ((cell_x * 32) + 32 + x_offset, (cell_y * 32) + 16 + y_offset)

class Explosion(Actor):
    def __init__(self, pos, type):
        super().__init__("blank", pos)

        self.type = type
        self.timer = 0

    def update(self):
        self.timer += 1

        # Set sprite based on explosion type and timer - update to a new image
        # every four frames
        self.image = "exp" + str(self.type) + str(self.timer // 4)


class Player(Actor):

    INVULNERABILITY_TIME = 100
    RESPAWN_TIME = 100
    RELOAD_TIME = 10

    def __init__(self, pos):
        super().__init__("blank", pos)

        # These determine which frame of animation the player sprite will use
        self.direction = 0
        self.frame = 0

        self.lives = 3
        self.alive = True

        # timer is used for animation, respawning and for ensuring the player is
        # invulnerable immediately after respawning
        self.timer = 0

        # When the player shoots, this is set to RELOAD_TIME - it then counts
        # down - when it reaches zero the player can shoot again
        self.fire_timer = 0

    def move(self, dx, dy, speed):
        # dx and dy will each be either 0, -1 or 1. speed is an integer indicating
        # how many pixels we should move in the specified direction.
        for i in range(speed):
            # For each pixel we want to move, we must first check if it's a valid place to move to
            if game.allow_movement(self.x + dx, self.y + dy):
                self.x += dx
                self.y += dy

    def update(self):
        self.timer += 1

        if self.alive:
            # Get keyboard input. dx and dy represent the direction the player is facing on each axis
            dx = 0
            if keyboard.left:
                dx = -1
            elif keyboard.right:
                dx = 1

            dy = 0
            if keyboard.up:
                dy = -1
            elif keyboard.down:
                dy = 1

            # Move in the relevant directions by the specified number of pixels. The purpose of 3 - abs(dy) is to
            # generate vectors which look either like (3,0) (which is 3 units long) or (2, 2) (which is sqrt(8) long)
            # so we move roughly the same distance regardless of whether we're travelling straight along the x or y axis.
            # or at 45 degrees. Without this, we would move noticeably faster when travelling diagonally.
            self.move(dx, 0, 3 - abs(dy))
            self.move(0, dy, 3 - abs(dx))

            # When the player presses a key to start handing in a new direction, we don't want the sprite to just
            # instantly change to facing in that new direction. That would look wrong, since in the real world vehicles
            # can't just suddenly change direction in the blink of an eye.
            # Instead, we want the vehicle to turn to face the new direction over several frames. If the vehicle is
            # currently facing down, and the player presses the left arrow key, the vehicle should first turn to face
            # diagonally down and to the left, and then turn to face left.

            # Each number in the following list corresponds to a direction - 0 is up, 1 is up and to the right, and
            # so on in clockwise order. -1 means no direction.
            # Think of it as a grid, as follows:
            # 7  0  1
            # 6 -1  2
            # 5  4  3
            directions = [7,0,1,6,-1,2,5,4,3]

            # But! If you look at the values that self.direction actually takes on during the game, you only see
            # numbers from 0 to 3. This is because although there are eight possible directions of travel, there are
            # only four orientations of the player vehicle. The same sprite, for example, is used if the player is
            # travelling either left or right. This is why the direction is ultimately clamped to a range of 0 to 4.
            # 0 = facing up or down
            # 1 = facing top right or bottom left
            # 2 = facing left or right
            # 3 = facing bottom right or top left

            # # It can be useful to think of the vehicle as being able to drive both forwards and backwards.

            # Choose the relevant direction from the above list, based on dx and dy
            dir = directions[dx+3*dy+4]

            # Every other frame, if the player is pressing a key to move in a particular direction, update the current
            # direction to rotate towards facing the new direction
            if self.timer % 2 == 0 and dir >= 0:

                # We first calculate the difference between the desired direction and the current direction.
                difference = (dir - self.direction)

                # We use the following list to decide how much to rotate by each frame, based on difference.
                # It's easiest to think about this by just considering the first four direction values - 0 to 3,
                # corresponding to facing up, to fit into the bottom right. However, because of the symmetry of the
                # player sprites as described above, these calculations work for all possible directions.
                # If there is no difference, no rotation is required.
                # If the difference is 1, we rotate by 1 (clockwise)
                # If the difference is 2, then the target direction is at right angles to the current direction,
                # so we have a free choice as to whether to turn clockwise or anti-clockwise to align with the
                # target direction. We choose clockwise.
                # If the difference is three, the symmetry of the player sprites means that we can reach the desired
                # animation frame by rotating one unit anti-clockwise.
                rotation_table = [0, 1, 1, -1]

                rotation = rotation_table[difference % 4]
                self.direction = (self.direction + rotation) % 4


            self.fire_timer -= 1

            # Fire cannon (or allow firing animation to finish)
            if self.fire_timer < 0 and (self.frame > 0 or keyboard.space):
                if self.frame == 0:
                    # Create a bullet
                    game.play_sound("laser")
                    game.bullets.append(Bullet((self.x, self.y - 8)))
                self.frame = (self.frame + 1) % 3
                self.fire_timer = Player.RELOAD_TIME

            # Check to see if any enemy segments collide with the player, as well as the flying enemy.
            # We create a list consisting of all enemy segments, and append another list containing only the
            # flying enemy.
            all_enemies = game.segments + [game.flying_enemy]
            for enemy in all_enemies:
                # The flying enemy might not exist, in which case its value
                # will be None. We cannot call a method or access any attributes
                # of a 'None' object, so we must first check for that case.
                # "if object:" is shorthand for "if object != None".
                if enemy and enemy.collidepoint(self.pos):
                    # Collision has occurred, check to see whether player is invulnerable
                    if self.timer > Player.INVULNERABILITY_TIME:
                        game.play_sound("player_explode")
                        game.explosions.append(Explosion(self.pos, 1))
                        self.alive = False
                        self.timer = 0
                        self.lives -= 1
        else:
            # Not alive
            # Wait a while before respawning
            if self.timer > Player.RESPAWN_TIME:
                # Respawn
                self.alive = True
                self.timer = 0
                self.pos = (240, 768)
                game.clear_rocks_for_respawn(*self.pos)     # Ensure there are no rocks at the player's respawn position

        # Display the player sprite if alive - BUT, if player is currently invulnerable, due to having just respawned,
        # switch between showing and not showing the player sprite on alternate frames
        invulnerable = self.timer > Player.INVULNERABILITY_TIME
        if self.alive and (invulnerable or self.timer % 2 == 0):
            self.image = "player" + str(self.direction) + str(self.frame)
        else:
            self.image = "blank"

class FlyingEnemy(Actor):
    def __init__(self, player_x):
        # Choose which side of the screen we start from. Don't start right next to the player as that would be
        # unfair - if not near player, start on a random side
        side = 1 if player_x < 160 else 0 if player_x > 320 else randint(0, 1)

        super().__init__("blank", (550*side-35, 688))

        # Always moves in the same X direction, but randomly pauses to just fly straight up or down
        self.moving_x = 1       # 0 if we're currently moving only vertically, 1 if moving along x axis (as well as y axis)
        self.dx = 1 - 2 * side  # Move left or right depending on which side of the screen we're on
        self.dy = choice([-1, 1])   # Start moving either up or down
        self.type = randint(0, 2)   # 3 different colours

        self.health = 1

        self.timer = 0

    def update(self):
        self.timer += 1

        # Move
        self.x += self.dx * self.moving_x * (3 - abs(self.dy))
        self.y += self.dy * (3 - abs(self.dx * self.moving_x))

        if self.y < 592 or self.y > 784:
            # Gone too high or low - reverse y direction
            self.moving_x = randint(0, 1)
            self.dy = -self.dy

        anim_frame = str([0, 2, 1, 2][(self.timer // 4) % 4])
        self.image = "meanie" + str(self.type) + anim_frame


class Rock(Actor):
    def __init__(self, x, y, totem=False):
        # Use a custom anchor point for totem rocks, which are taller than other rocks
        anchor = (24, 60) if totem else CENTRE_ANCHOR
        super().__init__("blank", cell2pos(x, y), anchor=anchor)

        self.type = randint(0, 3)

        if totem:
            # Totem rocks take five hits and give bonus points
            game.play_sound("totem_create")
            self.health = 5
            self.show_health = 5
        else:
            # Non-totem rocks are initially displayed as if they have one health, and animate until they
            # show the actualy sprite for their health level - resulting in a 'growing' animation.
            self.health = randint(3, 4)
            self.show_health = 1

        self.timer = 1

    def damage(self, amount, damaged_by_bullet=False):
        # Damage can occur by being hit by bullets, or by being destroyed by a segment, or by being cleared from the
        # player's respawn location. Points can be earned by hitting special "totem" rocks, which have 5 health, but
        # this should only happen when they are hit by a bullet.
        if damaged_by_bullet and self.health == 5:
            game.play_sound("totem_destroy")
            game.score += 100
        else:
            if amount > self.health - 1:
                game.play_sound("rock_destroy")
            else:
                game.play_sound("hit", 4)

        game.explosions.append(Explosion(self.pos, 2 * (self.health == 5)))
        self.health -= amount
        self.show_health = self.health

        self.anchor, self.pos = CENTRE_ANCHOR, self.pos

        # Return False if we've lost all our health, otherwise True
        return self.health < 1

    def update(self):
        self.timer += 1

        # Every other frame, update the growing animation
        if self.timer % 2 == 1 and self.show_health < self.health:
            self.show_health += 1

        if self.health == 5 and self.timer > 200:
            # Totem rocks turn into normal rocks if not shot within 200 frames
            self.damage(1)

        colour = str(max(game.wave, 0) % 3)
        health = str(max(self.show_health - 1, 0))
        self.image = "rock" + colour + str(self.type) + health


class Bullet(Actor):
    def __init__(self, pos):
        super().__init__("bullet", pos)

        self.done = False

    def update(self):
        # Move up the screen, 24 pixels per frame
        self.y -= 24

        # game.damage checks to see if there is a rock at the given position - if so, it damages
        # the rock and returns True
        # An asterisk before a list or tuple will unpack the contents into separate values
        grid_cell = pos2cell(*self.pos)
        if game.damage(*grid_cell, 1, True):
            # Hit a rock - destroy self
            self.done = True
        else:
            # Didn't hit a rock
            # Check each myriapod segment, and the flying enemy, to see if this bullet collides with them
            for obj in game.segments + [game.flying_enemy]:
                # Is this a valid object reference, and if so, does this bullet's location overlap with the
                # object's rectangle? (collidepoint is a method from Pygame's Rect class)
                if obj and obj.collidepoint(self.pos):
                    # Create explosion
                    game.explosions.append(Explosion(obj.pos, 2))

                    obj.health -= 1

                    # Is the object an instance of the Segment class?
                    if isinstance(obj, Segment):
                        # Should we create a new rock in the segment's place? Health must be zero, there must be no
                        # rock there already, and the player sprite must not overlap with the location
                        if obj.health == 0 and not game.grid[obj.cell_y][obj.cell_x] and game.allow_movement(game.player.x, game.player.y, obj.cell_x, obj.cell_y):
                            # Create new rock - 20% chance of being a totem
                            game.grid[obj.cell_y][obj.cell_x] = Rock(obj.cell_x, obj.cell_y, random() < .2)

                        game.play_sound("segment_explode")
                        game.score += 10
                    else:
                        # If it's not a segment, it must be the flying enemy
                        game.play_sound("meanie_explode")
                        game.score += 20

                    self.done = True    # Destroy self

                    # Don't continue the for loop, this bullet has hit something so shouldn't hit anything else
                    return


# SEGMENT MOVEMENT
# The code below creates several constants used in the Segment class in relation to movement and directions

# Each myriapod segment moves in relation to its current grid cell.
# A segment enters a cell from a particular edge (stored in 'in_edge' in the Segment class)
# After five frames it decides which edge it's going leave that cell through (stored in out_edge).
# For example, it might carry straight on and leave through the opposite edge from the one it started at.
# Or it might turn 90 degrees and leave through an edge to its left or right.
# In this case it initially turn 45 degrees and continues along that path for 8 frames. It then turns another
# 45 degrees, at which point they are heading directly towards the next grid cell.
# A segment spends a total of 16 frames in each cell. Within the update method, the variable 'phase' refers to
# where it is in that cycle - 0 meaning it's just entered a grid cell, and 15 meaning it's about to leave it.

# Let's imagine the case where a segment enters from the left edge of a cell and then turns to leave from the
# bottom edge. The segment will initially move along the horizontal (X) axis, and will end up moving along the
# vertical (Y) axis. In this case we'll call the X axis the primary axis, and the Y axis the secondary axis.
# The lists SECONDARY_AXIS_SPEED and SECONDARY_AXIS_POSITIONS are used to determine the movement of the segment.
# This is explained in more detail in the Segment.update method.


# In Python, multiplying a list by a number creates a list where the contents
# are repeated the specified number of times. So the code below is equivalent to:
# SECONDARY_AXIS_SPEED = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1 , 1, 2, 2, 2, 2]
# This list represents how much the segment moves along the secondary axis, in situations where it makes two 45° turns
# as described above. For the first four frames it doesn't move at all along the secondary axis. For the next eight
# frames it moves at one pixel per frame, then for the last four frames it moves at two pixels per frame.
SECONDARY_AXIS_SPEED = [0]*4 + [1]*8 + [2]*4


# The code below creates a list of 16 elements, where each element is the sum of all the equivalent elements in the
# SECONDARY_AXIS_SPEED list up to that point.
# It is equivalent to writing:
# SECONDARY_AXIS_POSITIONS = [0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14]
# This list stores the total secondary axis movement that will have occurred at each phase in the segment's movement
# through the current grid cell (if the segment is turning)
SECONDARY_AXIS_POSITIONS = [sum(SECONDARY_AXIS_SPEED[:i]) for i in range(16)]


# Constants representing directions
DIRECTION_UP = 0
DIRECTION_RIGHT = 1
DIRECTION_DOWN = 2
DIRECTION_LEFT = 3

# X and Y directions indexed into by in_edge and out_edge in Segment
# The indices correspond to the direction numbers above, i.e. 0 = up, 1 = right, 2 = down, 3 = left
DX = [0,1,0,-1]
DY = [-1,0,1,0]

def inverse_direction(dir):
    if dir == DIRECTION_UP:
        return DIRECTION_DOWN
    elif dir == DIRECTION_RIGHT:
        return DIRECTION_LEFT
    elif dir == DIRECTION_DOWN:
        return DIRECTION_UP
    elif dir == DIRECTION_LEFT:
        return DIRECTION_RIGHT

def is_horizontal(dir):
    return dir == DIRECTION_LEFT or dir == DIRECTION_RIGHT


class Segment(Actor):
    def __init__(self, cx, cy, health, fast, head):
        super().__init__("blank")

        # Grid cell positions
        self.cell_x = cx
        self.cell_y = cy

        self.health = health

        # Determines whether the 'fast' version of the sprite is used. Note that the actual speed of the myriapod is
        # determined by how much time is included in the State.update method
        self.fast = fast

        self.head = head        # Should this segment use the head sprite?

        # Each myriapod segment moves in a defined pattern within its current cell, before moving to the next one.
        # It will start at one of the edges - represented by a number, where 0=down,1=right,2=up,3=left
        # self.in_edge stores the edge through which it entered the cell.
        # Several frames after entering a cell, it chooses which edge to leave through - stored in out_edge
        # The path it follows is explained in the update and rank methods
        self.in_edge = DIRECTION_LEFT
        self.out_edge = DIRECTION_RIGHT

        self.disallow_direction = DIRECTION_UP      # Prevents segment from moving in a particular direction
        self.previous_x_direction = 1               # Used to create winding/snaking motion

    def rank(self):
        # The rank method creates and returns a function. Don't worry if this seems a strange concept - it is
        # fairly advanced stuff. The returned function is passed to Python's 'min' function in the update method,
        # as the 'key' optional parameter. min then calls this function with the numbers 0 to 3, representing the four
        # directions

        def inner(proposed_out_edge):
            # proposed_out_edge is a number between 0 and 3, representing a possible direction to move - see DIRECTION_UP etc and DX/DY above
            # This function returns a tuple consisting of a series of factors determining which grid cell the segment should try to move into next.
            # These are not absolute rules - rather they are used to rank the four directions in order of preference,
            # i.e. which direction is the best (or at least, least bad) to move in. The factors are boolean (True or False)
            # values. A value of False is preferable to a value of True.
            # The order of the factors in the returned tuple determines their importance in deciding which way to go,
            # with the most important factor coming first.
            new_cell_x = self.cell_x + DX[proposed_out_edge]
            new_cell_y = self.cell_y + DY[proposed_out_edge]

            # Does this direction take us to a cell which is outside the grid?
            # Note: when the segments start, they are all outside the grid so this would be True, except for the case of
            # walking onto the top-left cell of the grid. But the end result of this and the following factors is that
            # it will still be allowed to continue walking forwards onto the screen.
            out = new_cell_x < 0  or new_cell_x > num_grid_cols - 1 or new_cell_y < 0 or new_cell_y > num_grid_rows - 1

            # We don't want it to to turn back on itself..
            turning_back_on_self = proposed_out_edge == self.in_edge

            # ..or go in a direction that's disallowed (see comments in update method)
            direction_disallowed = proposed_out_edge == self.disallow_direction

            # Check to see if there's a rock at the proposed new grid cell.
            # rock will either be the Rock object at the new grid cell, or None.
            # It will be set to None if there is no Rock object is at the new location, or if the new location is
            # outside the grid. We also have to account for the special case where the segment is off the left-hand
            # side of the screen on the first row, where it is initially created. We mustn't try to access that grid
            # cell (unlike most languages, in Python trying to access a list index with negative value won't necessarily
            # result in a crash, but it's still not a good idea)
            if out or (new_cell_y == 0 and new_cell_x < 0):
                rock = None
            else:
                rock = game.grid[new_cell_y][new_cell_x]

            rock_present = rock != None

            # Is new cell already occupied by another segment, or is another segment trying to enter my cell from
            # the opposite direction?
            occupied_by_segment = (new_cell_x, new_cell_y) in game.occupied or (self.cell_x, self.cell_y, proposed_out_edge) in game.occupied

            # Prefer to move horizontally, unless there's a rock in the way.
            # If there are rocks both horizontally and vertically, prefer to move vertically
            if rock_present:
                horizontal_blocked = is_horizontal(proposed_out_edge)
            else:
                horizontal_blocked = not is_horizontal(proposed_out_edge)

            # Prefer not to go in the previous horizontal direction after we move up/down
            same_as_previous_x_direction = proposed_out_edge == self.previous_x_direction

            # Finally we create and return a tuple of factors determining which cell segment should try to move into next.
            # Most important first - e.g. we shouldn't enter a new cell if if's outside the grid
            return (out, turning_back_on_self, direction_disallowed, occupied_by_segment, rock_present, horizontal_blocked, same_as_previous_x_direction)

        return inner

    def update(self):
        # Segments take either 16 or 8 frames to pass through each grid cell, depending on the amount by which
        # game.time is updated each frame. phase will be a number between 0 and 15 indicating where we're at
        # in that cycle.
        phase = game.time % 16

        if phase == 0:
            # At this point, the segment is entering a new grid cell. We first update our current grid cell coordinates.
            self.cell_x += DX[self.out_edge]
            self.cell_y += DY[self.out_edge]

            # We then need to update in_edge. If, for example, we left the previous cell via its right edge, that means
            # we're entering the new cell via its left edge.
            self.in_edge = inverse_direction(self.out_edge)

            # During normal gameplay, once a segment reaches the bottom of the screen, it starts moving up again.
            # Once it reaches row 18, it starts moving down again, so that it remains a threat to the player.
            # During the title screen, we allow segments to go all the way back up to the top of the screen.
            if self.cell_y == (18 if game.player else 0):
                self.disallow_direction = DIRECTION_UP
            if self.cell_y == num_grid_rows-1:
                self.disallow_direction = DIRECTION_DOWN

        elif phase == 4:
            # At this point we decide which new cell we're going to go into (and therefore, which edge of the current
            # cell we will leave via - to be stored in out_edge)
            # range(4) generates all the numbers from 0 to 3 (corresponding to DIRECTION_UP etc)
            # Python's built-in 'min' function usually chooses the lowest number, so would usually return 0 as the result.
            # But if the optional 'key' argument is specified, this changes how the function determines the result.
            # The rank function (see above) returns a function (named 'inner' in rank), which min calls to decide
            # how the items should be ordered. The argument to inner represents a possible direction to move in.
            # The 'inner' function returns a tuple of boolean values - for example: (True,False,False,True,etc..)
            # When Python compares two such tuples, it considers values of False to be less than values of True,
            # and values that come earlier in the sequence are more significant than later values. So (False,True)
            # would be considered less than (True,False).
            self.out_edge = min(range(4), key = self.rank())

            if is_horizontal(self.out_edge):
                self.previous_x_direction = self.out_edge

            new_cell_x = self.cell_x + DX[self.out_edge]
            new_cell_y = self.cell_y + DY[self.out_edge]
            
            # Destroy any rock that might be in the new cell
            if new_cell_x >= 0 and new_cell_x < num_grid_cols:
                game.damage(new_cell_x, new_cell_y, 5)

            # Set new cell as occupied. It's a case of whichever segment is processed first, gets first dibs on a cell
            # The second line deals with the case where two segments are moving towards each other and are in
            # neighbouring cells. It allows a segment to tell if another segment trying to enter its cell from
            # the opposite direction
            game.occupied.add((new_cell_x, new_cell_y))
            game.occupied.add((new_cell_x, new_cell_y, inverse_direction(self.out_edge)))

        # turn_idx tells us whether the segment is going to be making a 90 degree turn in the current cell, or moving
        # in a straight line. 1 = anti-clockwise turn, 2 = straight ahead, 3 = clockwise turn, 0 = leaving through same
        # edge from which we entered (unlikely to ever happen in practice)
        turn_idx = (self.out_edge - self.in_edge) % 4

        # Calculate segment offset in the cell, measured from the cell's centre
        # We start off assuming that the segment is starting from the top of the cell - i.e. self.in_edge being DIRECTION_UP,
        # corresponding to zero. The primary and secondary axes, as described under "SEGMENT MOVEMENT" above, are Y and X.
        # We then apply a calculation to rotate these X and Y offsets, based on the actual direction the segment is coming from.
        # Let's take as an example the case where the segment is moving in a straight line from top to bottom.
        # We calculate offset_x by multiplying SECONDARY_AXIS_POSITIONS[phase] by 2-turn_idx. In this case, turn_idx
        # will be 2.  So 2 - turn_idx will be zero. Multiplying anything by zero gives zero, so we end up with no
        # movement on the X axis - which is what we want in this case.
        # The starting point for the offset_y calculation is that the segment starts at an offset of -16 and must cover
        # 32 pixels over the 16 phases - therefore we must multiply phase by 2. We then subtract the result of the
        # previous line, in which stolen_y_movement was calculated by multiplying SECONDARY_AXIS_POSITIONS[phase] by
        # turn_idx % 2.  mod 2 gives either zero (if turn_idx is 0 or 2), or 1 if it's 1 or 3. In the case we're looking
        # at, turn_idx is 2, so stolen_y_movement is zero.
        # The end result of all this is that in the case where the segment is moving in a straight line through a cell,
        # it just moves at 2 pixels per frame along the primary axis. If it's turning, it starts out moving at 2px
        # per frame on the primary axis, but then starts moving along the secondary axis based on the values in
        # SECONDARY_AXIS_POSITIONS. In this case we don't want it to continue moving along the primary axis - it should
        # initially slow to moving at 1px per phase, and then stop moving completely. Effectively, the secondary axis
        # is stealing movement from the primary axis - hence the name 'stolen_y_movement'
        offset_x = SECONDARY_AXIS_POSITIONS[phase] * (2 - turn_idx)
        stolen_y_movement = (turn_idx % 2) * SECONDARY_AXIS_POSITIONS[phase]
        offset_y = -16 + (phase * 2) - stolen_y_movement

        # A rotation matrix is a set of numbers which, when multiplied by a set of coordinates, result in those
        # coordinates being rotated. Recall that the code above  makes the assumption that segment is starting from the
        # top edge of the cell and moving down. The code below chooses the appropriate rotation matrix based on the
        # actual edge the segment started from, and then modifies offset_x and offset_y based on this rotation matrix.
        rotation_matrix = [[1,0,0,1],[0,-1,1,0],[-1,0,0,-1],[0,1,-1,0]][self.in_edge]
        offset_x, offset_y = offset_x * rotation_matrix[0] + offset_y * rotation_matrix[1], offset_x * rotation_matrix[2] + offset_y * rotation_matrix[3]

        # Finally, we can calculate the segment's position on the screen. See cell2pos function above.
        self.pos = cell2pos(self.cell_x, self.cell_y, offset_x, offset_y)

        # We now need to decide which image the segment should use as its sprite.
        # Images for segment sprites follow the format 'segABCDE' where A is 0 or 1 depending on whether this is a
        # fast-moving segment, B is 0 or 1 depending on whether we currently have 1 or 2 health, C is whether this
        # is the head segment of a myriapod, D represents the direction we're facing (0 = up, 1 = top right,
        # up to 7 = top left) and E is how far we are through the walking animation (0 to 3)

        # Three variables go into the calculation of the direction. turn_idx tells us if we're making a turn in this
        # cell - and if so, whether we're turning clockwise or anti-clockwise. self.in_edge tells us which side of the
        # grid cell we entered from. And we can use SECONDARY_AXIS_SPEED[phase] to find out whether we should be facing
        # along the primary axis, secondary axis or diagonally between them.
        # (turn_idx - 2) gives 0 if straight, -1 if turning anti-clockwise, 1 if turning clockwise
        # Multiplying this by SECONDARY_AXIS_SPEED[phase] gives 0 if we're not doing a turn in this cell, or if
        # we are going to be turning but have not yet begun to turn. If we are doing a turn in this cell, and we're
        # at a phase where we should be showing a sprite with a new rotation, the result will be -1 or 1 if we're
        # currently in the first (45°) part of a turn, or -2 or 2 if we have turned 90°.
        # The next part of the calculation multiplies in_edge by 2 and then adds the result to the result of the previous
        # part. in_edge will be a number from 0 to 3, representing all possible directions in 90° increments.
        # It must be multiplied by two because the direction value we're calculating will be a number between 0 and 7,
        # representing all possible directions in 45° increments.
        # In the sprite filenames, the penultimate number represents the direction the sprite is facing, where a value
        # of zero means it's facing up. But in this code, if, for example, in_edge were zero, this means the segment is
        # coming from the top edge of its cell, and therefore should be facing down. So we add 4 to account for this.
        # After all this, we may have ended up with a number outside the desired range of 0 to 7. So the final step
        # is to MOD by 8.
        direction = ((SECONDARY_AXIS_SPEED[phase] * (turn_idx - 2)) + (self.in_edge * 2) + 4) % 8

        leg_frame = phase // 4  # 16 phase cycle, 4 frames of animation

        # Converting a boolean value to an integer gives 0 for False and 1 for True. We then need to convert the
        # result to a string, as an integer can't be appended to a string.
        self.image = "seg" + str(int(self.fast)) + str(int(self.health == 2)) + str(int(self.head)) + str(direction) + str(leg_frame)

class Game:
    def __init__(self, player=None):
        self.wave = -1
        self.time = 0

        self.player = player

        # Create empty grid of 14 columns, 25 rows, each element intially just containing the value 'None'
        # Rocks will be added to the grid later
        self.grid = [[None] * num_grid_cols for y in range(num_grid_rows)]

        self.bullets = []
        self.explosions = []
        self.segments = []

        self.flying_enemy = None

        self.score = 0

    def damage(self, cell_x, cell_y, amount, from_bullet=False):
        # Find the rock at this grid cell (or None if no rock here)
        rock = self.grid[cell_y][cell_x]

        if rock != None:
            # rock.damage returns False if the rock has lost all its health - in this case, the grid cell will be set
            # to None, overwriting the rock object reference
            if rock.damage(amount, from_bullet):
                self.grid[cell_y][cell_x] = None

        # Return whether or not there was a rock at this position
        return rock != None

    def allow_movement(self, x, y, ax=-1, ay=-1):
        # ax/ay are only supplied when a segment is being destroyed, and we check to see if we should create a new
        # rock in the segment's place. They indicate a grid cell location where we're planning to create the new rock,
        # we need to ensure the new rock would not overlap with the player sprite

        # Don't go off edge of screen or above the player zone
        if x < 40 or x > 440 or y < 592 or y > 784:
            return False

        # Get coordinates of corners of player sprite's collision rectangle
        x0, y0 = pos2cell(x-18, y-10)
        x1, y1 = pos2cell(x+18, y+10)

        # Check each corner against grid
        for yi in range(y0, y1+1):
            for xi in range(x0, x1+1):
                if self.grid[yi][xi] or xi == ax and yi == ay:
                    return False

        return True

    def clear_rocks_for_respawn(self, x, y):
        # Destroy any rocks that might be overlapping with the player when they respawn
        # Could be more than one rock, hence the loop
        x0, y0 = pos2cell(x-18, y-10)
        x1, y1 = pos2cell(x+18, y+10)

        for yi in range(y0, y1+1):
            for xi in range(x0, x1+1):
                self.damage(xi, yi, 5)

    def update(self):
        # Increment time - used by segments. Time moves twice as fast every fourth wave.
        self.time += (2 if self.wave % 4 == 3 else 1)

        # At the start of each frame, we reset occupied to be an empty set. As each individual myriapod segment is
        # updated, it will create entries in the occupied set to indicate that other segments should not attempt to
        # enter its current grid cell. There are two types of entries that are created in the occupied set. One is a
        # tuple consisting of a pair of numbers, representing grid cell coordinates. The other is a tuple consisting of
        # three numbers - the first two being grid cell coordinates, the third representing an edge through which a
        # segment is trying to enter a cell.
        # It is only used for myriapod segments - not rocks. Those are stored in self.grid.
        self.occupied = set()

        # Call update method on all objects. grid is a list of lists, equivalent to a 2-dimensional array,
        # so sum can be used to produce a single list containing all grid objects plus the contents of the other
        # Actor lists. The player and flying enemy, which are object references rather than lists, are appended as single-item lists.
        all_objects = sum(self.grid, self.bullets + self.segments + self.explosions + [self.player] + [self.flying_enemy])
        for obj in all_objects:
            if obj:
                obj.update()

        # Recreate the bullets list, which will contain all existing bullets except those which have gone off the screen or have hit something
        self.bullets = [b for b in self.bullets if b.y > 0 and not b.done]

        # Recreate the explosions list, which will contain all existing explosions except those which have completed their animations
        self.explosions = [e for e in self.explosions if not e.timer == 31]

        # Recreate the segments list, which will contain all existing segments except those whose health is zero
        self.segments = [s for s in self.segments if s.health > 0]

        if self.flying_enemy:
            # Destroy flying enemy if it goes off the left or right sides of the screen, or health is zero
            if self.flying_enemy.health <= 0 or self.flying_enemy.x < -35 or self.flying_enemy.x > 515:
                self.flying_enemy = None
        elif random() < .01:    # If there is no flying enemy, small chance of creating one each frame
            self.flying_enemy = FlyingEnemy(self.player.x if self.player else 240)

        if self.segments == []:
            # No myriapod segments - start a new wave
            # First, ensure there are enough rocks. Count the number of rocks in the grid and if there aren't enough,
            # create one per frame. Initially there should be 30 rocks - each wave, this goes up by one.
            num_rocks = 0
            for row in self.grid:
                for element in row:
                    if element != None:
                        num_rocks += 1
            if num_rocks < 31+self.wave:
                while True:
                    x, y = randint(0, num_grid_cols-1), randint(1, num_grid_rows-3)     # Leave last 2 rows rock-free
                    if self.grid[y][x] == None:
                        self.grid[y][x] = Rock(x, y)
                        break
            else:
                # New wave and enough rocks - create a new myriapod
                game.play_sound("wave")
                self.wave += 1
                self.time = 0
                self.segments = []
                num_segments = 8 + self.wave // 4 * 2   # On the first four waves there are 8 segments - then 10, and so on
                for i in range(num_segments):
                    if DEBUG_TEST_RANDOM_POSITIONS:
                        cell_x, cell_y = randint(1, 7), randint(1, 7)
                    else:
                        cell_x, cell_y = -1-i, 0
                    # Determines whether segments take one or two hits to kill, based on the wave number.
                    # e.g. on wave 0 all segments take one hit; on wave 1 they alternate between one and two hits
                    health = [[1,1],[1,2],[2,2],[1,1]][self.wave % 4][i % 2]
                    fast = self.wave % 4 == 3   # Every fourth myriapod moves faster than usual
                    head = i == 0           # The first segment of each myriapod is the head
                    self.segments.append(Segment(cell_x, cell_y, health, fast, head))

        return self

    def draw(self):
        screen.blit("bg" + str(max(self.wave, 0) % 3), (0, 0))

        # Create a list of all grid locations and other objects which need to be drawn
        # (Most grid locations will be set to None as they are unoccupied, hence the check "if obj:" further down)
        all_objs = sum(self.grid, self.bullets + self.segments + self.explosions + [self.player])

        # We want to draw objects in order based on their Y position. Objects further down the screen should be drawn
        # after (and therefore in front of) objects higher up the screen. We can use Python's built-in sort function
        # to put the items in the desired order, before we draw them. The following function specifies the criteria
        # used to decide how the objects are sorted.
        def sort_key(obj):
            # Returns a tuple consisting of two elements. The first is whether the object is an instance of the
            # Explosion class (True or False). A value of true means it will be displayed in front of other objects.
            # The second element is a number - either the objects why position, or zero if obj is 'None'
            return (isinstance(obj, Explosion), obj.y if obj else 0)

        # Sort list using the above function to determine order
        all_objs.sort(key=sort_key)

        # Draw the flying enemy on top of everything else
        all_objs.append(self.flying_enemy)

        # Draw the objects
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
            state = State.PLAY
            game = Game(Player((240, 768)))  # Create new Game object, with a Player object

        game.update()

    elif state == State.PLAY:
        if game.player.lives == 0 and game.player.timer == 100:
            sounds.gameover.play()
            state = State.GAME_OVER
        else:
            game.update()

    elif state == State.GAME_OVER:
        if space_pressed():
            # Switch to menu state, and create a new game object without a player
            state = State.MENU
            game = Game()

def draw():
    # Draw the game, which covers both the game during gameplay but also the game displaying in the background
    # during the main menu and game over screens
    game.draw()

    if state == State.MENU:
        # Display logo
        screen.blit("title", (0, 0))

        # 14 frames of animation for "Press space to start", updating every 4 frames
        screen.blit("space" + str((game.time // 4) % 14), (0, 420))

    elif state == State.PLAY:
        # Display number of lives
        for i in range(game.player.lives):
            screen.blit("life", (i*40+8, 4))

        # Display score
        score = str(game.score)
        for i in range(1, len(score)+1):
            # In Python, a negative index into a list (or in this case, into a string) gives you items in reverse order,
            # e.g. 'hello'[-1] gives 'o', 'hello'[-2] gives 'l', etc.
            digit = score[-i]
            screen.blit("digit"+digit, (468-i*24, 5))

    elif state == State.GAME_OVER:
        # Display "Game Over" image
        screen.blit("over", (0, 0))

# Set up music on game start
try:
    pygame.mixer.quit()
    pygame.mixer.init(44100, -16, 2, 1024)

    music.play("theme")
    music.set_volume(0.4)
except:
    # If an error occurs, just ignore it
    pass

# Set the initial game state
state = State.MENU

# Create a new Game object, without a Player object
game = Game()

pgzrun.go()
