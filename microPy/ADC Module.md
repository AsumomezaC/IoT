#Python #Software #Electrónica #ADC #IoT #MicroPython #ESP32
# ADC en la Librería Machine de ESP32

> El módulo `machine.ADC` en [[MicroPython]] para ESP32 proporciona acceso a los convertidores analógico-digitales integrados en el chip, permitiendo leer voltajes analógicos desde pines GPIO específicos.
## Configuración Básica del [[ADC (Convertidor analógico-digital)|ADC]]

### Importación e Inicialización

```python
from machine import ADC, Pin

# Crear objeto ADC en un pin específico
adc = ADC(Pin(34))  # Pin 34 es solo de entrada analógica

# Configurar rango de lectura (0-4095 para 12 bits)
adc.read()  # Retorna valor entre 0-4095
```

## Características Técnicas del ADC en ESP32

### Resolución y Rango

```python
# Configurar resolución (bits)
adc.width(ADC.WIDTH_12BIT)  # 0-4095 (por defecto)
adc.width(ADC.WIDTH_11BIT)  # 0-2047
adc.width(ADC.WIDTH_10BIT)  # 0-1023
adc.width(ADC.WIDTH_9BIT)   # 0-511

# Atenuación (rango de voltaje)
adc.atten(ADC.ATTN_0DB)    # 0-1.1V
adc.atten(ADC.ATTN_2_5DB)  # 0-1.5V  
adc.atten(ADC.ATTN_6DB)    # 0-2.2V
adc.atten(ADC.ATTN_11DB)   # 0-3.3V (más común)
```

### Pines ADC Disponibles

**ESP32:** 
- **ADC1:** Pines 32-39 (8 canales)
- **ADC2:** Pines 0, 2, 4, 12-15, 25-27 (10 canales)

**Restricción importante:** ADC2 no disponible cuando WiFi está activo.

## Ejemplos Prácticos

### Lectura Simple de Sensor

```python
from machine import ADC, Pin
import time

# Configurar ADC en pin 34
sensor = ADC(Pin(34))
sensor.atten(ADC.ATTN_11DB)  # Rango 0-3.3V
sensor.width(ADC.WIDTH_12BIT)  # 12 bits de resolución

while True:
    valor_adc = sensor.read()
    voltaje = (valor_adc / 4095) * 3.3
    print(f"ADC: {valor_adc}, Voltaje: {voltaje:.2f}V")
    time.sleep(1)
```

### Lectura con Promediado para Reducir Ruido

```python
def leer_adc_promediado(adc, muestras=100):
    """Lee el ADC promediando múltiples muestras"""
    acumulado = 0
    for _ in range(muestras):
        acumulado += adc.read()
    return acumulado // muestras

# Uso
valor_estable = leer_adc_promediado(sensor, 50)
```

### Conversión a Unidades Físicas

```python
# Ejemplo: Sensor de temperatura LM35 (10mV/°C)
def leer_temperatura(adc):
    valor_adc = adc.read()
    voltaje = (valor_adc / 4095) * 3.3
    temperatura = voltaje * 100  # LM35: 10mV/°C
    return temperatura

temp = leer_temperatura(sensor)
print(f"Temperatura: {temp:.1f}°C")
```

## Configuraciones Avanzadas

### Múltiples Canales ADC

```python
# Leer de múltiples sensores
sensor1 = ADC(Pin(32))
sensor2 = ADC(Pin(33))
sensor3 = ADC(Pin(34))

sensores = [sensor1, sensor2, sensor3]

# Configurar todos igual
for sensor in sensores:
    sensor.atten(ADC.ATTN_11DB)
    sensor.width(ADC.WIDTH_12BIT)

def leer_todos():
    return [sensor.read() for sensor in sensores]
```

### Manejo de ADC2 con WiFi

```python
import network
from machine import ADC, Pin

# Al iniciar WiFi, ADC2 se deshabilita
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Solución: Usar solo ADC1 cuando WiFi está activo
if wlan.isconnected():
    sensor = ADC(Pin(34))  # ADC1 - seguro
else:
    sensor = ADC(Pin(4))   # ADC2 - solo sin WiFi
```

