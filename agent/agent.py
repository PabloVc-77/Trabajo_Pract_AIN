
from __future__ import annotations

try:
    # Newer docs often show this path.
    from google.adk.agents.llm_agent import Agent  # type: ignore
except Exception:  # pragma: no cover
    from google.adk.agents import Agent  # type: ignore


from google.adk.models.lite_llm import LiteLlm 

import datetime
import feedparser

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
def get_bibliografia(theme: str, max_results=6):

    from urllib.parse import quote_plus

    query = quote_plus(theme)
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"
    feed = feedparser.parse(url)

    resultados = []

    for entry in feed.entries:
        fecha = _parse_date(entry)

        if fecha is None:
            fecha = datetime.datetime(1,1,1)

        resultados.append({
            "titulo": entry.title,
            "autores": [a.name for a in entry.authors],
            "resumen": entry.summary[:1000],
            "url": entry.link,
            "fecha": fecha
        })

    resultados.sort(key=lambda x: x["fecha"], reverse=True)

    return resultados

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def get_salida(title: str, intro: str, state_art: str, 
               desarrollo: str, ejemplos: str, conclusiones: str, referencias: str):
    import json

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M::%S")
    pdf_path = f"salida_{timestamp}.pdf"
    json_path = f"salida_{timestamp}.json"

    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()
    story = []

    word_counter = [0, 0, 0, 0, 0, 0]
    segments = [("Introducción", intro), ("Estado del arte", state_art), ("Desarrollo", desarrollo), 
                ("Ejemplos", ejemplos), ("Conclusiones", conclusiones), ("Referencias", referencias)]

    #Titulo
    story.append(Paragraph(f"<b><font size=18>{title}</font></b>", styles["Heading1"]))
    story.append(Spacer(1, 12))

    i = 0
    for segment, texto in segments:
        story.append(Paragraph(f"<b><font size=14>{segment}</font></b>", styles["Heading2"]))
        story.append(Spacer(1, 12))
        for line in texto.split("\n"):
            line = line.strip()

            if not line:
                story.append(Spacer(1, 10))
                continue
            else:
                if i == 5:
                    word_counter[i] += 1
                else:
                    word_counter[i] += len(line.split())
                story.append(Paragraph(line, styles["Normal"]))
                story.append(Spacer(1, 8))
        
        i += 1

    doc.build(story)

    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "title": title,
            "sections": [
                {"section_name": segments[0][0], "word_count": word_counter[0]},
                {"section_name": segments[1][0], "word_count": word_counter[1]},
                {"section_name": segments[2][0], "word_count": word_counter[2]},
                {"section_name": segments[3][0], "word_count": word_counter[3]},
                {"section_name": segments[4][0], "word_count": word_counter[4]},
            ],
            "total_words": sum(word_counter) - word_counter[5],
            "num_sections": len([c for c in word_counter if c > 0]),
            "num_references": word_counter[5],
            "pdf_path": pdf_path
        }, f, ensure_ascii=False, indent=4)

    return {
        "pdf": pdf_path,
        "json": json_path
    }

# ---------------------------
# Root agent
# ---------------------------

root_agent = Agent(
    # Pick a model you have configured (Gemini via GOOGLE_API_KEY, or via Vertex).
    # You can also route via LiteLLM if your environment is set up that way.
    #model="gemini-3-flash-preview",
    model=LiteLlm(model="openai/gpt-oss-120b", api_base="https://api.poligpt.upv.es/", api_key="sk-LFXs1kjaSxtEDgOMlPUOpA"),

    name="root_agent",
    description=(
        "Diseñar un documento sobre el tema que se te plantee, con una salida sencilla de entender"
        "usando tools para fundamentar la respuesta."
    ),
    instruction=(
        "Eres un creador de documentos. SIEMPRE debes fundamentarte en herramientas.\n"
        "Pasos: (1) llama a get_bibliografia(tema) para obtener fuentes.\n"
        "(2) en base al abstract de las fuentes decide las que sean de interes respecto del tema a tratar (Elige hasta 4 fuentes)\n"
        "(3) Mezcla las fuentes para crear un texto por cada apartado de la estructura estructura.\n"
            "Introducción\n"
            "Estado del arte\n"
            "Desarrollo\n"
            "Ejemplos\n"
            "Conclusiones\n"
            "Referencias\n"
        "(4) llama a get_salida(título, intro, estado_arte, desarrollo, ejemplos, conclusiones, referencias) (siendo título el tema escogido y el resto de argumentos los apartados obtenidos del paso 3) para obtener el .pdf y .json.\n"
        "NO finalices la respuesta sin llamar a get_salida.\n"
        "(5) responde en español "
        "sin inventar información fuera de las fuentes."
    ),
    tools=[get_bibliografia, get_salida],
)
