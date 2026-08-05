import network
import time
import utime
import ubinascii
import machine
import json
from umqtt.simple import MQTTClient

# ESTABLECER CONSTANTES ----------------------------------------------------
# -------- CONFIGURACIÓN MQTT -------
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_CMD = b"afcs_fito/esp32/proyRiego/salidas/#"
CLIENT_ID = b'esp32_' + ubinascii.hexlify(machine.unique_id())

# INTERVALO DE PUBLICACIÓN
PUB_INTERVAL = 15 * 60 # 15 minutos
last_pub = time.time() - PUB_INTERVAL

# SALIDAS -entradas en el broker-
# ESTADOS
edoContenedor = "empty" # edos: empty, medium, full
tempAmb = 20 # en °C
# plantas
humP1 = 0 # en %
humP2 = 0 # en %
humP3 = 0 # en %
humP4 = 0 # en %

# RIEGO
riegoP1 = False # false = no se esta regando, true = se esta regando
riegoP2 = False
riegoP3 = False
riegoP4 = False
riegoManual = False # si se selecciona el riego manual, no se regará automáticamente por la duración de TIME_NO_AUTOMATIC_IRRIGATION
lastTimeRiegoManual = None
TIME_NO_AUTOMATIC_IRRIGATION = 1 * 60 * 60 # 1 hora 

# REGISTRO - se hace por cada envío xd

# COLOR - se recibe por BLE
mediumColor = [255,222,89] # amarillo
emptyColor = [255, 0, 0] # rojo

# ------------------------------
# FIN CONSTANTES ------------------------------------------------------------

# --------------------------------------------------------------------------
# MQTT helpers robustos (reintento/reconexión)
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
            # asegurar callback y suscripción en cada reconexión
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

def publish_safe(topic, payload, qos=0, retain=False):
    """
    Publica usando client.publish con manejo de OSError.
    Reintenta tras reconectar una vez.
    topic: bytes o str
    payload: str o bytes
    """
    global client
    # normalizar
    if isinstance(topic, str):
        topic_b = topic.encode('utf-8')
    else:
        topic_b = topic
    data = payload if isinstance(payload, bytes) else str(payload).encode('utf-8')
    try:
        client.publish(topic_b, data, qos=qos, retain=retain)
        return True
    except OSError as e:
        print("publish OSError:", e, "-> Intentando reconectar y reintentar...")
        if mqtt_connect():
            try:
                client.publish(topic_b, data, qos=qos, retain=retain)
                return True
            except Exception as e2:
                print("Reintento publish falló:", e2)
                return False
        else:
            return False
    except Exception as e:
        print("publish fallo (otro):", e)
        return False

# FUNCIONES -----------------------------------------------------------------
# Callback que se ejecuta cuando se recibe un mensaje
def callback(topic, msg):
    print("Mensaje recibido:")
    topic_str = topic.decode('utf-8') if isinstance(topic, bytes) else str(topic)
    print("  Topic:", topic_str)

    # Intentar decodificar como UTF-8 primero
    try:
        msg_str = msg.decode('utf-8') if isinstance(msg, bytes) else str(msg)
    except Exception:
        msg_str = str(msg)

    # Intentar JSON
    try:
        msg_dict = json.loads(msg_str)
        print("  Msg (dict):", msg_dict)
        recibir_info(topic_str, msg_dict)
        return
    except Exception:
        # mantener parecido a tu mensaje original
        print("  Error: El mensaje no es JSON válido (intento JSON falló).")
        print("  Msg (raw):", msg_str)

    # Si no es JSON: intentar parseo tolerante para casos comunes
    s = msg_str.strip()
    s_lower = s.lower()
    # Caso simple: payload "on" / "off"
    if s_lower in ("on", "off"):
        # inferir cmd según topic p1..p4
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
        msg_dict = {"cmd": cmd, "value": "on" if s_lower == "on" else "off"}
        print("  Msg (inferred simple):", msg_dict)
        recibir_info(topic_str, msg_dict)
        return

    # Caso: dict con comillas simples -> intentar reemplazar
    if s.startswith("{") and "'" in s and '"' not in s:
        try:
            candidate = s.replace("'", '"')
            msg_dict = json.loads(candidate)
            print("  Msg (fixed single-quotes -> dict):", msg_dict)
            recibir_info(topic_str, msg_dict)
            return
        except Exception:
            pass

    # Si nada, ya quedó en raw y se imprimió
    print("  No se pudo interpretar el mensaje recibido.")

def enviar_datos():
    # Actualizar estados
    enviarEdoContenedor()
    enviarEdoTempAmb()
    enviarEdoHumP1()
    enviarEdoHumP2()
    enviarEdoHumP3()
    enviarEdoHumP4()
    # Actualizar riegos (se mantiene llamado en el flujo principal si hace falta)

