import config
import logging
import socket
from files import *
import os
import sys
import json
import subprocess
import time
import atexit
import threading
from common import *
from setup_screens import *
from error import *
from info import *
from mlb import *
from nhl import *
from PIL import Image, ImageDraw, ImageFont
from string import Template
from flask import jsonify
from flask import request
from flask import Flask
print("Begin Scoreboard App.py")


logging.basicConfig(level=logging.INFO,
                    handlers=[
                        logging.FileHandler(os.path.join(
                            root_path, "../scoreboard_log"), "w"),
                        logging.StreamHandler(sys.stdout)
                    ])
log = logging.getLogger(__name__)
try:
    from rgbmatrix import graphics, RGBMatrixOptions, RGBMatrix
    log.info("Running in production mode")
except:
    config.testing = True
    log.info("Running in test mode")
    from fake_matrix import *
    hotspot_on = os.path.join(root_path, "hotspot_on_test.sh")
    hotspot_off = os.path.join(root_path, "hotspot_off_test.sh")

app = Flask(__name__)


common_data = {}


data_lock = threading.RLock()
render_thread = threading.Thread()


def create_app():
    app = Flask(__name__)

    def interrupt():
        global render_thread
        render_thread.cancel()

    def draw_image():
        # First, manage the setup state
        with data_lock:
            if common_data[SCREEN_ON_KEY]:
                common_data[SCREENS_KEY][common_data[ACTIVE_SCREEN_KEY]].refresh()
                image = common_data[SCREENS_KEY][common_data[ACTIVE_SCREEN_KEY]].get_image(
                )
                common_data[MATRIX_KEY].Clear()
                common_data[MATRIX_KEY].SetImage(image.convert("RGB"))
            else:
                common_data[MATRIX_KEY].Clear()

    def draw():
        global common_data
        global render_thread
        draw_image()
        render_thread = threading.Timer(
            common_data[SCREENS_KEY][common_data[ACTIVE_SCREEN_KEY]].get_sleep_time(), draw, ())

        render_thread.start()

    @app.route('/', methods=['GET'])
    def root():
        settings = get_settings()
        return jsonify(settings)

    @app.route('/configure', methods=['POST'])
    def configure():
        global common_data
        global data_lock
        with data_lock:
            interrupt()
            content = request.get_json()
            old_settings = get_settings()
            merged = {**old_settings, **content}
            write_settings(merged)
            initScreens()
        resp = jsonify(get_settings())
        return resp

    @app.route('/setPower', methods=['POST'])
    def setPower():
        global common_data
        global data_lock
        with data_lock:
            settings = get_settings()
            if settings[SETUP_STATE_KEY] == SetupState.READY.value:
                interrupt()
                content = request.get_json()
                common_data[SCREEN_ON_KEY] = content[SCREEN_ON_KEY]
                draw_image()
                settings[SCREEN_ON_KEY] = common_data[SCREEN_ON_KEY]
                write_settings(settings)
            else:
                log.error("Cannot power off, scoreboard is not ready")
        resp = jsonify(settings)
        return resp

    @app.route('/setSport', methods=['POST'])
    def setSport():
        global common_data
        global data_lock
        with data_lock:
            settings = get_settings()
            if settings[SETUP_STATE_KEY] == SetupState.READY.value:
                interrupt()
                common_data[ACTIVE_SCREEN_KEY] = ActiveScreen.REFRESH
                common_data[SCREEN_ON_KEY] = True
                draw()
                content = request.get_json()
                new_screen = ActiveScreen(content["sport"])
                common_data[ACTIVE_SCREEN_KEY] = ActiveScreen(content["sport"])
                # Update the file
                settings[ACTIVE_SCREEN_KEY] = common_data[ACTIVE_SCREEN_KEY].value
                settings[SCREEN_ON_KEY] = common_data[SCREEN_ON_KEY]
                write_settings(settings)
            else:
                log.error("Cannot set sport, scoreboard is not ready")
        resp = jsonify(settings)
        return resp

    # Used to set the wifi configuration
    @app.route('/wifi', methods=['POST'])
    def setup_wifi():
        global common_data
        global data_lock
        with data_lock:
            content = request.get_json()
            with open(wpa_template, "r") as template:
                wpa_content = Template(template.read())
                substituted = wpa_content.substitute(
                    ssid=content['ssid'], psk=content['psk'])
                common_data[SCREENS_KEY][ActiveScreen.WIFI_DETAILS].begin_countdown(
                    substituted, hotspot_off)
            return jsonify(settings)

    # This should also happen when the button is pressed and held for ten seconds
    @app.route('/reset_wifi', methods=['POST'])
    def reset_wifi():
        global common_data
        global data_lock
        with data_lock:
            settings = get_settings()
            settings[ACTIVE_SCREEN_KEY] = ActiveScreen.HOTSPOT.value
            settings[SETUP_STATE_KEY] = SetupState.HOTSPOT.value
            write_settings(settings)
            subprocess.Popen([hotspot_on])
            threading.Timer(3, reboot)
            return jsonify(settings)

    # Used on Sync screen. When the app parses the IP code, it will send this API request
    @app.route('/sync', methods=['POST'])
    def sync():
        global common_data
        global data_lock
        with data_lock:
            settings = get_settings()
            if settings[SETUP_STATE_KEY] == SetupState.SYNC.value:
                settings[SETUP_STATE_KEY] = SetupState.READY.value
                settings[ACTIVE_SCREEN_KEY] = ActiveScreen.NHL.value
                common_data[ACTIVE_SCREEN_KEY] = ActiveScreen.NHL
                write_settings(settings)
                return jsonify(settings)
            else:
                return jsonify(success=False)
    # Used on Hotspot state. When app connects to scoreboard, move to Wifi connect state
    @app.route('/connect', methods=['POST'])
    def connect():
        global common_data
        global data_lock
        global log
        with data_lock:
            settings = get_settings()
            log.info(settings)
            log.info("Got connection command, setupstate = {}".format(
                settings[SETUP_STATE_KEY]))
            if settings[SETUP_STATE_KEY] == SetupState.HOTSPOT.value:
                settings[SETUP_STATE_KEY] = SetupState.WIFI_CONNECT.value
                settings[ACTIVE_SCREEN_KEY] = ActiveScreen.WIFI_DETAILS.value
                interrupt()
                common_data[ACTIVE_SCREEN_KEY] = ActiveScreen.WIFI_DETAILS
                common_data[SCREEN_ON_KEY] = True
                draw()
                write_settings(settings)
                return jsonify(settings)
            else:
                # TODO find a better way to return failure
                response = jsonify(success=False)
                response.status_code = 500
                return response

    # Starting the service ALWAYS turns the screen on
    common_data[SCREEN_ON_KEY] = True
    settings = get_settings()
    settings[SCREEN_ON_KEY] = True
    if settings[SETUP_STATE_KEY] == SetupState.FACTORY.value:
        settings[SETUP_STATE_KEY] = SetupState.HOTSPOT.value
    elif settings[SETUP_STATE_KEY] == SetupState.SYNC.value:
        if get_ip_address() == "":
            # Got empty string, which means it failed to connect. Display something funky and make the user reset
            log.error("Failed to connect to wifi")
            common_data[SCREENS_KEY][ActiveScreen.ERROR] = ErrorScreen(
                "Failed to connect to wifi")
            settings[ACTIVE_SCREEN_KEY] = ActiveScreen.ERROR.value
        else:
            settings[ACTIVE_SCREEN_KEY] = ActiveScreen.SYNC.value

    write_settings(settings)

    draw()  # Draw the refresh screen
    initScreens()
    log.info("Done setup")
    atexit.register(interrupt)
    return app


