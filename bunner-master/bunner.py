# If the window is too tall to fit on the screen, check your operating system display settings and reduce display
# scaling if it is enabled.
import pgzero, pgzrun, pygame, sys
from random import *
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
TITLE = "Infinite Bunner"

ROW_HEIGHT = 40

# See what happens when you change this to True
DEBUG_SHOW_ROW_BOUNDARIES = False

# The MyActor class extends Pygame Zero's Actor class by allowing an object to have a list of child objects,
# which are drawn relative to the parent object.
class MyActor(Actor):
    def __init__(self, image, pos, anchor=("center", "bottom")):
        super().__init__(image, pos, anchor)

        self.children = []

    def draw(self, offset_x, offset_y):
        self.x += offset_x
        self.y += offset_y

        super().draw()
        for child_obj in self.children:
            child_obj.draw(self.x, self.y)

        self.x -= offset_x
        self.y -= offset_y

    def update(self):
        for child_obj in self.children:
            child_obj.update()

# The eagle catches the rabbit if it goes off the bottom of the screen
class Eagle(MyActor):
    def __init__(self, pos):
        super().__init__("eagles", pos)

        self.children.append(MyActor("eagle", (0, -32)))

    def update(self):
        self.y += 12

class PlayerState(Enum):
    ALIVE = 0
    SPLAT = 1
    SPLASH = 2
    EAGLE = 3

# Constants representing directions
DIRECTION_UP = 0
DIRECTION_RIGHT = 1
DIRECTION_DOWN = 2
DIRECTION_LEFT = 3

direction_keys = [keys.UP, keys.RIGHT, keys.DOWN, keys.LEFT]

# X and Y directions indexed into by in_edge and out_edge in Segment
# The indices correspond to the direction numbers above, i.e. 0 = up, 1 = right, 2 = down, 3 = left
# Numbers 0 to 3 correspond to up, right, down, left
DX = [0,4,0,-4]
DY = [-4,0,4,0]

