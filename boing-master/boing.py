import pgzero, pgzrun, pygame
import math, sys, random
from enum import Enum

# Check Python version number. sys.version_info gives version as a tuple, e.g. if (3,7,2,'final',0) for version 3.7.2.
# Unlike many languages, Python can compare two tuples in the same way that you can compare numbers.
if sys.version_info < (3,6):
    print("This game requires at least version 3.6 of Python. Please download it from www.python.org")
    sys.exit()

# Check Pygame Zero version. This is a bit trickier because Pygame Zero only lets us get its version number as a string.
# So we have to split the string into a list, using '.' as the character to split on. We convert each element of the
# version number into an integer - but only if the string contains numbers and nothing else, because it's possible for
# a component of the version to contain letters as well as numbers (e.g. '2.0.dev0')
# We're using a Python feature called list comprehension - this is explained in the Bubble Bobble/Cavern chapter.
pgzero_version = [int(s) if s.isnumeric() else s for s in pgzero.__version__.split('.')]
if pgzero_version < [1,2]:
    print(f"This game requires at least version 1.2 of Pygame Zero. You have version {pgzero.__version__}. Please upgrade using the command 'pip3 install --upgrade pgzero'")
    sys.exit()

# Set up constants
WIDTH = 800
HEIGHT = 480
TITLE = "Boing!"

HALF_WIDTH = WIDTH // 2
HALF_HEIGHT = HEIGHT // 2

PLAYER_SPEED = 6
MAX_AI_SPEED = 6

def normalised(x, y):
    # Return a unit vector
    # Get length of vector (x,y) - math.hypot uses Pythagoras' theorem to get length of hypotenuse
    # of right-angle triangle with sides of length x and y
    # todo note on safety
    length = math.hypot(x, y)
    return (x / length, y / length)

def sign(x):
    # Returns -1 or 1 depending on whether number is positive or negative
    return -1 if x < 0 else 1


