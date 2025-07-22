from django.core.management.base import BaseCommand
from django.db.models import Q
from typing import List

from products.models import Product, Price, BranchStock  # Import your models
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv
from products.models import Feature, Category, Brand  # for details
from django.core.exceptions import ObjectDoesNotExist
import logging
import datetime, time, pytz
from core.utils import calculate_mxn_price

last_results_ids = []  # Global for last search IDs
last_product_details = None  # Global for last product details

load_dotenv()  # Load .env file

SLP_SLUG = "san_luis_potosi"  # From your views.py

@tool
def search_products(query: str) -> list[dict]:
    """Search for products in the store database by keyword.
    Looks in title, model, description, and brand. Strips extra quotes/spaces from the query.
    Returns up to 5 matches with key info.
    """
    # ─── Sanitize query ───
    import re
    # Setup logging al inicio de handle, pero como es tool, usar global logger
    logger = logging.getLogger(__name__)
    # Remove quotes, parentheses and everything after first newline
    clean_q = query.splitlines()[0]
    clean_q = re.sub(r'["\'\(\)]', '', clean_q).strip()
    logger.debug(f"Raw user query after initial clean: '{clean_q}'")

    # Tokenize to keep only words and numbers
    tokens = re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", clean_q, flags=re.UNICODE)
    if not tokens:
        return [{"error": "Consulta vacía o no válida."}]

    logger.debug(f"Tokens extracted for filtering: {tokens}")

    # Construir filtro dinámico que coincida con cualquiera de los tokens
    q_obj = Q()
    for tok in tokens:
        q_obj |= Q(title__icontains=tok) | Q(model__icontains=tok) | Q(description__icontains=tok) | Q(brand__name__icontains=tok)

    products = (
        Product.objects.filter(q_obj)
        .filter(branch_stocks__branch__slug=SLP_SLUG, branch_stocks__quantity__gt=0)  # Solo con stock SLP > 0
        .select_related('brand')
        .prefetch_related('prices', 'branch_stocks', 'categories')
        .distinct()[:5]  # Evita duplicados y limita a 5
    )
    logger.debug(f"Found {products.count()} matching products")  # Log count

    results = []
    global last_results_ids
    temp_ids = []  # collect
    for idx, product in enumerate(products, start=1):
        # One-to-one relation: use getattr to avoid DoesNotExist
        try:
            price_obj = product.prices  # Price instance via OneToOne
        except Price.DoesNotExist:
            price_obj = None

        if price_obj:
            # Prefer discount, then special, then normal
            price_value = (
                calculate_mxn_price(price_obj, None)
            )
        else:
            price_value = "N/A"

        slp_stock = BranchStock.objects.filter(
            product=product, branch__slug=SLP_SLUG
        ).first().quantity if BranchStock.objects.filter(
            product=product, branch__slug=SLP_SLUG
        ).exists() else 0

        # Primer categoría (si existe)
        cat_name = product.categories.first().name if product.categories.exists() else "Sin categoría"

        results.append({
            "index": idx,
            "id": product.syscom_id,
            "title": product.title,
            "description": product.description[:200] + "..." if product.description else "No description",
            "brand": product.brand.name if product.brand else "Unknown",
            "category": cat_name,
            "price": price_value,
            "slp_stock": slp_stock,
            "total_stock": sum(stock.quantity for stock in product.branch_stocks.all()),
        })
        temp_ids.append(product.id)

    if results:
        last_results_ids = temp_ids  # update global only if found
    logger.debug(f"Stored IDs: {last_results_ids}")
    return results if results else [{"error": f"No products found for '{query}'"}]

# -----------------------------------------------------------------------------
# Tool: get_product_details
# -----------------------------------------------------------------------------