class Bunner(MyActor):
    MOVE_DISTANCE = 10

    def __init__(self, pos):
        super().__init__("blank", pos)

        self.state = PlayerState.ALIVE

        self.direction = 2
        self.timer = 0

        # If a control input is pressed while the rabbit is in the middle of jumping, it's added to the input queue
        self.input_queue = []

        # Keeps track of the furthest distance we've reached so far in the level, for scoring
        # (Level Y coordinates decrease as the screen scrolls)
        self.min_y = self.y

    def handle_input(self, dir):
        # Find row that player is trying to move to. This may or may not be the row they're currently standing on,
        # depending on whether the proposed movement would take them onto a different row
        for row in game.rows:
            if row.y == self.y + Bunner.MOVE_DISTANCE * DY[dir]:
                # Found the target row
                # Can the player move to the new location? Can't move if there's something in the way
                # (or if the new location is off the screen)
                if row.allow_movement(self.x + Bunner.MOVE_DISTANCE * DX[dir]):
                    # It's okay to move here, so set direction and timer. Player will move one pixel per frame
                    # for the specified number of frames
                    self.direction = dir
                    self.timer = Bunner.MOVE_DISTANCE
                    game.play_sound("jump", 1)

                # No need to continue searching
                return

    def update(self):
        # Check each control direction
        for direction in range(4):
            if key_just_pressed(direction_keys[direction]):
                self.input_queue.append(direction)

        if self.state == PlayerState.ALIVE:
            # While the player is alive, the timer variable is used for movement. If it's zero, the player is on
            # the ground. If it's above zero, they're currently jumping to a new location.

            # Are we on the ground, and are there inputs to process?
            if self.timer == 0 and len(self.input_queue) > 0:
                # Take the next input off the queue and process it
                self.handle_input(self.input_queue.pop(0))

            land = False
            if self.timer > 0:
                # Apply movement
                self.x += DX[self.direction]
                self.y += DY[self.direction]
                self.timer -= 1
                land = self.timer == 0      # If timer reaches zero, we've just landed

            current_row = None
            for row in game.rows:
                if row.y == self.y:
                    current_row = row
                    break

            if current_row:
                # Row.check receives the player's X coordinate and returns the new state the player should be in
                # (normally ALIVE, but SPLAT or SPLASH if they've collided with a vehicle or if they've fallen in
                # the water). It also returns a second result which is only used if there was a collision, and even
                # then only for certain collisions. When the new state is SPLAT, we will add a new child object to the
                # current row, with the appropriate 'splat' image. In this case, the second result returned from
                # check_collision is a Y offset which affects the position of this new child object. If the player is
                # hit by a car the Y offset is zero, but if they are hit by a train the returned offset is 8 as this
                # positioning looks a little better.
                self.state, dead_obj_y_offset = current_row.check_collision(self.x)
                if self.state == PlayerState.ALIVE:
                    # Water rows move the player along the X axis, if standing on a log
                    self.x += current_row.push()

                    if land:
                        # Just landed - play sound effect appropriate to the current row
                        current_row.play_sound()
                else:
                    if self.state == PlayerState.SPLAT:
                        # Add 'splat' graphic to current row with the specified position and Y offset
                        current_row.children.insert(0, MyActor("splat" + str(self.direction), (self.x, dead_obj_y_offset)))
                    self.timer = 100
            else:
                # There's no current row - either because player is currently changing row, or the row they were on
                # has been deleted. Has the player gone off the bottom of the screen?
                if self.y > game.scroll_pos + HEIGHT + 80:
                    # Create eagle
                    game.eagle = Eagle((self.x, game.scroll_pos))
                    self.state = PlayerState.EAGLE
                    self.timer = 150
                    game.play_sound("eagle")

            # Limit x position so player doesn't go off the screen. The player movement code doesn't allow jumping off
            # the screen, but without this line, the player could be carried off the screen by a log
            self.x = max(16, min(WIDTH - 16, self.x))
        else:
            # Not alive - timer now counts down prior to game over screen
            self.timer -= 1

        # Keep track of the furthest we've got in the level
        self.min_y = min(self.min_y, self.y)

        # Choose sprite image
        self.image = "blank"
        if self.state == PlayerState.ALIVE:
            if self.timer > 0:
                self.image = "jump" + str(self.direction)
            else:
                self.image = "sit" + str(self.direction)
        elif self.state == PlayerState.SPLASH and self.timer > 84:
            # Display appropriate 'splash' animation frame. Note that we use a different technique to display the
            # 'splat' image - see: comments earlier in this method. The reason two different techniques are used is
            # that the splash image should be drawn on top of other objects, whereas the splat image must be drawn
            # underneath other objects. Since the player is always drawn on top of other objects, changing the player
            # sprite is a suitable method of displaying the splash image.
            self.image = "splash" + str(int((100 - self.timer) / 2))

# Mover is the base class for Car, Log and Train
# The thing they all have in common, besides inheriting from MyActor, is that they need to store whether they're
# moving left or right and update their X position each frame
class Mover(MyActor):
    def __init__(self, dx, image, pos):
        super().__init__(image, pos)

        self.dx = dx

    def update(self):
        self.x += self.dx

class Car(Mover):
    # These correspond to the indicies of the lists self.sounds and self.played. Used in Car.update to trigger
    # playing of the corresponding sound effects.
    SOUND_ZOOM = 0
    SOUND_HONK = 1

    def __init__(self, dx, pos):
        image = "car" + str(randint(0, 3)) + ("0" if dx < 0 else "1")
        super().__init__(dx, image, pos)

        # Cars have two sound effects. Each can only play once. We use this
        # list to keep track of which has already played.
        self.played = [False, False]
        self.sounds = [("zoom", 6), ("honk", 4)]

    def play_sound(self, num):
        if not self.played[num]:
            # Select a sound and pass the name and count to Game.play_sound.
            # The asterisk operator unpacks the two items and passes them to play_sound as separate arguments
            game.play_sound(*self.sounds[num])
            self.played[num] = True

class Log(Mover):
    def __init__(self, dx, pos):
        image = "log" + str(randint(0, 1))
        super().__init__(dx, image, pos)

class Train(Mover):
    def __init__(self, dx, pos):
        image = "train"  +str(randint(0, 2)) + ("0" if dx < 0 else "1")
        super().__init__(dx, image, pos)

