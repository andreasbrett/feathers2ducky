# License : GPLv2.0
# copyright (c) 2021  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)
#
# Fork: Andreas Brett @andreasbrett
#  - major refactoring
#  - extended duckyscript language
#  - dynamic locale switching
#  - mouse and media key injection
#  - externalized configuration to customize ducky easily
#  - spawn new or connect to existing AP
#  - responsive web ui
#  - detailed debugging through serial monitor
#  - display support

import binascii
import gc
import json
import os
import random
import re
import time

import ampule
import socketpool
import supervisor
import storage
import usb_hid
import wifi
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS as KeyboardLayout
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
from board import *
from digitalio import DigitalInOut, Direction, Pull

# import configuration
try:
    from fd.config import config
except ImportError:
    print(
        "Using default configuration (config_default.py). To use your own settings copy as config.py and modify to taste."
    )
    from fd.config_default import config

from fd.consumerControlCommands import consumerControlCommands
from fd.duckyCommands import duckyCommands
from fd.htmlHeaders import headersAuth, headersCss, headersHtml, headersJs, headersJson
from fd.mouseButtons import mouseButtons
from fd.unquote import unquote

# -----------------------------------------------------------------------------------------------------
# Ducky Script Processing / HID Injection
# -----------------------------------------------------------------------------------------------------

def myprint(msg, store=True):
    global duckyScriptResult

    print(msg)
    if store:
        duckyScriptResult = duckyScriptResult + msg + "\r\n"


# check if provided pin is grounded
def isPinGrounded(pin):
    checkPin = DigitalInOut(pin)
    checkPin.switch_to_input(pull=Pull.UP)
    return not checkPin.value


# sleep a short amount of time (and add to global delay counter)
def delay(seconds):
    global delayCounter
    time.sleep(seconds)
    delayCounter += seconds


# split string into list tokens and make 1st token UPPERCASE
def splitToTokens(line):
    tokens = line.split(" ")
    tokens[0] = tokens[0].upper()
    return tokens


# join list of tokens to a string
def joinTokens(tokens, start=0):
    return " ".join(tokens[start:])


# pick a random delay time
#  - returns current timestamp and determined delay time
def pickRandomDelay():
    return time.monotonic(), (
        random.randint(
            config["mouseJiggler"]["delayMinimum"],
            config["mouseJiggler"]["delayMaximum"],
        )
    )


# blink onboard LED
def blinkLED(duration=0.2, repeats=1):
    for i in range(repeats):
        led.value = True
        delay(duration)
        led.value = False
        delay(duration)


# infinitely jiggle mouse ever so often
def mouseJigglerLoop():
    # blink LED (startup indicator)
    if config["mouseJiggler"]["LED"]["startupIndicator"]["enabled"]:
        blinkLED(
            config["mouseJiggler"]["LED"]["startupIndicator"]["duration"] / 1000,
            config["mouseJiggler"]["LED"]["startupIndicator"]["repetitions"],
        )

    myprint("")
    myprint("Running mouse jiggler")
    myprint("--------------------------------")
    myprint(" > movement  =", config["mouseJiggler"]["movement"], "pixels")
    myprint(" > delay min =", config["mouseJiggler"]["delayMinimum"], "seconds")
    myprint(" > delay max =", config["mouseJiggler"]["delayMaximum"], "seconds")
    myprint("--------------------------------")

    timestamp, delay = pickRandomDelay()

    myprint("waiting", delay, "seconds...")
    while True:
        if (time.monotonic() - timestamp) > delay:
            # move mouse up+left then back down+right
            myprint("jiggling mouse", config["mouseJiggler"]["movement"], "pixels")
            mouse.move(
                x=config["mouseJiggler"]["movement"] * -1,
                y=config["mouseJiggler"]["movement"] * -1,
            )
            mouse.move(
                x=config["mouseJiggler"]["movement"],
                y=config["mouseJiggler"]["movement"],
            )

            # blink LED
            if config["mouseJiggler"]["LED"]["enabled"]:
                blinkLED(config["mouseJiggler"]["LED"]["duration"] / 1000)

            # determine delay
            timestamp, delay = pickRandomDelay()
            myprint("waiting", delay, "seconds...")


