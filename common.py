from collections import namedtuple
from PIL import Image, ImageDraw, ImageFont
from enum import Enum
import time

Color = namedtuple('Color', 'red green blue')

class ActiveScreen(Enum):
    NHL = 0
    MLB = 1
    REFRESH = 100

class Team:
    def __init__(self, id, name, display_name, city, abbreviation, primary_color, secondary_color):
        self.id = id
        self.name = name
        self.display_name = display_name
        self.city = city
        self.abbreviation = abbreviation
        self.primary_color = primary_color
        self.secondary_color = secondary_color

    def __repr__(self):
        return "{!r}({!r}, {!r}, {!r}, {!r}, {!r}, {!r})".format(self.__class__.__name__,
           self.id, self.name, 
               self.city, self.abbreviation, 
               self.primary_color, self.secondary_color)

from enum import Enum
class GameStatus(Enum):
    INVALID = 0
    PREGAME = 1
    ACTIVE = 2
    INTERMISSION = 3
    END = 4

class Game:
    def __init__(self, id, away, home, away_score=0, home_score=0, start_time=0):
        self.id = id
        self.away = away
        self.home = home
        self.start_time = start_time
        self.away_score = away_score
        self.home_score = home_score
        self.status = GameStatus.INVALID
    def __repr__(self):
        return "{!r}({!r}, {!r}, {!r}, {!r}, {!r}, {!r}, {!r}, {!r})".format(self.__class__.__name__, self.game_id,
            self.away, self.home,
            self.away_score, self.home_score,
            self.start_time)

class Screen:
  def __init__(self):
    pass

  def reset(self):
    pass

  def get_image(self):
    pass 

  def refresh(self):
    pass

  def get_sleep_time(self):
    return 10

  def get_refresh_time(self):
    return 60

class League(Screen):
  def __init__(self):
      super().__init__()
      self.full_refresh_counter = 20
      self.active_index = 0
      self.last_refresh = time.time()
      self.reset()
  
  def reset(self):
      super().reset()
      self.full_refresh_counter = 20
      self.active_index = 0

  def refresh(self):
    #first, check if we need to do a full refresh
    if self.full_refresh_counter == 0:
      self.reset()
    elif (time.time() - self.last_refresh) > self.get_refresh_time():
      # if it's been more than X seconds since the last refresh, refresh all games
      self.last_refresh = time.time()
      self.full_refresh_counter -= 1
      for game in self.games:
        game.refresh()

    # Regardless, move the active game up one, unless a favorite team is playing
    if len(self.games) == 0:
      self.active_index = -1
    elif self.team_playing(19) is not None: #TODO store favorite teams
      active_index = self.team_playing(19)
    else:
      self.active_index = (self.active_index + 1) % len(self.games)

  def get_image(self):
    pass

  def get_refresh_time(self):
    if len(self.games) == 0:
        return 120
    elif self.team_playing(19) is not None: #TODO store favorite teams
        return 10
    else:
        return 60
      
  def team_playing(self, team_id):
    for game in self.games:
        if game.home.id == team_id or game.away.id == team_id:
            if game.status == GameStatus.ACTIVE or game.status == GameStatus.INTERMISSION:
                return self.games.index(game)
    return None

class Renderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height


    def draw_big_scoreboard(self, game):
        image = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(image) #  let's draw on this image
        team_font = ImageFont.load("/home/pi/nhlscoreboard/fonts/5x8.pil")

        #add teams
        draw.rectangle(((0,0), (64,9)), fill=game.away.primary_color)
        draw.rectangle(((0,0), (2, 9)), fill=game.away.secondary_color)
        draw.text((5, 1), game.away.display_name, font=team_font, fill=game.away.secondary_color)
        draw.text((57, 1), str(game.away_score), font=team_font, fill=game.away.secondary_color)

        draw.rectangle(((0,10), (64,19)), fill=game.home.primary_color)
        draw.rectangle(((0,10), (2, 19)), fill=game.home.secondary_color)
        draw.text((5, 11), game.home.display_name, font=team_font ,fill=game.home.secondary_color)
        draw.text((57, 11), str(game.home_score), font=team_font, fill=game.home.secondary_color)

        return (image, draw)

    def draw_small_scoreboard(self, game):
        image = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(image) #  let's draw on this image
        team_font = ImageFont.load("/home/pi/nhlscoreboard/fonts/4x6.pil")

        #add teams
        draw.rectangle(((0,0), (64,6)), fill=game.away.primary_color)
        draw.rectangle(((0,0), (2, 6)), fill=game.away.secondary_color)
        draw.text((5, 1), game.away.display_name, font=team_font, fill=game.away.secondary_color)
        draw.text((57, 1), str(game.away_score), font=team_font, fill=game.away.secondary_color)

        draw.rectangle(((0,7), (64,13)), fill=game.home.primary_color)
        draw.rectangle(((0,7), (2, 13)), fill=game.home.secondary_color)
        draw.text((5, 8), game.home.display_name, font=team_font ,fill=game.home.secondary_color)
        draw.text((57, 8), str(game.home_score), font=team_font, fill=game.home.secondary_color)

        return (image, draw)

