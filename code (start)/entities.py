from settings import *
from support import check_connections
from timer import Timer  # type: ignore
from random import choice

class Entity(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, facing_direction):
        super().__init__(groups)
        self.z = WORLD_LAYERS['main']  # Default z-index for entities
         # Use the y-coordinate for sorting
        # graphics
        self.frame_index, self.frames = 0, frames
        self.facing_direction = facing_direction  # Default facing direction
        # Movement
        self.direction = vector()
        self.speed = 250
        self.blocked = False  # Block movement by default
        #spite setup
        self.image = self.frames[self.get_state()][self.frame_index]
        self.rect = self.image.get_frect(center = pos)
        self.hit_box = self.rect.inflate(-self.rect.width / 2, -60)

        self.y_sort = self.rect.centery 
    def animate(self, dt):
        self.frame_index += ANIMATION_SPEED * dt
        self.image = self.frames[self.get_state()][int(self.frame_index % len(self.frames[self.get_state()]))]
    
    def get_state(self):
        moving = bool(self.direction)
        if moving:
            if self.direction.x != 0:
                self.facing_direction = 'right' if self.direction.x > 0 else 'left'
            if self.direction.y != 0:
                self.facing_direction = 'down' if self.direction.y > 0 else 'up'

        return f'{self.facing_direction}{'' if moving else '_idle'}'
        
    def change_facing_direction(self, target_pos):
        relation = vector(target_pos) - vector(self.rect.center)
        if abs(relation.y) < 30:
            self.facing_direction = 'right' if relation.x > 0 else 'left'
        else:
            self.facing_direction = 'down' if relation.y > 0 else 'up'
    def block(self):
        self.blocked = True
        self.direction = vector(0, 0)
    
    def unblock(self):
        self.blocked = False  # Stop movement when blocked

class Character(Entity):
    def __init__(self, pos, frames, groups, facing_direction, character_data, player, create_dialog, collision_sprites, radius):
        super().__init__(pos, frames, groups, facing_direction)
        self.character_data = character_data
        self.player = player
        self.create_dialog = create_dialog
        self.collision_rects = [sprite.rect for sprite in collision_sprites if sprite is not self]

        #movement
        self.has_moved = False
        self.can_rotate = True  # Allow rotation by default
        self.has_noticed = False  # Track if the character has noticed the player
        self.radius = int(radius)
        self.view_direction = character_data['directions']  # Possible view directions

        self.timers = {
            'look around': Timer(1500, autostart = True, repeat = True, func = self.random_view_direction),  # Timer for looking around
            'notice': Timer(500, func = self.start_move)
        }
    def random_view_direction(self):
        if self.can_rotate:
            self.facing_direction = choice(self.view_direction)

    def get_dialog(self):
        return self.character_data['dialog'][f'{'defeated' if self.character_data['defeated'] else 'default'}']
    
    def raycast(self):
        if check_connections(self.radius, self, self.player) and self.has_los() and not self.has_moved and not self.has_noticed:
            self.player.block()
            self.player.change_facing_direction(self.rect.center)
            self.timers['notice'].activate()  # Start the notice timer
            self.can_rotate = False  # Stop rotation when the player is noticed
            self.has_noticed = True  # Mark that the character has noticed the player
            self.player.noticed = True

    def has_los(self):
        if vector(self.rect.center).distance_to(self.player.rect.center) < self.radius:
            collisions = [bool(rect.clipline(self.rect.center, self.player.rect.center)) for rect in self.collision_rects]
            return not any(collisions)

    def move(self, dt):
        if not self.has_moved and self.direction:    
            if not self.hit_box.inflate(10, 10).colliderect(self.player.hit_box):
                self.rect.center += self.direction * self.speed * dt
                self.hit_box.center = self.rect.center
            else:
                self.direction = vector()  # Stop moving if colliding with the player
                self.has_moved = True  # Mark that the character has moved
                self.create_dialog(self)
                self.player.noticed = False  # Reset player's noticed state
    def start_move(self):
        relation = (vector(self.player.rect.center) - vector(self.rect.center)).normalize()
        self.direction = vector(round(relation.x), round(relation.y))

    def update(self, dt):
        for timer in self.timers.values():
            timer.update()
        self.animate(dt)
        if self.character_data['look_around']:
            self.raycast()
            self.move(dt)
class Player(Entity):
    def __init__(self, pos, frames, groups, facing_direction, collision_sprites):
        super().__init__( pos, frames, groups, facing_direction)
        self.collision_sprites = collision_sprites
        self.noticed = False
        
    def input(self):
        keys = pygame.key.get_pressed()
        input_vector = vector()
        if keys[pygame.K_UP]:
            input_vector.y = -1
        if keys[pygame.K_DOWN]:
            input_vector.y += 1
        if keys[pygame.K_LEFT]:
            input_vector.x -= 1
        if keys[pygame.K_RIGHT]:
            input_vector.x += 1
        self.direction = input_vector.normalize() if input_vector else input_vector    

    def move(self, dt):
        self.rect.centerx += self.direction.x *self.speed  *dt 
        self.hit_box.centerx = self.rect.centerx  # Update hit box position
        self.collision('x')

        self.rect.centery += self.direction.y *self.speed  *dt 
        self.hit_box.centery = self.rect.centery
        self.collision('y')
    
    def collision(self, axis):
        for sprites in self.collision_sprites:
            if sprites.hit_box.colliderect(self.hit_box):
                if axis == 'x':
                    if self.direction.x > 0:
                        self.hit_box.right = sprites.hit_box.left
                    if self.direction.x < 0:
                        self.hit_box.left = sprites.hit_box.right
                    self.rect.centerx = self.hit_box.centerx
                if axis == 'y':
                    if self.direction.y > 0:
                        self.hit_box.bottom = sprites.hit_box.top
                    if self.direction.y < 0:
                        self.hit_box.top = sprites.hit_box.bottom
                    self.rect.centery = self.hit_box.centery

    def update(self, dt):
        self.y_sort = self.rect.centery  # Update y_sort for sorting
        if not self.blocked:
            self.input()
            self.move(dt)
        self.animate(dt)