# dynamically load the provided keyboard locale
def loadLocale(locale):
    global KeyboardLayout, Keycode, kbd_layout
    if locale.upper() == "US":
        moduleKeyboardLayout = __import__(
            "adafruit_hid.keyboard_layout_us", globals(), locals(), ["KeyboardLayoutUS"]
        )
        moduleKeycode = __import__(
            "adafruit_hid.keycode", globals(), locals(), ["Keycode"]
        )
        KeyboardLayout = moduleKeyboardLayout.KeyboardLayoutUS
        Keycode = moduleKeycode.Keycode
    else:
        moduleKeyboardLayout = __import__(
            "keyboard_layout_win_" + locale.lower(),
            globals(),
            locals(),
            ["KeyboardLayout"],
        )
        moduleKeycode = __import__(
            "keycode_win_" + locale.lower(), globals(), locals(), ["Keycode"]
        )
        KeyboardLayout = moduleKeyboardLayout.KeyboardLayout
        Keycode = moduleKeycode.Keycode
    kbd_layout = KeyboardLayout(kbd)


# convert to keycodes
def convertLineToKeycodes(line):
    keycodes = []
    # loop on each key - the filter removes empty values
    for key in filter(None, line.split(" ")):
        key = key.upper()
        # find the keycode for the command in the list
        command_keycode = duckyCommands.get(key, None)
        if command_keycode is not None:
            # if it exists in the list, use it
            keycodes.append(command_keycode)
        elif hasattr(Keycode, key):
            # if it's in the Keycode module, use it (allows any valid keycode)
            keycodes.append(getattr(Keycode, key))
        else:
            # if it's not a known key name, show the error for diagnosis
            myprint(f"Unknown key: <{key}>")
    myprint(f"{line} (keycodes = {keycodes})")
    return keycodes


# build OR-ed list of mouse buttons to click/press/release
def convertLineToMouseButtons(line):
    buttons = 0
    for button in filter(None, line.split(" ")):
        buttons |= mouseButtons.get(button, None)
    return buttons


# perform a keyboard action (press keys provided in keycode list)
def performKeyboardAction(keycodes):
    for keycode in keycodes:
        kbd.press(keycode)
    kbd.release_all()


# perform a mouse action (move, scroll, click, press, release)
def performMouseAction(line):
    # split line into tokens (0 = command, 1-x = parameters)
    tokens = splitToTokens(line)

    # move mouse pointer
    if tokens[0] == "MOVE":
        moveX = int(tokens[1])
        moveY = int(tokens[2])
        myprint(f"MOUSE {line} (x={moveX}, y={moveY})")
        mouse.move(x=moveX, y=moveY)

    # scroll mouse wheel
    elif tokens[0] == "WHEEL":
        amount = int(joinTokens(tokens, 1))
        myprint(f"MOUSE {line}")
        mouse.move(wheel=amount)

    # click and release one or more mouse buttons
    elif tokens[0] == "CLICK":
        mouse_buttons = convertLineToMouseButtons(joinTokens(tokens, 1))
        myprint(f"MOUSE {line} (buttons = {mouse_buttons})")
        mouse.click(mouse_buttons)

    # press (and don't release) one or more mouse buttons
    elif tokens[0] == "PRESS":
        mouse_buttons = convertLineToMouseButtons(joinTokens(tokens, 1))
        myprint(f"MOUSE {line} (buttons = {mouse_buttons})")
        mouse.press(mouse_buttons)

    # release one or more mouse buttons
    elif tokens[0] == "RELEASE":
        mouse_buttons = convertLineToMouseButtons(joinTokens(tokens, 1))
        myprint(f"MOUSE {line} (buttons = {mouse_buttons})")
        mouse.release(mouse_buttons)

    # release all mouse buttons
    elif tokens[0] == "RELEASEALL":
        myprint(f"MOUSE RELEASEALL")
        mouse.release_all()


