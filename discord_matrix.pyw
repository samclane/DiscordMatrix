import atexit
import configparser
import os
import sched
import sys
import threading
import time
from shutil import copyfile
from time import strftime

import discord
from pyautogui import hotkey
from pyfirmata import Arduino, util, INPUT

import SysTrayIcon
from icons import *
from led_matrix import LedMatrix

REFRESH_RATE = 0.1  # seconds
SENSOR_COOLDOWN_MAX = 1  # seconds
SENSOR_COOLDOWN = SENSOR_COOLDOWN_MAX


class ExtendedMatrix(LedMatrix):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._matrix = ZEROS
        self._buffer = ZEROS
        self.state = None

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
        self._matrix = np.asarray(point_matrix, dtype=np.bool_)

    def composite_matrix(self, point_matrix):
        """ Add points to an existing picture. """
        new_matrix = np.asarray(
            [[int(self._matrix[x][y]) | int(point_matrix[x][y]) for y in range(8)] for x in range(8)], dtype=np.bool_)
        self.draw_matrix(new_matrix)

    def subtract_matrix(self, point_matrix):
        """ Remove points from an existing picture. """
        new_matrix = np.asarray([
            ["0" if (int(self._matrix[x][y]) & int(point_matrix[x][y])) else self._matrix[x][y] for y in range(8)] for x
            in range(8)])
        self.draw_matrix(new_matrix)

    def shift_left(self):
        """ Shifts current image left by 1 row """
        mat = np.roll(self._matrix, -1, axis=1)
        if np.count_nonzero(self._buffer):
            mat[:, -1] = self._buffer[:, 0]
            self._buffer = np.roll(self._buffer, -1, axis=1)
            self._buffer[:, -1] = np.zeros(8)
        self.draw_matrix(mat)

    def write_string(self, string, clear_after=False):
        string += "."
        for char in string:
            sprite = icons[char]
            self._buffer = sprite
            while np.count_nonzero(self._buffer):
                self.shift_left()
        if clear_after:
            self.clear()


class AvoidSensor:

    def __init__(self, board, pin):
        self._board = board
        self.pin = pin

        self.iter = util.Iterator(self._board)

    def setup(self):
        print("Initializing Avoid Sensor...")
        self._board.digital[self.pin].mode = INPUT
        self.iter.start()
        print("Avoid Sensor Initialized")

    def value(self):
        return self._board.digital[self.pin].read()


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

        self.keybinds = {}
        self.keybinds['mute'] = [w.lower() for w in self.config["Keybinds"]["mute"].split('+')]

        # Initialze Arduino and LED-matrix
        board = Arduino('COM3', baudrate=125000)
        # grab pinout from config file
        dataIn = int(self.config['Pins']['dataIn'])
        load = int(self.config['Pins']['load'])
        clock = int(self.config['Pins']['clock'])
        self.matrix = ExtendedMatrix(board, dataIn, load, clock, 1)
        self.matrix.setup()

        sensorPin = int(self.config['Pins']['sensor'])
        self.sensor = AvoidSensor(board, sensorPin)
        self.sensor.setup()

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

    def get_client_state(self):
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
        return state

    def update_status(self):
        global SENSOR_COOLDOWN
        state = self.get_client_state()
        if self.matrix.state != state:
            self.matrix.state = state
            if self.matrix.state != DISCONNECTED:
                self.matrix.draw_matrix(state)
        if self.matrix.state == DISCONNECTED:
            self.matrix.write_string(strftime("%I:%M"), clear_after=True)  # Huge blocking call. Should fix this.
        if any([server.get_member(self.client.user.id).voice.voice_channel for server in
                self.client.servers]) and not self.sensor.value() and not SENSOR_COOLDOWN:
            hotkey(*self.keybinds['mute'])  # Want to mute here
            SENSOR_COOLDOWN = SENSOR_COOLDOWN_MAX
        SENSOR_COOLDOWN = max(SENSOR_COOLDOWN - REFRESH_RATE, 0)
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
