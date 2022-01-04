# ------------------------------
# configure your pico-ducky here
# ------------------------------

config = {
    # initial sleep to allow device to be recognized by the host computer (in milliseconds)
    "initialSleep": 500,
    # default keyboard locale to use (put corresponding .mpy layout in lib folder)
    "locale": "DE",
    # default delay between processing duckyscript lines (in milliseconds)
    "defaultDelay": 0,
    # stealth mode settings
    "stealth": {
        # disable CDC module (needed for serial console = debugging)
        "disableCDC": True,
        # disable MIDI module
        "disableMIDI": True,
    },
    # which payload gets executed when grounding GP0/GP1/GP2/GP3/GP4/GP5
    "payloads": {
        "GP0": "pd/payload0.dd",
        "GP1": "pd/payload1.dd",
        "GP2": "pd/payload2.dd",
        "GP3": "pd/payload3.dd",
        "GP4": "pd/payload4.dd",
        "GP5": "pd/payload5.dd",
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
                "repetitions": 6,
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
