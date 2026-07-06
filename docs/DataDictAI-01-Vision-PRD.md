# DataDict AI — Vision & PRD
**Producto de NautilusTech S.A.S.**

*Documento 01 de la serie de documentación técnica. Estado: borrador para aprobación.*

---

## 0. Sistema de marca (definido a partir del logo de NautilusTech)

No inventé una paleta nueva desde cero — la extendí del logo que subiste para que DataDict AI se sienta como un producto de la misma casa, no un proyecto aislado.

| Elemento | Valor | Uso |
|---|---|---|
| **Primario — Cian eléctrico** | `#1FD8E8` | Acentos, CTAs, links, elementos activos |
| **Primario oscuro** | `#0EA5B7` | Hover states, texto sobre fondo claro |
| **Fondo base** | `#08141C` (azul marino casi negro) | Fondo principal, modo oscuro por defecto |
| **Fondo secundario** | `#0F2530` | Cards, paneles, contraste sutil |
| **Texto sobre oscuro** | `#E8F6F8` | Texto principal |
| **Éxito / dato correcto** | `#2ED8A7` (verde-teal, coherente con el degradado del logo) | Confirmaciones, estados "documentado" |
| **Alerta / esquema desactualizado** | `#F5A623` | Detección de cambios de esquema, warnings |

**Tipografía:**
- Headers: **Space Grotesk** (geométrica, técnica, con carácter — no el Inter genérico de cada SaaS)
- Cuerpo/UI: **Inter** (máxima legibilidad en dashboards y tablas de datos)
- Código/esquemas: **JetBrains Mono**

**Tono de comunicación:** directo, técnico, sin jerga de marketing inflada. Le hablamos a desarrolladores — ellos detectan el "SaaS bullshit" en dos segundos. Ejemplo de voz correcta: *"Conecta tu base. Ve tu esquema documentado en 3 minutos."* Ejemplo de voz incorrecta: *"Revoluciona la forma en que tu equipo colabora con los datos."*

**Modo por defecto:** oscuro (coherente con el logo y con las herramientas de developer que tu usuario ya usa a diario — terminal, VS Code, GitHub).

---

## 1. Visión

**Misión:** Que ningún desarrollador vuelva a abrir un `SELECT * FROM information_schema` a mano ni a mantener un diagrama ER desactualizado en Notion.

**Visión a 3 años:** DataDict AI es la capa de documentación viva que cualquier equipo con una base de datos relacional conecta en minutos — sin instalar CLI, sin aprender un lenguaje declarativo nuevo, sin depender de que alguien se acuerde de actualizar el diagrama.

**Principios del producto:**
1. **Cero fricción de entrada.** Conectar y ver valor en menos de 5 minutos, no en una tarde de configuración.
2. **Solo lectura, siempre.** Nunca escribimos en la base de datos del cliente. Esto no es negociable — es la base de la confianza que necesitamos para que alguien nos dé credenciales.
3. **La IA explica, no adivina.** Toda explicación generada por IA debe basarse en el esquema real (nombres, tipos, foreign keys, comentarios existentes) — no alucinar relaciones que no existen.
4. **Simple gana sobre completo.** Preferimos hacer 3 cosas perfectas (documentar, diagramar, responder en lenguaje natural) que 15 a medias.

---

## 2. El problema

Los equipos de desarrollo pierden tiempo real manteniendo documentación de esquema que se desactualiza en cuanto alguien hace un `ALTER TABLE` sin avisar. Hoy las alternativas son:

- **Hacerlo a mano** en Notion/Confluence → se desactualiza en la primera semana.
- **Herramientas CLI como Atlas** (atlasgo.io) → potentes, pero exigen instalar un binario, aprender HCL, y están pensadas para *migraciones* de esquema, no para que alguien no-técnico del equipo (un PM, un nuevo dev) entienda "qué significa esta tabla" en 30 segundos.
- **Nada** → la documentación vive en la cabeza de quien diseñó la base, y se va cuando esa persona se va.

## 3. Oportunidad y diferenciador real frente a Atlas

Ya lo identificamos en la investigación: Atlas resuelve inspección de esquema y migraciones muy bien, gratis y open source. **No vamos a competir ahí.** Nuestro hueco específico:

1. **Explicación en lenguaje natural con IA** — "¿qué tabla guarda el estado de una orden cancelada?" en vez de leer 40 tablas a mano.
2. **Producto hospedado, no herramienta de terminal** — para el 80% de los casos de uso (un dev nuevo entendiendo el sistema, un PM revisando qué datos existen) no queremos pedirle a nadie que instale nada.
3. **Documentación explicada, no solo estructura** — Atlas te da el DDL. Nosotros te explicamos qué hace cada tabla y por qué existe esa relación, con IA.

## 4. Usuario objetivo (MVP)

**Usuario primario:** desarrollador backend/full-stack en un equipo de 2-15 personas, con una base de datos Postgres en producción que ya tiene más de 15-20 tablas (el punto donde "me acuerdo de memoria" deja de funcionar).

**Caso de uso #1 (el que resolvemos primero, nada más):** *"Acabo de entrar a este proyecto / volví después de 3 meses y necesito entender la base de datos rápido."*

---

## 5. MVP — alcance exacto (lo que SÍ entra en 15 días)

1. Conectar una base de datos Postgres (solo lectura, vía connection string encriptado).
2. Generar automáticamente: diccionario de tablas/columnas, diagrama ER visual, detección de foreign keys e índices.
3. Búsqueda/pregunta en lenguaje natural sobre el esquema ("¿qué tabla tiene el email del usuario?") usando IA sobre el esquema ya extraído (no sobre los datos — nunca tocamos filas de datos del cliente, solo estructura).
4. Exportar a Markdown (HTML y PDF quedan para v2, no MVP).
5. Detección simple de cambios de esquema entre dos conexiones (snapshot A vs snapshot B).

## 6. Lo que NO entra en el MVP (v2 o más adelante)

- Explicación de procedimientos almacenados (complejidad alta, poco frecuente en Django-first shops)
- Exportación PDF/HTML (Markdown cubre el 80% del valor)
- Soporte MySQL/SQL Server (Postgres primero, valida, luego expande)
- Multiusuario/roles (el plan Team con esto llega después de validar con clientes individuales)

## 7. Restricciones técnicas del proyecto

- Stack: Python, Django, PostgreSQL, Celery, Redis, integración con IA para el motor de lenguaje natural.
- Nunca almacenamos las credenciales de BD en texto plano — encriptadas en reposo desde el día 1 (esto va en detalle en Security.md, próximo documento).
- Tiempo de respuesta de conexión inicial: menor a 3 minutos desde que el usuario pega su connection string hasta ver el primer resultado.

## 8. Criterios de éxito del MVP

- 10 usuarios beta pagando (aunque sea con descuento) en las primeras 2 semanas post-lanzamiento.
- Al menos 3 usuarios que conecten una segunda base de datos sin que se los pidamos (señal de retención real).
- Lanzamiento en Product Hunt con Hunter validado, no orgánico sin promoción.

---

## Siguiente documento

**Documento 02: Architecture + Database Design + Backend Spec (consolidado)** — la arquitectura técnica completa: modelos Django, cómo se conecta y lee el esquema del cliente, estructura del motor de IA, y el pipeline de Celery para procesar conexiones sin bloquear.

¿Apruebas este documento para que sigamos con el técnico, o quieres ajustar algo del alcance del MVP o la marca antes de avanzar?
