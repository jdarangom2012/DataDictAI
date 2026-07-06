# DataDict AI — API Specification + Frontend Spec
**Documento 03 de la serie. Estado: borrador para aprobación.**

---

## 1. Autenticación

- Registro/login con email + password (django-allauth) para el MVP. OAuth social (Google/GitHub) queda para v2 — no es crítico para validar y agrega complejidad de configuración.
- Autenticación de la API vía **token de sesión** (cookie httpOnly) para las vistas HTMX, y **API Key** por usuario para integraciones futuras (CI/CD, CLI propia más adelante).
- Todos los endpoints bajo `/api/` requieren autenticación. No hay endpoints públicos de datos.

## 2. Versionado

- Prefijo `/api/v1/` desde el día 1. No porque esperemos romper cosas pronto, sino porque cambiar esto después de tener clientes integrados es mucho más caro que ponerlo ahora.

## 3. Endpoints REST (MVP)

### Conexiones
```
POST   /api/v1/connections/                 → crear conexión (recibe connection string, lo encripta)
GET    /api/v1/connections/                 → listar conexiones del usuario
GET    /api/v1/connections/{id}/            → detalle de una conexión (nunca devuelve credenciales)
DELETE /api/v1/connections/{id}/            → eliminar conexión (borra credenciales inmediatamente)
POST   /api/v1/connections/{id}/sync/       → disparar re-introspección manual
```

### Esquema / documentación
```
GET    /api/v1/connections/{id}/schema/                 → último snapshot completo (tablas, columnas, FKs)
GET    /api/v1/connections/{id}/schema/tables/{table}/  → detalle + explicación IA de una tabla
GET    /api/v1/connections/{id}/diagram/                → estructura para renderizar el ERD (nodos + edges)
GET    /api/v1/connections/{id}/diffs/                  → historial de cambios entre snapshots
```

### IA / lenguaje natural
```
POST   /api/v1/connections/{id}/ask/        → { "question": "..." } → respuesta generada sobre el esquema
GET    /api/v1/connections/{id}/ask/history/ → historial de preguntas del usuario
```

### Exportación
```
GET    /api/v1/connections/{id}/export/markdown/  → descarga .md generado
```

### Billing
```
POST   /api/v1/billing/checkout/            → crea sesión de Stripe Checkout
POST   /api/v1/billing/webhook/             → webhook de Stripe (confirmación de pago, cancelación)
GET    /api/v1/billing/plan/                → plan actual del usuario
```

## 4. Formato de errores (consistente en toda la API)

```json
{
  "error": {
    "code": "connection_failed",
    "message": "No pudimos conectar con tu base de datos. Verifica que el usuario tenga permisos de solo lectura.",
    "field": null
  }
}
```

Códigos de error clave del MVP: `connection_failed`, `invalid_credentials_format`, `schema_too_large` (límite razonable inicial: 1,000 tablas, más que eso es un caso enterprise que no es el MVP), `ai_explanation_unavailable`, `plan_limit_reached`.

## 5. OpenAPI

Generado automáticamente con `drf-spectacular` a partir de los serializers de DRF — no se escribe a mano, se mantiene sincronizado con el código siempre.

---

## 6. Frontend — pantallas mínimas del MVP

Con HTMX + Alpine.js + TailwindCSS, sin build de SPA pesado — coherente con la filosofía de "simple gana sobre completo" del Documento 01.

| Pantalla | Elementos clave |
|---|---|
| **Onboarding (paso único)** | Input de connection string + checklist visible ("recomendamos un usuario de solo lectura") + botón "Conectar" |
| **Dashboard principal** | Lista de conexiones con estado (conectado/sincronizando/error), botón "+ Nueva conexión" |
| **Vista de esquema** | Diagrama ER interactivo (zoom/pan) + panel lateral con lista de tablas buscable |
| **Detalle de tabla** | Columnas, tipos, FKs, explicación IA, botón "regenerar explicación" |
| **Chat de lenguaje natural** | Input de pregunta + historial de conversación + respuestas con referencias a tablas específicas (clickeables) |
| **Historial de cambios** | Timeline simple de diffs entre snapshots, con lo agregado/eliminado resaltado en verde/rojo |
| **Configuración de cuenta** | Plan actual, upgrade/downgrade, API keys |

## 7. Modo oscuro

Por defecto activo, usando la paleta del Documento 01 (`#08141C` fondo, `#1FD8E8` acentos). Modo claro queda como toggle opcional en v2, no es prioridad — nuestro usuario vive en terminales oscuras.

## 8. Responsive

El dashboard y el chat de lenguaje natural deben funcionar en tablet. El diagrama ER completo en pantallas menores a 768px muestra una versión simplificada (lista en vez de grafo) — un ER de 40 tablas es ilegible en un celular sin importar cuánto lo optimicemos, así que no fingimos que sí.

## 9. Estado vacío (empty states) — detalle que muchos MVPs olvidan

- Dashboard sin conexiones: CTA claro a conectar la primera BD, con un GIF/video corto mostrando el flujo (mismo asset que usaríamos en Product Hunt).
- Tabla sin explicación IA generada aún: skeleton loader con mensaje "Generando explicación...", no un espacio en blanco confuso.

---

## Siguiente documento

**Documento 04: Security.md (con foco en manejo de credenciales de terceros) + Testing Strategy (ligero) + DevOps (Docker/CI básico)** — el último documento técnico antes de pasar a Sprint Planning y Launch Plan.

¿Apruebas para continuar?
