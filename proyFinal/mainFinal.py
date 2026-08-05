import network
import time
import utime
import ubinascii
import machine
from machine import Pin, PWM, ADC
import dht
import json
import bluetooth
import gc

from umqtt.simple import MQTTClient

# ESTABLECER CONSTANTES ----------------------------------------------------
# -------- CONFIGURACIÓN MQTT -------
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_CMD = b"afcs_fito/esp32/proyRiego/salidas/#"
CLIENT_ID = b'esp32_' + ubinascii.hexlify(machine.unique_id())

# INTERVALO DE PUBLICACIÓN
PUB_INTERVAL = 15 * 60  # 15 minutos
last_pub = time.time() - PUB_INTERVAL

# BLE
ENABLE_BLE = True

_device_name = "ESP32_Riego"
_ble = None
_pending_color_update = None
_ble_char_handle = None

_last_ble_pulse = 0
BLE_PULSE_PERIOD = 60  # segundos
BLE_PULSE_DURATION = 12

_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3

_ble_conn_handle = None
_ble_connected = False

# UUIDs
_SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
_CHAR_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")

# Colas y flags
_mqtt_queue = []  # mensajes entrantes desde callback: (topic_str, msg_dict)
_pending_publishes = []  # publish retrasados: (topic_bytes, data_bytes, qos, retain)
_in_ble_pulse = False

# SALIDAS -entradas en el broker-
edoContenedor = "empty"
tempAmb = 20
humP1 = humP2 = humP3 = humP4 = 0

# RIEGO
riegoP1 = riegoP2 = riegoP3 = riegoP4 = False
riegoManual = False
lastTimeRiegoManual = None
TIME_NO_AUTOMATIC_IRRIGATION = 1 * 60 * 60  # 1 hora

# COLOR - se recibe por BLE
mediumColor = [255, 222, 89]
emptyColor = [255, 0, 0]

# Topics para color
TOPIC_COLOR_MEDIO = b"afcs_fito/esp32/proyRiego/entradas/color/led_medio"
TOPIC_COLOR_BAJO = b"afcs_fito/esp32/proyRiego/entradas/color/led_bajo"

# HARDWARE
sw_Floa_Medium = Pin(12, Pin.IN)
sw_Floa_Down = Pin(13, Pin.IN)

# --------------------------------------------------------------------------
# MQTT client
# --------------------------------------------------------------------------
client = MQTTClient(
    client_id=CLIENT_ID,
    server=MQTT_BROKER,
    port=MQTT_PORT,
    keepalive=60
)

def mqtt_connect():
    """
    Intenta conectar al broker y (re)subscribir.
    Devuelve True si tuvo éxito.
    """
    global client
    tries = 0
    while tries < 5:
        try:
            client.connect()
            client.set_callback(callback)
            client.subscribe(TOPIC_CMD)
            print("Conectado al broker MQTT (mqtt_connect) y suscrito a:", TOPIC_CMD)
            return True
        except Exception as e:
            tries += 1
            print("Error conectando al broker (intento {}): {}".format(tries, e))
            time.sleep(1)
    print("Fallo al conectar al broker tras varios intentos.")
    return False

def _enqueue_publish_bytes(topic_b, data_b, qos=0, retain=False):
    """Encola un publish en forma de bytes para reintento posterior."""
    global _pending_publishes
    try:
        _pending_publishes.append((topic_b, data_b, qos, retain))
        try:
            # Log ligero para debug de cola
            print("[QUEUE] enqueue publish -> topic:", topic_b, "len_queue:", len(_pending_publishes))
        except Exception:
            pass
    except Exception:
        pass

def publish_safe(topic, payload, qos=0, retain=False):
    """
    Publica usando client.publish con manejo:
    - Si estamos en pulso BLE -> encola para enviar después.
    - Si falla y no estamos en pulso BLE -> intenta reconectar y reintentar; si falla en reintento, encola.
    """
    global client, _in_ble_pulse
    # normalizar topic y payload a bytes
    if isinstance(topic, str):
        topic_b = topic.encode('utf-8')
    else:
        topic_b = topic
    data_b = payload if isinstance(payload, (bytes, bytearray)) else str(payload).encode('utf-8')

    # Si estamos en pulso BLE, encolar y salir (evitamos reconexiones en ese momento)
    if _in_ble_pulse:
        _enqueue_publish_bytes(topic_b, data_b, qos, retain)
        return False

    try:
        client.publish(topic_b, data_b, qos=qos, retain=retain)
        # log exitoso
        try:
            print("[MQTT] publish OK ->", topic_b)
        except Exception:
            pass
        return True
    except OSError as e:
        print("publish OSError:", e, "-> Intentando reconectar y reintentar...")
        # Intentar reconectar y reintentar una vez
        try:
            if mqtt_connect():
                try:
                    client.publish(topic_b, data_b, qos=qos, retain=retain)
                    print("[MQTT] publish OK tras reconectar ->", topic_b)
                    return True
                except Exception as e2:
                    print("Reintento publish falló:", e2)
                    _enqueue_publish_bytes(topic_b, data_b, qos, retain)
                    return False
            else:
                _enqueue_publish_bytes(topic_b, data_b, qos, retain)
                return False
        except Exception as e3:
            print("publish_safe: reconectar/reintento falló:", e3)
            _enqueue_publish_bytes(topic_b, data_b, qos, retain)
            return False
    except Exception as e:
        print("publish fallo (otro):", e)
        _enqueue_publish_bytes(topic_b, data_b, qos, retain)
        return False

