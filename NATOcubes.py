#!/usr/bin/env python

from pygame import init, Rect, Surface, Color, display, event, \
                   MOUSEBUTTONDOWN, MOUSEMOTION, QUIT
from pygame.font import Font
from time import sleep
from sys import argv, exit, stdin
from os import walk
from os.path import exists, join
from socket import SHUT_RDWR, socket, error as socket_error
from random import Random
from getopt import getopt
from optparse import OptionParser
from thread import start_new_thread
import thread, pygame


COLORS = {-1: {'name': 'Grey', 'code': Color('#cccccc')},
           0: {'name': 'Red', 'code': Color('#cc0000')},
           1: {'name': 'Blue', 'code': Color('#0000cc')},
           2: {'name': 'Green', 'code': Color('#00cc00')},
           3: {'name': 'Yellow', 'code': Color('#eeee00')},
           4: {'name': 'Magenta', 'code': Color('#cc00cc')},
           5: {'name': 'Cyan', 'code': Color('#00cccc')},
          }


pygame.display.init()
if pygame.display.get_init() != 1:
  print 'pygame.display could not be loaded.'
  exit(1)
pygame.font.init()
if pygame.font.get_init() != 1:
  print 'pygame.font could not be loaded.'
  exit(1)

if pygame.font.get_fonts().count('arial') == 1:
    font = pygame.font.SysFont('arial', 20)
    smallfont = pygame.font.SysFont('arial', 16)
elif exists('/usr/share/fonts/truetype/msttcorefonts/arial.ttf'):
    font = Font('/usr/share/fonts/truetype/msttcorefonts/arial.ttf', 20)
    smallfont = Font('/usr/share/fonts/truetype/msttcorefonts/arial.ttf', 16)
else:
    for root, dirs, files in walk('/usr/share/fonts'):
        if 'arial.ttf' in files:
            font = Font(join(root, 'arial.ttf'), 20)
            smallfont = Font(join(root, 'arial.ttf'), 16)
            break
    if not font:
        if exists('./arial.ttf'):
            font = Font('arial.ttf', 20)
            smallfont = Font('arial.ttf', 16)
        else:
            font = Font(None, 20)
            smallfont = Font(None, 16)

class Network:
    closed = False
    def __init__(self, sock):
        self.sock = sock
        self.buffer = ""
        self.listener = start_new_thread(self.listen, ())

    def listen(self):
        try:
            while 1:
                try:
                    buf = self.sock.recv(1)
                except socket_error:
                    # socket closed unexpectedly
                    self.__class__.closed = True
                    print 'Connection lost'
                    return
                if len(buf) == 0:
                    self.__class__.closed = True
                    print 'Connection lost'
                    return
                self.buffer += buf
        except Exception, e:
            print e

    def get(self, length, blocking = True):
        if blocking:
            while self.len() < length:
                if self.__class__.closed:
                    return False
                sleep(0.1)
        ret = self.buffer[0:length]
        self.buffer = self.buffer[length+1:]
        return ret

    def send(self, string):
        if self.__class__.closed:
            return False
        else:
            return self.sock.sendall(string)

    def len(self):
        return len(self.buffer)

    def close(self):
        self.sock.close()