# Row is the base class for Pavement, Grass, Dirt, Rail and ActiveRow
# Each row corresponds to one of the 40 pixel high images which make up sections of grass, road, etc.
# The last row of each section is 60 pixels high and overlaps with the row above
class Row(MyActor):
    def __init__(self, base_image, index, y):
        # base_image and index form the name of the image file to use
        # Last argument is the anchor point to use
        super().__init__(base_image + str(index), (0, y), ("left", "bottom"))

        self.index = index

        # X direction of moving elements on this row
        # Zero by default - only ActiveRows (see below) and Rail have moving elements
        self.dx = 0

    def next(self):
        # Overridden in child classes. See comments in Game.update
        return

    def collide(self, x, margin=0):
        # Check to see if the given X coordinate is in contact with any of this row's child objects (e.g. logs, cars,
        # hedges). A negative margin makes the collideable area narrower than the child object's sprite, while a
        # positive margin makes the collideable area wider.
        for child_obj in self.children:
            if x >= child_obj.x - (child_obj.width / 2) - margin and x < child_obj.x + (child_obj.width / 2) + margin:
                return child_obj

        return None

    def push(self):
        return 0

    def check_collision(self, x):
        # Returns the new state the player should be in, based on whether or not the player collided with anything on
        # this road. As this class is the base class for other types of row, this method defines the default behaviour
        # - i.e. unless a subclass overrides this method, the player can walk around on a row without dying.
        return PlayerState.ALIVE, 0

    def allow_movement(self, x):
        # Ensure the player can't walk off the left or right sides of the screen
        return x >= 16 and x <= WIDTH-16

class ActiveRow(Row):
    def __init__(self, child_type, dxs, base_image, index, y):
        super().__init__(base_image, index, y)

        self.child_type = child_type    # Class to be used for child objects (e.g. Car)
        self.timer = 0
        self.dx = choice(dxs)   # Randomly choose a direction for cars/logs to move

        # Populate the row with child objects (cars or logs). Without this, the row would initially be empty.
        x = -WIDTH / 2 - 70
        while x < WIDTH / 2 + 70:
            x += randint(240, 480)
            pos = (WIDTH / 2 + (x if self.dx > 0 else -x), 0)
            self.children.append(self.child_type(self.dx, pos))

    def update(self):
        super().update()

        # Recreate the children list, excluding any which are too far off the edge of the screen to be visible
        self.children = [c for c in self.children if c.x > -70 and c.x < WIDTH + 70]

        self.timer -= 1

        # Create new child objects on a random interval
        if self.timer < 0:
            pos = (WIDTH + 70 if self.dx < 0 else -70, 0)
            self.children.append(self.child_type(self.dx, pos))
            # 240 is minimum distance between the start of one child object and the start of the next, assuming its
            # speed is 1. If the speed is 2, they can occur twice as frequently without risk of overlapping with
            # each other. The maximum distance is double the minimum distance (1 + random value of 1)
            self.timer = (1 + random()) * (240 / abs(self.dx))

# Grass rows sometimes contain hedges
class Hedge(MyActor):
    def __init__(self, x, y, pos):
        super().__init__("bush"+str(x)+str(y), pos)

def generate_hedge_mask():
    # In this context, a mask is a series of boolean values which allow or prevent parts of an underlying image from showing through.
    # This function creates a mask representing the presence or absence of hedges in a Grass row. False means a hedge
    # is present, True represents a gap. Initially we create a list of 12 elements. For each element there is a small
    # chance of a gap, but normally all element will be False, representing a hedge. We then randomly set one item to
    # True, to ensure that there is always at least one gap that the player can get through
    mask = [random() < 0.01 for i in range(12)]
    mask[randint(0, 11)] = True # force there to be one gap

    # We then widen gaps to a minimum of 3 tiles. This happens in two steps.
    # First, we recreate the mask list, except this time whether a gap is present is based on whether there was a gap
    # in either the original element or its neighbouring elements. When using Python's built-in sum function, a value
    # of True is treated as 1 and False as 0. We must use the min/max functions to ensure that we don't try to look
    # at a neighbouring element which doesn't exist (e.g. there is no neighbour to the right of the last element)
    mask = [sum(mask[max(0, i-1):min(12, i+2)]) > 0 for i in range(12)]

    # We want to ensure gaps are a minimum of 3 tiles wide, but the previous line only ensures a minimum gap of 2 tiles
    # at the edges. The last step is to return a new list consisting of the old list with the first and last elements duplicated
    return [mask[0]] + mask + 2 * [mask[-1]]