def process_pending_publishes(max_per_cycle=6):
    """
    Reintenta publishes encolados. Corre solo si no estamos en pulso BLE.
    Si falla por desconexión, intenta reconectar una vez antes de abandonar.
    """
    global _pending_publishes, _in_ble_pulse, client
    if _in_ble_pulse:
        # no tocar la cola durante pulso BLE
        return
    try:
        if not _pending_publishes:
            return
        # mostrar estado inicial
        try:
            print("[QUEUE] process_pending_publishes -> inicio, len:", len(_pending_publishes))
        except Exception:
            pass

        i = 0
        while _pending_publishes and i < max_per_cycle:
            topic_b, data_b, qos, retain = _pending_publishes.pop(0)
            try:
                client.publish(topic_b, data_b, qos=qos, retain=retain)
                try:
                    print("[QUEUE] publicado desde cola ->", topic_b, "remaining:", len(_pending_publishes))
                except Exception:
                    pass
            except OSError as e:
                # intento reconectar una vez si detectamos OSError
                print("process_pending_publishes: OSError en publish:", e, "-> intentando reconectar MQTT...")
                # re-enqueue el item al inicio
                _pending_publishes.insert(0, (topic_b, data_b, qos, retain))
                if mqtt_connect():
                    # si reconectó, seguimos en próximos ciclos
                    print("process_pending_publishes: reconectado MQTT, reintentar en próximos ciclos.")
                else:
                    print("process_pending_publishes: reconexión fallida, saliendo del reproceso por ahora.")
                break
            except Exception as e2:
                # re-enqueue y salir para no spamear el bus
                _pending_publishes.insert(0, (topic_b, data_b, qos, retain))
                print("process_pending_publishes: publish falló, re-enqueue:", e2)
                break
            i += 1

        try:
            print("[QUEUE] process_pending_publishes -> fin, len:", len(_pending_publishes))
        except Exception:
            pass

    except Exception as e:
        print("Error en process_pending_publishes:", e)

# --------------------------------------------------------------------------
# BLE helpers
# --------------------------------------------------------------------------
def _uuid_from(text_or_obj):
    try:
        if isinstance(text_or_obj, bluetooth.UUID):
            return text_or_obj
        if isinstance(text_or_obj, int):
            return bluetooth.UUID(text_or_obj)
        if isinstance(text_or_obj, (bytes, bytearray)) and len(text_or_obj) == 16:
            return bluetooth.UUID(bytes(text_or_obj))
        s = str(text_or_obj).strip()
        if s.startswith("0x") or (len(s) <= 6 and all(c in "0123456789abcdefx" for c in s.lower())):
            return bluetooth.UUID(int(s, 16))
        hs = s.replace("-", "")
        if len(hs) == 32:
            return bluetooth.UUID(bytes.fromhex(hs))
        return bluetooth.UUID(s)
    except Exception:
        try:
            return bluetooth.UUID(str(text_or_obj))
        except Exception:
            return None

def _ble_irq_min(event, data):
    """
    IRQ seguro: maneja connect/disconnect/write de forma ligera.
    Guarda payloads para procesar fuera del IRQ, y registra conn handle.
    """
    global _pending_color_update, _ble_char_handle, _ble_conn_handle, _ble_connected
    try:
        if event == _IRQ_CENTRAL_CONNECT:
            try:
                conn = data[0] if isinstance(data, (list, tuple)) and len(data) > 0 else data
                _ble_conn_handle = conn
            except Exception:
                _ble_conn_handle = data
            _ble_connected = True
            return

        if event == _IRQ_CENTRAL_DISCONNECT:
            _ble_connected = False
            _ble_conn_handle = None
            return

        if event == _IRQ_GATTS_WRITE:
            if isinstance(data, tuple) and len(data) == 3:
                attr_handle = data[1]
                mv = data[2]
                if _ble_char_handle is None:
                    _ble_char_handle = attr_handle
                try:
                    raw = bytes(mv)
                    if raw:
                        # guardamos texto tal cual; lo procesamos fuera del IRQ
                        _pending_color_update = raw.decode('utf-8', 'ignore').strip()
                        # debug mínimo (no prints pesados en IRQ, pero esto suele funcionar)
                        # not guaranteed safe in all firmwares, but helpful on many
                except Exception:
                    pass
                return
            if isinstance(data, tuple) and len(data) >= 2:
                attr_handle = data[1]
                if _ble_char_handle is None:
                    _ble_char_handle = attr_handle
                return
    except Exception:
        pass

