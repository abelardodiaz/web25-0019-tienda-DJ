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
    button.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation(); // Prevent opening product detail
        
        const slug = button.dataset.slug;
        try {
            const csrftoken = getCookie('csrftoken');
            const response = await fetch(`/add-to-cart/${slug}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success) {
                // Update cart count
                const cartCountSpan = document.querySelector('#cart-toggle span');
                if (cartCountSpan) {
                    cartCountSpan.textContent = data.cart_count;
                    cartCountSpan.className = 'absolute -top-2 -right-2 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center';
                    cartCountSpan.classList.add(data.cart_count > 0 ? 'bg-red-500' : 'bg-gray-500');
                }
                
                // Show notification
                toast.classList.remove('hidden');
                toast.textContent = '¡Producto añadido al carrito!';
                setTimeout(() => toast.classList.add('hidden'), 2500);
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                // New: Update sidebar cart
                updateSidebarCart(data);
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            toast.classList.remove('hidden');
            toast.textContent = 'Error al añadir al carrito';
            toast.classList.add('bg-red-500');
            setTimeout(() => {
                toast.classList.add('hidden');
                toast.classList.remove('bg-red-500');
            }, 2500);
        }
    });
});

// Función para obtener el token CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    // Fallback: use global variable set server-side if cookie not present
    if (!cookieValue && window.CSRF_TOKEN) {
        cookieValue = window.CSRF_TOKEN;
    }
    return cookieValue;
}

// Añadir al carrito con AJAX
document.querySelectorAll('.add-to-cart:not(:disabled)').forEach(button => {
    button.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log('Click detected on add-to-cart button. Propagation stopped.');
        const originalContent = button.innerHTML; // Save original (e.g. + icon)
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; // Spinner
        const slug = button.dataset.slug;
        try {
            console.log('Attempting fetch to /add-to-cart/' + slug + '/');
            const csrftoken = getCookie('csrftoken');
            console.log('CSRF token:', csrftoken);
            const response = await fetch(`/add-to-cart/${slug}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                credentials: 'include'  // Added to ensure cookies are sent with the request
            });
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Response data:', data);
            if (data.success) {
                // Update cart count
                const cartCountSpan = document.querySelector('#cart-toggle span');
                if (cartCountSpan) {
                    cartCountSpan.textContent = data.cart_count;
                    cartCountSpan.className = 'absolute -top-2 -right-2 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center';
                    cartCountSpan.classList.add(data.cart_count > 0 ? 'bg-red-500' : 'bg-gray-500');
                }
                // Success toast
                toast.innerHTML = '<i class="fas fa-check mr-2"></i> ¡Producto añadido!';
                toast.classList.add('bg-green-500');
                toast.classList.remove('hidden');
                setTimeout(() => toast.classList.add('hidden'), 2500);
                
                // New: Update sidebar cart
                updateSidebarCart(data);
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            alert('Error al añadir: ' + error.message + '. Revisa consola.');
            toast.innerHTML = '<i class="fas fa-exclamation-triangle mr-2"></i> Error: ' + error.message;
            toast.classList.add('bg-red-500');
            toast.classList.remove('hidden');
            setTimeout(() => {
                toast.classList.add('hidden');
                toast.classList.remove('bg-red-500');
            }, 2500);
        } finally {
            button.disabled = false;
            button.innerHTML = originalContent; // Restore original content
        }
    });
});

