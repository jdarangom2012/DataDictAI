# DataDict AI — Plan de pruebas manual

Este documento acompaña al checklist interactivo entregado en el chat. Úsalo como
referencia permanente en el repo; el checklist interactivo es mejor para ir marcando
progreso mientras pruebas.

## Estado del entorno al momento de escribir esto

- Stack completo corriendo en Docker (`db`, `redis`, `web`, `worker`, `beat`) — todos `Up`.
- App disponible en **http://localhost:8000**
- Cuenta existente: `jdarangom2012@gmail.com`, plan **Pro** (ya se hizo una compra real
  en modo de prueba de LemonSqueezy durante el desarrollo, por eso no está en Starter).
- Dos conexiones ya existen en esa cuenta:
  - `Base de prueba` — estado `pending`, quedó de una prueba con host inválido, es
    normal y puedes borrarla o ignorarla.
  - `DataDict metadata DB` — estado `connected`, apunta a la propia base de datos de
    la app (`db` del docker-compose). Úsala para probar diagrama/chat/export sin
    tener que traer tu propia base de datos.
- `AI_API_KEY` está vacía en `.env`. Esto es esperado en este entorno: el chat y las
  explicaciones de tabla van a mostrar el texto de fallback documentado (no es un bug).
  Si quieres ver respuestas reales de IA, añade una key de OpenAI a `.env` y corre
  `docker compose up -d --force-recreate worker web`.
- LemonSqueezy está en **modo de prueba** — usa la tarjeta `4242 4242 4242 4242`,
  cualquier fecha futura, cualquier CVC.

Comandos útiles mientras pruebas:

```bash
# Ver logs en vivo
docker compose logs -f web worker

# Reiniciar tomando cambios nuevos de .env
docker compose up -d --force-recreate web worker

# Volver a levantar todo si lo cerraste
docker compose up -d db redis web worker beat
```

## Cobertura

1. Registro y verificación de email obligatoria
2. Crear conexión (válida, inválida, host inseguro)
3. Límite de conexiones por plan
4. Diccionario de datos + diagrama ER
5. Chat en lenguaje natural
6. Exportar a Markdown
7. Historial de cambios de esquema (diffs)
8. Planes y pago (LemonSqueezy)
9. Aislamiento entre usuarios
10. Responsive / mobile
11. Documentación de la API (`/api/docs/`)
12. Seguridad — verificaciones no visibles en la UI

El detalle paso a paso de cada punto está en el checklist interactivo. Las
expectativas ("resultado esperado") son las mismas en ambos documentos — este
archivo es la copia de respaldo versionada en git.