class Field(object):
    def __init__(self, w, h, size):
        """Initialize the field with w fields in width, h fields in height and cubes with size length"""
        self.w, self.h, self.size = w, h, size
        self.content = [[[-1, 1] for _w in xrange(w)] for _h in xrange(h)]

    def turn(self, player, x, y, override=False, origx = False, origy = False):
        """Execute a player's turn, i.e. set the fields right"""
        if self.winner():
            return True
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        field = self.content[y][x]
        if not override and field[0] not in (-1, player):
            return False
        else:
            if origx == False:
                origx = x
                origy = y
            field[0] = player
            field[1] += 1

            # neighbours
            needed = 5
            if x in (0, self.w - 1):
                needed -= 1
            if y in (0, self.h - 1):
                needed -= 1

            if field[1] == needed:
                field[1] = 1
                self.turn(player, x - 1, y, True, origx, origy)
                self.turn(player, x + 1, y, True, origx, origy)
                self.turn(player, x, y - 1, True, origx, origy)
                self.turn(player, x, y + 1, True, origx, origy)
        return True

    winner = lambda self: len(set(self.content[y][x][0]
                                  for x in xrange(self.w)
                                  for y in xrange(self.h))
                             ) == 1 and self.content[0][0][0] != -1


    def render(self, newx = -1, newy = -1):
        """Render the field along with the current player on a Surface and return it"""
        surf = Surface((self.w * (self.size + 1) - 1, self.h * (self.size + 1) + 18))
        surf.fill(Color('#ffffff'))
        for y in xrange(self.h):
            for x in xrange(self.w):
                player, n = self.content[y][x]
                col = COLORS[player]
                surf.fill(col['code'], (x * (self.size + 1), 18 + y * (self.size + 1), self.size, self.size))
                pygame.draw.circle(surf, Color('#ffffff'), (x * (self.size + 1) + self.size / 2, 18 + y * (self.size + 1) + self.size / 2), 13)
                s = font.render(str(n), True, Color('#000000'))
                sw, sh = s.get_size()
                surf.blit(s, ((x * (self.size + 1) + (self.size - sw) / 2),
                              18 + (y * (self.size + 1) + (self.size - sh) / 2)))
        if newx != -1:
            pygame.draw.rect(surf, Color('#000000'), pygame.Rect(newx * (self.size + 1) - 1, 17 + newy * (self.size + 1), self.size + 2, self.size + 2), 2)
        return surf

    def count(self, player):
        count = 0
        for y in xrange(self.h):
            for x in xrange(self.w):
                fplayer, n = self.content[y][x]
                if player == fplayer:
                    count += 1
        return count