def ble_pulse_listen(duration_s=12, advertise_interval_us=100_000):
    """
    Activa BLE temporalmente, maneja connect/disconnect y procesa durante duration_s segundos.
    """
    global _ble, _ble_char_handle, _pending_color_update, _ble_conn_handle, _ble_connected
    global _in_ble_pulse
    _in_ble_pulse = True

    print("[BLE pulse] inicio (dur {}s)".format(duration_s))
    try:
        gc.collect()
    except Exception:
        pass

    try:
        _ble = bluetooth.BLE()
    except Exception as e:
        print("[BLE pulse] bluetooth.BLE() fallo:", e)
        _ble = None
        _in_ble_pulse = False
        return False

    try:
        _ble.active(True)
    except Exception as e:
        print("[BLE pulse] active(True) fallo:", e)
        _ble = None
        _in_ble_pulse = False
        return False

    try:
        _ble.irq(_ble_irq_min)
    except Exception as e:
        print("[BLE pulse] irq() fallo (continuamos):", e)

    # registrar servicio/char (tolerante)
    try:
        svc = (_SERVICE_UUID, ((_CHAR_UUID, bluetooth.FLAG_WRITE | bluetooth.FLAG_READ),))
        res = _ble.gatts_register_services((svc,))
        try:
            if isinstance(res, (list, tuple)) and len(res) > 0:
                first = res[0]
                if isinstance(first, (list, tuple)) and len(first) > 1:
                    chars = first[1]
                    if isinstance(chars, (list, tuple)) and len(chars) > 0:
                        _ble_char_handle = chars[0]
                        print("[BLE pulse] char handle:", _ble_char_handle)
                else:
                    print("[BLE pulse] gatts_register_services result:", res)
        except Exception:
            pass
    except Exception as e:
        print("[BLE pulse] gatts_register_services fallo (continuamos):", e)

    # advertising sencillo
    try:
        name = _device_name
        if len(name) > 20:
            name = name[:20]
        adv = bytearray(b'\x02\x01\x06') + bytes((len(name) + 1, 0x09)) + name.encode('utf-8')
        try:
            _ble.gap_advertise(advertise_interval_us, adv)
        except TypeError:
            _ble.gap_advertise(int(advertise_interval_us / 1000), adv)
        print("[BLE pulse] advertising ON (name {})".format(name))
    except Exception as e:
        print("[BLE pulse] gap_advertise fallo:", e)

    # ventana activa (no bloqueante para MQTT; iteraciones cortas)
    t0 = time.time()
    while time.time() - t0 < duration_s:
        if _ble_connected:
            try:
                _ble.gap_advertise(None)
            except Exception:
                try:
                    _ble.gap_advertise(0)
                except Exception:
                    pass

        # mantener MQTT responsivo: NO forzar reconexión aquí
        try:
            client.check_msg()
        except Exception as e:
            print("[BLE pulse] check_msg ex (ignorado aquí):", e)

        # procesar payload BLE recibido por IRQ
        try:
            if _pending_color_update:
                s = _pending_color_update
                _pending_color_update = None
                print("[BLE pulse] payload recibido:", repr(s))
                try:
                    # En lugar de publicar directamente (pues publish_safe encola si estamos en pulso),
                    # llamamos la función que parsea y usa publish_safe (que encolará).
                    _process_and_publish_color(s)
                except Exception as e:
                    print("[BLE pulse] error procesando color:", e)
        except Exception as e:
            print("[BLE pulse] procesar pending ex:", e)

        time.sleep(0.08)

    # teardown: intentar desconectar central si es posible
    try:
        if _ble_conn_handle is not None:
            try:
                if hasattr(_ble, "gap_disconnect"):
                    _ble.gap_disconnect(_ble_conn_handle)
                    print("[BLE pulse] gap_disconnect pedido para handle", _ble_conn_handle)
            except Exception as e:
                print("[BLE pulse] gap_disconnect fallo (no crítico):", e)
    except Exception:
        pass

    try:
        _ble.gap_advertise(None)
    except Exception:
        try:
            _ble.gap_advertise(0)
        except Exception:
            pass
    try:
        _ble.active(False)
    except Exception:
        pass

    _ble = None
    _ble_char_handle = None
    _ble_conn_handle = None
    _ble_connected = False
    try:
        gc.collect()
    except Exception:
        pass

    print("[BLE pulse] terminado y limpiado")
    _in_ble_pulse = False
    return True