def recibir_info(topic, msg):
    # RIEGO
    if(topic == "afcs_fito/esp32/proyRiego/salidas/riego/p1" and msg.get("cmd") == "val1"): # planta 1
        if(msg.get("value") == "on"):
            riego(1,True,True)
        elif(msg.get("value") == "off"):
            riego(1,False,True)
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/riego/p2" and msg.get("cmd") == "val2"): # planta 2
        if(msg.get("value") == "on"):
            riego(2,True,True)
        elif(msg.get("value") == "off"):
            riego(2,False,True)
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/riego/p3" and msg.get("cmd") == "val3"): # planta 3
        if(msg.get("value") == "on"):
            riego(3,True,True)
        elif(msg.get("value") == "off"):
            riego(3,False,True)
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/riego/p4" and msg.get("cmd") == "val4"): # planta 4
        if(msg.get("value") == "on"):
            riego(4,True,True)
        elif(msg.get("value") == "off"):
            riego(4,False,True)
        else:
            print("La solicitud no se reconoce con un valor valido")
    # ESTADOS
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/estados/contenedor" and msg.get("cmd") == "contenedor"): # contenedor
        if(msg.get("value") == "update"):
            enviarEdoContenedor()
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/estados/tempAmb" and msg.get("cmd") == "tempAmb"): # tempAmb
        if(msg.get("value") == "update"):
            enviarEdoTempAmb()
        else:
            print("La solicitud no se reconoce con un valor valido")
    # plantas
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/estados/plantas/p1" and msg.get("cmd") == "Hum_P1"): # planta 1
        if(msg.get("value") == "update"):
            enviarEdoHumP1()
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/estados/plantas/p2" and msg.get("cmd") == "Hum_P2"): # planta 2
        if(msg.get("value") == "update"):
            enviarEdoHumP2()
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/estados/plantas/p3" and msg.get("cmd") == "Hum_P3"): # planta 3
        if(msg.get("value") == "update"):
            enviarEdoHumP3()
        else:
            print("La solicitud no se reconoce con un valor valido")
    elif(topic == "afcs_fito/esp32/proyRiego/salidas/estados/plantas/p4" and msg.get("cmd") == "Hum_P4"): # planta 4
        if(msg.get("value") == "update"):
            enviarEdoHumP4()
        else:
            print("La solicitud no se reconoce con un valor valido")
    else:
        print("El mensaje no fue reconocido con un formato valido")
        
# Enviar actualizaciones de estado
def enviarEdoContenedor():
    datos = {
        "cmd": "contenedor",
        "value": actualizarEdoContenedor(),
        "ts": time.time()
    }
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/contenedor", payload, qos=1, retain = True)
    enviarRegistro("Actualizacion del estado del contenedor", datos)

def enviarEdoTempAmb():
    datos = {
        "cmd": "temperatura ambiente",
        "value": actualizarEdoTempAmb(),
        "ts": time.time()
    }
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/tempAmb", payload, qos=1, retain= True)
    enviarRegistro("Actualizacion del estado de la temperatura ambiente", datos)

def enviarEdoHumP1():
    datos = {
        "cmd": "humedad planta 1",
        "value": actualizarEdoHumP1(),
        "ts": time.time()
    }
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/plantas/hum/p1", payload, qos=1, retain = True)
    enviarRegistro("Actualizacion del estado de la Humedad de la planta 1", datos)

def enviarEdoHumP2():
    datos = {
        "cmd": "humedad planta 2",
        "value": actualizarEdoHumP2(),
        "ts": time.time()
    }
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/plantas/hum/p2", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado de la Humedad de la planta 2", datos)

def enviarEdoHumP3():
    datos = {
        "cmd": "humedad planta 3",
        "value": actualizarEdoHumP3(),
        "ts": time.time()
    }
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/plantas/hum/p3", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado de la Humedad de la planta 3", datos)

def enviarEdoHumP4():
    datos = {
        "cmd": "humedad planta 4",
        "value": actualizarEdoHumP4(),
        "ts": time.time()
    }
    payload = json.dumps(datos)
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/estados/plantas/hum/p4", payload, qos=1, retain=True)
    enviarRegistro("Actualizacion del estado de la Humedad de la planta 4", datos)

# Actualizaciones de estado
def actualizarEdoContenedor():
    global edoContenedor
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
    payloadRegister = json.dumps({"cmd": tipo,"value": datos, "ts": time.time()})
    publish_safe(b"afcs_fito/esp32/proyRiego/entradas/registros", payloadRegister, qos=1)
    print("registro enviado")

