import adafruit_displayio_ssd1306
import board
import displayio
import terminalio
from adafruit_display_text import label

# import configuration
try:
    from fd.config import config
except ImportError:
    from fd.config_default import config


alignHorizontal = {"left": 0.0, "center": 0.5, "right": 1.0}
alignVertical = {"top": 0.0, "center": 0.5, "bottom": 1.0}


def clearDisplay():
    global displayGroup
    displayGroup = displayio.Group()
    display.show(displayGroup)


def displayText(
    text, alignX=alignHorizontal["left"], alignY=alignVertical["top"], clear=False
):
    global displayGroup

    if not isInitialized:
        initializeDisplay()

    if clear:
        clearDisplay()

    textLabel = label.Label(terminalio.FONT, text=text, color=0xFFFFFF)
    textLabel.anchor_point = (alignX, alignY)
    textLabel.anchored_position = (
        alignX * config["display"]["width"],
        alignY * config["display"]["height"],
    )
    displayGroup.append(textLabel)

    return textLabel


def clearTextLine(lineNumber=1):
    global lines

    if lines[lineNumber - 1]:
        displayGroup.remove(lines[lineNumber - 1])
        lines[lineNumber - 1] = None


def displayTextLine(text, lineNumber=1, clear=False):
    global lines

    if lines[lineNumber - 1]:
        lines[lineNumber - 1].text = text
    else:
        if lineNumber == 1:
            lines[lineNumber - 1] = displayText(text=text, clear=clear)
        elif lineNumber == 2:
            lines[lineNumber - 1] = displayText(
                text=text, alignY=alignVertical["bottom"], clear=clear
            )


def initializeDisplay():
    global display, isInitialized

    displayio.release_displays()
    i2c = board.I2C()
    displayBus = displayio.I2CDisplay(
        i2c, device_address=0x3C, reset=config["display"]["resetPin"]
    )
    display = adafruit_displayio_ssd1306.SSD1306(
        displayBus, width=config["display"]["width"], height=config["display"]["height"]
    )
    isInitialized = True


lines = [None, None]
isInitialized = False