def classify_hedge_segment(mask, previous_mid_segment):
    # This function helps determine which sprite should be used by a particular hedge segment. Hedge sprites are numbered
    # 00, 01, 10, 11, 20, 21 - up to 51. The second number indicates whether it's a bottom (0) or top (1) segment,
    # but this method is concerned only with the first number. 0 represents a single-tile-width hedge. 1 and 2 represent
    # the left-most or right-most sprites in a multi-tile-width hedge. 3, 4 and 5 all represent middle pieces in hedges
    # which are 3 or more tiles wide.

    # mask is a list of 4 boolean values - a slice from the list generated by generate_hedge_mask. True represents a gap
    # and False represents a hedge. mask[1] is the item we're currently looking at.
    if mask[1]:
        # mask[1] == True represents a gap, so there will be no hedge sprite at this location
        sprite_x = None
    else:
        # There's a hedge here - need to check either side of it to see if it's a single-width, left-most, right-most
        # or middle piece. The calculation generates a number from 0 to 3 accordingly. Note that when boolean values
        # are used in arithmetic in Python, False is treated as being 0 and True as 1.
        sprite_x = 3 - 2 * mask[0] - mask[2]

    if sprite_x == 3:
        # If this is a middle piece, to ensure the piece tiles correctly, we alternate between sprites 3 and 4.
        # If the next piece is going to be the last of this hedge section (sprite 2), we need to make sure that sprite 3
        # does not precede it, as the two do not tile together correctly. In this case we should use sprite 5.
        # mask[3] tells us whether there's a gap 2 tiles to the right - which means the next tile will be sprite 2
        if previous_mid_segment == 4 and mask[3]:
            return 5, None
        else:
            # Alternate between 3 and 4
            if previous_mid_segment == None or previous_mid_segment == 4:
                sprite_x = 3
            elif previous_mid_segment == 3:
                sprite_x = 4
            return sprite_x, sprite_x
    else:
        # Not a middle piece
        return sprite_x, None

class Grass(Row):
    def __init__(self, predecessor, index, y):
        super().__init__("grass", index, y)

        # In computer graphics, a mask is a series of boolean (true or false) values indicating which parts of an image
        # will be transparent. Grass rows may contain hedges which block the player's movement, and we use a similar
        # mechanism here. In our hedge mask, values of False mean a hedge is present, while True means there is a gap
        # in the hedges. Hedges are two rows high - once hedges have been created on a row, the pattern will be
        # duplicated on the next row (although the sprites will be different - e.g. there are separate sprites
        # for the top-left and bottom-left corners of a hedge). Note that the upper sprites overlap with the row above.
        self.hedge_row_index = None     # 0 or 1, or None if no hedges on this row
        self.hedge_mask = None

        if not isinstance(predecessor, Grass) or predecessor.hedge_row_index == None:
            # Create a brand-new set of hedges? We will only create hedges if the previous row didn't have any.
            # We also only want hedges to appear on certain types of grass row, and on only a random selection
            # of rows
            if random() < 0.5 and index > 7 and index < 14:
                self.hedge_mask = generate_hedge_mask()
                self.hedge_row_index = 0
        elif predecessor.hedge_row_index == 0:
            self.hedge_mask = predecessor.hedge_mask
            self.hedge_row_index = 1

        if self.hedge_row_index != None:
            # See comments in classify_hedge_segment for explanation of previous_mid_segment
            previous_mid_segment = None
            for i in range(1, 13):
                sprite_x, previous_mid_segment = classify_hedge_segment(self.hedge_mask[i - 1:i + 3], previous_mid_segment)
                if sprite_x != None:
                    self.children.append(Hedge(sprite_x, self.hedge_row_index, (i * 40 - 20, 0)))

    def allow_movement(self, x):
        # allow_movement in the base class ensures that the player can't walk off the left and right sides of the
        # screen. The call to our own collide method ensures that the player can't walk through hedges. The margin of
        # 8 prevents the player sprite from overlapping with the edge of a hedge.
        return super().allow_movement(x) and not self.collide(x, 8)

    def play_sound(self):
        game.play_sound("grass", 1)

    def next(self):
        if self.index <= 5:
            row_class, index = Grass, self.index + 8
        elif self.index == 6:
            row_class, index = Grass, 7
        elif self.index == 7:
            row_class, index = Grass, 15
        elif self.index >= 8 and self.index <= 14:
            row_class, index = Grass, self.index + 1
        else:
            row_class, index = choice((Road, Water)), 0

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)

