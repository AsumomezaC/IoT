#Amazon #Software #Internet #IoT 
# Amazon Web Services (AWS)

**Amazon Web Services (AWS)** es la plataforma de computación en la nube más amplia y adoptada a nivel mundial, ofrecida por Amazon.com. Proporciona más de 200 servicios integrales de centros de datos a nivel global, que incluyen cómputo, almacenamiento, bases de datos, redes, análisis, machine learning, inteligencia artificial, IoT, seguridad y más.

---
## Índice
1. [[#¿Qué es AWS? Modelo de Servicio]]
2. [[#Modelos de Nube en AWS]]
3. [[#Servicios Principales y Categorías (Por Área)]]
4. [[#Ventajas Clave de AWS]]
5. [[#Conceptos Fundamentales de Arquitectura]]
6. [[#Casos de Uso Comunes]]
7. [[#Consideraciones y Desafíos]]
8. [[#Certificaciones AWS]]

---

## ¿Qué es AWS? Modelo de Servicio

AWS opera bajo un modelo de **[[Computación en la nube]]** de pago por uso ("pay-as-you-go"). En lugar de comprar y mantener servidores físicos, los usuarios alquilan capacidad de AWS, pagando solo por lo que consumen.

- **Lanzamiento:** 2006, con el lanzamiento de S3 (Simple Storage Service) y EC2 (Elastic Compute Cloud).
- **Filosofía:** Proporcionar bloques de construcción fundamentales que permitan a las empresas construir aplicaciones complejas y escalables de manera ágil.

## Modelos de Nube en AWS

AWS ofrece flexibilidad para desplegar cargas de trabajo de diferentes maneras:

1.  **Nube Pública (Public Cloud):** Recursos propiedad de AWS, disponibles para cualquier cliente. Es el modelo principal.
2.  **Nube Híbrida (Hybrid Cloud):** Conexión de infraestructura local (on-premise) con la nube de AWS mediante servicios como **AWS Outposts** o **VPN**.
3.  **Nube Privada (On AWS):** Entornos aislados dentro de AWS, como **AWS Virtual Private Cloud (VPC)**, que permite lanzar recursos en una red virtual definida por el usuario.

## Servicios Principales y Categorías (Por Área)

AWS tiene una cartera enorme. Estos son algunos de los servicios fundamentales:

| Categoría | Servicios Clave | Descripción Breve |
| :--- | :--- | :--- |
| **Computación** | **EC2 (Elastic Compute Cloud)** | Servidores virtuales configurables en la nube. |
| | **Lambda** | [[Computación sin Servidor (Serverless)]]: ejecuta código sin aprovisionar servidores. |
| | **Elastic Beanstalk** | Plataforma como Servicio (PaaS) para desplegar aplicaciones fácilmente. |
| **Almacenamiento** | **S3 (Simple Storage Service)** | Almacenamiento de objetos escalable y duradero. |
| | **EBS (Elastic Block Store)** | Volúmenes de almacenamiento en bloque para usar con EC2. |
| | **Glacier** | Almacenamiento seguro y duradero para archivado y copias de seguridad. |
| **Bases de Datos** | **RDS (Relational Database Service)** | Servicio gestionado para bases de datos relacionales (MySQL, PostgreSQL, etc.). |
| | **DynamoDB** | Base de datos NoSQL rápida y flexible. |
| | **Redshift** | Almacén de datos (data warehouse) a gran escala para análisis. |
| **Redes y Contenido** | **VPC (Virtual Private Cloud)** | Red virtual privada y aislada lógicamente dentro de AWS. |
| | **CloudFront** | Red de entrega de contenidos (CDN) global. |
| | **Route 53** | Servicio de DNS web escalable y altamente disponible. |
| **Seguridad e Identidad**| **IAM (Identity and Access Management)** | Gestiona el acceso a los servicios y recursos de AWS de forma segura. |
| | **KMS (Key Management Service)** | Servicio gestionado para crear y controlar claves de cifrado. |
| **Machine Learning e IA** | **SageMaker** | Servicio completo para construir, entrenar e implementar modelos de [[Machine Learning]]. |
| | **Rekognition** | Análisis de imágenes y vídeo mediante IA (reconocimiento facial, escenas). |
| | **Comprehend** | Procesamiento de Lenguaje Natural (NLP) para analizar texto. |

## Ventajas Clave de AWS

-   **Agilidad y Velocidad:** Permite aprovisionar recursos en minutos, acelerando la innovación.
-   **Escalabilidad Elástica:** Escala la capacidad hacia arriba o hacia abajo automáticamente según la demanda.
-   **Ahorro de Costos (CAPEX vs OPEX):** Cambia el gasto de capital (CAPEX) por gasto operativo (OPEX). Solo pagas por lo que usas.
-   **Confiabilidad y Alta Disponibilidad:** Infraestructura global en **Regiones y Zonas de Disponibilidad** diseñadas para ser tolerantes a fallos.
-   **Seguridad:** Infraestructura y servicios diseñados para ser seguros, con herramientas de [[Ciberseguridad]] integradas. El modelo de responsabilidad compartida es clave.
-   **Ecosistema y Madurez:** La plataforma más grande, con la comunidad más extensa, mayor cantidad de documentación y socios.

## Conceptos Fundamentales de Arquitectura

-   **Región (Region):** Ubicación física en el mundo que agrupa múltiples **Zonas de Disponibilidad** (ej: `us-east-1` - Norte de Virginia).
-   **Zona de Disponibilidad (AZ - Availability Zone):** Uno o más centros de datos discretos con energía, red y conectividad redundantes dentro de una Región. El objetivo es la **tolerancia a fallos**.
-   **Modelo de Responsabilidad Compartida:**
    -   **AWS es responsable** *de* la seguridad *de* la nube (la infraestructura global).
    -   **El cliente es responsable** *de* la seguridad *en* la nube (configuración del SO, firewalls, datos, cifrado, gestión de acceso con IAM).

## Casos de Uso Comunes

-   **Alojamiento Web y Aplicaciones:** Sitios web y aplicaciones escalables usando EC2, S3, y RDS.
-   **Almacenamiento y Backup:** Soluciones de backup rentables y archivado en S3 y Glacier.
-   **Entornos de Desarrollo y Pruebas:** Crear y desmantelar entornos bajo demanda, reduciendo costos.
-   **Big Data y Analytics:** Procesar y analizar grandes volúmenes de datos con EMR, Redshift, y Athena.
-   **Sitios Web de Alto Tráfico:** Arquitecturas escalables para manejar picos de tráfico impredecibles.
-   **[[IoT (Internet de las cosas)]]:** Plataforma AWS IoT para conectar, gestionar e ingerir datos de dispositivos IoT.

## Consideraciones y Desafíos

-   **Gobernanza de Costos:** La facilidad de aprovisionar recursos puede llevar al "desperdicio" o a facturas sorpresa si no se monitoriza. Herramientas como **AWS Cost Explorer** y **Budgets** son esenciales.
-   **Curva de Aprendizaje:** La amplia gama de servicios y conceptos puede ser abrumadora para principiantes.
-   **Vendor Lock-in:** Adoptar servicios propietarios de AWS (ej: DynamoDB, Lambda) puede dificultar una migración futura a otro proveedor.
-   **Seguridad por Configuración:** La seguridad no es automática; debe ser configurada y gestionada correctamente por el cliente (especialmente IAM y políticas de S3).

## Certificaciones AWS

Las certificaciones validan el conocimiento técnico y son altamente valoradas en la industria. Siguen un camino de aprendizaje:
1.  **Nivel Foundational:** Cloud Practitioner.
2.  **Nivel Associate:** Solutions Architect, Developer, [[Sistema Operativo]], Administrator.
3.  **Nivel Professional:** Solutions Architect, DevOps Engineer.
4.  **Nivel Especialty:** Security, Advanced Networking, Machine Learning, etc.

---

**Notas vinculadas:**
- [[Computación en la nube]]
- [[Microsoft Azure]]
- [[Google Cloud Platform - GCP]]
- [[Computación sin Servidor (Serverless)]]
- [[Ciberseguridad]]
- [[Concepto de Region y AZ en Cloud]]