class base:
    handler = 0
    def __init__(self):
        parser = OptionParser(
            usage="Usage: %prog [OPTIONS] [HOST]",
            version="NATOcubes 0.5",
            epilog="If HOST is not specified, the game will start in local mode. Otherwise it will start in client mode, with HOST as server.")
        parser.add_option('-s', '--server', action="store_true", dest="server", default=False, help="server mode")
        parser.add_option('-p', '--port', type="int", dest="port", default=12345, help="set port (client & server mode) [default: %default]")
        parser.add_option('-x', type="int", dest="x", default=5, help="field width (server & local mode) [default: %default]")
        parser.add_option('-y', type="int", dest="y", default=5, help="field height (server & local mode) [default: %default]")
        parser.add_option('-z', '--size', type="int", dest="size", default=75, help="size of one field [default: %default]")
        parser.add_option('-l', '--player', type="int", dest="numplayers", default=2, help="number of players (local mode) [default: %default]")
        options, args = parser.parse_args()

        self.xsize, self.ysize, self.fieldsize = options.x, options.y, options.size

        if options.server:
            self.handler = server('', options.port, options.x, options.y)
        else:
            if len(args) > 0:
                self.handler = client(args[0], options.port)
                self.xsize, self.ysize = self.handler.getsize()
            else:
                self.handler = local(options.numplayers)

        self.__class__.handler = self.handler

        self.player, self.localplayer, self.numplayers = self.handler.getopts()
        self.counts = []

        self.f = Field(self.xsize, self.ysize, self.fieldsize)
        display.set_mode(((self.xsize * (self.fieldsize + 1) - 1), 18 + (self.ysize * (self.fieldsize + 1) - 1)))
        display.set_caption('NATOcubes')
        surf = self.f.render()
        self.handler.surface(surf, self.player, self.fieldsize)
        display.get_surface().blit(surf, (0, 0))
        display.update()

        ev = event.wait()
        while ev.type != QUIT:
            event.clear()
            display.update()
            if self.player == self.localplayer or self.localplayer == -1:
                ev = event.wait()
                if ev.type == MOUSEBUTTONDOWN:
                    px, py = ev.pos
                    x = px / (self.fieldsize + 1)
                    y = (py - 18) / (self.fieldsize + 1)
                    if self.f.turn(self.player, x, y):
                        self.handler.onTurn(x, y)
                        surf = self.f.render(x, y)
                        self.handler.surface(surf, self.newplayer(), self.fieldsize)
                        display.get_surface().blit(surf, (0, 0))
                        display.update()
                        if self.after_turn():
                            return
            else:
                recv = self.handler.recv_data()
                if recv and len(recv) == 2:
                    x = ord(recv[0])
                    y = ord(recv[1])
                    if self.f.turn(self.player, x, y):
                        self.handler.distribute_data(x, y)
                        surf = self.f.render(x, y)
                        self.handler.surface(surf, self.newplayer(), self.fieldsize)
                        display.get_surface().blit(surf, (0,0))
                        display.update()
                        if self.after_turn():
                            return
                    else:
                        self.handler.failed_turn()
                elif recv == '\x00':
                    s = smallfont.render('Lost Connection', True, Color('#FFFFFF'), Color('#000000'))
                    sw, sh = s.get_size()
                    display.get_surface().blit(s, (((self.xsize * self.fieldsize) - sw) / 2, ((self.ysize * self.fieldsize) - sh) / 2 + 18))
                    display.update()
                    while event.wait().type != QUIT:
                        pass
                    return
                else:
                    sleep(0.1)
                ev = event.poll()

    def newplayer(self, player = -1):
        if player == -1:
            player = self.player
        new = (player + 1) % self.numplayers
        if self.f.count(new) > 0 or self.f.count(-1) > 0:
            return new
        else:
            return self.newplayer(new)
    
    def after_turn(self):
        if self.f.winner():
            out = self.handler.onWin()
            s = smallfont.render(out, True, Color('#000000'), Color('#ffffff'))
            sw, sh = s.get_size()
            display.get_surface().blit(s, (((self.xsize * self.fieldsize) - sw) / 2, 0))
            display.update()
            while pygame.event.wait().type != QUIT:
                pass
            return True
        self.player = self.newplayer()
        self.handler.player = self.player

class server:
    def __init__(self, host = '', port = 1234, fieldx = 5, fieldy = 5):
        self.players = [{}]
        self.sock = socket()
        self.sock.bind(('', int(port)))
        self.sock.listen(2)
        i = 1

        # Get client connections
        while 1:
            print "Waiting for connection..."
            clientsock, clientaddr = self.sock.accept()
            print "Got connection from %s:%i. Accept it? (Y/n) " \
                % (clientaddr[0], clientaddr[1]),
            input = stdin.readline()
            if input[0] != 'n':
                self.players.append({'addr': clientaddr, 'sock': Network(clientsock)})
                self.players[i]['sock'].send("%c%c%c" % (chr(fieldx), chr(fieldy), chr(i)))
                print "Wait for more players? (y/N) ",
                input = stdin.readline()
                if input[0] != 'y':
                    break
                i += 1
        self.localplayer = 0
        self.numplayers = len(self.players)

        # shut down listening socket
        self.sock.close()

        # define random player
        rand = Random()
        self.player = rand.choice(range(self.numplayers))

        # send information to clients
        for id, client in enumerate(self.players):
            if id > 0:
                # #PLAYERS CURRENT_PLAYER
                client['sock'].send("%c%c"
                    % (chr(self.numplayers), chr(self.player)))

    def getopts(self):
        return (self.player, self.localplayer, self.numplayers)

    def surface(self, surf, newplayer, fieldsize):
        s = smallfont.render('Current: %s' % COLORS[newplayer]['name'], True, COLORS[newplayer]['code'])
        sw, sh = s.get_size()
        surf.blit(s, (0, 0))
        s = smallfont.render('You are %s' % COLORS[self.localplayer]['name'], True, COLORS[self.localplayer]['code'])
        sw, sh = s.get_size()
        surf.blit(s, (surf.get_width() - sw, 0))

    def onTurn(self, x, y):
        for id, client in enumerate(self.players):
            if id > 0:
                client['sock'].send("%c%c" % (chr(x), chr(y)))

    def recv_data(self):
        if self.players[self.player]['sock'].len() >= 2:
            return self.players[self.player]['sock'].get(2, False)
        elif self.players[self.player]['sock'].closed:
            return '\x00'
        return False

    def distribute_data(self, x, y):
        self.players[self.player]['sock'].send('%c' % chr(0))
        for id, client in enumerate(self.players):
            if id > 0 and id != self.player:
                client['sock'].send('%c%c' % (chr(x), chr(y)))

    def failed_turn(self):
        self.players[self.player]['sock'].send('%c' % chr(255))

    def onWin(self):
        for id, client in enumerate(self.players):
            if id > 0:
                client['sock'].close()
        if self.localplayer == self.player:
            return 'You win!'
        else:
            return 'You lose!'

    def check_closed(self):
        return False