# perform a consumer control action
def performConsumerControlAction(line):
    # split line into tokens (0 = command, 1-x = parameters)
    tokens = splitToTokens(line)

    # send cc action
    if tokens[0] == "SEND":
        consumer_code = consumerControlCommands.get(joinTokens(tokens, 1))
        myprint(f"CC {line} (code = {consumer_code})")
        cc.send(consumer_code)

    # press (and don't release) one or more mouse buttons
    elif tokens[0] == "PRESS":
        consumer_code = consumerControlCommands.get(joinTokens(tokens, 1))
        myprint(f"CC {line} (code = {consumer_code})")
        cc.press(consumer_code)

    # release currently  pressed cc (only one can be pressed at a time)
    elif tokens[0] == "RELEASE":
        myprint(f"CC RELEASE")
        cc.release()


# type out provided string
#  - randomly moves mouse in psychoMouse mode
#  - stops time to type out the provided string
def typeString(s):
    prefix = s[0:32] + ("..." if len(s) > 32 else "")
    myprint(f"STRING {prefix}")
    stopwatch = time.monotonic()

    if psychoMouse:
        rand = []
        for i in range(0, config["psychoMouse"]["randomMovements"]):
            rand.append(
                random.randint(
                    -1 * config["psychoMouse"]["range"], config["psychoMouse"]["range"]
                )
            )
        i = pos = 0
        while pos < len(s):
            kbd_layout.write(s[pos : (pos + config["psychoMouse"]["characters"])])
            mouse.move(
                x=rand[i % config["psychoMouse"]["randomMovements"]],
                y=rand[(i + 1) % config["psychoMouse"]["randomMovements"]],
            )
            i += 1
            pos += config["psychoMouse"]["characters"]
    else:
        kbd_layout.write(s)

    stopwatch = time.monotonic() - stopwatch
    if stopwatch > 1:
        myprint(f" -> {len(s)} characters in {round(stopwatch, 2)} seconds")
    else:
        myprint(f" -> {len(s)} characters in {round(1000 * stopwatch, 2)} milliseconds")


# wait for presence of give Wifi Access Point
def waitForWifiAP(ssid, bssid=None, minimumRssi=None):

    myprint("")
    myprint(f'Waiting for Wifi AP "{ssid}"...')
    myprint("--------------------------------------------------")

    stopwatch = time.monotonic()

    ssid = ssid.lower()
    if bssid:
        bssid = binascii.unhexlify(bssid.replace(":", "").replace("-", ""))

    while True:

        for ap in wifi.radio.start_scanning_networks():

            if ap.ssid.lower() == ssid:
                bSsid = True
            else:
                bSsid = False

            if not bssid:
                bBssid = True
            elif ap.bssid == bssid:
                bBssid = True
            else:
                bBssid = False

            if not minimumRssi:
                bRssi = True
            elif ap.rssi > minimumRssi:
                bRssi = True
            else:
                bRssi = False

            if bSsid and bBssid and bRssi:
                bssid = binascii.hexlify(ap.bssid).decode()
                bssid = (
                    bssid[0:2]
                    + ":"
                    + bssid[2:4]
                    + ":"
                    + bssid[4:6]
                    + ":"
                    + bssid[6:8]
                    + ":"
                    + bssid[8:10]
                    + ":"
                    + bssid[10:12]
                )

                stopwatch = time.monotonic() - stopwatch
                myprint(
                    f" --> Access Point present after {round(stopwatch, 2)} seconds"
                )
                myprint(f"     * SSID:  {ap.ssid}")
                myprint(f"     * BSSID: {bssid}")
                myprint(f"     * RSSI:  {ap.rssi}")

                wifi.radio.stop_scanning_networks()
                return True

        wifi.radio.stop_scanning_networks()
        delay(2)


