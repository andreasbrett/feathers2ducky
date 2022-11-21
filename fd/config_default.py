import board

# -----------------------------------
# configure your feathers2-ducky here
# -----------------------------------

config = {
    # wifi configuration
    "wifi": {
        # wifi mode: spawn / connect / off
        "mode": "spawn",
        # spawn own Wifi Access Point
        "spawnAP": {
            "ssid": "FeatherS2Ducky",
            "password": "feathers2ducky",
            "channel": 6,
            # mac address format: xx:xx:xx:xx:xx:xx or xx-xx-xx-xx-xx-xx or None
            "macAddress": None,
        },
        # connect to existing Wifi Access Point
        "connectAP": {
            "ssid": "yourrouteraccesspoint",
            "password": "somepassword",
            # bssid format: xx:xx:xx:xx:xx:xx or xx-xx-xx-xx-xx-xx or None
            "bssid": None,
            # mac address format: xx:xx:xx:xx:xx:xx or xx-xx-xx-xx-xx-xx or None
            "macAddress": None,
        },
    },
    # internal webserver
    "webserver": {
        # hostname of the feather ducky (only effective in wifi-connect mode; use IPv4 address 192.168.4.1 in wifi-spawn mode)
        "hostname": "feathers2ducky",
        # which port should be used
        "port": 80,
        # login credentials (set to None to disable authentication)
        "credentials": {
            "username": "feather",
            "password": "ducky",
        },
        # print out debugging information about HTTP requests on serial
        "debugRequests": {
            "enabled": False,
            # show headers?
            "showHeaders": True,
            # show GET parameters?
            "showParameters": True,
            # show body (of e.g. POST messages)?
            "showBody": True,
        },
    },
    # label the feather ducky should receive (used for some payloads to determine drive letter to load/run further payloads from flash)
    "driveLabel": "_",
    # display configuration
    "display": {
        # enable display? disable if your board isn't equipped with one
        "enabled": True,
        # width and height in pixels
        "width": 128,
        "height": 32,
        # reset pin
        "resetPin": board.IO18,
    },
    # initial sleep to allow device to be recognized by the host computer (in milliseconds)
    "initialSleep": 500,
    # default keyboard locale to use (put corresponding .mpy layout in lib folder)
    "locale": "DE",
    # default delay between processing duckyscript lines (in milliseconds)
    "defaultDelay": 0,
    # USB connection settings
    "usbConnection": {
        # time to wait between each re-check (in milliseconds)
        "waitDelay": 500,
        # how many re-checks to perform before starting webserver (if enabled)
        "waitCycles": 60,
        # auto-restart FeatherS2Ducky when changes are written to its storage (you can Ctrl+C and Ctrl+D in REPL to restart)
        "autoRestartOnTouch": False,
    },
    # stealth mode settings
    "stealth": {
        # disable CDC module (needed for serial console = debugging)
        "disableCDC": True,
        # disable MIDI module
        "disableMIDI": True,
    },
    # which payload gets executed when grounding IO11/IO12/IO13/IO14/IO15/IO16
    "payloads": {
        "IO11": "fd/payloads/payload1.dd",
        "IO12": "fd/payloads/payload2.dd",
        "IO13": "fd/payloads/payload3.dd",
        "IO14": "fd/payloads/payload4.dd",
        "IO15": "fd/payloads/payload5.dd",
        "IO16": "fd/payloads/payload6.dd",
    },
    # mouseJiggler configuration
    "mouseJiggler": {
        # minimum amount of wait time for mouse jiggling (in seconds)
        "delayMinimum": 1,
        # maximum amount of wait time for mouse jiggling (in seconds)
        "delayMaximum": 15,
        # amount of mouse movement in X and Y directions (in pixels)
        "movement": 10,
        # LED configuration
        "LED": {
            # indicate jiggling through blinking the LED?
            "enabled": True,
            # how long to flash the LED (in milliseconds)
            "duration": 150,
            # indicate mouseJiggler mode through the LED
            "startupIndicator": {
                # indicate mouseJiggler mode on startup?
                "enabled": True,
                # how long to flash the LED (in milliseconds)
                "duration": 80,
                # how often to flash the LED
                "repeats": 6,
            },
        },
    },
    # psychoMouse configuration
    "psychoMouse": {
        # move mouse after X characters
        "characters": 5,
        # maximum amount to mouse movement in X and Y directions (in pixels)
        "range": 250,
        # number of random movements to generate
        "randomMovements": 10,
    },
}
