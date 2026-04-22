from __future__ import annotations

try:
    from google.adk.agents.llm_agent import Agent  # type: ignore
except Exception:  # pragma: no cover
    from google.adk.agents import Agent  # type: ignore

from google.adk.models.lite_llm import LiteLlm

import datetime
import feedparser
import requests

# --- Helpers ---
def _parse_date(entry):
    fecha_raw = entry.get("published") or entry.get("updated")

    if not fecha_raw:
        return None

    try:
        return datetime.datetime.strptime(fecha_raw, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        try:
            return datetime.datetime(*entry.published_parsed[:6])
        except Exception:
            return None


# --- Tools ---
def bibliografia1(theme: str, max_results: int = 4):
    """
    Busca artículos científicos recientes en ArXiv sobre el tema dado.
    Devuelve una lista de hasta max_results artículos con título, autores, resumen (máx 500 chars), URL y fecha.
    Úsala SIEMPRE como primera fuente bibliográfica.
    """

    from urllib.parse import quote_plus

    query = quote_plus(theme)
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"
    feed = feedparser.parse(url)

    resultados = []

    for entry in feed.entries:
        fecha = _parse_date(entry)

        if fecha is None:
            fecha = datetime.datetime(1, 1, 1)

        resultados.append({
            "titulo": entry.title,
            "autores": [a.name for a in entry.authors[:3]], 
            "resumen": entry.summary[:500],                  
            "url": entry.link,
            "fecha": fecha.strftime("%Y-%m-%d") if fecha.year > 1 else "desconocida",
        })

    resultados.sort(key=lambda x: x["fecha"], reverse=True)

    return resultados


def bibliografia2(theme: str, max_results: int = 4):
    """
    Busca artículos científicos en Semantic Scholar sobre el tema dado.
    Devuelve una lista de hasta max_results artículos con título, autores, año, resumen (máx 500 chars), URL y citas.
    Úsala SOLO si bibliografia1 devuelve menos de 3 resultados relevantes.
    """

    url = "https://api.semanticscholar.org/graph/v1/paper/search"

    params = {
        "query": theme,
        "limit": max_results,
        "fields": "title,authors,year,abstract,url,citationCount"
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return {"error": "Error en la API de Semantic Scholar"}

    data = response.json()

    resultados = []

    for paper in data.get("data", []):
        abstract = paper.get("abstract") or ""
        resultados.append({
            "titulo": paper.get("title"),
            "autores": [a["name"] for a in paper.get("authors", [])[:3]],
            "año": paper.get("year"),
            "resumen": abstract[:500],                                       
            "url": paper.get("url"),
            "citas": paper.get("citationCount", 0)
        })

    resultados.sort(key=lambda x: x.get("año") or 0, reverse=True)

    return resultados


from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def salida(title: str, intro: str, state_art: str,
           desarrollo: str, ejemplos: str, conclusiones: str, referencias: str):
    """
    Genera el PDF y el JSON del informe a partir del contenido redactado.
    DEBE llamarse obligatoriamente al final, con el texto de cada sección ya redactado.
    Devuelve un objeto JSON con metadatos del documento generado.
    """

    import json

    slug = title.replace(' ', '-')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_path = f"{slug}_{timestamp}.pdf"
    json_path = f"{slug}_{timestamp}.json"

    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()
    story = []

    word_counter = [0, 0, 0, 0, 0, 0]
    segments = [
        ("Introducción", intro),
        ("Estado del arte", state_art),
        ("Desarrollo", desarrollo),
        ("Ejemplos", ejemplos),
        ("Conclusiones", conclusiones),
        ("Referencias", referencias),
    ]

    # Título
    story.append(Paragraph(f"<b><font size=18>{title}</font></b>", styles["Heading1"]))
    story.append(Spacer(1, 12))

    for i, (segment, texto) in enumerate(segments):
        story.append(Paragraph(f"<b><font size=14>{segment}</font></b>", styles["Heading2"]))
        story.append(Spacer(1, 12))
        for line in texto.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 10))
                continue
            if i == 5:
                word_counter[i] += 1
            else:
                word_counter[i] += len(line.split())
            story.append(Paragraph(line, styles["Normal"]))
            story.append(Spacer(1, 8))

    doc.build(story)

    data = {
        "title": title,
        "sections": [
            {"section_name": segments[0][0], "word_count": word_counter[0]},
            {"section_name": segments[1][0], "word_count": word_counter[1]},
            {"section_name": segments[2][0], "word_count": word_counter[2]},
            {"section_name": segments[3][0], "word_count": word_counter[3]},
            {"section_name": segments[4][0], "word_count": word_counter[4]},
        ],
        "total_words": sum(word_counter) - word_counter[5],
        "num_sections": len([c for c in word_counter[:5] if c > 0]),
        "num_references": word_counter[5],
        "pdf_path": pdf_path,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return data


# ---------------------------
# Root agent
# ---------------------------

root_agent = Agent(
    model=LiteLlm(model="openai/gpt-oss-120b", api_base="https://api.poligpt.upv.es/", api_key="sk-LFXs1kjaSxtEDgOMlPUOpA"),

    name="root_agent",
    description=(
        "Agente que genera informes académicos estructurados en PDF y JSON "
        "a partir de fuentes científicas reales, usando exclusivamente las tools disponibles."
    ),
    instruction=(
        "Eres un redactor de informes académicos. Genera un informe estructurado "
        "siguiendo este flujo OBLIGATORIO. No inventes información: usa solo los abstracts recuperados.\n\n"

        "REGLAS:\n"
        "- Nombres de tools exactos: `bibliografia1`, `bibliografia2`, `salida`.\n"
        "- No uses ningún otro nombre.\n"
        "- Responde siempre en español.\n\n"

        "PASO 0 — VALIDAR TEMA\n"
        "Antes de cualquier otra acción, identifica el tema del informe en el mensaje del usuario. "
        "Si el mensaje NO especifica un tema concreto (por ejemplo: 'Haz un informe.', 'Genera un documento.', etc.), "
        "responde ÚNICAMENTE con esta pregunta y detente: "
        "'¿Sobre qué tema deseas que genere el informe académico?'. "
        "No llames a ninguna tool hasta recibir un tema claro.\n\n"

        "PASO 1 — RECUPERAR FUENTES\n"
        "Llama a bibliografia1(tema). "
        "Solo si obtienes menos de 3 resultados relevantes, llama también a bibliografia2(tema). "
        "Máximo 2 llamadas en total.\n\n"

        "PASO 2 — SELECCIONAR FUENTES\n"
        "Elige 3 o 4 fuentes cuyo resumen sea relevante para el tema. Descarta el resto.\n\n"

        "PASO 3 — REDACTAR SECCIONES\n"
        "Con los abstracts seleccionados, redacta en español cada sección. "
        "Cada sección (excepto Referencias) debe tener al menos 150 palabras:\n"
        "- Introducción: contextualiza el tema.\n"
        "- Estado del arte: conocimiento actual según las fuentes.\n"
        "- Desarrollo: conceptos, métodos y hallazgos clave.\n"
        "- Ejemplos: aplicaciones o casos concretos de las fuentes.\n"
        "- Conclusiones: puntos clave y perspectivas futuras.\n"
        "- Referencias: una línea por fuente con formato 'Autor(es) (Año). Título. URL'.\n\n"

        "PASO 4 — LLAMAR A salida (OBLIGATORIO)\n"
        "Llama a salida(title, intro, state_art, desarrollo, ejemplos, conclusiones, referencias) "
        "con el texto redactado. SIN esta llamada la tarea es incorrecta.\n\n"

        "PASO 5 — RESPUESTA FINAL\n"
        "Responde ÚNICAMENTE con el JSON devuelto por salida. Sin texto adicional.\n\n"
    ),
    tools=[bibliografia1, bibliografia2, salida],
)