# process a line of duckyscript
def processLine(line):
    global defaultDelay, psychoMouse, config

    # split line into tokens (0 = command, 1-x = parameters)
    tokens = splitToTokens(line)

    # comment => ignore them
    if tokens[0] == "REM":
        pass

    # wait X milliseconds
    elif tokens[0] == "DELAY":
        delay(float(tokens[1]) / 1000)

    # output a string directly
    elif tokens[0] == "STRING":
        typeString(joinTokens(tokens, 1))

    # output a string with carriage return directly
    elif tokens[0] == "STRINGLN":
        typeString(joinTokens(tokens, 1))
        performKeyboardAction(convertLineToKeycodes("ENTER"))

    # print out statement
    elif tokens[0] == "PRINT":
        myprint(f"[SCRIPT]: {joinTokens(tokens, 1)}")

    # set default delay
    elif tokens[0] == "DEFAULTDELAY" or tokens[0] == "DEFAULT_DELAY":
        defaultDelay = int(tokens[1]) * 10

    # control the LED
    elif tokens[0] == "LED":
        # toggle if there are not parameters
        if len(tokens) == 1:
            led.value = not led.value
        # enable or disable LED otherwise
        else:
            led.value = True if tokens[1].upper() == "ON" else False

    # control the LED
    elif tokens[0] == "BLINK_LED":
        if len(tokens) == 1:
            blinkLED()
        elif len(tokens) == 2:
            blinkLED(duration=(float(tokens[1]) / 1000))
        elif len(tokens) == 3:
            blinkLED(duration=(float(tokens[1]) / 1000), repeats=float(tokens[2]))

    # import another duckyscript payload
    elif tokens[0] == "IMPORT":
        processDuckyScript(tokens[1], initialCall=False)

    # switch locale
    elif tokens[0] == "LOCALE":
        loadLocale(tokens[1])

    # control mouse
    elif tokens[0] == "MOUSE":
        performMouseAction(joinTokens(tokens, 1))

    # consumer control command
    elif tokens[0] == "CC":
        performConsumerControlAction(joinTokens(tokens, 1))

    # control psychoMouse mode
    elif tokens[0] == "PSYCHOMOUSE":
        # enable psychoMouse mode
        psychoMouse = True
        if len(tokens) > 1:
            # disable psychoMouse mode
            if tokens[1] == "OFF":
                psychoMouse = False

            # set psychoMouse settings
            else:
                config["psychoMouse"]["characters"] = int(tokens[1])
                if len(tokens) > 2:
                    config["psychoMouse"]["range"] = int(tokens[2])

    elif tokens[0] == "WAITFORWIFI":
        waitForWifiAP(joinTokens(tokens, 1))

    elif tokens[0] == "WAITFORLED":
        ledCodes = {
            "CAPS_LOCK": Keyboard.LED_CAPS_LOCK,
            "COMPOSE": Keyboard.LED_COMPOSE,
            "NUM_LOCK": Keyboard.LED_NUM_LOCK,
            "SCROLL_LOCK": Keyboard.LED_SCROLL_LOCK,
        }
        ledCode = ledCodes[tokens[1].upper()]
        ledState = (tokens[2].upper() == "ON")

        myprint(f"Waiting for {tokens[1].upper()} LED to be {tokens[2].lower()}...")
        while True:
            if kbd.led_on(ledCode) == ledState:
                break
            delay(0.1)

    # no recognized special command => just run the converted keycodes
    else:
        performKeyboardAction(convertLineToKeycodes(line))


# process a duckyscript file or file content
def processDuckyScript(duckyScriptPath, duckyScript=None, initialCall=True):
    global delayCounter

    if initialCall:
        delayCounter = 0
        if duckyScriptPath:
            displayTextLine(f"{duckyScriptPath.replace("fd/payloads/", "")}", clear=True)
        elif duckyScript:
            displayTextLine("<fileless payload>", clear=True)
        displayTextLine("... running ...", 2)

    if not initialCall:
        myprint("")

    stopwatch = time.monotonic()
    if duckyScriptPath:
        myprint(f"Running {duckyScriptPath}")
        myprint("--------------------------------")
        f = open(duckyScriptPath, "r", encoding="utf-8")
        duckyScript = f.readlines()
        f.close()

    elif duckyScript:
        myprint(f"Running fileless duckyscript")
        myprint("--------------------------------")
        duckyScriptPath = "<fileless duckyscript>"
        duckyScript = duckyScript.split("\n")

    previousLine = ""
    for line in duckyScript:

        # split line into tokens (0 = command, 1-x = parameters)
        line = line.rstrip()
        tokens = splitToTokens(line)

        if tokens[0] == "REPEAT":
            # repeat the last command
            for i in range(int(tokens[1])):
                processLine(previousLine)
                delay(float(defaultDelay) / 1000)
        else:
            processLine(line)
            previousLine = line
        delay(float(defaultDelay) / 1000)

    myprint("--------------------------------")

    stopwatch = time.monotonic() - stopwatch
    if stopwatch > 1:
        myprint(
            f" -> Finished {duckyScriptPath}. Processed {len(duckyScript)} lines in {round(stopwatch, 2)} seconds."
        )
    else:
        myprint(
            f" -> Finished {duckyScriptPath}. Processed {len(duckyScript)} lines in {round(1000 * stopwatch, 2)} milliseconds."
        )
    if initialCall:
        displayTextLine(f"finished in {round(stopwatch, 2)}s", 2)
        myprint(
            f" -> All delays (commands and default delay) summed up to {delayCounter} seconds."
        )
    myprint("")


