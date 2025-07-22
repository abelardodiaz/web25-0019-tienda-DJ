from django.db.models import Q
from products.models import Product, Price, BranchStock, Feature, Category, Brand
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv
from django.core.exceptions import ObjectDoesNotExist
import logging
import re
import json
import bleach
import warnings
import pytz
from datetime import datetime
import pathlib
from functools import reduce
import operator
from django.core.cache import cache
from django.http import HttpRequest
import hashlib
from langchain.tools import Tool
from core.utils import calculate_mxn_price

load_dotenv()

# Setup file logger once
logger = logging.getLogger("agent_web")
if not any(isinstance(h, logging.FileHandler) and h.baseFilename.endswith("agent_web.log") for h in logger.handlers):
    log_path = pathlib.Path(__file__).resolve().parent / "agent_web.log"
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)

SLP_SLUG = "san_luis_potosi"

class ConversationBufferMemoryWithResults(ConversationBufferMemory):
    @property
    def memory_variables(self) -> list[str]:
        return super().memory_variables + ["last_results"]

def run_agent(request: HttpRequest, user_input: str) -> str:
    logger.debug(f"📥 Received input: '{user_input}'")
    
    # ─── Herramientas ───
    last_results_ids = request.session.get('last_search_ids', [])
    last_product_details = request.session.get('last_product_details', {})
    
    # ─── Tool: search_products (from agent_terminal) ───
    @tool
    def search_products(query: str) -> list:
        """Search for products in the store database by keyword."""
        logger = logging.getLogger(__name__)
        clean_q = query.splitlines()[0]
        clean_q = re.sub(r'["\'\(\)]', '', clean_q).strip()
        logger.debug(f"Raw user query after initial clean: '{clean_q}'")
        
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
            .filter(branch_stocks__branch__slug=SLP_SLUG, branch_stocks__quantity__gt=0)
            .select_related('brand')
            .prefetch_related('prices', 'branch_stocks', 'categories')
            .distinct()[:5]
        )
        logger.debug(f"Found {products.count()} matching products")
        
        results = []
        temp_ids = []
        for idx, product in enumerate(products, start=1):
            try:
                price_obj = product.prices
            except Price.DoesNotExist:
                price_obj = None
                
            if price_obj:
                price_value = calculate_mxn_price(price_obj, None)
            else:
                price_value = "N/A"
                
            slp_stock = BranchStock.objects.filter(
                product=product, branch__slug=SLP_SLUG
            ).first().quantity if BranchStock.objects.filter(
                product=product, branch__slug=SLP_SLUG
            ).exists() else 0
            
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
            request.session['last_search_ids'] = temp_ids
        logger.debug(f"Stored IDs: {temp_ids}")
        return results if results else [{"error": f"No products found for '{query}'"}]
    
    # ─── Tool: get_product_details (from agent_terminal) ───
    @tool
    def get_product_details(index: str) -> dict:
        """Devuelve detalles completos del producto seleccionado por su número (1-5) de la última búsqueda."""
        logger = logging.getLogger(__name__)
        last_results_ids = request.session.get('last_search_ids', [])
        if not last_results_ids:
            return {"error": "Primero realiza una búsqueda de productos."}
        
        word_to_num = {'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5}
        cleaned_index = re.sub(r'[^a-z0-9 ]', '', str(index).lower())
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
            raw_price = price_obj.discount or price_obj.special or price_obj.normal
            if raw_price is not None:
                price_value = float(calculate_mxn_price(price_obj, None))
            else:
                price_value = "N/A"
        except Price.DoesNotExist:
            price_value = "N/A"
            
        features = [f.text for f in product.features.all()]
        categories = [c.name for c in product.categories.all()]
        
        slp_stock = BranchStock.objects.filter(product=product, branch__slug=SLP_SLUG).first()
        slp_qty = slp_stock.quantity if slp_stock else 0
        
        summary = ""
        warnings.filterwarnings('ignore', category=bleach.sanitizer.NoCssSanitizerWarning)
        clean_desc = bleach.clean(product.description, strip=True, tags=[], attributes={})
        
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
            "description": clean_desc[:1000] + "..." if len(clean_desc) > 1000 else clean_desc,
        }
        request.session['last_product_details'] = details
        return details

    # ─── Agente LangChain (from agent_terminal) ───
    # Initialize DeepSeek LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        temperature=0,
        max_tokens=400,
        streaming=True,
    )

    # Memory for conversation context
    memory = ConversationBufferMemoryWithResults(
        memory_key="chat_history", 
        input_key="input",
        output_key="output"  # Explicitly set output key
    )
    
    # Get chat history from session
    chat_history_list = request.session.get('chat_history', [])
    for msg in chat_history_list:
        if msg['type'] == 'user':
            memory.chat_memory.add_user_message(msg['content'])
        else:
            memory.chat_memory.add_ai_message(msg['content'])
            
    # Use the proven prompt from agent_terminal
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
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=5,
        max_execution_time=60
    )

    # Build context for the agent
    last_results_str = ", ".join(str(pid) for pid in last_results_ids) if last_results_ids else "Sin búsquedas recientes"
    last_details_str = str(last_product_details) if last_product_details else "Ninguno"
    
    # Revert to proven working approach
    logger.debug(f"⏳ Iniciando agente para input: {user_input}")
    response = agent_executor.invoke({
        "input": user_input,
        "last_results": last_results_str,
        "last_product_details": last_details_str
    })
    logger.debug(f"✅ Respuesta agente: {response}")

    # Update session
    chat_history_list.append({'type': 'user', 'content': user_input})
    chat_history_list.append({'type': 'agent', 'content': response['output']})
    request.session['chat_history'] = chat_history_list
    logger.debug(f"USER: {user_input}")
    logger.debug(f"ASSISTANT: {response['output']}")

    return response['output'] 