class Dirt(Row):
    def __init__(self, predecessor, index, y):
        super().__init__("dirt", index, y)

    def play_sound(self):
        game.play_sound("dirt", 1)

    def next(self):
        if self.index <= 5:
            row_class, index = Dirt, self.index + 8
        elif self.index == 6:
            row_class, index = Dirt, 7
        elif self.index == 7:
            row_class, index = Dirt, 15
        elif self.index >= 8 and self.index <= 14:
            row_class, index = Dirt, self.index + 1
        else:
            row_class, index = choice((Road, Water)), 0

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)
    
class Water(ActiveRow):
    def __init__(self, predecessor, index, y):
        # dxs contains a list of possible directions (and speeds) in which child objects (in this case, logs) on this
        # row could move. We pass the lists to the constructor of the base class, which randomly chooses one of the
        # directions. We want logs on alternate rows to move in opposite directions, so we take advantage of the fact
        # that that in Python, multiplying a list by True or False results in either the same list, or an empty list.
        # So by looking at the direction of child objects on the previous row (predecessor.dx), we can decide whether
        # child objects on this row should move left or right. If this is the first of a series of Water rows,
        # predecessor.dx will be zero, so child objects could move in either direction.
        dxs = [-2,-1]*(predecessor.dx >= 0) + [1,2]*(predecessor.dx <= 0)
        super().__init__(Log, dxs, "water", index, y)

    def update(self):
        super().update()

        for log in self.children:
            # Child (log) object positions are relative to the parent row. If the player exists, and the player is at the
            # same Y position, and is colliding with the current log, make the log dip down into the water slightly
            if game.bunner and self.y == game.bunner.y and log == self.collide(game.bunner.x, -4):
                log.y = 2
            else:
                log.y = 0

    def push(self):
        # Called when the player is standing on a log on this row, so player object can be moved at the same speed and
        # in the same direction as the log
        return self.dx

    def check_collision(self, x):
        # If we're colliding with a log, that's a good thing!
        # margin of -4 ensures we can't stand right on the edge of a log
        if self.collide(x, -4):
            return PlayerState.ALIVE, 0
        else:
            game.play_sound("splash")
            return PlayerState.SPLASH, 0

    def play_sound(self):
        game.play_sound("log", 1)

    def next(self):
        # After 2 water rows, there's a 50-50 chance of the next row being either another water row, or a dirt row
        if self.index == 7 or (self.index >= 1 and random() < 0.5):
            row_class, index = Dirt, randint(4,6)
        else:
            row_class, index = Water, self.index + 1

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)