# -----------------------------------------------------------------------------------------------------
# Web Server
# -----------------------------------------------------------------------------------------------------


def encodeForTransport(s):
    s = s.encode("utf-8")
    s = binascii.b2a_base64(s)
    return s


def decodeFromTransport(s):
    s = unquote(s)
    s = binascii.a2b_base64(s)
    s = s.decode("utf-8")
    return s


def debugRequest(request):
    if config["webserver"]["debugRequests"]["enabled"]:
        print("[REQUEST]", request.path)
        if config["webserver"]["debugRequests"]["showHeaders"]:
            print(" - headers:")
            for key, value in request.headers.items():
                print(f"    - {key} = {value}")

        if config["webserver"]["debugRequests"]["showParameters"]:
            print(" - params:")
            for key, value in request.params.items():
                print(f"    - {key} = {value}")

        if config["webserver"]["debugRequests"]["showBody"]:
            print(" - body:   ", request.body)


def getPostParams(request):
    params = {}
    pairs = request.body.split("&")
    for pair in pairs:
        tmp = pair.split("=")
        if len(tmp) == 2:
            params[tmp[0]] = tmp[1]
    return params


def readFile(filename):
    try:
        f = open(filename, "r")
        d = f.read()
        f.close()
        return d
    except Exception:
        print("Error trying to read file: ", filename)
        return None


def writeFile(filename, content):
    try:
        f = open(filename, "w", encoding="utf-8")
        for line in content:
            f.write(line)
        f.close()
        return True
    except Exception:
        print("Error trying to write file: ", filename)
        return False


def htmlHeader():
    return readFile("fd/web/header.html")


def htmlFooter():
    return readFile("fd/web/footer.html")


def checkAuthorization(request):
    # don't ask for credentials when disabled
    if config["webserver"]["credentials"] is None:
        return False

    # 'authorization' header present?
    if "authorization" in request.headers.keys():

        # derive credentials from authorization header
        credentialsBase64 = request.headers["authorization"].replace("Basic ", "")
        credentials = binascii.a2b_base64(credentialsBase64).decode().split(":")

        # compare username and password
        if credentials[0] == config["webserver"]["credentials"]["username"] and credentials[1] == config["webserver"]["credentials"]["password"]:
            return False

    return (401, headersAuth, "")


@ampule.route("/")
def light_set(request):
    debugRequest(request)

    if requiresAuthorization := checkAuthorization(request):
        return requiresAuthorization

    html = htmlHeader()
    html += readFile("fd/web/content.html")
    html += htmlFooter()
    return (200, headersHtml, html)


@ampule.route("/script.js")
def light_set(request):
    debugRequest(request)

    if requiresAuthorization := checkAuthorization(request):
        return requiresAuthorization

    content = readFile("fd/web/script.js")
    return (200, headersJs, content)


@ampule.route("/style.css")
def light_set(request):
    debugRequest(request)

    if requiresAuthorization := checkAuthorization(request):
        return requiresAuthorization

    content = readFile("fd/web/style.css")
    return (200, headersCss, content)


