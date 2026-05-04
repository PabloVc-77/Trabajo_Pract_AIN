# Agente Generador de Informes Académicos

Trabajo universitario desarrollado con **Google Agent Development Kit (ADK)**. El agente recibe un tema, busca fuentes científicas reales y genera un informe académico estructurado en PDF y JSON.

## Cómo funciona

El agente sigue un flujo fijo de cinco pasos:

1. **Valida el tema** — si el usuario no especifica un tema, lo solicita antes de continuar.
2. **Recupera fuentes** — busca artículos en [ArXiv](https://arxiv.org) y, si hay pocos resultados, también en [Semantic Scholar](https://www.semanticscholar.org).
3. **Selecciona fuentes** — elige las 3-4 más relevantes.
4. **Redacta el informe** — genera en español las secciones: Introducción, Estado del arte, Desarrollo, Ejemplos, Conclusiones y Referencias.
5. **Genera los archivos** — produce un PDF y un JSON con metadatos (conteo de palabras por sección, número de referencias, etc.).

## Estructura del proyecto

```
trabajo_Pract_Ain/
├── agent/
│   ├── agent.py           # Agente principal y herramientas
│   ├── model_registry.py  # Registro del modelo LiteLLM personalizado
│   └── test_config.json   # Criterios de evaluación automática
└── Ejemplos_Resumenes/    # Informes generados de ejemplo
```

## Requisitos

- Python 3.10+
- `google-adk`
- `feedparser`
- `requests`
- `reportlab`

## Ejecución

```bash
cd agent
adk run .
```

El agente arranca en modo interactivo. Escribe el tema del informe y espera a que termine — los archivos se guardan en el directorio de trabajo.

## Ejemplo de salida (JSON)

```json
{
  "title": "Inteligencia Artificial en Medicina",
  "sections": [
    { "section_name": "Introducción", "word_count": 180 },
    { "section_name": "Estado del arte", "word_count": 210 },
    ...
  ],
  "total_words": 950,
  "num_sections": 5,
  "num_references": 4,
  "pdf_path": "Inteligencia-Artificial-en-Medicina_2026-04-22_12-44-04.pdf"
}
```