def ble_init_minimal_safe(advertise_interval_us=100_000):
    global _ble
    try:
        gc.collect()
    except Exception:
        pass

    try:
        _ble = bluetooth.BLE()
    except Exception as e:
        print("[BLE] bluetooth.BLE() falló:", e)
        _ble = None
        return False

    try:
        _ble.active(True)
    except Exception as e:
        print("[BLE] active(True) falló:", e)
        _ble = None
        return False

    try:
        name = _device_name
        if len(name) > 20:
            name = name[:20]
        adv = bytearray(b'\x02\x01\x06')
        adv += bytes((len(name) + 1, 0x09)) + name.encode('utf-8')
        try:
            _ble.gap_advertise(advertise_interval_us, adv)
        except TypeError:
            _ble.gap_advertise(int(advertise_interval_us / 1000), adv)
        time.sleep(0.05)
        print("[BLE] Advertise iniciado (nombre):", name)
        return True
    except Exception as e:
        print("[BLE] Error iniciando advertise:", e)
        try:
            _ble.active(False)
        except Exception:
            pass
        _ble = None
        return False

# ---------------------- Nuevos parsers: single y combinado ----------------
def _parse_rgb_from_string(s):
    """
    Acepta:
     - JSON array: [r,g,b]
     - JSON dict: {"r":..,"g":..,"b":..} o {"red":..,"green":..,"blue":..}
     - Texto: "r,g,b" (con espacios tolerados)
    Devuelve tupla (r,g,b) ints 0..255 o None si inválido.
    """
    try:
        ss = s.strip()
        try:
            obj = json.loads(ss)
            if isinstance(obj, (list, tuple)) and len(obj) == 3:
                r, g, b = obj
            elif isinstance(obj, dict):
                if "r" in obj and "g" in obj and "b" in obj:
                    r = obj["r"]; g = obj["g"]; b = obj["b"]
                elif "red" in obj and "green" in obj and "blue" in obj:
                    r = obj["red"]; g = obj["green"]; b = obj["blue"]
                elif "rgb" in obj and isinstance(obj["rgb"], (list,tuple)) and len(obj["rgb"])==3:
                    r, g, b = obj["rgb"]
                else:
                    return None
            else:
                return None
        except Exception:
            parts = ss.split(",")
            if len(parts) != 3:
                return None
            try:
                r = int(parts[0].strip())
                g = int(parts[1].strip())
                b = int(parts[2].strip())
            except Exception:
                return None

        try:
            r_i = int(r); g_i = int(g); b_i = int(b)
        except Exception:
            return None
        if not (0 <= r_i <= 255 and 0 <= g_i <= 255 and 0 <= b_i <= 255):
            return None
        return (r_i, g_i, b_i)
    except Exception:
        return None

def _parse_combined_colors(s):
    """
    Parseo del formato combinado:
    "medium:rr,gg,bb;empty:rr,gg,bb" (orden y mayúsc/minúsc tolerado)
    Devuelve dict con claves 'medium' y/o 'empty' mapeando a (r,g,b), o None si inválido.
    """
    try:
        parts = [p.strip() for p in s.split(";") if p.strip()]
        if not parts:
            return None
        res = {}
        for p in parts:
            if ":" not in p:
                # ignorar segmento inválido
                continue
            key, val = p.split(":", 1)
            key_n = key.strip().lower()
            val_s = val.strip()
            rgb = _parse_rgb_from_string(val_s)
            if rgb is None:
                # segmento inválido -> considerar fallo completo
                return None
            if key_n in ("medium", "medio", "med"):
                res["medium"] = rgb
            elif key_n in ("empty", "bajo", "emptycolor", "low"):
                res["empty"] = rgb
            else:
                # recogerlo con su nombre por si se usa
                res[key_n] = rgb
        if not res:
            return None
        return res
    except Exception:
        return None

