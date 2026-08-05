#Redes #Computación #IoT

# Tipos
Existe una relación inversamente proporcional entre el alcance y la cantidad de datos enviados, para compensarlo se vuelve más caro.
![[Pasted image 20250820111754.png]]
## Alto Alcance
### LP[[WAN]]: Red de Área Amplia de Baja Potencia
![[Pasted image 20251101171515.png]]
Es una tecnología con alance de kilómetros y con una extrema eficiencia energética (años).
#### Tipos / Filosofías
##### Espectro no-licenciado
![[Pasted image 20251028192815.png]]
Similar a un parque público: gratis, pero se puede llenar de gente, y puede comprometer la seguridad.
###### LoRa WAN
Red de Área Amplia de Largo Alcance: Cubre grandes distancias con costes bajos.
**Características**
- Puede escucharse incluso en ambientes con gran interferencia
- Busca que ==cada quien construya su red==
>Útil en campo y ciudades inteligentes, donde se ocupan muchos dispositivos con bajo presupuesto.
###### SIGFOX
[[Red]] global única y patentada.
**Características**:
- Eficiencia energética
- Velocidad de datos muy baja (100bps)
- Cada dispositivo puede enviar pocos mensajes al día
##### Espectro licenciado
![[Pasted image 20251028192822.png]]
Similar a una autopista de peaje: se debe de pagar, pero incluye un carril exclusivo, seguro y confiable.
###### NB-IoT
Internet de las cosas de banda estrecha: usa las redes celulares que ya existen, dando confiabilidad y [[Seguridad]]. Incluye una cobertura increíble (lugares subterráneos y duración de batería de más de diez años).
**Características**:
- Cada torre puede aceptar hasta 100k dispositivos
**Historia**
![[Pasted image 20251101172059.png]]
Proviene del 4G/LTE.

## Bajo Alcance

> [!summary] De Bolsillo:
### Bluetooth
#### BLE
Llamado también Bluetooth de baja energía. Es ideal para dispositivos que deben funcionar por años con un par de pilas.
>Muy usado en los 'Wearable'

Su objetivo es mandar pequeñas cantidades de datos de vez en cuándo, teniendo un consumo de energía muy bajo.
### NFC (Near Field Comm)
Interacciones rápidas, con una gran seguridad (pues tienen un alcance similar al toque).
Permite leer [[Etiquetas Pasivas]] (como "calcomanías eléctricas sin batería").

> [!summary] En el hogar:
> 

|               | [[#WiFi]]      | [[#Zigbee]]       | [[#Z-Wave]]       |
| ------------- | -------------- | ----------------- | ----------------- |
| [[Topología]] | Estrella       | Malla             | Malla             |
| Frecuencia    | 2.4/5 GHz      | 2.4 GHz           | Sub-1 GHz         |
| Alcance       | 45m interior   | 75m interior      | 100m exterior     |
| Clave         | Alta Velocidad | Interoperabilidad | Sin Interferencia |

### [[Wi-Fi]]
Rápido, pero consume mucha energía.
>Útil solo con enchufes a la mano.
#### Tipos
- 2.4 GHz: Lento, pero constante, puede encontrarse con bandas saturadas (como un maratonista)
- 5 GHz: Rápido, pero se cansa rápido (como un velocista)
### Zigbee
> Busca solucionar el problema del alcance

En lugares de extensión moderada o baja, se puede buscar la colaboración entre distintos dispositivos para amentar el alcance de la comunicación. Esto se le conoce como ==Malla Zigbee==.
![[Pasted image 20251028191818.png]]
>Entre más dispositivos, más fuerte es la red.
>>Utiliza el concepto de [[Red de Malla (Mesh)]]

### Z-Wave
Al usar otra frecuencia, no se interfiere con el [[#WiFi]]
>Utiliza el concepto de [[Red de Malla (Mesh)]]