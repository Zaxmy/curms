#!/usr/bin/env python3

# Copyright Johan Zaxmy johan@zaxmy.com 
# License GPLv3

from termios import TIOCLINUX
import time
import curses
import random
from curses import wrapper

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
   GOOD_OBJECTS = {'¤':5,'@':10,'$':15}
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
      coll = surface.inch(self.head.y,self.head.x)
      coll = getbyte(coll,0)
      #surface.addstr(2,2,chr(coll))
      #surface.addstr(3,2,"%4x"%coll,curses.color_pair(2))
      # Did we hit anything bad?
      if chr(coll) in Tile.BAD_OBJECTS:
         return Wurm.DIED
      # Anything we can eat?
      if chr(coll) in Tile.GOOD_OBJECTS.keys():
         self.add += Tile.GOOD_OBJECTS[chr(coll)]
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
      msg = "[Score: %d]" % (10*(len(self.body)-3))
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
      
#

def collision(char):
   return char in Tile.BAD_OBJECTS or char in Tile.GOOD_OBJECTS.keys() 

def get_char(x,y,surface):
   char = surface.inch(y,x)
   return chr(getbyte(char,0))
 
def draw_fruit(x,y,surface):
   fruit = random.choice([f for f in Tile.GOOD_OBJECTS.keys()])
   surface.addstr(y,x,fruit,curses.color_pair(3))
 
def add_fruit(surface):
   nx = random.randint(2,curses.COLS-1)
   ny = random.randint(2,curses.LINES-1)
   coll = get_char(nx,ny,surface)
   
   # Did we pick a bad space ?
   if collision(coll):
      # Mitigiation 1:st approach, test 10 more squares
      for _ in range(0,10):       
         nx = random.randint(2,curses.COLS-1)
         ny = random.randint(2,curses.LINES-1)
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
         if ny>curses.LINES-2:
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
   win.border('|','|','-','-','+','+','+','+') 
   win.addstr(1,width//2-len(msg)//2,msg,curses.color_pair(2))
   win.addstr(2,2,msg2,curses.color_pair(2))
   win.refresh()
   # getch is blocking again =)
   _ = win.getch()
   del win
   surface.touchwin()
   surface.refresh()

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
   # window.border([ls[, rs[, ts[, bs[, tl[, tr[, bl[, br]]]]]]]])
   stdscr.border('|','|','-','-','+','+','+','+')
   wurm.draw(stdscr)
   # Add some test fruit
   for i in range(5):
      add_fruit(stdscr)
   stdscr.refresh()
   curses.curs_set(0)
   while True:
      
      c=stdscr.getch()
      if c == ord('q'):
         break
      elif c == curses.KEY_UP:
         wurm.turn(Tile.UP)
      elif c == curses.KEY_DOWN:
         wurm.turn(Tile.DOWN)
      elif c == curses.KEY_LEFT:
         wurm.turn(Tile.LEFT)
      elif c == curses.KEY_RIGHT:
         wurm.turn(Tile.RIGHT)
      elif c == ord('e'):
         wurm.add += 1
      elif c == ord('p'):
         pause_game(stdscr)
 
      wurm.move()
      state = wurm.draw(stdscr) 
      if(state == Wurm.DIED):
         go = "-=[ GAME OVER ]=-"
         stdscr.addstr(curses.LINES//2,curses.COLS//2-len(go)//2,go,curses.color_pair(2))
         stdscr.refresh()
         time.sleep(5)
         break
      elif (state == Wurm.ATE):
         if not add_fruit(stdscr):
            go = "-=[ YOU BEAT THE GAME ]=-"
            stdscr.addstr(curses.LINES//2,curses.COLS//2-len(go)//2,go,curses.color_pair(2))
            stdscr.refresh()
            time.sleep(5)
      stdscr.refresh()
      time.sleep(0.1)

wrapper(main)