def _process_and_publish_color(s):
    """
    Procesa string 's' recibido por BLE; soporta:
     - solo RGB -> publica a led_medio y led_bajo con el mismo color
     - formato combinado medium:...;empty:... -> publica medium->led_medio y empty->led_bajo
    """
    global mediumColor, emptyColor
    try:
        ss = s.strip()
        # si parece combinado (tiene ';' o menciona 'medium'/'empty'), intentar combinado primero
        combined = None
        if ";" in ss or "medium" in ss.lower() or "empty" in ss.lower() or "medio" in ss.lower() or "bajo" in ss.lower():
            combined = _parse_combined_colors(ss)
        if combined:
            # publicar según claves encontradas
            published = {}
            if "medium" in combined:
                r,g,b = combined["medium"]
                mediumColor = [r,g,b]
                datos = {"cmd": "update", "value": [r,g,b], "ts": time.time()}
                payload = json.dumps(datos)
                ok = publish_safe(TOPIC_COLOR_MEDIO, payload, qos=1, retain=True)
                published["medium"] = ok
            if "empty" in combined:
                r,g,b = combined["empty"]
                emptyColor = [r,g,b]
                datos = {"cmd": "update", "value": [r,g,b], "ts": time.time()}
                payload = json.dumps(datos)
                ok = publish_safe(TOPIC_COLOR_BAJO, payload, qos=1, retain=True)
                published["empty"] = ok
            print("[COLOR] Combined parsed -> published:", published)
            return True
        # No es combinado válido: intentar parseo single
        rgb = _parse_rgb_from_string(ss)
        if not rgb:
            print("[COLOR] payload inválido para RGB (ni single ni combined):", repr(s))
            return False
        r,g,b = rgb
        mediumColor = [r,g,b]
        emptyColor = [r,g,b]
        datos = {"cmd": "update", "value": [r,g,b], "ts": time.time()}
        payload = json.dumps(datos)
        ok1 = publish_safe(TOPIC_COLOR_MEDIO, payload, qos=1, retain=True)
        ok2 = publish_safe(TOPIC_COLOR_BAJO, payload, qos=1, retain=True)
        print("[COLOR] RGB válidos:", (r,g,b), "-> publicados:", ok1, ok2)
        return True
    except Exception as e:
        print("[COLOR] Error procesando/publish color:", e)
        return False

# FUNCIONES -----------------------------------------------------------------
def callback(topic, msg):
    """
    Callback mínimo y seguro: encola el mensaje para ser procesado en el loop principal.
    """
    global _mqtt_queue
    try:
        topic_str = topic.decode('utf-8') if isinstance(topic, (bytes, bytearray)) else str(topic)
    except Exception:
        topic_str = str(topic)
    try:
        msg_str = msg.decode('utf-8') if isinstance(msg, (bytes, bytearray)) else str(msg)
    except Exception:
        msg_str = str(msg)

    msg_dict = None
    try:
        msg_dict = json.loads(msg_str)
    except Exception:
        s = msg_str.strip().lower()
        if s in ("on", "off"):
            if topic_str.endswith("/p1"):
                cmd = "val1"
            elif topic_str.endswith("/p2"):
                cmd = "val2"
            elif topic_str.endswith("/p3"):
                cmd = "val3"
            elif topic_str.endswith("/p4"):
                cmd = "val4"
            else:
                cmd = "val"
            msg_dict = {"cmd": cmd, "value": "on" if s == "on" else "off"}
        else:
            msg_dict = {"__raw__": msg_str}

    # encolar (rápido)
    try:
        _mqtt_queue.append((topic_str, msg_dict))
        # debug
        try:
            print("[MQTT_QUEUE] enqueued:", topic_str, "queue_len:", len(_mqtt_queue))
        except Exception:
            pass
    except Exception:
        pass

def enviar_datos():
    enviarEdoContenedor()
    enviarEdoTempAmb()
    enviarEdoHumP1()
    enviarEdoHumP2()
    enviarEdoHumP3()
    enviarEdoHumP4()

def recibir_info(topic, msg):
    # RIEGO
    if (topic == "afcs_fito/esp32/proyRiego/salidas/riego/p1" and msg.get("cmd") == "val1"):
        if msg.get("value") == "on":
            riego(1, True, True)
        elif msg.get("value") == "off":
            riego(1, False, True)
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/riego/p2" and msg.get("cmd") == "val2"):
        if msg.get("value") == "on":
            riego(2, True, True)
        elif msg.get("value") == "off":
            riego(2, False, True)
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/riego/p3" and msg.get("cmd") == "val3"):
        if msg.get("value") == "on":
            riego(3, True, True)
        elif msg.get("value") == "off":
            riego(3, False, True)
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/riego/p4" and msg.get("cmd") == "val4"):
        if msg.get("value") == "on":
            riego(4, True, True)
        elif msg.get("value") == "off":
            riego(4, False, True)
        else:
            print("La solicitud no se reconoce con un valor valido")
    # ESTADOS
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/estados/contenedor" and msg.get("cmd") == "contenedor"):
        if msg.get("value") == "update":
            enviarEdoContenedor()
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/estados/tempAmb" and msg.get("cmd") == "tempAmb"):
        if msg.get("value") == "update":
            enviarEdoTempAmb()
        else:
            print("La solicitud no se reconoce con un valor valido")
    # plantas
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/estados/plantas/p1" and msg.get("cmd") == "Hum_P1"):
        if msg.get("value") == "update":
            enviarEdoHumP1()
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/estados/plantas/p2" and msg.get("cmd") == "Hum_P2"):
        if msg.get("value") == "update":
            enviarEdoHumP2()
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/estados/plantas/p3" and msg.get("cmd") == "Hum_P3"):
        if msg.get("value") == "update":
            enviarEdoHumP3()
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif (topic == "afcs_fito/esp32/proyRiego/salidas/estados/plantas/p4" and msg.get("cmd") == "Hum_P4"):
        if msg.get("value") == "update":
            enviarEdoHumP4()
        else:
            print("La solicitud no se reconoce con un valor valido")
    else:
        # Si recibes mensajes de color desde MQTT (por si llega así), procesarlos también:
        try:
            if topic.startswith("afcs_fito/esp32/proyRiego/salidas/") and isinstance(msg, dict):
                # Si alguien publica un payload color por MQTT en formato esperado, podríamos llamarlo
                pass
        except Exception:
            pass
        print("El mensaje no fue reconocido con un formato valido")