def initScreens():
    screen_settings = get_settings()["screens"]
    try:
        mlb_settings = next(
            screen for screen in screen_settings if screen["id"] == ActiveScreen.MLB.value)
        nhl_settings = next(
            screen for screen in screen_settings if screen["id"] == ActiveScreen.NHL.value)
    except:
        print("Something went wrong while parsing screen settings")
    print(nhl_settings)
    print(mlb_settings)
    log.info("Refreshing Sports")
    mlb = MLB(mlb_settings)
    log.info("Got MLB")
    nhl = NHL(nhl_settings)
    log.info("Got NHL")
    with data_lock:
        common_data[SCREENS_KEY][ActiveScreen.NHL] = nhl
        common_data[SCREENS_KEY][ActiveScreen.MLB] = mlb
        common_data[ACTIVE_SCREEN_KEY] = ActiveScreen(
            get_settings()[ACTIVE_SCREEN_KEY])


def run_webserver():
    create_app().run(host='0.0.0.0', port=5005)


if __name__ == '__main__':
    # Set up the matrix options
    print("In app main")
    options = RGBMatrixOptions()
    options.brightness = 100
    options.rows = 32
    options.cols = 64
    options.hardware_mapping = "adafruit-hat"  # TODO use the hack to remove flicker

    with data_lock:
        common_data[ACTIVE_SCREEN_KEY] = ActiveScreen.REFRESH
        common_data[SCREENS_KEY] = {
            ActiveScreen.REFRESH: InfoScreen("Refreshing...")}
        common_data[MATRIX_KEY] = RGBMatrix(options=options)
        common_data[SCREENS_KEY][ActiveScreen.SYNC] = SyncScreen()
        common_data[SCREENS_KEY][ActiveScreen.HOTSPOT] = WifiHotspot()
        common_data[SCREENS_KEY][ActiveScreen.WIFI_DETAILS] = ConnectionScreen()
        common_data[SCREENS_KEY][ActiveScreen.ERROR] = ErrorScreen(
            "Dummy Error Message")

    if not config.testing:
        run_webserver()
    else:  # This is a terrible hack but it helps keep things running in test mode
        web_thread = threading.Thread(target=run_webserver)
        web_thread.start()
        common_data[MATRIX_KEY].master.mainloop()
