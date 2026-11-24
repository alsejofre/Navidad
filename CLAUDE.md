# CLAUDE.md — Proyecto «navidad»

Regalo de Navidad para **Sara** (apodo: **Bitxo**). Dos apartados:

| Carpeta | Qué es |
|---|---|
| `adviento/` | **Principal.** Calendario de adviento web (1–24 de diciembre) publicado en GitHub Pages. |
| `taller-ascii/` | Laboratorio de código: dibujos ASCII, animaciones de terminal, conversor foto→ASCII y patio de pruebas. |

El usuario habla en castellano conmigo. **Todo lo que ve Sara está en catalán.**

---

## Decisiones tomadas (entrevista inicial, 23-11-2026)

- **Formato:** web estática en GitHub Pages, pensada primero para móvil (ella la abrirá en el móvil y la puede añadir a la pantalla de inicio).
- **Días:** 24 casillas (1–24 de diciembre de 2026). Cada casilla **solo se abre en su fecha o después**, en hora de `Europe/Madrid`. Los días pasados siguen abiertos.
- **Estilo:** Navidad acogedora: colores cálidos (rojo vino, verde abeto, crema, dorado), nieve suave cayendo y casillas con forma de regalo o puerta. Sin estridencias.
- **Tipos de contenido** (se mezclan a lo largo del mes):
  - `missatge`: mensaje de amor o recuerdo, con foto opcional.
  - `joc`: minijuego o reto (trivia sobre ellos, adivinanza, puzle, memory, sopa de letras...).
  - `cupo`: cupón canjeable («Val per...») que se guarda en la cartera.
  - `humor`: bromas internas, memes o dibujo ASCII gracioso.
- **Día 14 = cumpleaños de Sara.** Es el día más especial:
  - El regalo **aún no está decidido**. Todo lo relacionado con él va en el campo `regal` del contenido y debe poder cambiarse sin tocar código.
  - En los días anteriores (por defecto el **10, 12 y 13**, configurable) aparece una **pista** del regalo, con un diseño propio («Pista 1/3»).
  - El día 14 abre una pantalla de cumpleaños distinta del resto: celebración (confeti o velas que se soplan con un toque), mensaje largo y un cierre del tipo «La sorpresa final te la dono jo 🎁». **La web no revela el regalo:** lo entrega él en persona.
- **Extras elegidos:** cartera de cupones (`localStorage`, con botón «Bescanviar» y fecha de canje) y música y sonidos (villancico suave opcional con botón de silencio, y un sonido al abrir casilla; el audio solo empieza tras un toque, por las políticas de los navegadores).
- **Extras descartados por ahora:** cuenta atrás del cumpleaños y easter eggs. No añadirlos sin preguntar.
- **Contenido:** el usuario aporta ideas y recuerdos y **Claude redacta** los 24 días en catalán, con tono cariñoso, divertido y natural (nada cursi en exceso). Las ideas llegan a través de `ideas.plantilla.md`, que él rellena en `privado/ideas.md` o me pega en el chat.

## Privacidad: muy importante

El repositorio es **público** (requisito de GitHub Pages gratis), así que:

1. El contenido real de los días vive **solo** en `privado/` (en `.gitignore`). **Nunca hacer commit de texto, fotos ni ideas personales en claro.**
2. `herramientas/xifrar.mjs` cifra `privado/contingut.json` (y las fotos de `privado/fotos/`) y genera `adviento/contingut.enc.json`, que es lo único que se sube.
3. Cifrado: **AES-GCM 256** con clave derivada por **PBKDF2-SHA256** (≥ 250 000 iteraciones, salt aleatorio) a partir de la **respuesta a una pregunta personal**. Antes de derivar la clave, la respuesta se normaliza: minúsculas, sin acentos y sin espacios sobrantes.
4. La pregunta (no la respuesta) va en claro en `adviento/config.json`. La respuesta **nunca** se escribe en el repo ni en el código; el script la pide por terminal o por la variable `NAVIDAD_CLAU`.
5. Cuando ella acierta, la clave derivada se guarda en `localStorage` para no volver a pedirla.
6. El bloqueo por fecha es solo en el cliente (se puede saltar cambiando la hora del móvil). Se acepta; no hace falta más.
7. Antes de cada commit: `git status` y comprobar que no se cuela nada de `privado/`.

## Estructura