# Enviar actualizaciones de estado
def enviarEdoContenedor():
    datos = {"cmd": "contenedor", "value": actualizarEdoContenedor(), "ts": time.time()}
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/contenedor", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado del contenedor", datos)

def enviarEdoTempAmb():
    datos = {"cmd": "temperatura ambiente", "value": actualizarEdoTempAmb(), "ts": time.time()}
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/tempAmb", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado de la temperatura ambiente", datos)

def enviarEdoHumP1():
    datos = {"cmd": "humedad planta 1", "value": actualizarEdoHumP1(), "ts": time.time()}
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/plantas/hum/p1", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado de la Humedad de la planta 1", datos)

def enviarEdoHumP2():
    datos = {"cmd": "humedad planta 2", "value": actualizarEdoHumP2(), "ts": time.time()}
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/plantas/hum/p2", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado de la Humedad de la planta 2", datos)

def enviarEdoHumP3():
    datos = {"cmd": "humedad planta 3", "value": actualizarEdoHumP3(), "ts": time.time()}
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/plantas/hum/p3", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado de la Humedad de la planta 3", datos)

def enviarEdoHumP4():
    datos = {"cmd": "humedad planta 4", "value": actualizarEdoHumP4(), "ts": time.time()}
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/plantas/hum/p4", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado de la Humedad de la planta 4", datos)

# Actualizaciones de estado
def actualizarEdoContenedor():
    global edoContenedor, sw_Floa_Medium, sw_Floa_Down
    if not sw_Floa_Medium.value() and sw_Floa_Down.value(): # si el sensor inferior no detecta agua, pero el superior si
        print("Error en sensores, favor de revisar")
        edoContenedor = "ERROR"
        datos = {"cmd": "Sensores de Contenedr", "value": "lecturas imposibles", "ts": time.time()}
        enviarRegistro("ERROR DE SENSOR", datos)
    elif sw_Floa_Down.value(): # si esta vacío
        edoContenedor = "empty"
    elif sw_Floa_Medium.value(): # si esta a media capacidad
        edoContenedor = "half"
    else:
        edoContenedor = "full"
    return edoContenedor

def actualizarEdoTempAmb():
    global tempAmb
    return tempAmb

def actualizarEdoHumP1():
    global humP1
    return humP1

def actualizarEdoHumP2():
    global humP2
    return humP2

def actualizarEdoHumP3():
    global humP3
    return humP3

def actualizarEdoHumP4():
    global humP4
    return humP4

# Registros
def enviarRegistro(tipo, datos):
    try:
        del datos["ts"]
    except KeyError:
        pass
    payloadRegister = json.dumps({"cmd": tipo, "value": datos, "ts": time.time()})
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/registros", payloadRegister, qos=1)
    print("registro enviado")

# Riego
def riego(number, regar, manual):
    global riegoManual, lastTimeRiegoManual
    riegoManual = manual
    if riegoManual:
        lastTimeRiegoManual = time.time()
    tipo = "Riego planta " + str(number)
    cmd = "Riego" if regar else "Parar riego"
    value = "Elección manual" if manual else "Elección automático"
    datos = {"cmd": cmd, "value": value}
    topic_riego = "afcs_fito/esp32/proyRiego/entradas/riego/p{}".format(number)
    payload = json.dumps(datos)
    publish_safe(topic_riego, payload, qos=1)
    enviarRegistro(tipo, datos)

