# Brief Generation Skill

## Purpose
Generate a content brief JSON without using an AI API. The user provides context, and you output the same JSON that an agent would produce.

## Input Context

Provide the following information:
- **Topic**: What the video is about
- **Platforms**: youtube_lf, shorts, reels, tiktok (list)
- **Goal**: educativo, entretenimiento, tutorial, review
- **Tone**: directo y pratico, amigable, profesional, casual
- **CTA**: Call to action (e.g., "Suscribete")
- **Duration**: Estimated duration in minutes

## Output Format

Generate a JSON file with this structure:

```json
{
  "titles": ["title 1", "title 2", "title 3", "title 4", "title 5"],
  "hooks": [
    {"text": "hook text", "type": "pregunta|estadistica|afirmacion|historia", "energy": "alta|media"}
  ],
  "thumbnail_concept": {
    "texto_principal": "max 4 words",
    "subtexto": "max 6 words",
    "emocion": "curious|excited|serious|happy",
    "colores": ["color1", "color2"],
    "composicion": "cara_izquierda|cara_derecha|cara_centro|sin_cara"
  },
  "scene_outline": [
    {"id": 0, "titulo": "intro", "descripcion": "description", "duracion_s": 10}
  ],
  "broll_ideas": ["idea 1", "idea 2", "idea 3", "idea 4", "idea 5"],
  "motion_style": "energetico|limpio|cinematico",
  "retention_notes": ["note 1", "note 2", "note 3"],
  "hook_timestamp_target_s": 3,
  "export_targets": ["youtube_lf", "shorts"]
}
```

## Guidelines

### Titles (Spanish, SEO-optimized)
- Include numbers when applicable ("5 Trucos", "3 Razones")
- Use power words: Increible, Secreto, Definitivo, Oculto
- Keep under 60 characters
- Make specific to the topic

### Hooks
Generate 5 hooks:
- 2 preguntas (questions) - engage curiosity
- 1 estadistica (statistic) - build credibility
- 1 afirmacion (statement) - strong opinion
- 1 historia (story) - personal connection

### Scene Outline
- Estimate 3-5 scenes based on duration
- Include: intro, main content (3-4 points), conclusion
- Durations should add up to ~target duration

### B-Roll Ideas
- Screen recording moments
- Transitions
- Visual demonstrations
- Graphics/text overlays

### Thumbnail Concept
- Face-centered if presenter is key
- High contrast colors
- Minimal text
- Emotional expression matching content

## Example

**Input:**
- Topic: "5 Trucos de Python que no conocías"
- Goal: educativo
- Tone: directo y pratico
- Duration: 12 min

**Output:**
```json
{
  "titles": [
    "5 Trucos de Python que Cambiarán tu Código",
    "Python Definitivo: 5 Tricks que Debes Conocer",
    "Los Mejores Trucos de Python en Español",
    "Domina Python con Estos 5 Atajos",
    "Mejora tu Código: 5 Secrets de Python"
  ],
  "hooks": [
    {"text": "¿Sabías que Python tiene estas funciones ocultas?", "type": "pregunta", "energy": "alta"},
    {"text": "El 90% de desarrolladores no conoce este truco", "type": "estadistica", "energy": "alta"},
    {"text": "Este truco de Python me ahorró 100 horas", "type": "historia", "energy": "media"},
    {"text": "El error más común en Python y cómo evitarlo", "type": "afirmacion", "energy": "media"},
    {"text": "¿Qué son los walrus operators?", "type": "pregunta", "energy": "alta"}
  ],
  "thumbnail_concept": {
    "texto_principal": "5 TRUCOS",
    "subtexto": "PYTHON",
    "emocion": "excited",
    "colores": ["amarillo", "negro"],
    "composicion": "cara_centro"
  },
  "scene_outline": [
    {"id": 0, "titulo": "Intro", "descripcion": "Hook + presentación del tema", "duracion_s": 15},
    {"id": 1, "titulo": "Truco 1", "descripcion": "Walrus operator", "duracion_s": 120},
    {"id": 2, "titulo": "Truco 2", "descripcion": "List comprehensions avanzadas", "duracion_s": 120},
    {"id": 3, "titulo": "Truco 3", "descripcion": "enumerate con start", "duracion_s": 120},
    {"id": 4, "titulo": "Truco 4", "descripcion": "zip y unpacking", "duracion_s": 120},
    {"id": 5, "titulo": "Truco 5", "descripcion": "get con default", "duracion_s": 120},
    {"id": 6, "titulo": "Cierre", "descripcion": "Resumen + CTA", "duracion_s": 30}
  ],
  "broll_ideas": [
    "Pantalla con código VS Code",
    "Animación de terminal",
    "Gráfico de rendimiento",
    "Transiciones con código",
    "Pantalla de error comunes"
  ],
  "motion_style": "limpio",
  "retention_notes": [
    "Hook fuerte en 3 segundos",
    "Transiciones rapidas entre trucos",
    "Ejemplos visuales claros"
  ],
  "hook_timestamp_target_s": 3,
  "export_targets": ["youtube_lf", "shorts"]
}
```