```
navidad/
├── CLAUDE.md
├── README.md
├── ideas.plantilla.md        # preguntas guiadas para recoger recuerdos (sin respuestas)
├── .gitignore                # incluye privado/
├── privado/                  # NO se sube
│   ├── contingut.json        # los 24 días en claro
│   ├── ideas.md              # respuestas del usuario
│   └── fotos/
├── herramientas/
│   └── xifrar.mjs            # cifra privado/ → adviento/contingut.enc.json
├── adviento/                 # raíz publicada en GitHub Pages
│   ├── index.html
│   ├── config.json           # pregunta, fechas, días de pista, zona horaria
│   ├── contingut.enc.json    # contenido cifrado (generado)
│   ├── contingut.exemple.json# ejemplo con contenido inventado, para desarrollo
│   ├── css/  js/  assets/audio/
├── taller-ascii/
│   ├── dibujos/              # arte ASCII .txt reutilizable en el calendario
│   ├── animaciones/          # animaciones de terminal (nieve, árbol, fuegos)
│   ├── conversor/            # foto → ASCII
│   └── patio/                # experimentos libres
└── .github/workflows/pages.yml  # despliega adviento/ en Pages
```

## Stack y convenciones

- **Calendario:** HTML, CSS y JavaScript sin framework ni bundler (módulos ES nativos). Solo Web Crypto para el cifrado y Web Audio o `<audio>` para el sonido. Dependencias externas, las mínimas: nada de CDNs de terceros si se puede evitar.
- **Herramientas:** Node ≥ 20 (`xifrar.mjs`, sin dependencias npm).
- **Taller ASCII:** Python 3 (Pillow para el conversor). Cada script se ejecuta solo y tiene una línea de uso al principio.
- Los dibujos de `taller-ascii/dibujos/` se pueden incrustar en los días de tipo `humor` o `missatge` (campo `ascii`), siempre en un bloque monoespaciado.
- Código e identificadores en catalán o en inglés (lo que salga natural); los textos visibles, **siempre en catalán**.
- Accesible y ligero: botones grandes, contraste suficiente, que funcione bien en un móvil antiguo y que respete `prefers-reduced-motion` (sin nieve ni confeti animados).
- Desarrollo local: `npx serve adviento` o `python3 -m http.server -d adviento`. En `localhost` existe un **modo prueba** (`?prova=1`) que ignora el bloqueo por fecha y carga `contingut.exemple.json`. En producción no debe funcionar.

## Formato de `contingut.json`

```json
{
  "regal": {
    "diesPista": [10, 12, 13],
    "pistes": ["Pista 1...", "Pista 2...", "Pista 3..."],
    "missatgeAniversari": "Text llarg del dia 14...",
    "tancament": "La sorpresa final te la dono jo 🎁"
  },
  "dies": {
    "1": { "tipus": "missatge", "titol": "...", "text": "...", "foto": "fotos/01.jpg" },
    "2": { "tipus": "cupo", "titol": "Val per...", "text": "...", "condicions": "..." },
    "3": { "tipus": "joc", "joc": "trivia", "preguntes": [ { "q": "...", "opcions": ["..."], "correcta": 0 } ], "premi": "..." },
    "4": { "tipus": "humor", "text": "...", "ascii": "dibujos/bitxo.txt" }
  }
}
```

Si un día tiene pista (`diesPista`), se muestra **además** de su contenido normal.

## Fechas clave

- Hoy: 23-11-2026. **Fecha límite para publicar: 30-11-2026** (el 1 de diciembre ella abre la primera casilla).
- Orden de trabajo: 1) estructura y web funcionando con el contenido de ejemplo → 2) cifrado y despliegue → 3) recogida de ideas y redacción de los 24 días → 4) taller ASCII (puede seguir creciendo en diciembre).

## Estado (24-11-2026)

- Web hecha y probada con Playwright en un móvil emulado: bloqueo, graella, juegos (trivia, endevinalla, memory), cupones y cartera, pistas, pantalla del 14 y música.
- `adviento/contingut.enc.json` contiene **el contenido de ejemplo cifrado con la clave de prueba «prova»**. Hay que sustituirlo por el real (`node herramientas/xifrar.mjs --nou-salt`) y cambiar la `pregunta` de `config.json` antes del 30-11.
- Probar en local: `python3 -m http.server -d adviento 8123` y abrir `http://localhost:8123/?prova=1&dia=14` (el parámetro `dia` simula la fecha).
- El workflow de Pages elimina `contingut.exemple.json` antes de publicar.

## Pendiente o abierto

- Decidir el **regalo** y escribir las 3 pistas.
- Definir la **pregunta personal** (la respuesta solo la sabe el usuario).
- Recoger ideas en `privado/ideas.md`.
- Elegir la música: tiene que ser libre de derechos o generada (nada con copyright).
- Crear el repo `alsejofre/navidad` en GitHub (no se pudo desde la sesión de Claude) y activar Pages con «GitHub Actions» como fuente.
