       // Menú de usuario
        const userMenuBtn = document.getElementById('user-menu-btn');
        const userDropdown = document.getElementById('user-dropdown');
        
        userMenuBtn.addEventListener('click', () => {
            userDropdown.classList.toggle('active');
        });
        
        // Cerrar menú al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (!userMenuBtn.contains(e.target) && !userDropdown.contains(e.target)) {
                userDropdown.classList.remove('active');
            }
        });
        
        // Sistema de tabs
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Remover clase activa de todos los botones
                tabBtns.forEach(b => b.classList.remove('active', 'text-white', 'border-accent-500'));
                tabBtns.forEach(b => b.classList.add('text-gray-400', 'border-transparent'));
                
                // Añadir clase activa al botón seleccionado
                btn.classList.add('active', 'text-white', 'border-accent-500');
                btn.classList.remove('text-gray-400', 'border-transparent');
                
                // Ocultar todos los contenidos
                tabContents.forEach(content => content.classList.remove('active'));
                
                // Mostrar el contenido correspondiente
                const tabId = btn.getAttribute('data-tab');
                document.getElementById(tabId).classList.add('active');
            });
        });
        
        // Confirmación para reset completo
        const confirmReset = document.getElementById('confirm-reset');
        const fullResetBtn = document.getElementById('full-reset-btn');
        
        confirmReset.addEventListener('change', () => {
            fullResetBtn.disabled = !confirmReset.checked;
            fullResetBtn.classList.toggle('opacity-50', !confirmReset.checked);
            fullResetBtn.classList.toggle('opacity-100', confirmReset.checked);
        });
        
        // Simular acciones
        const saveBtns = document.querySelectorAll('button:not(#full-reset-btn)');
        const toast = document.getElementById('toast');
        
        saveBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.textContent.includes('Guardar') || btn.textContent.includes('Ejecutar')) {
                    toast.classList.remove('hidden');
                    setTimeout(() => {
                        toast.classList.add('hidden');
                    }, 2500);
                }
            });
        });
        
        // Reset completo
        fullResetBtn.addEventListener('click', () => {
            const toast = document.getElementById('toast');
            toast.querySelector('p.font-medium').textContent = '¡Reset completo iniciado!';
            toast.querySelector('p.text-sm').textContent = 'Todos los datos están siendo eliminados';
            toast.classList.remove('hidden');
            
            setTimeout(() => {
                toast.classList.add('hidden');
            }, 2500);
        });