// New function to update sidebar
function updateSidebarCart(data) {
    const itemsList = document.getElementById('cart-items-list');
    if (!itemsList) return;
    
    itemsList.innerHTML = '';
    
    if (data.cart_items.length === 0) {
        itemsList.innerHTML = '<p class="text-center text-gray-400">Tu carrito está vacío</p>';
    } else {
        data.cart_items.forEach(item => {
            const itemHTML = `
                <div class="flex items-center">
                    <img src="${item.image}" class="w-16 h-16 object-cover rounded mr-4" alt="${item.title}">
                    <div class="flex-1">
                        <p class="font-medium">${item.title}</p>
                        <p class="text-sm text-gray-400">${item.price.toLocaleString('es-MX', {minimumFractionDigits: 2, maximumFractionDigits: 2})} x ${item.qty}</p>
                    </div>
                    <p class="font-medium">${item.total.toLocaleString('es-MX', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
                </div>
            `;
            itemsList.innerHTML += itemHTML;
        });
    }
    
    document.getElementById('cart-count').textContent = data.cart_count;
    document.getElementById('cart-total').textContent = data.grand_total.toLocaleString('es-MX', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

// NUEVO: Vaciar carrito desde el sidebar
const cartEmptyBtn = document.getElementById('cart-empty');
if (cartEmptyBtn) {
    cartEmptyBtn.addEventListener('click', async () => {
        try {
            const csrftoken = getCookie('csrftoken');
            const response = await fetch('/update-cart/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrftoken
                },
                body: new URLSearchParams({ action: 'clear' })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (data.success) {
                // Actualizar recuento en el icono del carrito del header
                const cartCountSpan = document.querySelector('#cart-toggle span');
                if (cartCountSpan) {
                    cartCountSpan.textContent = '0';
                    cartCountSpan.classList.remove('bg-red-500');
                    cartCountSpan.classList.add('bg-gray-500');
                }
                // Actualizar recuento y total dentro del sidebar
                const cartCountEl = document.getElementById('cart-count');
                if (cartCountEl) cartCountEl.textContent = '0';
                const cartTotalEl = document.getElementById('cart-total');
                if (cartTotalEl) cartTotalEl.textContent = '0.00';
                // Vaciar lista de items
                const itemsList = document.getElementById('cart-items-list');
                if (itemsList) {
                    itemsList.innerHTML = '<p class="text-center text-gray-400">Tu carrito está vacío</p>';
                }
                // Mostrar toast
                if (toast) {
                    toast.textContent = '¡Carrito vaciado!';
                    toast.classList.remove('hidden');
                    setTimeout(() => toast.classList.add('hidden'), 2200);
                }
            }
        } catch (error) {
            console.error('Error clearing cart:', error);
            if (toast) {
                toast.textContent = 'Error al vaciar el carrito';
                toast.classList.add('bg-red-500');
                toast.classList.remove('hidden');
                setTimeout(() => {
                    toast.classList.add('hidden');
                    toast.classList.remove('bg-red-500');
                }, 2500);
            }
        }
    });
}

// Buscar y eliminar cualquier intervalo de rotación automática
document.querySelectorAll('.carousel').forEach(carousel => {
    const autoRotate = carousel.dataset.autoRotate;
    if (autoRotate === 'true') {
        clearInterval(parseInt(carousel.dataset.intervalId));
        carousel.removeAttribute('data-auto-rotate');
        carousel.removeAttribute('data-interval-id');
    }
});

// Attach instant search to multiple inputs (desktop + mobile)
document.addEventListener('DOMContentLoaded', function () {
    console.log('Instant search init');

    function setupInstantSearch(inputEl, resultsEl) {
        if (!inputEl || !resultsEl) return;

        let debounceTimer;
        resultsEl.style.display = 'none';

        inputEl.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            const query = this.value.trim();

            if (query.length === 0) {
                resultsEl.style.display = 'none';
                resultsEl.innerHTML = '';
                return;
            }

            if (query.length > 2) {
                debounceTimer = setTimeout(() => {
                    resultsEl.innerHTML = '<div class="p-4 text-center text-gray-400">Buscando productos...</div>';
                    resultsEl.style.display = 'block';

                    fetch(`/instant-search/?q=${encodeURIComponent(query)}`)
                        .then(r => {
                            if (!r.ok) throw new Error('Error ' + r.status);
                            return r.json();
                        })
                        .then(data => {
                            resultsEl.innerHTML = '';
                            if (data.results && data.results.length) {
                                data.results.forEach(prod => {
                                    const a = document.createElement('a');
                                    a.href = prod.url;
                                    a.className = 'instant-result-item flex justify-between items-center p-3 hover:bg-dark-700 border-b border-dark-700 last:border-0';
                                    a.innerHTML = `<span class="product-name font-medium text-gray-200">${prod.name}</span><span class="product-price text-sm text-accent-500 ml-4">${prod.price}</span>`;
                                    resultsEl.appendChild(a);
                                });
                            } else {
                                resultsEl.innerHTML = '<div class="p-4 text-center text-gray-400">No se encontraron productos</div>';
                            }
                        })
                        .catch(err => {
                            console.error('Instant search fetch error:', err);
                            resultsEl.innerHTML = '<div class="p-4 text-center text-red-400">Error: ' + err.message + '</div>';
                        });
                }, 300);
            } else {
                resultsEl.style.display = 'none';
            }
        });

        document.addEventListener('click', e => {
            if (!resultsEl.contains(e.target) && e.target !== inputEl) {
                resultsEl.style.display = 'none';
            }
        });
    }

    // Desktop selectors
    setupInstantSearch(
        document.getElementById('search-input'),
        document.getElementById('instant-results')
    );

    // Mobile selectors
    setupInstantSearch(
        document.getElementById('mobile-search-input'),
        document.getElementById('mobile-instant-results')
    );
});