# Class for an animation which is displayed briefly whenever the ball bounces
class Impact(Actor):
    def __init__(self, pos):
        super().__init__("blank", pos)
        self.time = 0

    def update(self):
        # There are 5 impact sprites numbered 0 to 4. We update to a new sprite every 2 frames.
        self.image = "impact" + str(self.time // 2)

        # The Game class maintains a list of Impact instances. In Game.update, if the timer for an object
        # has gone beyond 10, the object is removed from the list.
        self.time += 1


class Ball(Actor):
    def __init__(self, dx):
        super().__init__("ball", (0,0))

        self.x, self.y = HALF_WIDTH, HALF_HEIGHT

        # dx and dy together describe the direction in which the ball is moving. For example, if dx and dy are 1 and 0,
        # the ball is moving to the right, with no movement up or down. If both values are negative, the ball is moving
        # left and up, with the angle depending on the relative values of the two variables. If you're familiar with
        # vectors, dx and dy represent a unit vector. If you're not familiar with vectors, see the explanation in the
        # book.
        self.dx, self.dy = dx, 0

        self.speed = 5

    def update(self):
        # Each frame, we move the ball in a series of small steps - the number of steps being based on its speed attribute
        for i in range(self.speed):
            # Store the previous x position
            original_x = self.x

            # Move the ball based on dx and dy
            self.x += self.dx
            self.y += self.dy

            # Check to see if ball needs to bounce off a bat

            # To determine whether the ball might collide with a bat, we first measure the horizontal distance from the
            # ball to the centre of the screen, and check to see if its edge has gone beyond the edge of the bat.
            # The centre of each bat is 40 pixels from the edge of the screen, or to put it another way, 360 pixels
            # from the centre of the screen. The bat is 18 pixels wide and the ball is 14 pixels wide. Given that these
            # sprites are anchored from their centres, when determining if they overlap or touch, we need to look at
            # their half-widths - 9 and 7. Therefore, if the centre of the ball is 344 pixels from the centre of the
            # screen, it can bounce off a bat (assuming the bat is in the right position on the Y axis - checked
            # shortly afterwards).
            # We also check the previous X position to ensure that this is the first frame in which the ball crossed the threshold.
            if abs(self.x - HALF_WIDTH) >= 344 and abs(original_x - HALF_WIDTH) < 344:

                # Now that we know the edge of the ball has crossed the threshold on the x-axis, we need to check to
                # see if the bat on the relevant side of the arena is at a suitable position on the y-axis for the
                # ball collide with it.

                if self.x < HALF_WIDTH:
                    new_dir_x = 1
                    bat = game.bats[0]
                else:
                    new_dir_x = -1
                    bat = game.bats[1]

                difference_y = self.y - bat.y

                if difference_y > -64 and difference_y < 64:
                    # Ball has collided with bat - calculate new direction vector

                    # To understand the maths used below, we first need to consider what would happen with this kind of
                    # collision in the real world. The ball is bouncing off a perfectly vertical surface. This makes for a
                    # pretty simple calculation. Let's take a ball which is travelling at 1 metre per second to the right,
                    # and 2 metres per second down. Imagine this is taking place in space, so gravity isn't a factor.
                    # After the ball hits the bat, it's still going to be moving at 2 m/s down, but it's now going to be
                    # moving 1 m/s to the left instead of right. So its speed on the y-axis hasn't changed, but its
                    # direction on the x-axis has been reversed. This is extremely easy to code - "self.dx = -self.dx".
                    # However, games don't have to perfectly reflect reality.
                    # In Pong, hitting the ball with the upper or lower parts of the bat would make it bounce diagonally
                    # upwards or downwards respectively. This gives the player a degree of control over where the ball
                    # goes. To make for a more interesting game, we want to use realistic physics as the starting point,
                    # but combine with this the ability to influence the direction of the ball. When the ball hits the
                    # bat, we're going to deflect the ball slightly upwards or downwards depending on where it hit the
                    # bat. This gives the player a bit of control over where the ball goes.

                    # Bounce the opposite way on the X axis
                    self.dx = -self.dx

                    # Deflect slightly up or down depending on where ball hit bat
                    self.dy += difference_y / 128

                    # Limit the Y component of the vector so we don't get into a situation where the ball is bouncing
                    # up and down too rapidly
                    self.dy = min(max(self.dy, -1), 1)

                    # Ensure our direction vector is a unit vector, i.e. represents a distance of the equivalent of
                    # 1 pixel regardless of its angle
                    self.dx, self.dy = normalised(self.dx, self.dy)

                    # Create an impact effect
                    game.impacts.append(Impact((self.x - new_dir_x * 10, self.y)))

                    # Increase speed with each hit
                    self.speed += 1

                    # Add an offset to the AI player's target Y position, so it won't aim to hit the ball exactly
                    # in the centre of the bat
                    game.ai_offset = random.randint(-10, 10)

                    # Bat glows for 10 frames
                    bat.timer = 10

                    # Play hit sounds, with more intense sound effects as the ball gets faster
                    game.play_sound("hit", 5)  # play every time in addition to:
                    if self.speed <= 10:
                        game.play_sound("hit_slow", 1)
                    elif self.speed <= 12:
                        game.play_sound("hit_medium", 1)
                    elif self.speed <= 16:
                        game.play_sound("hit_fast", 1)
                    else:
                        game.play_sound("hit_veryfast", 1)

            # The top and bottom of the arena are 220 pixels from the centre
            if abs(self.y - HALF_HEIGHT) > 220:
                # Invert vertical direction and apply new dy to y so that the ball is no longer overlapping with the
                # edge of the arena
                self.dy = -self.dy
                self.y += self.dy

                # Create impact effect
                game.impacts.append(Impact(self.pos))

                # Sound effect
                game.play_sound("bounce", 5)
                game.play_sound("bounce_synth", 1)

    def out(self):
        # Has ball gone off the left or right edge of the screen?
        return self.x < 0 or self.x > WIDTH


class Bat(Actor):
    def __init__(self, player, move_func=None):
        x = 40 if player == 0 else 760
        y = HALF_HEIGHT
        super().__init__("blank", (x, y))

        self.player = player
        self.score = 0

        # move_func is a function we may or may not have been passed by the code which created this object. If this bat
        # is meant to be player controlled, move_func will be a function that when called, returns a number indicating
        # the direction and speed in which the bat should move, based on the keys the player is currently pressing.
        # If move_func is None, this indicates that this bat should instead be controlled by the AI method.
        if move_func != None:
            self.move_func = move_func
        else:
            self.move_func = self.ai

        # Each bat has a timer which starts at zero and counts down by one every frame. When a player concedes a point,
        # their timer is set to 20, which causes the bat to display a different animation frame. It is also used to
        # decide when to create a new ball in the centre of the screen - see comments in Game.update for more on this.
        # Finally, it is used in Game.draw to determine when to display a visual effect over the top of the background
        self.timer = 0

    def update(self):
        self.timer -= 1

        # Our movement function tells us how much to move on the Y axis
        y_movement = self.move_func()

        # Apply y_movement to y position, ensuring bat does not go through the side walls
        self.y = min(400, max(80, self.y + y_movement))

        # Choose the appropriate sprite. There are 3 sprites per player - e.g. bat00 is the left-hand player's
        # standard bat sprite, bat01 is the sprite to use when the ball has just bounced off the bat, and bat02
        # is the sprite to use when the bat has just missed the ball and the ball has gone out of bounds.
        # bat10, 11 and 12 are the equivalents for the right-hand player

        frame = 0
        if self.timer > 0:
            if game.ball.out():
                frame = 2
            else:
                frame = 1

        self.image = "bat" + str(self.player) + str(frame)

    def ai(self):
        # Returns a number indicating how the computer player will move - e.g. 4 means it will move 4 pixels down
        # the screen.

        # To decide where we want to go, we first check to see how far we are from the ball.
        x_distance = abs(game.ball.x - self.x)

        # If the ball is far away, we move towards the centre of the screen (HALF_HEIGHT), on the basis that we don't
        # yet know whether the ball will be in the top or bottom half of the screen when it reaches our position on
        # the X axis. By waiting at a central position, we're as ready as it's possible to be for all eventualities.
        target_y_1 = HALF_HEIGHT

        # If the ball is close, we want to move towards its position on the Y axis. We also apply a small offset which
        # is randomly generated each time the ball bounces. This is to make the computer player slightly less robotic
        # - a human player wouldn't be able to hit the ball right in the centre of the bat each time.
        target_y_2 = game.ball.y + game.ai_offset

        # The final step is to work out the actual Y position we want to move towards. We use what's called a weighted
        # average - taking the average of the two target Y positions we've previously calculated, but shifting the
        # balance towards one or the other depending on how far away the ball is. If the ball is more than 400 pixels
        # (half the screen width) away on the X axis, our target will be half the screen height (target_y_1). If the
        # ball is at the same position as us on the X axis, our target will be target_y_2. If it's 200 pixels away,
        # we'll aim for halfway between target_y_1 and target_y_2. This reflects the idea that as the ball gets closer,
        # we have a better idea of where it's going to end up.
        weight1 = min(1, x_distance / HALF_WIDTH)
        weight2 = 1 - weight1

        target_y = (weight1 * target_y_1) + (weight2 * target_y_2)

        # Subtract target_y from our current Y position, then make sure we can't move any further than MAX_AI_SPEED
        # each frame
        return min(MAX_AI_SPEED, max(-MAX_AI_SPEED, target_y - self.y))


class Game:
    def __init__(self, controls=(None, None)):
        # Create a list of two bats, giving each a player number and a function to use to receive
        # control inputs (or the value None if this is intended to be an AI player)
        self.bats = [Bat(0, controls[0]), Bat(1, controls[1])]

        # Create a ball object
        self.ball = Ball(-1)

        # Create an empty list which will later store the details of currently playing impact
        # animations - these are displayed for a short time every time the ball bounces
        self.impacts = []

        # Add an offset to the AI player's target Y position, so it won't aim to hit the ball exactly
        # in the centre of the bat
        self.ai_offset = 0

    def update(self):
        # Update all active objects
        for obj in self.bats + [self.ball] + self.impacts:
            obj.update()

        # Remove any expired impact effects from the list. We go through the list backwards, starting from the last
        # element, and delete any elements those time attribute has reached 10. We go backwards through the list
        # instead of forwards to avoid a number of issues which occur in that scenario. In the next chapter we will
        # look at an alternative technique for removing items from a list, using list comprehensions.
        for i in range(len(self.impacts) - 1, -1, -1):
            if self.impacts[i].time >= 10:
                del self.impacts[i]

        # Has ball gone off the left or right edge of the screen?
        if self.ball.out():
            # Work out which player gained a point, based on whether the ball
            # was on the left or right-hand side of the screen
            scoring_player = 1 if self.ball.x < HALF_WIDTH else 0
            losing_player = 1 - scoring_player

            # We use the timer of the player who has just conceded a point to decide when to create a new ball in the
            # centre of the level. This timer starts at zero at the beginning of the game and counts down by one every
            # frame. Therefore, on the frame where the ball first goes off the screen, the timer will be less than zero.
            # We set it to 20, which means that this player's bat will display a different animation frame for 20
            # frames, and a new ball will be created after 20 frames
            if self.bats[losing_player].timer < 0:
                self.bats[scoring_player].score += 1

                game.play_sound("score_goal", 1)

                self.bats[losing_player].timer = 20

            elif self.bats[losing_player].timer == 0:
                # After 20 frames, create a new ball, heading in the direction of the player who just missed the ball
                direction = -1 if losing_player == 0 else 1
                self.ball = Ball(direction)

    def draw(self):
        # Draw background
        screen.blit("table", (0,0))

        # Draw 'just scored' effects, if required
        for p in (0,1):
            if self.bats[p].timer > 0 and game.ball.out():
                screen.blit("effect" + str(p), (0,0))

        # Draw bats, ball and impact effects - in that order. Square brackets are needed around the ball because
        # it's just an object, whereas the other two are lists - and you can't directly join an object onto a
        # list without first putting it in a list
        for obj in self.bats + [self.ball] + self.impacts:
            obj.draw()

        # Display scores - outer loop goes through each player
        for p in (0,1):
            # Convert score into a string of 2 digits (e.g. "05") so we can later get the individual digits
            score = f"{self.bats[p].score:02d}"
            # Inner loop goes through each digit
            for i in (0,1):
                # Digit sprites are numbered 00 to 29, where the first digit is the colour (0 = grey,
                # 1 = blue, 2 = green) and the second digit is the digit itself
                # Colour is usually grey but turns red or green (depending on player number) when a
                # point has just been scored
                colour = "0"
                other_p = 1 - p
                if self.bats[other_p].timer > 0 and game.ball.out():
                    colour = "2" if p == 0  else "1"
                image = "digit" + colour + str(score[i])
                screen.blit(image, (255 + (160 * p) + (i * 55), 46))

    def play_sound(self, name, count=1, menu_sound=False):
        # Some sounds have multiple varieties. If count > 1, we'll randomly choose one from those
        # We don't play any in-game sound effects if player 0 is an AI player - as this means we're on the menu
        # Updated Jan 2022 - some Pygame installations have issues playing ogg sound files. play_sound can skip sound
        # errors without stopping the game, but it previously couldn't be used for menu-only sounds
        if self.bats[0].move_func != self.bats[0].ai or menu_sound:
            # Pygame Zero allows you to write things like 'sounds.explosion.play()'
            # This automatically loads and plays a file named 'explosion.wav' (or .ogg) from the sounds folder (if
            # such a file exists)
            # But what if you have files named 'explosion0.ogg' to 'explosion5.ogg' and want to randomly choose
            # one of them to play? You can generate a string such as 'explosion3', but to use such a string
            # to access an attribute of Pygame Zero's sounds object, we must use Python's built-in function getattr
            try:
                getattr(sounds, name + str(random.randint(0, count - 1))).play()
            except Exception as e:
                pass

def p1_controls():
    move = 0
    if keyboard.z or keyboard.down:
        move = PLAYER_SPEED
    elif keyboard.a or keyboard.up:
        move = -PLAYER_SPEED
    return move

def p2_controls():
    move = 0
    if keyboard.m:
        move = PLAYER_SPEED
    elif keyboard.k:
        move = -PLAYER_SPEED
    return move

class State(Enum):
    MENU = 1
    PLAY = 2
    GAME_OVER = 3

num_players = 1

# Is space currently being held down?
space_down = False


# Pygame Zero calls the update and draw functions each frame

def update():
    global state, game, num_players, space_down

    # Work out whether the space key has just been pressed - i.e. in the previous frame it wasn't down,
    # and in this frame it is.
    space_pressed = False
    if keyboard.space and not space_down:
        space_pressed = True
    space_down = keyboard.space

    if state == State.MENU:
        if space_pressed:
            # Switch to play state, and create a new Game object, passing it the controls function for
            # player 1, and if we're in 2 player mode, the controls function for player 2 (otherwise the
            # 'None' value indicating this player should be computer-controlled)
            state = State.PLAY
            controls = [p1_controls]
            controls.append(p2_controls if num_players == 2 else None)
            game = Game(controls)
        else:
            # Detect up/down keys
            if num_players == 2 and keyboard.up:
                game.play_sound("up", menu_sound=True)
                num_players = 1
            elif num_players == 1 and keyboard.down:
                game.play_sound("down", menu_sound=True)
                num_players = 2

            # Update the 'attract mode' game in the background (two AIs playing each other)
            game.update()

    elif state == State.PLAY:
        # Has anyone won?
        if max(game.bats[0].score, game.bats[1].score) > 9:
            state = State.GAME_OVER
        else:
            game.update()

    elif state == State.GAME_OVER:
        if space_pressed:
            # Reset to menu state
            state = State.MENU
            num_players = 1

            # Create a new Game object, without any players
            game = Game()

def draw():
    game.draw()

    if state == State.MENU:
        menu_image = "menu" + str(num_players - 1)
        screen.blit(menu_image, (0,0))

    elif state == State.GAME_OVER:
        screen.blit("over", (0,0))


# The mixer allows us to play sounds and music
try:
    pygame.mixer.quit()
    pygame.mixer.init(44100, -16, 2, 1024)

    music.play("theme")
    music.set_volume(0.3)
except Exception:
    # If an error occurs (e.g. no sound device), just ignore it
    pass

# Set the initial game state
state = State.MENU

# Create a new Game object, without any players
game = Game()

# Tell Pygame Zero to start - this line is only required when running the game from an IDE such as IDLE or PyCharm
pgzrun.go()
