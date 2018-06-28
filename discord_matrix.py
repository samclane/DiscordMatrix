import configparser
import os
import sched
import threading
import time
from shutil import copyfile
import atexit

import discord
from pyfirmata import Arduino

import led_matrix
import SysTrayIcon


REFRESH_RATE = 250

DISCONNECTED = [[1, 0, 0, 0, 0, 0, 0, 1],
                [0, 1, 0, 0, 0, 0, 1, 0],
                [0, 0, 1, 0, 0, 1, 0, 0],
                [0, 0, 0, 1, 1, 0, 0, 0],
                [0, 0, 0, 1, 1, 0, 0, 0],
                [0, 0, 1, 0, 0, 1, 0, 0],
                [0, 1, 0, 0, 0, 0, 1, 0],
                [1, 0, 0, 0, 0, 0, 0, 1]]

CONNECTED = [[0, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 0, 1],
             [0, 0, 0, 0, 0, 0, 1, 0],
             [0, 0, 0, 0, 0, 1, 0, 0],
             [1, 0, 0, 0, 1, 0, 0, 0],
             [0, 1, 0, 1, 0, 0, 0, 0],
             [0, 0, 1, 0, 0, 0, 0, 0]]

MUTED = DEAFENED = [[0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1, 0, 0, 1, 0, 0],
                    [0, 0, 0, 1, 1, 0, 0, 0],
                    [0, 0, 0, 1, 1, 0, 0, 0],
                    [0, 0, 1, 0, 0, 1, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0]]



class DiscordListener:
    def __init__(self):
        self.client = discord.Client()
        self.config = configparser.ConfigParser()
        if not os.path.isfile("config.ini"):
            copyfile("default.ini", "config.ini")
        self.config.read("config.ini")
        self.username = self.config['LoginInfo']['Username']
        self.password = self.config['LoginInfo']['Password']

        board = Arduino('COM3')
        self.matrix = led_matrix.LedMatrix(board)
        self.matrix.setup()

        self.threads = {}

        self.sched = sched.scheduler(time.time, time.sleep)
        self.sched.enter(1, 1, self.update_status)
        t_sched = threading.Thread(target=self.sched.run)
        t_sched.start()
        self.threads['t_sched'] = t_sched

        def run_tray_icon(): SysTrayIcon.SysTrayIcon('eye.ico', 'DiscordMatrix', (), on_quit=lambda *_: self.exit())
        t_tray = threading.Thread(target=run_tray_icon)
        t_tray.start()
        self.threads['t_tray'] = t_tray

        self.attempt_login()

    def update_status(self):
        state = DISCONNECTED
        if self.client.is_logged_in:
            for server in self.client.servers:
                mem = server.get_member(self.client.user.id)
                vs = mem.voice
                if vs.voice_channel is not None:
                    if vs.mute or vs.self_mute:
                        state = MUTED
                        break
                    else:
                        state = CONNECTED
                        break
        self.matrix.draw_matrix(state)
        self.sched.enter(1, 1, self.update_status)

    def attempt_login(self):
        print("Attempting to log in as {}...".format(self.username))
        # Kill the existing client thread if it already exists
        if self.threads.get("t_client"):
            self.client.logout()
        t_client = threading.Thread(target=self.client.run, args=(self.username, self.password))
        t_client.start()
        self.threads['t_client'] = t_client

    def exit(self):
        self.matrix.clear()
        os._exit(1)


def main():
    dl = DiscordListener()
    atexit.register(dl.exit)

if __name__ == "__main__":
    main()