@ampule.route("/api/statistics")
def light_set(request):
    debugRequest(request)

    if requiresAuthorization := checkAuthorization(request):
        return requiresAuthorization

    # board
    board_name = os.uname().machine
    chip_name = os.uname().nodename
    circuit_python_version = os.uname().release
    circuit_python_version_full = os.uname().version

    # storage
    fs_stat = os.statvfs("/")
    storage_total = fs_stat[0] * fs_stat[2] / 1024
    storage_available = fs_stat[0] * fs_stat[3] / 1024
    storage_used = storage_total - storage_available

    # memory
    mem_available = gc.mem_free() / 1024
    mem_used = gc.mem_alloc() / 1024
    mem_total = mem_available + mem_used

    result = {
        "board": {
            "name": board_name,
            "chip": chip_name,
            "circuitpython_version": circuit_python_version,
            "circuitpython_version_full": circuit_python_version_full,
        },
        "storage": {
            "absolute": {
                "unit_of_measurement": "KB",
                "available": round(storage_available, 2),
                "used": round(storage_used, 2),
                "total": round(storage_total, 2),
            },
            "relative": {
                "unit_of_measurement": "%",
                "available": round(100 * storage_available / storage_total, 2),
                "used": round(100 * storage_used / storage_total, 2),
            },
        },
        "memory": {
            "absolute": {
                "unit_of_measurement": "KB",
                "available": round(mem_available, 2),
                "used": round(mem_used, 2),
                "total": round(mem_total, 2),
            },
            "relative": {
                "unit_of_measurement": "%",
                "available": round(100 * mem_available / mem_total, 2),
                "used": round(100 * mem_used / mem_total, 2),
            },
        },
        "usb_connected": supervisor.runtime.usb_connected
    }

    return (200, headersJson, json.dumps(result))


@ampule.route("/api/fetchPayloads")
def light_set(request):
    debugRequest(request)

    if requiresAuthorization := checkAuthorization(request):
        return requiresAuthorization

    payloads = []
    files = os.listdir("fd/payloads")
    payloads = [f for f in files if f.endswith(".dd")]
    return (200, headersJson, json.dumps(payloads))


@ampule.route("/api/loadPayload")
def light_set(request):
    debugRequest(request)

    if requiresAuthorization := checkAuthorization(request):
        return requiresAuthorization

    if "file" in request.params.keys():
        file = request.params["file"]
        payload = readFile(f"fd/payloads/{file}")
        if payload:
            return (200, headersJson, json.dumps({"payload": encodeForTransport(payload)}))

    return (404, headersJson, json.dumps({"error": "file not found"}))


@ampule.route("/api/runPayload", method="POST")
def light_set(request):
    global duckyScriptResult

    debugRequest(request)

    if requiresAuthorization := checkAuthorization(request):
        return requiresAuthorization

    params_post = getPostParams(request)

    duckyScriptResult = ""
    processDuckyScript(
        duckyScriptPath=None, duckyScript=decodeFromTransport(params_post["payload"])
    )

    result = {
        "result": encodeForTransport(duckyScriptResult),
        "notification": "Script ran successfully. See script output below.",
    }
    return (200, headersJson, json.dumps(result))


@ampule.route("/api/savePayload", method="POST")
def light_set(request):

    debugRequest(request)

    if requiresAuthorization := checkAuthorization(request):
        return requiresAuthorization

    params_post = getPostParams(request)

    filename = f"fd/payloads/{decodeFromTransport(params_post["filename"])}"
    content = decodeFromTransport(params_post["payload"])

    try:
        # remount with write permissions
        storage.remount("/", readonly=False)
    except Exception:
        result = {
            "result": "error",
            "notification": "USB drive is mounted on the host. Configure FeatherS2 Ducky to boot into stealth-mode.",
        }
        return (200, headersJson, json.dumps(result))

    # write payload to file
    if writeFile(filename, content):
        result = {
            "result": "success",
            "notification": "Successfully written file.",
        }
    else:
        result = {
            "result": "error",
            "notification": "Error writing file.",
        }

    # remount with read-only permissions
    storage.remount("/", readonly=True)

    return (200, headersJson, json.dumps(result))


@ampule.route("/api/deletePayload", method="POST")
def light_set(request):
    return (200, headersJson, "")


