# DataDict AI — Architecture + Database Design + Backend Spec
**Documento 02 de la serie. Estado: borrador para aprobación.**

---

## 1. Arquitectura general

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO (browser)                       │
└───────────────────────────────┬─────────────────────────────────┘
                                 │ HTTPS
                                 ▼
                    ┌────────────────────────┐
                    │   Django (Gunicorn)    │
                    │   - Views (HTMX)       │
                    │   - REST API (DRF)     │
                    │   - Auth               │
                    └───────────┬────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │  PostgreSQL  │  │    Redis     │  │   Celery     │
      │ (nuestra BD, │  │ (cache +     │  │   Workers    │
      │  metadatos)  │  │  broker)     │  │ (async jobs) │
      └──────────────┘  └──────────────┘  └──────┬───────┘
                                                   │
                          ┌────────────────────────┼───────────────────┐
                          ▼                        ▼                   ▼
                ┌──────────────────┐   ┌──────────────────┐  ┌─────────────────┐
                │ Conexión BD del  │   │  Motor de IA     │  │  Detección de   │
                │ CLIENTE          │   │  (explicación +  │  │  cambios entre  │
                │ (solo lectura)   │   │  lenguaje nat.)  │  │  snapshots       │
                └──────────────────┘   └──────────────────┘  └─────────────────┘
```

**Principio de diseño clave:** la conexión a la base de datos del cliente NUNCA ocurre dentro de una request síncrona de Django. Todo pasa por Celery. Si la base del cliente está lenta, caída, o el schema es enorme (500+ tablas), no queremos que eso bloquee ni un solo segundo el servidor web.

---

## 2. Apps de Django (módulos)

| App | Responsabilidad |
|---|---|
| `accounts` | Registro, login, planes, billing (Stripe) |
| `connections` | Almacenar y gestionar conexiones a bases de datos del cliente (encriptadas) |
| `introspection` | Lógica de lectura de esquema (tablas, columnas, FKs, índices) |
| `snapshots` | Guardar versiones del esquema en el tiempo, comparar cambios |
| `ai_engine` | Capa de explicación en lenguaje natural sobre el esquema extraído |
| `exports` | Generación de Markdown (y futuro HTML/PDF) |
| `dashboard` | Vistas HTMX del panel del usuario |

---

## 3. Modelo de datos (nuestra base, no la del cliente)

```python
# accounts/models.py
class User(AbstractUser):
    plan = models.CharField(choices=[("starter","Starter"),("pro","Pro"),("team","Team")], default="starter")
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)

# connections/models.py
class DatabaseConnection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="connections")
    name = models.CharField(max_length=100)                # "Producción", "Staging"
    engine = models.CharField(max_length=20, default="postgresql")
    encrypted_credentials = models.BinaryField()            # Fernet-encrypted connection string
    last_synced_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(choices=[("pending","Pending"),("connected","Connected"),("error","Error")], default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

# introspection/models.py
class SchemaSnapshot(models.Model):
    connection = models.ForeignKey(DatabaseConnection, on_delete=models.CASCADE, related_name="snapshots")
    raw_schema_json = models.JSONField()   # estructura completa: tablas, columnas, tipos, FKs, índices
    created_at = models.DateTimeField(auto_now_add=True)

class TableDoc(models.Model):
    snapshot = models.ForeignKey(SchemaSnapshot, on_delete=models.CASCADE, related_name="tables")
    table_name = models.CharField(max_length=255)
    ai_explanation = models.TextField(blank=True)   # generado por ai_engine, cacheado
    row_count_estimate = models.BigIntegerField(null=True)

class ColumnDoc(models.Model):
    table = models.ForeignKey(TableDoc, on_delete=models.CASCADE, related_name="columns")
    column_name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=100)
    is_nullable = models.BooleanField()
    is_foreign_key = models.BooleanField(default=False)
    references_table = models.CharField(max_length=255, blank=True, null=True)