# Riego
def riego(number, regar, manual):
    # Variables globales
    global riegoManual
    global lastTimeRiegoManual
    
    # regar o cerrar 'number', 'regar'
    riegoManual = manual
    if riegoManual:
        lastTimeRiegoManual = time.time() # actualizamos tiempo último riego manual
    
    # Envío registro y riego
    tipo = "Riego planta " + str(number)
    if regar:
        cmd = "Riego"
    else:
        cmd = "Parar riego"
    if manual:
        value = "Elección manual"
    else:
        value = "Elección automático"
    datos = {
        "cmd": cmd,
        "value": value,
    }
    topic_riego = "afcs_fito/esp32/proyRiego/entradas/riego/p{}".format(number)
    payload = json.dumps(datos)
    publish_safe(topic_riego, payload, qos=1)
    enviarRegistro(tipo, datos)

def decidir_regar(
    soil_moisture_pct,       # Humedad de la maceta en %, 0..100
    ambient_temp_c,          # Temperatura ambiente en °C (None o outlier -> se reporta)
    ambient_humidity_pct,    # Humedad ambiente en %
    plant_profile,           # perfil de planta (uno de PLANT_PROFILES)
    reservoir_available=True,# bool Si hay agua en depósito
    only_night=True,         # bool Si solo riega por la noche
    current_time_s=None,     # timestamp en segundos (utime.time())
    last_water_time_s=None,  # timestamp en segundos de último riego
    min_interval_minutes=60, # no regar si se regó hace menos (anti-ciclado)
    night_window=(20,6),     # hora inicio noche y fin (cruza medianoche si end <= start)
    debug=True
):
    """
    Devuelve 1 si debe regarse, 0 si no.
    Implementado para MicroPython (usa utime).
    """
    # Tiempo actual en segundos
    now_s = current_time_s or utime.time()

    # Utilidad de log
    def log(msg):
        if debug:
            print("[decidir_regar] " + msg)

    # ------ Validaciones básicas y detección de fallos ------
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

    # Temperatura
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

    # Humedad ambiente
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

    # ------ Regla de horario (solo de noche) ------
    if only_night:
        start_h, end_h = night_window
        h = utime.localtime(now_s)[3]  # obtener hora 0..23
        if start_h <= end_h:
            in_night = (start_h <= h < end_h)
        else:
            in_night = (h >= start_h) or (h < end_h)
        if not in_night:
            log("No es hora nocturna (hora actual: {}) -> No regar.".format(h))
            return 0
        else:
            log("Estamos en ventana nocturna -> riego permitido por horario.")

    # ------ Anti-ciclado ------
    if last_water_time_s:
        try:
            delta_s = now_s - last_water_time_s
            if delta_s < (min_interval_minutes * 60):
                log("Se regó hace {:.1f} min (< {} min) -> evitar riegos repetidos.".format(delta_s/60.0, min_interval_minutes))
                return 0
        except Exception:
            log("Aviso: last_water_time_s no válido -> ignorando anti-ciclado.")

    # ------ Regla tajante: si la humedad del suelo < umbral específico -> regar siempre ------
    try:
        dryness_threshold = float(plant_profile.get("dryness_threshold", 30.0))
    except Exception:
        dryness_threshold = 30.0

    if soil_moisture_pct < dryness_threshold:
        log("Humedad suelo {:.1f}% < umbral {:.1f}% -> Regar (ret 1).".format(soil_moisture_pct, dryness_threshold))
        return 1

    # ------ Cálculo de score combinando suelo/temp/hum ------
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
# FIN FUNCIONES ---------------------------------------------------------------   

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

# Registrar callback (se asegura también en mqtt_connect)
client.set_callback(callback)

# Conectar MQTT de forma robusta
if not mqtt_connect():
    print("ATENCIÓN: no se pudo conectar al broker MQTT en el inicio. El script seguirá intentando en publish/check_msg.")

# CICLO PRINCIPAL---------------------------------------------------------------------------------------
while True:
    # Recibir mensajes
    try:
        client.check_msg()
    except OSError as e:
        print("check_msg OSError:", e, "-> intentando reconectar...")
        mqtt_connect()
    except Exception as e:
        print("check_msg fallo (otro):", e)

    # Envío de datos
    if time.time() - last_pub >= PUB_INTERVAL:
        enviar_datos()
        last_pub = time.time()
        # Riego automático
        if riegoManual: # checamos si mantenemos la condición de riego manual
            if time.time() - lastTimeRiegoManual >= 0:
                riegoManual = False
        if not riegoManual: # lógica de riego atomático
            # if(decidir_regar()), usa la función riego, en manual = false
            print("Riego automático")
    time.sleep(.1)