@ampule.route("/api/checkUsbHid")
def light_set(request):

    if supervisor.runtime.usb_connected:
        kbd = Keyboard(usb_hid.devices)
        mouse = Mouse(usb_hid.devices)
        cc = ConsumerControl(usb_hid.devices)
        loadLocale(config["locale"])

    return (200, headersJson, json.dumps({ "result": supervisor.runtime.usb_connected }))


# spawn or connect to Wifi Access Point
def runWebserver():
    print("")

    if config["webserver"]["hostname"]:
        wifi.radio.enabled = False
        wifi.radio.hostname = config["webserver"]["hostname"]
        wifi.radio.enabled = True

    if config["wifi"]["mode"] == "connect":
        displayTextLine(f"Connecting to Wifi\n{config['wifi']['connectAP']['ssid']}", clear=True)
        displayTextLine(f"...", 2)
        print(f"Connecting to Wifi AP \"{config['wifi']['connectAP']['ssid']}\"")
        if config["wifi"]["connectAP"]["macAddress"]:
            macAddress = binascii.unhexlify(
                config["wifi"]["connectAP"]["macAddress"]
                .replace(":", "")
                .replace("-", "")
            )
            wifi.radio.mac_address = macAddress

        if config["wifi"]["connectAP"]["bssid"]:
            bssid = binascii.unhexlify(
                config["wifi"]["connectAP"]["bssid"].replace(":", "").replace("-", "")
            )

            wifi.radio.connect(
                ssid=config["wifi"]["connectAP"]["ssid"],
                password=config["wifi"]["connectAP"]["password"],
                bssid=bssid,
            )
        else:
            wifi.radio.connect(
                ssid=config["wifi"]["connectAP"]["ssid"],
                password=config["wifi"]["connectAP"]["password"],
            )
        print(" - Hostname:   ", wifi.radio.hostname)
        print(" - IP Address: ", wifi.radio.ipv4_address)
        print(" - Subnet:     ", wifi.radio.ipv4_subnet)
        print(" - MAC Address:", ":".join("%02X" % _ for _ in wifi.radio.mac_address))
        print(" - Gateway:    ", wifi.radio.ipv4_gateway)
        print(" - DNS:        ", wifi.radio.ipv4_dns)
        ipAddress = wifi.radio.ipv4_address

        displayTextLine(f"{config['wifi']['connectAP']['ssid']}")

    else:
        displayTextLine(f"Spawning Wifi\n{config['wifi']['spawnAP']['ssid']}", clear=True)
        displayTextLine(f"...", 2)
        print(f"Spawning Wifi AP \"{config['wifi']['spawnAP']['ssid']}\"")
        if config["wifi"]["spawnAP"]["macAddress"]:
            macAddress = binascii.unhexlify(
                config["wifi"]["spawnAP"]["macAddress"]
                .replace(":", "")
                .replace("-", "")
            )
            wifi.radio.mac_address_ap = macAddress

        wifi.radio.start_ap(
            ssid=config["wifi"]["spawnAP"]["ssid"],
            password=config["wifi"]["spawnAP"]["password"],
            channel=config["wifi"]["spawnAP"]["channel"],
        )
        print(" - Wifi Secret:", config["wifi"]["spawnAP"]["password"])
        print(" - Hostname:   ", wifi.radio.hostname)
        print(" - IP Address: ", wifi.radio.ipv4_address_ap)
        print(
            " - MAC Address:", ":".join("%02X" % _ for _ in wifi.radio.mac_address_ap)
        )
        print(" - Subnet:     ", wifi.radio.ipv4_subnet_ap)
        print(" - Gateway:    ", wifi.radio.ipv4_gateway_ap)
        ipAddress = wifi.radio.ipv4_address_ap

        displayTextLine(f"{config['wifi']['spawnAP']['ssid']}")

    # run HTTP server and listen
    print("")

    if config["webserver"]["port"] == 80:
        if config["wifi"]["mode"] == "connect":
            displayTextLine(f"http://{wifi.radio.hostname}", 2)
        else:
            displayTextLine(f"http://{ipAddress}", 2)

        print("Serving via HTTP at:")
        print(f" - http://{wifi.radio.hostname}")
        print(f" - http://{ipAddress}")
    else:
        if config["wifi"]["mode"] == "connect":
            displayTextLine(f"http://{wifi.radio.hostname}:{config['webserver']['port']}", 2)
        else:
            displayTextLine(f"http://{ipAddress}:{config['webserver']['port']}", 2)

        print("Serving via HTTP at:")
        print(f" - http://{wifi.radio.hostname}:{config['webserver']['port']}")
        print(f" - http://{ipAddress}:{config['webserver']['port']}")
    pool = socketpool.SocketPool(wifi.radio)
    socket = pool.socket()
    socket.bind(["0.0.0.0", config["webserver"]["port"]])
    socket.listen(1)

    if config["webserver"]["credentials"] is None:
        print(" - no credentials required")
    else:
        print(f" - Username: {config['webserver']['credentials']['username']}")
        print(f" - Password: {config['webserver']['credentials']['password']}")

    # webserver listen loop
    while True:
        ampule.listen(socket)