class client:
    def __init__(self, host = 'localhost', port = 1234):
        sock = socket()
        print "Connecting to %s:%i..." % (host, int(port))
        sock.connect((host, int(port)))
        self.sock = Network(sock)
        print "Waiting for acception..."
        recv = self.sock.get(5, True)
        self.xsize = ord(recv[0])
        self.ysize = ord(recv[1])
        self.localplayer = ord(recv[2])
        self.numplayers = ord(recv[3])
        self.player = ord(recv[4])

    def getopts(self):
        return (self.player, self.localplayer, self.numplayers)

    def getsize(self):
        return (self.xsize, self.ysize)

    def surface(self, surf, newplayer, fieldsize):
        s = smallfont.render('Current: %s' % COLORS[newplayer]['name'], True, COLORS[newplayer]['code'])
        sw, sh = s.get_size()
        surf.blit(s, (0, 0))
        s = smallfont.render('You are %s' % COLORS[self.localplayer]['name'], True, COLORS[self.localplayer]['code'])
        sw, sh = s.get_size()
        surf.blit(s, (surf.get_width() - sw, 0))

    def onTurn(self, x, y):
        self.sock.send("%c%c" % (chr(x), chr(y)))
        recv = self.sock.get(1, True)
        if recv == False:
            return False
        if ord(recv[0]) == 255:
            # an error occured bla bla bla
            self.sock.close()
            print 'An Error occured'

    def recv_data(self):
        if self.sock.len() >= 2:
            return self.sock.get(2, False)
        if self.sock.closed:
            return '\x00'
        return False

    def distribute_data(self, x, y):
        pass

    def failed_turn(self):
        pass

    def onWin(self):
        self.sock.close()
        if self.localplayer == self.player:
            return 'You win!'
        else:
            return 'You lose!'

    def check_closed(self):
        return self.sock.closed

class local:
    def __init__(self, numplayers = 2):
        self.numplayers = int(numplayers)
        self.player = 0

    def getopts(self):
        return (self.player, -1, self.numplayers)

    def surface(self, surf, newplayer, fieldsize):
        s = smallfont.render('Current: %s' % COLORS[newplayer]['name'], True, COLORS[newplayer]['code'])
        sw, sh = s.get_size()
        surf.blit(s, (0, 0))

    def onTurn(self, x, y):
        pass

    def recv_data(self):
        pass

    def distribute_data(self, x, y):
        pass

    def failed_turn(self):
        pass

    def onWin(self):
        return '%s wins!' % COLORS[self.player]['name']

if __name__ == '__main__':
    call = base()
