#Redes #ComunicacionesElectrónicas #Software 

Para comunicarse con la [[Red]] se utiliza una [[APIs]].

## Importación de módulos
```python
import network
import urequests
import time
```
## Conexión [[Wi-Fi]]
```python
print("Conectando...")
sta_if=network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('Wokwi-GUEST', '') # simular conexión en Wokwi

while not sta_if.isconnected(): # si no esta conectado
    print("*", end="")
    time.sleep(0.5)
print("\nConexión exitosa")
```

## Solicitud por [[APIs]] gratuita
```python
# Enviar requerimiento por HTTPs a una API gratuita
print("Enviando requerimiento por HTTPs...")
response=urequests.get("https://reqres.in/api/users?page=2")

print(response.text)
```
>Se usa la página [Reqres - A hosted REST-API ready to respond to your AJAX requests](https://reqres.in/)