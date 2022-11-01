#!/usr/bin/env python3

# Copyright Johan Zaxmy johan@zaxmy.com 
# License GPLv3

from locale import setlocale
from termios import TIOCLINUX
import time
import curses
import random
import pickle
import hashlib
import locale
from curses import wrapper
import curses.textpad as textpad



def getbyte(number, i):
   return (number & (0xff << (i * 8))) >> (i * 8)

class Tile:
   RIGHT = (1,0)
   LEFT  = (-1,0)
   UP    = (0,-1)
   DOWN  = (0,1)
   BODY = 'O'
   TAIL =  'o'
   BAD_OBJECTS = [BODY,TAIL,'<','>','^','v','-','|','+']
   GOOD_OBJECTS = {'¤':5,'@':10,'$':15,'§':20}
   
   def __init__(self,x,y,d) -> None:
      self.x=x
      self.y=y
      self.d=d
      self.b=Tile.BODY

   def move(self):
      (dx,dy) = self.d
      self.x += dx
      self.y += dy
   
   def draw(self,surface):
      surface.addstr(self.y,self.x,self.b,curses.color_pair(1))

class Wurm():
   DIED = 'D'
   ATE = 'E'
   NOTHING = 'N'

   def __init__(self) -> None:
      self.head = Tile(7,5,Tile.RIGHT)
      self.head.b = "<"
      self.body = []
      self.body.append(Tile(6,5,Tile.RIGHT))
      self.body.append(Tile(5,5,Tile.RIGHT))
      self.body.append(Tile(4,5,Tile.RIGHT))
      self.tail = Tile(3,5,Tile.RIGHT)
      self.tail.b=Tile.TAIL
      self.add = 0
      self.score = 0
      self.oldtail_x=None
      self.oldtail_y=None 

   def move(self):
      # save old tail coords for draw method
      self.oldtail_x=self.tail.x
      self.oldtail_y=self.tail.y
      ohx=self.head.x
      ohy=self.head.y
      self.head.move()
      for b in self.body:
         obx = b.x
         oby = b.y
         b.x = ohx
         b.y = ohy
         ohx = obx
         ohy = oby
      if self.add > 0:
         self.body.append(Tile(ohx,ohy,Tile.RIGHT))
         self.add -= 1
      else:
         self.tail.x = ohx
         self.tail.y = ohy
   
   def draw(self,surface):
      """Redraws the snake on screen
      """
      state = Wurm.NOTHING
      
      # Check head coord on screen
      coll = get_char(self.head.x,self.head.y,surface)

      # Did we hit anything bad?
      if coll in Tile.BAD_OBJECTS:
         return Wurm.DIED
      # Anything we can eat?
      if coll in Tile.GOOD_OBJECTS.keys():
         self.add += Tile.GOOD_OBJECTS[coll]
         state=Wurm.ATE
      # Draw snake
      self.head.draw(surface)
      for b in self.body:
         b.draw(surface)
      # Erase old tail, it gets redrawn if needed
      if self.oldtail_x != None:
         surface.addstr(self.oldtail_y,self.oldtail_x," ")
      self.tail.draw(surface)
      # Current body length is the score, starts with 3
      self.score= 10*(len(self.body)-3)
      msg = "[Score: %d]" % (self.score)
      surface.addstr(curses.LINES-1,curses.COLS//2-len(msg)//2,msg,curses.color_pair(3))

      return state


   def turn(self,direction):
      self.head.d = direction
      if direction == Tile.UP:
         self.head.b="v"
      elif direction == Tile.DOWN:
         self.head.b="^"
      elif direction == Tile.RIGHT:
         self.head.b="<"
      elif direction == Tile.LEFT:
         self.head.b=">"
    
def collision(char):
   return char in Tile.BAD_OBJECTS or char in Tile.GOOD_OBJECTS.keys() 

def get_char(x,y,surface):
   char = surface.inch(y,x)
   return chr(getbyte(char,0))
   
def draw_fruit(x,y,surface):
   fruit = random.choice([f for f in Tile.GOOD_OBJECTS.keys()])
   surface.addstr(y,x,fruit,curses.color_pair(3))
 
def add_fruit(surface):
   nx = random.randint(1,curses.COLS-1)
   ny = random.randint(1,curses.LINES-2)
   coll = get_char(nx,ny,surface)
   
   # Did we pick a bad space ?
   if collision(coll):
      # Mitigiation 1:st approach, test 10 more squares
      for _ in range(0,10):       
         nx = random.randint(1,curses.COLS-1)
         ny = random.randint(1,curses.LINES-2)
         coll = get_char(nx,ny,surface)
         if not collision(coll):
            draw_fruit(nx,ny,surface)
            return True
 
      # Bummer, last resort search whole playfield for free spot
      nx = 1
      ny = 1
      while collision(coll):
         nx += 1
         if nx>curses.COLS-2:
            ny += 1
            nx = 1
         # No free space he wins!
         if ny>curses.LINES-1:
            return False
         coll = get_char(nx,ny,surface)

   draw_fruit(nx,ny,surface) 
   return True

def pause_game(surface):
   msg  = "Game is paused"
   msg2 = "press any key to continue"
   height =4
   width = len(msg2)+4
   tlx = curses.COLS//2-width//2
   tly = curses.LINES//2-height//2
   win = curses.newwin(height,width,tly,tlx)
   win.box() 
   win.addstr(1,width//2-len(msg)//2,msg,curses.color_pair(2))
   win.addstr(2,2,msg2,curses.color_pair(3))
   win.refresh()
   # getch is blocking again =)
   _ = win.getch()
   del win
   surface.touchwin()
   surface.refresh()

class HighScore:
   def __init__(self,filename):
      self.scores = []
      self.load_highscore(filename)

   def load_highscore(self,filename):
      try:
         fp = open(filename,'rb')
      except:
         return
      
      data=fp.read()
      fp.close()
      try:
         scores_hsh=pickle.loads(data)
      except:
         print("Bajs")
         return
      
      hash=[k for k in scores_hsh.keys()][0]
      self.scores = scores_hsh[hash]
      cmp_hash= hashlib.sha256(bytes(str(self.scores).encode('utf8'))).hexdigest()
      if hash != cmp_hash:
         self.scores={}
      
      

   def save_highscore(self,filename):
      hash = hashlib.sha256(bytes(str(self.scores).encode('utf8'))).hexdigest()
      data = pickle.dumps({hash:self.scores})
      try:
         fp = open(filename,'wb') 
      except:
         return False
      fp.write(data)
      fp.flush()
      fp.close()
      return True

   def high_score(self,surface):
      msg = "Highscores"
      height = 14
      width = len(msg)+8
      tlx = curses.COLS//2-width//2
      tly = curses.LINES//2-height//2
      win = curses.newwin(height,width,tly,tlx)
      win.box() 
      win.addch(2,0,curses.ACS_LTEE)
      win.hline(2,1,curses.ACS_HLINE,width-2)
      win.addch(2,width-1,curses.ACS_RTEE)
      win.addstr(1,width//2-len(msg)//2,msg,curses.color_pair(3))
      
      i=0
      while i<10 and len(self.scores)!=i:
         (points,name) = self.scores[i]
         win.addstr(3+i,1,"%6d %-9s"%(points,name),curses.color_pair(1))
         i += 1
      win.refresh()
      # getch is blocking again =)
      _ = win.getch()
      del win
      surface.touchwin()
      surface.refresh()
   
   def add_entry(self,points,name):
      self.scores.append((points,name))
      self.scores.sort(reverse=True)
      if len(self.scores)>10:
         _ = self.scores.pop()

   def is_highscore(self,points):
      if len(self.scores)<10:
         return True
      # List can't be empty
      (min,_) = self.scores[-1]
      if points>min:
         return True
      return False


def game_over(surface,highscore,score):
   go = "-=[ GAME OVER ]=-"
   msg="New highscore - enter your name"
   height = 4
   width = len(msg)+4
   tlx = curses.COLS//2-width//2
   tly = curses.LINES//2-height//2
   win = curses.newwin(height,width,tly,tlx)
   win.box() 
   win.addstr(1,width//2-len(go)//2,go,curses.color_pair(2))
   if highscore.is_highscore(score):
      msg="New highscore - enter your name"
      win.addstr(2,2,msg,curses.color_pair(2))
      win.refresh()
      namebox = curses.newwin(1,8,tly+4,curses.COLS//2-4)
      name_field=textpad.Textbox(namebox)
      name_field.stripspaces=True
      name=name_field.edit()
      highscore.add_entry(score,name)
      del name_field
      del namebox      
   else:
      win.refresh()
      _ = win.getch()
      
   del win
   draw_main(surface)
   surface.touchwin()
   surface.refresh()
   highscore.high_score(surface)
   


def draw_main(stdscr):
   stdscr.clear()
   stdscr.border('|','|','-',' ','+','+',' ',' ')
   stdscr.addstr(curses.LINES-2,0,'+')
   stdscr.hline(curses.LINES-2,1,'-',curses.COLS-2)
   stdscr.addstr(curses.LINES-2,curses.COLS-1,'+')
   for i in range(5):
      add_fruit(stdscr)
   
def main(stdscr):
   stdscr.clear()
   curses.init_pair(1,curses.COLOR_BLACK,curses.COLOR_GREEN)
   curses.init_pair(2,curses.COLOR_RED,curses.COLOR_BLACK)
   curses.init_pair(3,curses.COLOR_YELLOW,curses.COLOR_BLACK)
   # Let curses translate key sequences for us
   stdscr.keypad(True)
   # Don't wait for enter on input
   curses.cbreak()
   # Non blocking getch() and getkey()
   stdscr.nodelay(True)
   wurm = Wurm()
   draw_main(stdscr)
   wurm.draw(stdscr)
   stdscr.refresh()
   curses.curs_set(0)
   high = HighScore("snake.dat")
 
   while True:
    
      c=stdscr.getch()
      if c == ord('q'):
         high.save_highscore("snake.dat")
         break
      elif c == curses.KEY_UP:
         wurm.turn(Tile.UP)
      elif c == curses.KEY_DOWN:
         wurm.turn(Tile.DOWN)
      elif c == curses.KEY_LEFT:
         wurm.turn(Tile.LEFT)
      elif c == curses.KEY_RIGHT:
         wurm.turn(Tile.RIGHT)
      elif c == ord('p'):
         pause_game(stdscr)
      
      wurm.move()
      state = wurm.draw(stdscr) 
      if(state == Wurm.DIED):
         game_over(stdscr,high,wurm.score)
         draw_main(stdscr)
         del wurm
         wurm = Wurm()
 
      elif (state == Wurm.ATE):
         if not add_fruit(stdscr):
            go = "-=[ YOU BEAT THE GAME ]=-"
            stdscr.addstr(curses.LINES//2,curses.COLS//2-len(go)//2,go,curses.color_pair(2))
            stdscr.refresh()
            time.sleep(5)
      stdscr.refresh()
      time.sleep(0.1)

locale.setlocale(locale.LC_ALL, '')
wrapper(main)
