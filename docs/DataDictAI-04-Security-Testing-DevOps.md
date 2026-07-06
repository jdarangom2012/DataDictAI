# DataDict AI — Security + Testing Strategy + DevOps
**Documento 04 de la serie. Estado: borrador para aprobación.**

---

## PARTE A — Seguridad

### 1. Manejo de credenciales de terceros (el punto más crítico de todo el producto)

Esto es lo que determina si un desarrollador confía en pegarnos su connection string de producción o no. No es una sección más — es la que más cuidado necesita.

**Reglas no negociables:**
1. El connection string se encripta con **Fernet** (AES-128 en modo CBC + HMAC) antes de tocar la base de datos. Nunca se persiste en texto plano en ningún punto del flujo, incluidos logs.
2. La clave de encriptación (`FERNET_KEY`) vive en **Azure Key Vault**, se inyecta como variable de entorno en runtime — nunca en el repositorio, nunca en `.env` versionado, nunca en un secret manager compartido con otros servicios.
3. **Rotación de clave:** documentado desde el día 1 aunque no se implemente hasta v2 — cuando rotemos, re-encriptamos todas las credenciales activas en un job de migración controlado, nunca en caliente sin ventana de mantenimiento.
4. Onboarding **obligatorio, no opcional**: el flujo de conexión debe mostrar instrucciones específicas para crear un usuario de solo lectura en Postgres:
   ```sql
   CREATE USER datadictai_readonly WITH PASSWORD '...';
   GRANT CONNECT ON DATABASE tu_base TO datadictai_readonly;
   GRANT USAGE ON SCHEMA public TO datadictai_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO datadictai_readonly;
   ```
5. Al eliminar una conexión o cancelar la cuenta: `DELETE` real e inmediato del campo `encrypted_credentials` (no soft-delete de este campo específico, aunque el resto del registro se conserve para historial de facturación).
6. Ningún nivel de logging (ni `DEBUG`) debe imprimir el connection string completo. Se loguea únicamente el host y el nombre de la base, nunca usuario/password.

### 2. OWASP — lo que aplica realmente a este producto (no la lista genérica completa)

- **Inyección SQL:** no aplica en el sentido tradicional porque no ejecutamos queries arbitrarias del usuario contra su base — solo leemos `information_schema` con queries parametrizadas fijas que nosotros controlamos.
- **SSRF:** riesgo real, porque el usuario nos da un host/puerto para conectarnos. Validar que el connection string no apunte a rangos de IP internos de nuestra propia infraestructura (169.254.x.x, localhost, rangos privados de nuestro VPC) antes de intentar conectar.
- **Broken authentication:** rate limiting en login, verificación de email obligatoria antes de conectar la primera base de datos.
- **CSRF:** Django lo maneja por defecto vía middleware — verificar que HTMX envíe el token correctamente en cada request.

### 3. Auditoría

Tabla `AuditLog` simple desde el MVP: quién conectó/eliminó una conexión, cuándo, desde qué IP. No es opcional en un producto que maneja credenciales de terceros, incluso en la versión más mínima.

### 4. Backups

Backup diario automático de nuestra propia base de datos (metadatos, nunca las bases de los clientes — nosotros no almacenamos sus datos, solo su estructura). Retención de 7 días en el MVP, suficiente para recuperación ante errores humanos.

---

## PARTE B — Testing Strategy (nivel MVP, no enterprise)

| Tipo | Alcance en el MVP | Herramienta |
|---|---|---|
| Unitarias | Encriptación/desencriptación de credenciales, parsing de `information_schema`, detección de diffs entre snapshots | `pytest` + `pytest-django` |
| Integración | Flujo completo: crear conexión → introspección → generación de docs IA (con BD Postgres de prueba en Docker) | `pytest` + fixture de Postgres real, no mocks para esto específico |
| Seguridad | Test explícito de que las credenciales nunca aparecen en logs ni en respuestas de API | Test dedicado, no opcional |
| Carga | **Fuera del MVP.** Con 10 usuarios beta no es prioridad — se hace antes de escalar a cientos de usuarios, no antes de validar que alguien quiere pagar. |
| UI | **Fuera del MVP.** Testing manual del flujo crítico (onboarding → primera conexión) antes de cada release. |

**Regla práctica para 2 devs en 15 días:** cobertura de tests centrada en lo que puede romper la confianza del usuario (credenciales, precisión de la documentación generada) — no perseguir 90% de cobertura general a costa de tiempo de shipping.

---

## PARTE C — DevOps

### Infraestructura mínima viable

```
GitHub (repo + Actions)
   │
   ▼
GitHub Actions (CI)
   - lint (ruff)
   - tests (pytest)
   - build de imagen Docker
   │
   ▼
Azure Container Apps (o App Service — decidir según costo real al momento de desplegar)
   - Django (Gunicorn)
   - Celery worker
   - Celery beat
   │
   ├── Azure Database for PostgreSQL (nuestra BD)
   └── Azure Cache for Redis
   │
   ▼
Cloudflare (DNS + proxy + protección básica DDoS)
```

### Docker

Un solo `Dockerfile` multi-stage (build de dependencias + imagen final ligera), `docker-compose.yml` para desarrollo local con Postgres + Redis + el propio Django, para que cualquiera del equipo levante el proyecto completo con `docker compose up`.

### CI/CD (GitHub Actions)

- En cada PR: lint + tests.
- En merge a `main`: build de imagen + deploy automático a un ambiente de staging.
- Deploy a producción: manual (un click), nunca automático en el MVP — con 2 devs y clientes reales pagando, un deploy accidental a producción es más caro que el segundo que toma aprobarlo a mano.

### Variables de entorno (mínimas del MVP)

```
DJANGO_SECRET_KEY
FERNET_KEY
DATABASE_URL
REDIS_URL
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
AI_API_KEY
ALLOWED_HOSTS
```

### Monitoreo (nivel MVP, no observability enterprise)

- Sentry para errores de aplicación (gratis hasta cierto volumen, suficiente para el arranque).
- Un health check simple (`/health/`) que verifica conexión a Postgres y Redis — usado por Azure para reinicios automáticos si el servicio cae.
- **Fuera del MVP:** dashboards de observabilidad completos (Datadog/Grafana) — con 10 clientes beta, Sentry + logs de Azure son suficientes.

### Rollback

Cada deploy a producción etiqueta la imagen Docker con el hash del commit. Rollback = re-deployar la imagen anterior por su tag. Sin esto documentado, un bug en producción se convierte en una crisis en vez de un comando.

---

## Siguiente documento

**Documento 05: Sprint Planning (2 sprints de 1 semana cada uno para cubrir los 15 días) + Backlog priorizado + Launch Plan (Product Hunt, Reddit, Indie Hackers, con fechas concretas).**

Este sería el último documento antes de que Claude Code empiece a escribir código sobre esta base. ¿Aprobado para continuar?
