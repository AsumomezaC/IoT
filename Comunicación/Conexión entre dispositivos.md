#Software #Redes #IoT 

## Introducción
Cada conexión es distinta y se deben de tomar distintas consideraciones para saber cuál [[Redes para IoT|red]] es más apropiada para cada caso:

| Características | Significado                        | Desafío                             |
| --------------- | ---------------------------------- | ----------------------------------- |
| **Alcance**     | Qué tan lejos viaja la señal       | + alcance = + energía               |
| **Velocidad**   | Qué tan rápido se envían los datos | + velocidad = + energía             |
| **Consumo**     | Cuánta batería se necesita         | - consumo = - alcance y/o - energía |
## Conectividad en el hogar
Se usa principalmente [[Redes para IoT#Bajo Alcance|redes de bajo alcance]], entre las que se destacan [[Redes para IoT#Wifi|WiFi]], [[Redes para IoT#Bluetooth|Bluetooth]], [[Redes para IoT#Zigbee|Zigbee]]
## Conectividad en el mundo exterior
Se usan principalmente [[Redes para IoT#Alto Alcance|redes de alto alcance]], entre las que se destaca [[Redes para IoT#LPWAN Red de Área Amplia de Baja Potencia|LPWAN]].
## Conclusión
![[Pasted image 20251028193541.png]]
Lo mejor es una combinación de todas las tecnologías para cada caso particular. Trabajando un equipo de especialistas:
### WiFi
![[Pasted image 20251028193651.png]]
Velocidad
### BLE
![[Pasted image 20251028193735.png]]
Dispositivos personales que necesitan ahorrar batería.
### Zigbee
![[Pasted image 20251028193806.png]]
Para crear redes fuertes dentro de casa.
### LoRa WAN
![[Pasted image 20251028193840.png]]
Largas distancias
### NB-IoT
![[Pasted image 20251028193906.png]]
Un mensajero seguro, para datos críticos o difíciles de alcanzar.