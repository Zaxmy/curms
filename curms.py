#!/usr/bin/env python3

# Copyright Johan Zaxmy johan@zaxmy.com 
# License GPLv3

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
      self.head = Tile(10,5,Tile.RIGHT)
      self.head.b = "<"
      self.body = []
      self.body.append(Tile(9,5,Tile.RIGHT))
      self.body.append(Tile(8,5,Tile.RIGHT))
      self.body.append(Tile(7,5,Tile.RIGHT))
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
      # Current body length is the score
      msg = "[Score: %d]" % (10*len(self.body))
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
def add_fruit(surface):
   nx = random.randint(2,curses.COLS-1)
   ny = random.randint(2,curses.LINES-1)
   coll = surface.inch(ny,nx)
   coll = getbyte(coll,0)
   # Did we pick a bad space ?
   if chr(coll) in Tile.BAD_OBJECTS or chr(coll) in Tile.GOOD_OBJECTS.keys():
      # Bummer search whole playfield for free spot
      nx = 1
      ny = 2
      while chr(coll) in Tile.BAD_OBJECTS or chr(coll) in Tile.GOOD_OBJECTS.keys():
         
         nx += 1
         if nx>curses.COLS-2:
            ny += 1
            nx = 2
         # No free space he wins!
         if ny>curses.LINES-2:
            return False
         coll = surface.inch(ny,nx)
         coll = getbyte(coll,0)
   
   fruit = random.choice([f for f in Tile.GOOD_OBJECTS.keys()])
   surface.addstr(ny,nx,fruit,curses.color_pair(3))
   return True

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
