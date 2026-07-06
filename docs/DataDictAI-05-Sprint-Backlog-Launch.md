# DataDict AI — Sprint Planning + Backlog + Launch Plan
**Documento 05 de la serie (final de la fase de documentación). Estado: borrador para aprobación.**

---

## PARTE A — Sprint Planning (2 sprints de 1 semana, 14-15 días totales)

### Sprint 1 (Días 1-7): Backend + introspección funcionando de punta a punta

**Objetivo del sprint:** al final del día 7, un desarrollador puede pegar un connection string de Postgres y ver, sin interfaz bonita todavía, el JSON completo de su esquema documentado.

| Historia de usuario | Tareas | Estimado | Dependencias |
|---|---|---|---|
| Como usuario, puedo registrarme y loguearme | Setup Django + allauth + modelo `User` | 0.5 día | Ninguna |
| Como usuario, puedo guardar una conexión de forma segura | Modelo `DatabaseConnection` + encriptación Fernet + endpoint `POST /connections/` | 1 día | Registro |
| Como sistema, puedo leer el esquema de una BD Postgres | Módulo de introspección vía `information_schema` + tarea Celery | 1.5 días | Modelo de conexión |
| Como sistema, guardo el esquema como snapshot versionado | Modelo `SchemaSnapshot` + lógica de guardado | 0.5 día | Introspección |
| Como usuario, la IA me explica cada tabla | Integración con IA + prompt de explicación + cache en `TableDoc` | 1.5 días | Snapshot guardado |
| Como usuario, puedo comparar dos snapshots | Lógica de diff + modelo `SchemaDiff` | 1 día | Snapshots |
| Setup de infraestructura base | Docker Compose local, GitHub Actions básico (lint + test) | 1 día | Puede correr en paralelo desde el día 1 |

**Entregable del Sprint 1:** backend funcional completo, probado vía API (Postman/curl), sin frontend pulido.

### Sprint 2 (Días 8-15): Frontend + IA conversacional + billing + preparación de lanzamiento

| Historia de usuario | Tareas | Estimado | Dependencias |
|---|---|---|---|
| Como usuario, tengo una pantalla de onboarding simple | Vista HTMX de conexión + checklist de permisos de solo lectura | 1 día | Backend Sprint 1 |
| Como usuario, veo mi esquema como diagrama ER | Integración de librería de diagramas + endpoint de nodos/edges | 1.5 días | Snapshot disponible |
| Como usuario, puedo preguntar en lenguaje natural sobre mi esquema | Vista de chat + endpoint `/ask/` + historial | 1.5 días | Motor de IA |
| Como usuario, puedo exportar a Markdown | Endpoint de exportación + botón de descarga | 0.5 día | Documentación generada |
| Como usuario, puedo pagar y elegir un plan | Integración Stripe Checkout + webhook + límites por plan | 1.5 días | Puede empezar en paralelo desde el día 10 |
| QA manual del flujo completo | Recorrido end-to-end: registro → conexión → documentación → pago | 1 día | Todo lo anterior |
| Preparación de assets de lanzamiento | GIF de demo, copy de Product Hunt, posts de Reddit/Indie Hackers | 1 día | Producto funcionando, en paralelo con QA |
| Deploy a producción + pruebas finales | Deploy manual a Azure, verificación de health checks | 1 día | Todo lo anterior |

**Entregable del Sprint 2:** producto en producción, con pago funcionando, listo para el primer usuario real.

---

## PARTE B — Backlog priorizado (post-MVP, no se toca hasta validar)

**Prioridad alta (primeras semanas post-lanzamiento, según feedback real):**
1. Soporte MySQL (si los primeros usuarios lo piden — no antes)
2. Notificaciones por email/Slack cuando se detecta un cambio de esquema
3. Exportación HTML y PDF

**Prioridad media:**
4. OAuth social (Google/GitHub) para reducir fricción de registro
5. Multiusuario dentro de una cuenta (plan Team)
6. API keys para integraciones externas (CI/CD)

**Prioridad baja / evaluar según demanda real:**
7. Explicación de procedimientos almacenados
8. Modo claro
9. Soporte SQL Server / otros motores

---

## PARTE C — Launch Plan

### Semana de lanzamiento (inmediatamente después del día 15)

| Día | Acción |
|---|---|
| Día -3 | Beta privada con 5-10 desarrolladores de tu red (GitHub, comunidades Django/Postgres) — recolectar feedback y el primer testimonio real |
| Día -2 | Ajustes finales según feedback de beta, confirmar que el flujo de pago funciona sin fricción |
| Día -1 | Preparar el listing de Product Hunt (título, tagline, GIF de demo de 20 segundos, primeras respuestas a comentarios ya escritas) |
| Día 0 (martes o miércoles, mayor tráfico en PH) | Lanzamiento en Product Hunt + post simultáneo en Show HN + posts en r/PostgreSQL, r/django, r/webdev (tono "hice esto para mi propio problema", no venta) |
| Día 1-3 | Publicar en Indie Hackers con números reales de las primeras conversiones, responder cada comentario de PH/HN activamente |
| Semana 2 | Outreach a newsletters de developers (Bytes.dev, TLDR Web Dev, Pointer) si el tracción inicial lo justifica |

### Recordatorio de lo que ya acordamos y no hay que perder de vista

- El **Hunter** de Product Hunt debe ser alguien con audiencia real, no una cuenta nueva — esto lo defines tú antes del día 0.
- En Reddit e Indie Hackers: nunca tono de venta directa, siempre "resolví esto para mí, quizás le sirva a alguien más".
- El pricing ($19 / $39 / $79-99) se confirma con los primeros pagos reales de la beta privada, no antes — si en la beta nadie paga $19, ajustamos antes del lanzamiento público, no después.

---

## Cierre de la fase de documentación

Con este documento se completa la serie: Vision+PRD, Architecture+DB+Backend, API+Frontend, Security+Testing+DevOps, y este de Sprint+Backlog+Launch. Es la base completa que le vamos a pasar a Claude Code para empezar a escribir el proyecto real.

¿Aprobado? Si es así, el siguiente paso es literalmente abrir la terminal: te preparo el prompt inicial para Claude Code con todo este contexto para que arranque el Sprint 1, Día 1.
