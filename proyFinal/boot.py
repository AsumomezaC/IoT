import network
import time

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("INFINITUM1E77_EXT", "Qm3Bz8Bz8v")

while not wifi.isconnected():
    time.sleep(0.2)

print("WiFi listo:", wifi.ifconfig())
