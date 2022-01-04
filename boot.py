import storage
import usb_cdc
import usb_midi
from board import *
from digitalio import DigitalInOut, Pull

# import configuration
try:
    from fd.config import config
except ImportError:
    print(
        "Using default configuration (config_default.py). To use your own settings copy as config.py and modify to taste."
    )
    from fd.config_default import config


# change the drive's label
def changeDriveLabel(name):
    storage.remount("/", readonly=False)
    storage.getmount("/").label = name
    storage.remount("/", readonly=True)


# check if provided pin is grounded
def isPinGrounded(pin):
    checkPin = DigitalInOut(pin)
    checkPin.switch_to_input(pull=Pull.UP)
    return not checkPin.value


# boilerplate
print("")
print("Configuration")
print("--------------------------------")
print(" > Drive Label  =", config["driveLabel"])
print(" > disable CDC  =", config["stealth"]["disableCDC"])
print(" > disable MIDI =", config["stealth"]["disableMIDI"])
print("--------------------------------")

# change drive label
changeDriveLabel(config["driveLabel"])

# check IO21 for stealth mode
if isPinGrounded(IO21):

    print("IO21 is grounded")

    if config["stealth"]["disableCDC"]:
        print(" -> disabling CDC...")
        usb_cdc.disable()

    if config["stealth"]["disableMIDI"]:
        print(" -> disabling MIDI...")
        usb_midi.disable()

    print(" -> disabling USB drive...")
    storage.disable_usb_drive()

else:
    # normal boot
    print("IO21 not grounded => USB drive enabled")