# decidir_regar (tu implementación completa)
def decidir_regar(
    soil_moisture_pct,
    ambient_temp_c,
    ambient_humidity_pct,
    plant_profile,
    reservoir_available=True,
    only_night=True,
    current_time_s=None,
    last_water_time_s=None,
    min_interval_minutes=60,
    night_window=(20,6),
    debug=True
):
    now_s = current_time_s or utime.time()
    def log(msg):
        if debug:
            print("[decidir_regar] " + msg)

    if not reservoir_available:
        log("Depósito SIN agua -> No se riega (ret 0).")
        return 0

    if soil_moisture_pct is None:
        log("ERROR: lectura de humedad del suelo ausente -> no regar (ret 0).")
        return 0
    try:
        if not (0.0 <= soil_moisture_pct <= 100.0):
            log("AVISO: humedad del suelo fuera de rango ({}) -> no regar.".format(soil_moisture_pct))
            return 0
    except Exception:
        log("AVISO: valor de humedad del suelo no numérico -> no regar.")
        return 0

    temp_ok = True
    if ambient_temp_c is None:
        log("AVISO: lectura de temperatura ausente. Proceder sin temp.")
        temp_ok = False
    else:
        try:
            if ambient_temp_c > 50.0 or ambient_temp_c < -20.0:
                log("ERROR: temperatura atípica detectada ({} °C). Ignorar temp.".format(ambient_temp_c))
                temp_ok = False
        except Exception:
            log("ERROR: lectura de temperatura no numérica. Ignorar temp.")
            temp_ok = False

    hum_ok = True
    if ambient_humidity_pct is None:
        log("Aviso: humedad ambiente ausente. Proceder sin ese dato.")
        hum_ok = False
    else:
        try:
            if not (0.0 <= ambient_humidity_pct <= 100.0):
                log("AVISO: humedad ambiente fuera de rango ({}) -> ignorar.".format(ambient_humidity_pct))
                hum_ok = False
        except Exception:
            log("AVISO: humedad ambiente no numérica -> ignorar.")
            hum_ok = False

    if only_night:
        start_h, end_h = night_window
        h = utime.localtime(now_s)[3]
        if start_h <= end_h:
            in_night = (start_h <= h < end_h)
        else:
            in_night = (h >= start_h) or (h < end_h)
        if not in_night:
            log("No es hora nocturna (hora actual: {}) -> No regar.".format(h))
            return 0
        else:
            log("Estamos en ventana nocturna -> riego permitido por horario.")

    if last_water_time_s:
        try:
            delta_s = now_s - last_water_time_s
            if delta_s < (min_interval_minutes * 60):
                log("Se regó hace {:.1f} min (< {} min) -> evitar riegos repetidos.".format(delta_s/60.0, min_interval_minutes))
                return 0
        except Exception:
            log("Aviso: last_water_time_s no válido -> ignorando anti-ciclado.")

    try:
        dryness_threshold = float(plant_profile.get("dryness_threshold", 30.0))
    except Exception:
        dryness_threshold = 30.0

    if soil_moisture_pct < dryness_threshold:
        log("Humedad suelo {:.1f}% < umbral {:.1f}% -> Regar (ret 1).".format(soil_moisture_pct, dryness_threshold))
        return 1

    soil_weight = 0.70
    temp_weight = 0.20
    hum_weight = 0.10

    available_weights = soil_weight
    if temp_ok:
        available_weights += temp_weight
    else:
        temp_weight = 0.0
    if hum_ok:
        available_weights += hum_weight
    else:
        hum_weight = 0.0

    if available_weights > 0:
        soil_weight = soil_weight / available_weights
        if temp_weight:
            temp_weight = temp_weight / available_weights
        if hum_weight:
            hum_weight = hum_weight / available_weights

    hysteresis_margin = 5.0
    if soil_moisture_pct <= dryness_threshold + hysteresis_margin:
        soil_need = (dryness_threshold + hysteresis_margin - soil_moisture_pct) / (hysteresis_margin + 1e-6)
        if soil_need < 0.0:
            soil_need = 0.0
        if soil_need > 1.0:
            soil_need = 1.0
    else:
        soil_need = - (soil_moisture_pct - (dryness_threshold + hysteresis_margin)) / (100.0 - (dryness_threshold + hysteresis_margin))
        if soil_need < -1.0:
            soil_need = -1.0
        if soil_need > 0.0:
            soil_need = 0.0

    temp_need = 0.0
    if temp_ok:
        try:
            tmin, tmax = plant_profile.get("ideal_temp_range", (15.0, 30.0))
        except Exception:
            tmin, tmax = (15.0, 30.0)
        if ambient_temp_c > tmax:
            temp_need = (ambient_temp_c - tmax) / 10.0
            if temp_need > 1.0:
                temp_need = 1.0
        elif ambient_temp_c < tmin:
            temp_need = - ((tmin - ambient_temp_c) / 10.0)
            if temp_need < -1.0:
                temp_need = -1.0
        else:
            temp_need = 0.0

    hum_need = 0.0
    if hum_ok:
        try:
            hmin, hmax = plant_profile.get("ideal_humidity_range", (30.0, 60.0))
        except Exception:
            hmin, hmax = (30.0, 60.0)
        if ambient_humidity_pct < hmin:
            hum_need = (hmin - ambient_humidity_pct) / max(1.0, hmin)
            if hum_need > 1.0:
                hum_need = 1.0
        elif ambient_humidity_pct > hmax:
            hum_need = - ((ambient_humidity_pct - hmax) / max(1.0, 100.0 - hmax))
            if hum_need < -1.0:
                hum_need = -1.0
        else:
            hum_need = 0.0

    score = soil_weight * soil_need + temp_weight * temp_need + hum_weight * hum_need

    log("Valores: soil={:.1f}%, soil_need={:.3f}, temp_ok={}, temp_need={:.3f}, hum_ok={}, hum_need={:.3f}".format(
        soil_moisture_pct, soil_need, temp_ok, temp_need, hum_ok, hum_need))
    log("Pesos normalizados: soil_w={:.2f}, temp_w={:.2f}, hum_w={:.2f} -> score={:.3f}".format(
        soil_weight, temp_weight, hum_weight, score))

    decision_threshold = 0.20
    if score > decision_threshold:
        log("Score {:.3f} > {:.2f} -> Regar (ret 1).".format(score, decision_threshold))
        return 1
    else:
        log("Score {:.3f} <= {:.2f} -> No regar (ret 0).".format(score, decision_threshold))
        return 0