# snapshots/models.py
class SchemaDiff(models.Model):
    connection = models.ForeignKey(DatabaseConnection, on_delete=models.CASCADE)
    from_snapshot = models.ForeignKey(SchemaSnapshot, on_delete=models.CASCADE, related_name="diffs_from")
    to_snapshot = models.ForeignKey(SchemaSnapshot, on_delete=models.CASCADE, related_name="diffs_to")
    changes_json = models.JSONField()   # tablas agregadas, columnas eliminadas, tipos cambiados
    created_at = models.DateTimeField(auto_now_add=True)

# ai_engine/models.py
class NLQuery(models.Model):
    connection = models.ForeignKey(DatabaseConnection, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

**Índices necesarios desde el día 1:** `DatabaseConnection.user_id`, `SchemaSnapshot.connection_id + created_at` (para traer el snapshot más reciente rápido), `TableDoc.snapshot_id`.

---

## 4. Flujo técnico paso a paso (el corazón del producto)

1. Usuario pega connection string → se valida el formato → se encripta con Fernet (clave en variable de entorno, nunca en código ni en BD en texto plano) → se guarda en `DatabaseConnection`.
2. Se dispara una tarea Celery `introspect_database(connection_id)`:
   - Abre conexión de **solo lectura** (usuario de BD debe tener permisos `SELECT` únicamente — lo indicamos explícitamente en el onboarding).
   - Lee `information_schema` (tablas, columnas, tipos, nullable, FKs, índices).
   - Guarda todo como JSON en `SchemaSnapshot`.
   - Cierra la conexión inmediatamente. No mantenemos conexiones abiertas de forma persistente.
3. Segunda tarea Celery `generate_ai_docs(snapshot_id)`:
   - Por cada tabla, arma un prompt con el nombre, columnas, tipos y relaciones (nunca datos reales de filas) y pide a la IA una explicación en lenguaje simple.
   - Cachea la explicación en `TableDoc.ai_explanation` — no se vuelve a llamar a la IA a menos que el esquema cambie.
4. Cuando el usuario hace una pregunta en lenguaje natural (`NLQuery`), el motor arma el contexto con el `raw_schema_json` completo (no toda la BD, solo su estructura) y responde solo con esa información — nunca inventa tablas que no existen.
5. Job periódico (Celery Beat, diario u on-demand) vuelve a correr introspección → si hay diferencias con el snapshot anterior, genera `SchemaDiff` y notifica al usuario.

---

## 5. Seguridad de credenciales (crítico, no negociable)

- Encriptación **Fernet** (simétrica, de la librería `cryptography`) sobre el connection string completo antes de guardar.
- La clave de encriptación vive en variable de entorno / Azure Key Vault — nunca en el repositorio.
- Recomendamos explícitamente en el onboarding que el cliente cree un **usuario de base de datos de solo lectura** dedicado a DataDict AI (no su usuario admin). Esto lo documentamos como requisito, no como sugerencia opcional.
- Al cancelar la cuenta o eliminar una conexión: borrado inmediato y verificable del `encrypted_credentials` (no soft-delete de esto en particular).
- Ningún log de la aplicación debe imprimir el connection string ni credenciales, ni siquiera en modo debug.

---

## 6. Motor de IA — alcance del MVP

- Input: esquema estructural (JSON), nunca filas de datos del cliente.
- Cache agresivo: una tabla que no cambió no vuelve a pasar por la IA.
- Fallback: si la IA no puede generar explicación (tabla con nombres muy crípticos, sin contexto suficiente), el sistema debe decir explícitamente "no hay suficiente contexto para explicar esta tabla" — nunca inventar un propósito de negocio que no se puede inferir del esquema.

---

## 7. Lo que dejamos fuera del backend del MVP (v2)

- Multi-engine (MySQL/SQL Server) — el modelo ya lo soporta (`engine` field) pero el introspector solo se implementa para Postgres en el MVP.
- Webhooks de notificación (Slack/email cuando hay cambio de esquema) — v2.
- Rate limiting granular por plan — para el MVP, límite simple por número de conexiones activas, ya suficiente.

---

## Siguiente documento

**Documento 03: API Specification + Frontend Spec (consolidado)** — endpoints REST, autenticación, y las pantallas mínimas necesarias (onboarding, dashboard de conexión, vista de esquema, chat de lenguaje natural).

¿Apruebas este documento para seguir con API + Frontend?