## Consideraciones de Precisión

### Errores Comunes y Soluciones

```python
# PROBLEMA: Lecturas ruidosas
# SOLUCIÓN: Promediado y filtrado
def leer_adc_filtrado(adc, factor=0.1):
    valor_anterior = adc.read()
    while True:
        valor_actual = adc.read()
        # Filtro pasa-bajos digital
        valor_suavizado = valor_anterior + factor * (valor_actual - valor_anterior)
        valor_anterior = valor_suavizado
        yield int(valor_suavizado)

# USO
filtro = leer_adc_filtrado(sensor)
valor_suave = next(filtro)
```

### Calibración y Compensación

```python
# Compensación de no linealidad del ADC
def calibrar_adc(adc, voltaje_conocido, pin_lectura):
    """Calibra usando un voltaje de referencia conocido"""
    lectura = adc.read()
    factor_calibracion = voltaje_conocido / (lectura / 4095 * 3.3)
    return factor_calibracion

# Ejemplo de calibración
factor = calibrar_adc(sensor, 3.3, 34)  # Usar fuente de 3.3V exacta
```

## Ejemplo Completo: Monitor de Batería

```python
from machine import ADC, Pin, deepsleep
import time

class MonitorBateria:
    def __init__(self, pin_bateria=35):
        self.adc = ADC(Pin(pin_bateria))
        self.adc.atten(ADC.ATTN_11DB)
        self.adc.width(ADC.WIDTH_12BIT)
        # Divisor de voltaje: 100k+100k = mitad del voltaje
        self.factor_divisor = 2.0
        
    def leer_voltaje_bateria(self):
        valor_adc = self.adc.read()
        voltaje_adc = (valor_adc / 4095) * 3.3
        voltaje_bateria = voltaje_adc * self.factor_divisor
        return voltaje_bateria
    
    def porcentaje_bateria(self, voltaje_min=3.0, voltaje_max=4.2):
        voltaje = self.leer_voltaje_bateria()
        porcentaje = ((voltaje - voltaje_min) / (voltaje_max - voltaje_min)) * 100
        return max(0, min(100, porcentaje))

# Uso
bateria = MonitorBateria()
print(f"Batería: {bateria.leer_voltaje_bateria():.2f}V")
print(f"Porcentaje: {bateria.porcentaje_bateria():.1f}%")
```

## Optimización y Mejores Prácticas

### 1. Gestión de Energía

```python
# Apagar ADC cuando no se use (ahorro de energía)
adc = ADC(Pin(34))
# Lectura única y luego deshabilitar
valor = adc.read()
adc.deinit()  # Desinicializar
```

### 2. Muestreo de Alta Velocidad

```python
# Para aplicaciones que requieren velocidad máxima
import time

def muestreo_rapido(adc, cantidad=1000):
    tiempos = []
    valores = []
    inicio = time.ticks_us()
    
    for i in range(cantidad):
        valores.append(adc.read())
        if i % 100 == 0:
            tiempos.append(time.ticks_us() - inicio)
    
    return valores, tiempos
```

### 3. Manejo de Errores

```python
try:
    valor = adc.read()
except OSError as e:
    print(f"Error ADC: {e}")
    # Reconectar o reinicializar
    adc = ADC(Pin(34))
```

## Limitaciones del ADC del ESP32

- **Resolución real:** ≈ 9-10 bits efectivos debido a ruido
- **No linealidad:** Puede requerir calibración para aplicaciones críticas
- **Voltaje de referencia:** Varía con temperatura y tensión de alimentación
- **Impedancia de fuente:** Máximo recomendado: 10kΩ

---
## Véase También

- [[PWM en ESP32 con Machine]]
- [[Sensores Analógicos con MicroPython]]
- [[Gestión de Energía en ESP32]]
- [[Comunicación WiFi en ESP32]]
- [[Calibración de Sensores]]