@tool
def get_product_details(index: str) -> dict:
    """Devuelve detalles completos del producto seleccionado por su número (1-5) de la última búsqueda.
    Incluye descripción completa, características, categorías, precio y existencias.
    Debe usarse cuando el usuario pida más información sobre un resultado previo.
    """
    import re

    global last_results_ids, last_product_details
    logger = logging.getLogger(__name__)
    logger.debug(f"last_results_ids length: {len(last_results_ids)} → {last_results_ids}")
    if not last_results_ids:
        return {"error": "Primero realiza una búsqueda de productos."}
    # Mejorado: Captura números en dígitos o palabras (uno a cinco, ya que limitamos a 5 resultados)
    word_to_num = {'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5}
    cleaned_index = re.sub(r'[^a-z0-9 ]', '', str(index).lower())  # Limpia y baja
    for word, num in word_to_num.items():
        if word in cleaned_index:
            idx = num
            break
    else:
        return {"error": "No se encontró un número válido (1-5 o en palabras) en la solicitud."}

    if idx < 1 or idx > len(last_results_ids):
        return {"error": f"Índice fuera de rango. Elige un número entre 1 y {len(last_results_ids)}."}

    prod_id = last_results_ids[idx - 1]
    try:
        product = Product.objects.select_related("brand").prefetch_related("features", "categories").get(id=prod_id)
    except Product.DoesNotExist:
        return {"error": "Producto no encontrado."}

    try:
        price_obj = product.prices
        price_value = calculate_mxn_price(price_obj, None)
    except Price.DoesNotExist:
        price_value = "N/A"

    features = [f.text for f in product.features.all()]
    categories = [c.name for c in product.categories.all()]

    slp_stock = BranchStock.objects.filter(product=product, branch__slug=SLP_SLUG).first()
    slp_qty = slp_stock.quantity if slp_stock else 0

    # --- Resumen de descripción usando DeepSeek ---
    summary = ""
    # Limpiar descripción completa para texto plano
    import bleach
    import warnings
    warnings.filterwarnings('ignore', category=bleach.sanitizer.NoCssSanitizerWarning)
    clean_desc = bleach.clean(product.description, strip=True, tags=[], attributes={})
    # Generar resumen solo si hay descripción
    if product.description:
        try:
            llm_sum = ChatOpenAI(
                model="deepseek-chat",
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com/v1",
                temperature=0.2,
                max_tokens=150,
            )
            prompt_msgs = [
                SystemMessage(content="Eres un asistente que resume descripciones de productos en español en máximo 4 oraciones."),
                HumanMessage(content=f"Resume brevemente la siguiente descripción de producto:\n{product.clean_description() if hasattr(product,'clean_description') else product.description}")
            ]
            summary = llm_sum.invoke(prompt_msgs).content.strip()
        except Exception as e:
            summary = "(No se pudo generar resumen)"

    details = {
        "title": product.title,
        "model": product.model,
        "brand": product.brand.name if product.brand else "Sin marca",
        "price": price_value,
        "stock_slp": slp_qty,
        "categories": categories,
        "features": features,
        "summary": summary,
        "description": clean_desc[:1000] + "..." if len(clean_desc) > 1000 else clean_desc,  # Acortar para legibilidad
    }
    last_product_details = details  # Store globally
    return details

# -----------------------------------------------------------------------------
# Memoria personalizada para incluir last_results como variable interna
# -----------------------------------------------------------------------------


class ConversationBufferMemoryWithResults(ConversationBufferMemory):
    """Extiende ConversationBufferMemory para considerar 'last_results' como parte de las
    variables de memoria, evitando el error cuando se pasa al agente junto con
    'input'."""

    @property
    def memory_variables(self) -> list[str]:  # type: ignore[override]
        # Añadimos 'last_results' a las variables de memoria para que no cuente
        # como un input separado y así cumplir la expectativa de una única key.
        return super().memory_variables + ["last_results"]


class Command(BaseCommand):
    help = 'Run a terminal-based agent for product search'

    def handle(self, *args, **options):
        global last_results_ids, last_product_details
        last_results_ids = []  # Reset global
        last_product_details = None  # Reset global
        # ─── Debug: Confirm DB connection and show basic info ───
        product_count = Product.objects.count()
        sample_titles = list(Product.objects.values_list('title', flat=True)[:5])
        # Configurar logging
        # Aseguramos crear siempre un FileHandler, aunque Django ya haya configurado logging
        log_filename = 'agent_terminal.log'
        root_logger = logging.getLogger()
        file_exists = any(isinstance(h, logging.FileHandler) and h.baseFilename.endswith(log_filename) for h in root_logger.handlers)

        class LocalTZFormatter(logging.Formatter):
            """Formatter que usa la zona horaria definida en env (APP_TIMEZONE) o America/Mexico_City."""

            def __init__(self, fmt=None, datefmt=None):
                super().__init__(fmt=fmt, datefmt=datefmt)
                tz_name = os.getenv("APP_TIMEZONE", "America/Mexico_City")
                try:
                    self._tzinfo = pytz.timezone(tz_name)
                except Exception:
                    self._tzinfo = pytz.timezone("America/Mexico_City")

            def converter(self, timestamp):
                return datetime.datetime.fromtimestamp(timestamp, tz=self._tzinfo).timetuple()

        log_fmt = '%(asctime)s %(levelname)s - %(message)s'
        date_fmt = '%Y-%m-%d %H:%M:%S %z'

        if not file_exists:
            file_handler = logging.FileHandler(log_filename)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(LocalTZFormatter(log_fmt, datefmt=date_fmt))
            root_logger.addHandler(file_handler)

        # Capturar DEBUG en archivo pero evitar que aparezca en consola
        root_logger.setLevel(logging.DEBUG)  # Necesario para que los DEBUG lleguen al file_handler
        for h in root_logger.handlers:
            # Elevar nivel de todos los manejadores que NO sean FileHandler a WARNING
            if not isinstance(h, logging.FileHandler):
                h.setLevel(logging.WARNING)
        logger = logging.getLogger(__name__)
        logger.debug(f"DB check → Products in DB: {product_count}. Sample: {', '.join(sample_titles) if sample_titles else 'No products'}")
        # Initialize DeepSeek LLM (using OpenAI-compatible API)
        llm = ChatOpenAI(
            model="deepseek-chat",  # Or your preferred DeepSeek model
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",  # DeepSeek API endpoint
            temperature=0,  # Set to 0 for strict adherence
            max_tokens=400,
            streaming=True,
        )

        # Memory for conversation context; incluye 'last_results' como memoria
        memory = ConversationBufferMemoryWithResults(memory_key="chat_history", input_key="input")

        # Define a custom ReAct prompt
        react_prompt = PromptTemplate.from_template(
            """Responde SIEMPRE en ESPAÑOL. Eres un asistente de catálogo para una tienda en línea.
            Cuando el usuario pregunte por productos:
            1. Usa search_products.
            2. Devuelve los resultados numerados del 1 al 5 (si hay) con título, marca, categorías, precio y stock SLP.
            3. Si el usuario pide más detalles de "el 2", "producto 5", "detalles del tres" o números en palabras (convierte 'cinco' a 5), llama get_product_details con ese número. En la respuesta, muestra solo un resumen corto + features clave, y pregunta '¿Quieres la descripción completa? Di sí o más'.
            4. Si el usuario dice 'si', 'sí' o 'más' después de ofrecer descripción completa, muestra DIRECTAMENTE la 'description' del último producto en un formato simple, usando la información de {last_product_details}. Usa Thought → Final Answer SIN Action, ya que no necesitas herramientas. Recuerda del historial.
            5. Si no hay búsqueda previa, pídele al usuario que busque primero.

            FORMATO estricto para el razonamiento de herramientas:
            
            You have access to the following tools:
 
            {tools}
 
            Use the following format EXACTLY. NO inventes Observations; el sistema las proporcionará. Después de escribir la línea "Action Input: ..." DEBES DETENERTE POR COMPLETO: no agregues texto, ni ejemplos, ni la palabra '(DETENTE)'. NO incluyas la palabra '(DETENTE)'. No continúes con Thought ni Final Answer hasta que el sistema envíe la Observation.

            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question

            Example of FIRST STEP (con herramienta):
            Thought: Debo buscar productos.
            Action: search_products
            Action Input: "routers mikrotik"
            [Aquí te detienes. El sistema llamará a la herramienta y te entregará "Observation: ..." en la siguiente interacción]

            Ejemplo de ÚLTIMO PASO (cuando ya tienes la info):
            Thought: Ya conozco la respuesta final.
            Final Answer: [lista numerada con título, marca, etc.]

            ¡Sigue ESTE formato EXACTAMENTE! Ni una palabra más ni menos.

            Historial de la conversación (para contexto):
            {chat_history}

            Últimos IDs de productos encontrados (para referencia numérica):
            {last_results}

            Últimos detalles de producto (para descripción completa):
            {last_product_details}
 
            ¡Comencemos!

            Question: {input}
            Thought: {agent_scratchpad}"""
        )

        # Create agent including both tools
        agent = create_react_agent(llm, tools=[search_products, get_product_details], prompt=react_prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=[search_products, get_product_details],
            memory=memory,
            verbose=False,  # Salida limpia para el usuario; logs van al archivo
            handle_parsing_errors=True,
            max_iterations=5,
        )

        self.stdout.write(self.style.SUCCESS("Agent ready! Type 'exit' to quit."))

        while True:
            user_input = input("¿Qué buscas hoy?: ").strip().lower()
            if user_input in ['exit', 'adios', 'salir', 'bye', 'hasta luego']:
                self.stdout.write(self.style.SUCCESS("¡Hasta luego! 👋"))
                break

            # Aviso al usuario antes de buscar
            self.stdout.write(self.style.NOTICE("Nota: Solo se mostrarán productos con existencia en la sucursal San Luis Potosí."))

            # Construir cadena con los últimos IDs o mensaje si no hay búsqueda previa
            last_results_str = ", ".join(str(pid) for pid in last_results_ids) if last_results_ids else "Sin búsquedas recientes"

            last_details_str = str(last_product_details) if last_product_details else "Ninguno"

            response = agent_executor.invoke({
                "input": user_input,
                "last_results": last_results_str,
                "last_product_details": last_details_str,
            })
            # Mostrar solo la respuesta final, sin prefijo ni datos de debug
            self.stdout.write(response['output'])
