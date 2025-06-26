// file: static/js/cat.js

// 1. DECLARACIÓN INICIAL DE VARIABLES GLOBALES
// --------------------------------------------
// Obtenemos todos los elementos necesarios una sola vez
const cartToggle = document.getElementById('cart-toggle');
const cartPanel = document.getElementById('cart-panel');
const cartClose = document.getElementById('cart-close');
const filterToggle = document.getElementById('filter-toggle');
const filterPanel = document.getElementById('filter-panel');
const filterClose = document.getElementById('filter-close');
const searchToggle = document.getElementById('search-toggle');
const searchPanel   = document.getElementById('mobile-search-panel');
const searchClose = document.getElementById('search-close');
const overlay = document.getElementById('overlay');
const toast = document.getElementById('toast');

// 2. FUNCIONES DE UTILIDAD (MODIFICADAS)
// ✅ BLOQUE MEJORADO  (fichero: static/js/cat.js)
// - Cambiamos la lógica para alternar las clases Tailwind
//   (-translate-x-full   ↔   translate-x-0)
// - Añadimos guard clausules por si panel es null
function openPanel(panel) {
    if (!panel) return;
    panel.classList.add('active', 'translate-x-0', 'translate-y-0');
    panel.classList.remove('-translate-x-full', 'translate-x-full',
                           '-translate-y-full', 'translate-y-full');
    overlay.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

function closePanel(panel) {
    if (!panel) return;
    panel.classList.remove('active', 'translate-x-0', 'translate-y-0');

    // Cada panel usa su propia clase “cerrado”
    if (panel.id === 'cart-panel') {
        panel.classList.add('translate-x-full');
    } else if (panel.id === 'filter-panel') {
        panel.classList.add('-translate-x-full');
    } else {                      // buscador móvil
        panel.classList.add('-translate-y-full');
    }
    overlay.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
}


// 3. EVENT LISTENERS
// ------------------
// Carrito
if (cartToggle && cartPanel) {
    cartToggle.addEventListener('click', () => openPanel(cartPanel));
}
if (cartClose && cartPanel) {     // cartClose puede ser null
    cartClose.addEventListener('click', () => closePanel(cartPanel));
}

// LISTENERS PARA FILTROS
// Comprobamos que los nodos existan antes de enganchar
if (filterToggle && filterPanel) {
    filterToggle.addEventListener('click', () => openPanel(filterPanel));
}
if (filterClose && filterPanel) {
    filterClose .addEventListener('click', () => closePanel(filterPanel));
}

// Búsqueda móvil
searchToggle.addEventListener('click', () => openPanel(searchPanel));
searchClose.addEventListener('click', () => closePanel(searchPanel));

// Overlay unificado
overlay.addEventListener('click', () => {
    // Cerrar todos los paneles
    document.querySelectorAll('.search-panel, .cart-panel, .filter-panel').forEach(panel => {
        closePanel(panel);
    });
});

// 4. SIMULACIÓN DE AÑADIR AL CARRITO
// ----------------------------------
const addButtons = document.querySelectorAll('.product-card button:last-child');
addButtons.forEach(button => {
    button.addEventListener('click', () => {
        toast.classList.remove('hidden');
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 2500);
    });
});