# -----------------------------------------------------------------------------------------------------
# RUNTIME
# -----------------------------------------------------------------------------------------------------

def importDisplay():
    if config["display"]["enabled"]:
        from fd.display import displayTextLine
        return displayTextLine
    else:
        def _func(text, lineNumber=1, clear=False):
            pass
        return _func


# disable CircuitPython auto-restart feature
if not config["usbConnection"]["autoRestartOnTouch"]:
    supervisor.disable_autoreload()

# dynamically import display lib (if enabled)
displayTextLine = importDisplay()

# set up LED
displayTextLine("Setting up LED...", clear=True)
led = DigitalInOut(LED)
led.direction = Direction.OUTPUT

# default settings
defaultDelay = config["defaultDelay"]
psychoMouse = False
delayCounter = 0
duckyScriptResult = ""

# wait for USB mount
displayTextLine("Waiting for USB...")
usbWaitCounter = 1
while (not supervisor.runtime.usb_connected) and (usbWaitCounter <= config["usbConnection"]["waitCycles"]):
    displayTextLine(f" --> {usbWaitCounter} / {config["usbConnection"]["waitCycles"]}", 2)
    time.sleep(config["usbConnection"]["waitDelay"] / 1000)
    usbWaitCounter += 1

# no USB HID device for quite some time => start the webserver (if enabled)
if usbWaitCounter >= config["usbConnection"]["waitCycles"]:
    displayTextLine(" -> timed out!", 2)
    time.sleep(2)
    displayTextLine("", 2, clear=True)

    # run web server
    displayTextLine("Starting Webserver...")
    if config["wifi"]["mode"] != "off":
        runWebserver()

# normal mode
else:

    # set up keyboard + mouse
    displayTextLine("Setting up HID...")
    kbd = Keyboard(usb_hid.devices)
    mouse = Mouse(usb_hid.devices)
    cc = ConsumerControl(usb_hid.devices)
    loadLocale(config["locale"])

    # sleep at the start to allow the device to be recognized by the host computer
    time.sleep(config["initialSleep"] / 1000)

    # check IO11/IO12/IO13/IO14/IO15/IO16/IO17 for run mode
    displayTextLine("Checking PINs...")
    if isPinGrounded(IO11):
        processDuckyScript(config["payloads"]["IO11"])
    elif isPinGrounded(IO12):
        processDuckyScript(config["payloads"]["IO12"])
    elif isPinGrounded(IO13):
        processDuckyScript(config["payloads"]["IO13"])
    elif isPinGrounded(IO14):
        processDuckyScript(config["payloads"]["IO14"])
    elif isPinGrounded(IO15):
        processDuckyScript(config["payloads"]["IO15"])
    elif isPinGrounded(IO16):
        processDuckyScript(config["payloads"]["IO16"])
    elif isPinGrounded(IO17):
        mouseJigglerLoop()
    else:
        print(
            "You're in setup mode. Update your payload(s) and ground the corresponding pin (IO11-IO16) to run one of them afterwards."
        )

    # run web server
    displayTextLine("Starting Webserver...")
    if config["wifi"]["mode"] != "off":
        runWebserver()
