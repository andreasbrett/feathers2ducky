from adafruit_hid.consumer_control_code import ConsumerControlCode

# map cc commands to consumercontrolcodes
consumerControlCommands = {
    "BRIGHTNESS_DECREMENT": ConsumerControlCode.BRIGHTNESS_DECREMENT,
    "BRIGHTNESS_INCREMENT": ConsumerControlCode.BRIGHTNESS_INCREMENT,
    "EJECT": ConsumerControlCode.EJECT,
    "FAST_FORWARD": ConsumerControlCode.FAST_FORWARD,
    "MUTE": ConsumerControlCode.MUTE,
    "PLAY_PAUSE": ConsumerControlCode.PLAY_PAUSE,
    "RECORD": ConsumerControlCode.RECORD,
    "REWIND": ConsumerControlCode.REWIND,
    "SCAN_NEXT_TRACK": ConsumerControlCode.SCAN_NEXT_TRACK,
    "SCAN_PREVIOUS_TRACK": ConsumerControlCode.SCAN_PREVIOUS_TRACK,
    "STOP": ConsumerControlCode.STOP,
    "VOLUME_DECREMENT": ConsumerControlCode.VOLUME_DECREMENT,
    "VOLUME_INCREMENT": ConsumerControlCode.VOLUME_INCREMENT,
}