class Road(ActiveRow):
    def __init__(self, predecessor, index, y):
        # Specify the possible directions and speeds from which the movement of cars on this row will be chosen
        # We use Python's set data structure to specify that the car velocities on this row will be any of the numbers
        # from -5 to 5, except for zero or the velocity of the cars on the previous row
        dxs = list(set(range(-5, 6)) - set([0, predecessor.dx]))
        super().__init__(Car, dxs, "road", index, y)

    def update(self):
        super().update()

        # Trigger car sound effects. The zoom effect should play when the player is on the row above or below the car,
        # the honk effect should play when the player is on the same row.
        for y_offset, car_sound_num in [(-ROW_HEIGHT, Car.SOUND_ZOOM), (0, Car.SOUND_HONK), (ROW_HEIGHT, Car.SOUND_ZOOM)]:
            # Is the player on the appropriate row?
            if game.bunner and game.bunner.y == self.y + y_offset:
                for child_obj in self.children:
                    # The child object must be a car
                    if isinstance(child_obj, Car):
                        # The car must be within 100 pixels of the player on the x-axis, and moving towards the player
                        # child_obj.dx < 0 is True or False depending on whether the car is moving left or right, and
                        # dx < 0 is True or False depending on whether the player is to the left or right of the car.
                        # If the results of these two comparisons are different, the car is moving towards the player.
                        # Also, for the zoom sound, the car must be travelling faster than one pixel per frame
                        dx = child_obj.x - game.bunner.x
                        if abs(dx) < 100 and ((child_obj.dx < 0) != (dx < 0)) and (y_offset == 0 or abs(child_obj.dx) > 1):
                            child_obj.play_sound(car_sound_num)

    def check_collision(self, x):
        if self.collide(x):
            game.play_sound("splat", 1)
            return PlayerState.SPLAT, 0
        else:
            return PlayerState.ALIVE, 0

    def play_sound(self):
        game.play_sound("road", 1)

    def next(self):
        if self.index == 0:
            row_class, index = Road, 1
        elif self.index < 5:
            # 80% chance of another road
            r = random()
            if r < 0.8:
                row_class, index = Road, self.index + 1
            elif r < 0.88:
                row_class, index = Grass, randint(0,6)
            elif r < 0.94:
                row_class, index = Rail, 0
            else:
                row_class, index = Pavement, 0
        else:
            # We've reached maximum of 5 roads in a row, so choose something else
            r = random()
            if r < 0.6:
                row_class, index = Grass, randint(0,6)
            elif r < 0.9:
                row_class, index = Rail, 0
            else:
                row_class, index = Pavement, 0

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)

class Pavement(Row):
    def __init__(self, predecessor, index, y):
        super().__init__("side", index, y)

    def play_sound(self):
        game.play_sound("sidewalk", 1)

    def next(self):
        if self.index < 2:
            row_class, index = Pavement, self.index + 1
        else:
            row_class, index = Road, 0

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)

# Note that Rail does not inherit from ActiveRow
class Rail(Row):
    def __init__(self, predecessor, index, y):
        super().__init__("rail", index, y)

        self.predecessor = predecessor

    def update(self):
        super().update()

        # Only Rail rows with index 1 have trains on them
        if self.index == 1:
            # Recreate the children list, excluding any which are too far off the edge of the screen to be visible
            self.children = [c for c in self.children if c.x > -1000 and c.x < WIDTH + 1000]

            # If on-screen, and there is currently no train, and with a 1% chance every frame, create a train
            if self.y < game.scroll_pos+HEIGHT and len(self.children) == 0 and random() < 0.01:
                # Randomly choose a direction for trains to move. This can be different for each train created
                dx = choice([-20, 20])
                self.children.append(Train(dx, (WIDTH + 1000 if dx < 0 else -1000, -13)))
                game.play_sound("bell")
                game.play_sound("train", 2)

    def check_collision(self, x):
        if self.index == 2 and self.predecessor.collide(x):
            game.play_sound("splat", 1)
            return PlayerState.SPLAT, 8     # For the meaning of the second return value, see comments in Bunner.update
        else:
            return PlayerState.ALIVE, 0

    def play_sound(self):
        game.play_sound("grass", 1)

    def next(self):
        if self.index < 3:
            row_class, index = Rail, self.index + 1
        else:
            item = choice( ((Road, 0), (Water, 0)) )
            row_class, index = item[0], item[1]

        # Create an object of the chosen row class
        return row_class(self, index, self.y - ROW_HEIGHT)

