import atexit
import configparser
import os
import sched
import sys
import threading
import time
from shutil import copyfile

import discord
from pyfirmata import Arduino

import SysTrayIcon
from icons import *
from led_matrix import LedMatrix

REFRESH_RATE = 0.5  # seconds


class ExtendedMatrix(LedMatrix):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._matrix = ZEROS

    def __eq__(self, other):
        if isinstance(other, ExtendedMatrix):
            return self._matrix == other._matrix
        else:
            return self._matrix == other

    def clear(self):
        super().clear()
        self._matrix = ZEROS

    def draw_matrix(self, point_matrix):
        super().draw_matrix(point_matrix)
        self._matrix = point_matrix

    def composite_matrix(self, point_matrix):
        """ Add points to an existing picture. """
        new_matrix = [[int(self._matrix[x][y]) | int(point_matrix[x][y]) for y in range(8)] for x in range(8)]
        self.draw_matrix(new_matrix)

    def erase_matrix(self, point_matrix):
        """ Remove points from an existing picture. """
        new_matrix = [["0" if (int(self._matrix[x][y]) & int(point_matrix[x][y])) else self._matrix[x][y] for y in range(8)] for x in range(8)]
        self.draw_matrix(new_matrix)

class DiscordListener:
    def __init__(self):
        # Initialize client
        self.client = discord.Client()

        # Try and find username and password from config file
        self.config = configparser.ConfigParser()
        if not os.path.isfile("config.ini"):
            copyfile("default.ini", "config.ini")
        self.config.read("config.ini")
        self.username = self.config['LoginInfo']['Username']
        self.password = self.config['LoginInfo']['Password']

        # Initialze Arduino and LED-matrix
        board = Arduino('COM3')
        # grab pinout from config file
        dataIn = int(self.config['Pins']['dataIn'])
        load = int(self.config['Pins']['load'])
        clock = int(self.config['Pins']['clock'])
        self.matrix = ExtendedMatrix(board, dataIn, load, clock, 1)
        self.matrix.setup()

        # Will hold a reference to each running thread
        self.threads = {}

        # Schedule update callback
        self.sched = sched.scheduler(time.time, time.sleep)
        self.sched.enter(REFRESH_RATE, 1, self.update_status)
        t_sched = threading.Thread(target=self.sched.run, daemon=True)
        t_sched.start()
        self.threads['t_sched'] = t_sched

        # Setup System Tray Icon
        def run_tray_icon(): SysTrayIcon.SysTrayIcon('mat_icon.ico', 'DiscordMatrix', (),
                                                     on_quit=lambda *_: self.exit())

        t_tray = threading.Thread(target=run_tray_icon, daemon=False)
        t_tray.start()
        self.threads['t_tray'] = t_tray

        # Finally, login to discord
        self.attempt_login()

    def update_status(self):
        state = DISCONNECTED
        if self.client.is_logged_in:
            for server in self.client.servers:
                mem = server.get_member(self.client.user.id)
                vs = mem.voice
                if vs.voice_channel is not None:
                    if vs.deaf or vs.self_deaf:
                        state = DEAFENED
                        break
                    elif vs.mute or vs.self_mute:
                        state = MUTED
                        break
                    else:
                        state = CONNECTED
                        break
        if self.matrix != state:
            self.matrix.draw_matrix(state)
        self.sched.enter(REFRESH_RATE, 1, self.update_status)

    def attempt_login(self):
        print("Attempting to log in as {}...".format(self.username))
        # Kill the existing client thread if it already exists
        if self.threads.get("t_client"):
            self.client.logout()
        t_client = threading.Thread(target=self.client.run, args=(self.username, self.password), daemon=True)
        t_client.start()
        self.threads['t_client'] = t_client
        print("Done")

    def exit(self):
        print("Exiting...")
        self.matrix.clear()
        sys.exit()


def main():
    dl = DiscordListener()
    atexit.register(dl.exit)


if __name__ == "__main__":
    while True:
        try:
            main()
        except:
            pass
        else:
            break