# CONFIGURACIONES EXTRAS -----------------------------------------------------
# Esperar a que el WiFi esté listo
w = network.WLAN(network.STA_IF)
t0 = time.time()
while not w.isconnected():
    time.sleep(0.1)
    if time.time() - t0 > 10:
        print("WiFi no conectado.")
        break

print("IP obtenida:", w.ifconfig())

# Registrar callback
client.set_callback(callback)

# Conectar MQTT
if not mqtt_connect():
    print("ATENCIÓN: no se pudo conectar al broker MQTT en el inicio. El script seguirá intentando en publish/check_msg.")

# Iniciar BLE (advertise corto o init base)
if ENABLE_BLE:
    ok = ble_init_minimal_safe()
    if not ok:
        print("[BOOT] BLE no pudo iniciarse. Continuamos solo con MQTT.")
else:
    print("[BOOT] BLE deshabilitado por configuración (ENABLE_BLE=False).")

# CICLO PRINCIPAL---------------------------------------------------------------------------------------
while True:
    # Recibir mensajes MQTT (callback encola)
    try:
        client.check_msg()
    except OSError as e:
        print("check_msg OSError:", e, "-> intentando reconectar...")
        mqtt_connect()
    except Exception as e:
        print("check_msg fallo (otro):", e)

    # Reintentar publishes pendientes lo antes posible (antes de BLE pulse)
    try:
        process_pending_publishes(max_per_cycle=8)
    except Exception as e:
        print("Error procesando pending publishes:", e)

    # Procesar mensajes MQTT encolados (fuera del callback)
    try:
        if _mqtt_queue:
            batch = min(6, len(_mqtt_queue))
            for _ in range(batch):
                try:
                    topic_str, msg_dict = _mqtt_queue.pop(0)
                except Exception:
                    break
                if isinstance(msg_dict, dict) and "__raw__" in msg_dict:
                    print("MQTT raw recibido (ignorado):", msg_dict["__raw__"])
                    continue
                try:
                    recibir_info(topic_str, msg_dict)
                except Exception as e:
                    print("Error procesando mensaje en loop principal:", e)
    except Exception as e:
        print("Error al manejar cola mqtt:", e)

    # Manejo BLE: lanzar pulso periódicamente (no bloquea mucho)
    try:
        if ENABLE_BLE and time.time() - _last_ble_pulse >= BLE_PULSE_PERIOD:
            ok = ble_pulse_listen(BLE_PULSE_DURATION)
            _last_ble_pulse = time.time()
    except Exception as e:
        print("Error en BLE pulse scheduling:", e)

    # Si quedó algún _pending_color_update por alguna razón (defensivo),
    # procesarlo aquí fuera del pulso (publish_safe encolará si es necesario)
    try:
        if _pending_color_update:
            s = _pending_color_update
            _pending_color_update = None
            print("[MAIN] procesando pending_color_update:", repr(s))
            _process_and_publish_color(s)
    except Exception as e:
        print("Error procesando pending_color_update en main:", e)

    # Envío de datos periódico
    try:
        if time.time() - last_pub >= PUB_INTERVAL:
            enviar_datos()
            last_pub = time.time()
            if riegoManual:
                if time.time() - lastTimeRiegoManual >= 0:
                    riegoManual = False
            if not riegoManual:
                print("Riego automático")
    except Exception as e:
        print("Error en enviar_datos:", e)

    time.sleep(.1)