class Game:
    def __init__(self, bunner=None):
        self.bunner = bunner
        self.looped_sounds = {}

        try:
            if bunner:
                music.set_volume(0.4)
            else:
                music.play("theme")
                music.set_volume(1)
        except:
            pass

        self.eagle = None
        self.frame = 0

        # First (bottom) row is always grass
        self.rows = [Grass(None, 0, 0)]

        self.scroll_pos = -HEIGHT

    def update(self):
        if self.bunner:
            # Scroll faster if the player is close to the top of the screen. Limit scroll speed to
            # between 1 and 3 pixels per frame.
            self.scroll_pos -= max(1, min(3, float(self.scroll_pos + HEIGHT - self.bunner.y) / (HEIGHT // 4)))
        else:
            self.scroll_pos -= 1

        # Recreate the list of rows, excluding any which have scrolled off the bottom of the screen
        self.rows = [row for row in self.rows if row.y < int(self.scroll_pos) + HEIGHT + ROW_HEIGHT * 2]

        # In Python, a negative index into a list gives you items in reverse order, e.g. my_list[-1] gives you the
        # last element of a list. Here, we look at the last row in the list - which is the top row - and check to see
        # if it has scrolled sufficiently far down that we need to add a new row above it. This may need to be done
        # multiple times - particularly when the game starts, as only one row is added to begin with.
        while self.rows[-1].y > int(self.scroll_pos)+ROW_HEIGHT:
            new_row = self.rows[-1].next()
            self.rows.append(new_row)

        # Update all rows, and the player and eagle (if present)
        for obj in self.rows + [self.bunner, self.eagle]:
            if obj:
                obj.update()

        # Play river and traffic sound effects, and adjust volume each frame based on the player's proximity to rows
        # of the appropriate types. For each such row, a number is generated representing how much the row should
        # contribute to the volume of the sound effect. These numbers are added together by Python's sum function.
        # On the following line we ensure that the volume can never be above 40% of the maximum possible volume.
        if self.bunner:
            for name, count, row_class in [("river", 2, Water), ("traffic", 3, Road)]:
                # The first line uses a list comprehension to get each row of the appropriate type, e.g. Water rows
                # if we're currently updating the "river" sound effect.
                volume = sum([16.0 / max(16.0, abs(r.y - self.bunner.y)) for r in self.rows if isinstance(r, row_class)]) - 0.2
                volume = min(0.4, volume)
                self.loop_sound(name, count, volume)

        return self

    def draw(self):
        # Create a list of all objects which need to be drawn. This includes all rows, plus the player
        # Using list(s.rows) means we're creating a copy of that list to use - we don't want to create a reference
        # to it as that would mean we're modifying the original list's contents
        all_objs = list(self.rows)

        if self.bunner:
            all_objs.append(self.bunner)

        # We want to draw objects in order based on their Y position. In general, objects further down the screen should be drawn
        # after (and therefore in front of) objects higher up the screen. We can use Python's built-in sort function
        # to put the items in the desired order, before we draw the  The following function specifies the criteria
        # used to decide how the objects are sorted.
        def sort_key(obj):
            # Adding 39 and then doing an integer divide by 40 (the height of each row) deals with the situation where
            # the player sprite would otherwise be drawn underneath the row below. This could happen when the player
            # is moving up or down. If you assume that it occupies a 40x40 box which can be at an arbitrary y offset,
            # it generates the row number of the bottom row that that box overlaps. If the player happens to be
            # perfectly aligned to a row, adding 39 and dividing by 40 has no effect on the result. If it isn't, even
            # by a single pixel, the +39 causes it to be drawn one row later.
            return (obj.y + 39) // ROW_HEIGHT

        # Sort list using the above function to determine order
        all_objs.sort(key=sort_key)

        # Always draw eagle on top of everything
        all_objs.append(self.eagle)
        
        for obj in all_objs:
            if obj:
                # Draw the object, taking the scroll position into account
                obj.draw(0, -int(self.scroll_pos))

        if DEBUG_SHOW_ROW_BOUNDARIES:
            for obj in all_objs:
                if obj and isinstance(obj, Row):
                    pygame.draw.rect(screen.surface, (255, 255, 255), pygame.Rect(obj.x, obj.y - int(self.scroll_pos), screen.surface.get_width(), ROW_HEIGHT), 1)
                    screen.draw.text(str(obj.index), (obj.x, obj.y - int(self.scroll_pos) - ROW_HEIGHT))

    def score(self):
        return int(-320 - game.bunner.min_y) // 40

    def play_sound(self, name, count=1):
        try:
            # Some sounds have multiple varieties. If count > 1, we'll randomly choose one from those
            # We don't play any sounds if there is no player (e.g. if we're on the menu)
            if self.bunner:
                # Pygame Zero allows you to write things like 'sounds.explosion.play()'
                # This automatically loads and plays a file named 'explosion.wav' (or .ogg) from the sounds folder (if
                # such a file exists)
                # But what if you have files named 'explosion0.ogg' to 'explosion5.ogg' and want to randomly choose
                # one of them to play? You can generate a string such as 'explosion3', but to use such a string
                # to access an attribute of Pygame Zero's sounds object, we must use Python's built-in function getattr
                sound = getattr(sounds, name + str(randint(0, count - 1)))
                sound.play()
        except:
            # If a sound fails to play, ignore the error
            pass

    def loop_sound(self, name, count, volume):
        try:
            # Similar to play_sound above, but for looped sounds we need to keep a reference to the sound so that we can
            # later modify its volume or turn it off. We use the dictionary self.looped_sounds for this - the sound
            # effect name is the key, and the value is the corresponding sound reference.
            if volume > 0 and not name in self.looped_sounds:
                full_name = name + str(randint(0, count - 1))
                sound = getattr(sounds, full_name)      # see play_sound method above for explanation
                sound.play(-1)  # -1 means sound will loop indefinitely
                self.looped_sounds[name] = sound

            if name in self.looped_sounds:
                sound = self.looped_sounds[name]
                if volume > 0:
                    sound.set_volume(volume)
                else:
                    sound.stop()
                    del self.looped_sounds[name]
        except:
            # If a sound fails to play, ignore the error
            pass


    def stop_looped_sounds(self):
        try:
            for sound in self.looped_sounds.values():
                sound.stop()
            self.looped_sounds.clear()
        except:
            # If sound system is not working/present, ignore the error
            pass

# Dictionary to keep track of which keys are currently being held down
key_status = {}

# Was the given key just pressed? (i.e. is it currently down, but wasn't down on the previous frame?)
def key_just_pressed(key):
    result = False

    # Get key's previous status from the key_status dictionary. The dictionary.get method allows us to check for a given
    # entry without giving an error if that entry is not present in the dictionary. False is the default value returned
    # when the key is not present.
    prev_status = key_status.get(key, False)

    # If the key wasn't previously being pressed, but it is now, we're going to return True
    if not prev_status and keyboard[key]:
        result = True

    # Before we return, we need to update the key's entry in the key_status dictionary (or create an entry if there
    # wasn't one already
    key_status[key] = keyboard[key]

    return result

def display_number(n, colour, x, align):
    # align: 0 for left, 1 for right
    n = str(n)  # Convert number to string
    for i in range(len(n)):
        screen.blit("digit" + str(colour) + n[i], (x + (i - len(n) * align) * 25, 0))


# Pygame Zero calls the update and draw functions each frame

class State(Enum):
    MENU = 1
    PLAY = 2
    GAME_OVER = 3

def update():
    global state, game, high_score

    if state == State.MENU:
        if key_just_pressed(keys.SPACE):
            state = State.PLAY
            game = Game(Bunner((240, -320)))
        else:
            game.update()

    elif state == State.PLAY:
        # Is it game over?
        if game.bunner.state != PlayerState.ALIVE and game.bunner.timer < 0:
            # Update high score
            high_score = max(high_score, game.score())

            # Write high score file
            try:
                with open("high.txt", "w") as file:
                    file.write(str(high_score))
            except:
                # If an error occurs writing the file, just ignore it and carry on, rather than crashing
                pass

            state = State.GAME_OVER
        else:
            game.update()

    elif state == State.GAME_OVER:
        # Switch to menu state, and create a new game object without a player
        if key_just_pressed(keys.SPACE):
            game.stop_looped_sounds()
            state = State.MENU
            game = Game()

def draw():
    game.draw()

    if state == State.MENU:
        screen.blit("title", (0, 0))
        screen.blit("start" + str([0, 1, 2, 1][game.scroll_pos // 6 % 4]), ((WIDTH - 270) // 2, HEIGHT - 240))

    elif state == State.PLAY:
        # Display score and high score
        display_number(game.score(), 0, 0, 0)
        display_number(high_score, 1, WIDTH - 10, 1)

    elif state == State.GAME_OVER:
        # Display "Game Over" image
        screen.blit("gameover", (0, 0))

# Set up sound system
try:
    pygame.mixer.quit()
    pygame.mixer.init(44100, -16, 2, 512)
    pygame.mixer.set_num_channels(16)
except:
    # If an error occurs, just ignore it
    pass

# Load high score from file
try:
    with open("high.txt", "r") as f:
        high_score = int(f.read())
except:
    # If opening the file fails (likely because it hasn't yet been created), set high score to 0
    high_score = 0

# Set the initial game state
state = State.MENU

# Create a new Game object, without a Player object
game = Game()

pgzrun.go()
