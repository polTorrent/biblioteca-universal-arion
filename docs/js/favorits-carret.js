/**
 * ═══════════════════════════════════════════════════════════════════
 * FAVORITS I CARRET - Biblioteca Universal Arion
 * Sistema de favorits (cors) i carret de mecenatge
 * ═══════════════════════════════════════════════════════════════════
 */

(function() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────
    // CONSTANTS
    // ─────────────────────────────────────────────────────────────────

    const STORAGE_KEYS = {
        FAVORITS: 'arion_favorits',
        CARRET: 'arion_carret'
    };

    // ─────────────────────────────────────────────────────────────────
    // GESTOR DE FAVORITS
    // ─────────────────────────────────────────────────────────────────

    const FavoritsManager = {
        _cache: null,

        /**
         * Obté tots els favorits de l'usuari
         */
        async getAll() {
            if (window.ArionSupabase?.isAvailable() && window.ArionAuth?.isLoggedIn()) {
                const userId = window.ArionAuth.getCurrentUser()?.id;
                const { data, error } = await window.ArionSupabase.query('favorits', {
                    eq: { usuari_id: userId },
                    order: { column: 'afegit_el', ascending: false }
                });
                if (!error) {
                    this._cache = data || [];
                    return this._cache;
                }
            }

            // Fallback localStorage
            return this._getFromLocalStorage();
        },

        /**
         * Comprova si una obra és favorita
         */
        async isFavorit(obraId) {
            const favorits = await this.getAll();
            return favorits.some(f => f.obra_id === obraId);
        },

        /**
         * Afegeix una obra als favorits
         */
        async add(obra) {
            if (!window.ArionAuth?.isLoggedIn()) {
                window.ArionMecenatge?.Toast.show('Has d\'iniciar sessió per guardar favorits', 'info');
                return { error: { message: 'No autenticat' } };
            }

            const favorit = {
                obra_id: obra.id || obra.obra_id,
                obra_titol: obra.titol || obra.obra_titol,
                obra_autor: obra.autor || obra.obra_autor
            };

            if (window.ArionSupabase?.isAvailable()) {
                const userId = window.ArionAuth.getCurrentUser()?.id;
                const { data, error } = await window.ArionSupabase.insert('favorits', {
                    usuari_id: userId,
                    ...favorit
                });

                if (error) {
                    if (error.code === '23505') { // Duplicate
                        return { error: { message: 'Ja tens aquesta obra als favorits' } };
                    }
                    return { data: null, error };
                }

                this._cache = null; // Invalidar cache
                this._notifyChange();
                return { data, error: null };
            }

            // Fallback localStorage
            return this._addToLocalStorage(favorit);
        },

        /**
         * Elimina una obra dels favorits
         */
        async remove(obraId) {
            if (window.ArionSupabase?.isAvailable() && window.ArionAuth?.isLoggedIn()) {
                const userId = window.ArionAuth.getCurrentUser()?.id;
                const { error } = await window.ArionSupabase.remove('favorits', {
                    usuari_id: userId,
                    obra_id: obraId
                });

                if (!error) {
                    this._cache = null;
                    this._notifyChange();
                }
                return { error };
            }

            // Fallback localStorage
            return this._removeFromLocalStorage(obraId);
        },

        /**
         * Toggle favorit
         */
        async toggle(obra) {
            const obraId = obra.id || obra.obra_id;
            const esFavorit = await this.isFavorit(obraId);

            if (esFavorit) {
                const result = await this.remove(obraId);
                if (!result.error) {
                    window.ArionMecenatge?.Toast.show('Eliminat dels favorits', 'info');
                }
                return { added: false, ...result };
            } else {
                const result = await this.add(obra);
                if (!result.error) {
                    window.ArionMecenatge?.Toast.show('Afegit als favorits', 'success');
                }
                return { added: true, ...result };
            }
        },

        /**
         * Obté el nombre de favorits
         */
        async getCount() {
            const favorits = await this.getAll();
            return favorits.length;
        },

        // ─── LocalStorage helpers ───

        _getFromLocalStorage() {
            try {
                const data = localStorage.getItem(STORAGE_KEYS.FAVORITS);
                return data ? JSON.parse(data) : [];
            } catch {
                return [];
            }
        },

        _addToLocalStorage(favorit) {
            const favorits = this._getFromLocalStorage();
            if (favorits.some(f => f.obra_id === favorit.obra_id)) {
                return { error: { message: 'Ja existeix' } };
            }
            favorits.unshift({
                ...favorit,
                id: 'fav_' + Date.now(),
                afegit_el: new Date().toISOString()
            });
            localStorage.setItem(STORAGE_KEYS.FAVORITS, JSON.stringify(favorits));
            this._notifyChange();
            return { data: favorit, error: null };
        },

        _removeFromLocalStorage(obraId) {
            let favorits = this._getFromLocalStorage();
            favorits = favorits.filter(f => f.obra_id !== obraId);
            localStorage.setItem(STORAGE_KEYS.FAVORITS, JSON.stringify(favorits));
            this._notifyChange();
            return { error: null };
        },

        _notifyChange() {
            window.dispatchEvent(new CustomEvent('favorits-changed'));
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // GESTOR DE CARRET
    // ─────────────────────────────────────────────────────────────────

    const CarretManager = {
        _cache: null,

        /**
         * Obté tots els items del carret
         */
        async getAll() {
            if (window.ArionSupabase?.isAvailable() && window.ArionAuth?.isLoggedIn()) {
                const userId = window.ArionAuth.getCurrentUser()?.id;
                const { data, error } = await window.ArionSupabase.query('carret', {
                    eq: { usuari_id: userId },
                    order: { column: 'afegit_el', ascending: false }
                });
                if (!error) {
                    this._cache = data || [];
                    return this._cache;
                }
            }

            // Fallback localStorage
            return this._getFromLocalStorage();
        },

        /**
         * Afegeix una obra al carret
         */
        async add(obra, importValue) {
            if (!window.ArionAuth?.isLoggedIn()) {
                // Guardar al localStorage i redirigir a login
                this._addToLocalStorage(obra, importValue);
                return { data: obra, error: null, needsLogin: true };
            }

            const item = {
                obra_id: obra.id || obra.obra_id,
                obra_titol: obra.titol || obra.obra_titol,
                obra_autor: obra.autor || obra.obra_autor,
                import: importValue,
                tipus: obra.tipus || 'micromecenatge'
            };

            if (window.ArionSupabase?.isAvailable()) {
                const userId = window.ArionAuth.getCurrentUser()?.id;

                // Verificar si ja existeix i actualitzar
                const { data: existing } = await window.ArionSupabase.query('carret', {
                    eq: { usuari_id: userId, obra_id: item.obra_id },
                    single: true
                });

                if (existing) {
                    // Actualitzar import
                    const { data, error } = await window.ArionSupabase.update('carret', {
                        import: item.import
                    }, { id: existing.id }, { single: true, select: '*' });

                    if (!error) {
                        this._cache = null;
                        this._notifyChange();
                    }
                    return { data, error };
                }

                // Inserir nou
                const { data, error } = await window.ArionSupabase.insert('carret', {
                    usuari_id: userId,
                    ...item
                }, { single: true, select: '*' });

                if (!error) {
                    this._cache = null;
                    this._notifyChange();
                }
                return { data, error };
            }

            // Fallback localStorage
            return this._addToLocalStorage(obra, importValue);
        },

        /**
         * Actualitza l'import d'un item
         */
        async updateImport(itemId, newImport) {
            if (window.ArionSupabase?.isAvailable() && window.ArionAuth?.isLoggedIn()) {
                const { data, error } = await window.ArionSupabase.update('carret', {
                    import: newImport
                }, { id: itemId });

                if (!error) {
                    this._cache = null;
                    this._notifyChange();
                }
                return { data, error };
            }

            // Fallback localStorage
            return this._updateLocalStorage(itemId, newImport);
        },

        /**
         * Elimina un item del carret
         */
        async remove(itemId) {
            if (window.ArionSupabase?.isAvailable() && window.ArionAuth?.isLoggedIn()) {
                const { error } = await window.ArionSupabase.remove('carret', { id: itemId });

                if (!error) {
                    this._cache = null;
                    this._notifyChange();
                }
                return { error };
            }

            // Fallback localStorage
            return this._removeFromLocalStorage(itemId);
        },

        /**
         * Buida tot el carret
         */
        async clear() {
            if (window.ArionSupabase?.isAvailable() && window.ArionAuth?.isLoggedIn()) {
                const userId = window.ArionAuth.getCurrentUser()?.id;
                const { error } = await window.ArionSupabase.remove('carret', {
                    usuari_id: userId
                });

                if (!error) {
                    this._cache = null;
                    this._notifyChange();
                }
                return { error };
            }

            // Fallback localStorage
            localStorage.removeItem(STORAGE_KEYS.CARRET);
            this._notifyChange();
            return { error: null };
        },

        /**
         * Obté el total del carret
         */
        async getTotal() {
            const items = await this.getAll();
            return items.reduce((sum, item) => sum + (parseFloat(item.import) || 0), 0);
        },

        /**
         * Obté el nombre d'items
         */
        async getCount() {
            const items = await this.getAll();
            return items.length;
        },

        /**
         * Processa el pagament de tot el carret
         */
        async checkout() {
            const items = await this.getAll();
            if (items.length === 0) {
                return { error: { message: 'El carret és buit' } };
            }

            const results = [];
            for (const item of items) {
                // Crear mecenatge per cada item
                const result = await window.ArionAuth?.addMecenatge(
                    item.obra_id,
                    item.obra_titol,
                    parseFloat(item.import)
                );
                results.push(result);
            }

            // Buidar carret
            await this.clear();

            return { data: results, error: null };
        },

        // ─── LocalStorage helpers ───

        _getFromLocalStorage() {
            try {
                const data = localStorage.getItem(STORAGE_KEYS.CARRET);
                return data ? JSON.parse(data) : [];
            } catch {
                return [];
            }
        },

        _addToLocalStorage(obra, importValue) {
            let items = this._getFromLocalStorage();
            const obraId = obra.id || obra.obra_id;

            // Actualitzar si existeix
            const existingIndex = items.findIndex(i => i.obra_id === obraId);
            if (existingIndex !== -1) {
                items[existingIndex].import = importValue;
            } else {
                items.unshift({
                    id: 'cart_' + Date.now(),
                    obra_id: obraId,
                    obra_titol: obra.titol || obra.obra_titol,
                    obra_autor: obra.autor || obra.obra_autor,
                    import: importValue,
                    tipus: obra.tipus || 'micromecenatge',
                    afegit_el: new Date().toISOString()
                });
            }

            localStorage.setItem(STORAGE_KEYS.CARRET, JSON.stringify(items));
            this._notifyChange();
            return { data: items[0], error: null };
        },

        _updateLocalStorage(itemId, newImport) {
            let items = this._getFromLocalStorage();
            const index = items.findIndex(i => i.id === itemId);
            if (index !== -1) {
                items[index].import = newImport;
                localStorage.setItem(STORAGE_KEYS.CARRET, JSON.stringify(items));
                this._notifyChange();
            }
            return { error: null };
        },

        _removeFromLocalStorage(itemId) {
            let items = this._getFromLocalStorage();
            items = items.filter(i => i.id !== itemId);
            localStorage.setItem(STORAGE_KEYS.CARRET, JSON.stringify(items));
            this._notifyChange();
            return { error: null };
        },

        _notifyChange() {
            window.dispatchEvent(new CustomEvent('carret-changed'));
            this._updateBadge();
        },

        _updateBadge() {
            this.getCount().then(count => {
                const badges = document.querySelectorAll('.carret-badge');
                badges.forEach(badge => {
                    badge.textContent = count;
                    badge.style.display = count > 0 ? 'flex' : 'none';
                });
            });
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // UI COMPONENTS
    // ─────────────────────────────────────────────────────────────────

    const FavoritsCarretUI = {
        /**
         * Renderitza el botó de favorit per una obra
         */
        renderFavoritButton(obra, isFavorit = false) {
            const obraId = obra.id || obra.obra_id;
            return `
                <button class="btn-favorit ${isFavorit ? 'active' : ''}"
                        data-obra-id="${obraId}"
                        data-obra-titol="${obra.titol || obra.obra_titol || ''}"
                        data-obra-autor="${obra.autor || obra.obra_autor || ''}"
                        title="${isFavorit ? 'Eliminar dels favorits' : 'Afegir als favorits'}">
                    <span class="favorit-icon">${isFavorit ? '❤️' : '🤍'}</span>
                </button>
            `;
        },

        /**
         * Renderitza la llista de favorits al perfil
         */
        renderFavoritsLlista(favorits) {
            if (!favorits || favorits.length === 0) {
                return `
                    <div class="empty-state">
                        <div class="empty-icon">🤍</div>
                        <h3>No tens cap favorit</h3>
                        <p>Explora el catàleg i marca les obres que t'interessin.</p>
                        <a href="index.html" class="btn-submit">Veure catàleg</a>
                    </div>
                `;
            }

            return `
                <div class="favorits-list">
                    ${favorits.map(fav => `
                        <div class="favorit-item" data-obra-id="${fav.obra_id}">
                            <div class="favorit-icon">📖</div>
                            <div class="favorit-info">
                                <span class="favorit-titol">${fav.obra_titol || 'Obra'}</span>
                                ${fav.obra_autor ? `<span class="favorit-autor">${fav.obra_autor}</span>` : ''}
                            </div>
                            <div class="favorit-actions">
                                <a href="${fav.obra_id}.html" class="btn-veure-mini">Veure</a>
                                <button class="btn-remove-favorit" data-obra-id="${fav.obra_id}" title="Eliminar">
                                    <span>✕</span>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        },

        /**
         * Renderitza el mini carret a la capçalera
         */
        renderMiniCarret() {
            return `
                <div class="mini-carret" id="mini-carret">
                    <button class="btn-carret" id="btn-toggle-carret" title="Carret de mecenatge">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="9" cy="21" r="1"></circle>
                            <circle cx="20" cy="21" r="1"></circle>
                            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                        </svg>
                        <span class="carret-badge" style="display: none;">0</span>
                    </button>
                    <div class="carret-dropdown" id="carret-dropdown" style="display: none;">
                        <div class="carret-header">
                            <h4>Carret de mecenatge</h4>
                            <button class="btn-close-carret" id="btn-close-carret">✕</button>
                        </div>
                        <div class="carret-items" id="carret-items">
                            <!-- Items renderitzats dinàmicament -->
                        </div>
                        <div class="carret-footer" id="carret-footer">
                            <!-- Total i botó de pagament -->
                        </div>
                    </div>
                </div>
            `;
        },

        /**
         * Renderitza els items del carret dropdown
         */
        renderCarretItems(items) {
            if (!items || items.length === 0) {
                return `
                    <div class="carret-empty">
                        <span>El carret és buit</span>
                        <a href="mecenatge.html">Veure projectes</a>
                    </div>
                `;
            }

            return items.map(item => `
                <div class="carret-item" data-item-id="${item.id}">
                    <div class="carret-item-info">
                        <span class="carret-item-titol">${item.obra_titol}</span>
                        <span class="carret-item-import">${parseFloat(item.import).toFixed(2)}€</span>
                    </div>
                    <button class="btn-remove-item" data-item-id="${item.id}" title="Eliminar">✕</button>
                </div>
            `).join('');
        },

        /**
         * Renderitza el footer del carret amb total
         */
        renderCarretFooter(total, itemCount) {
            if (itemCount === 0) return '';

            return `
                <div class="carret-total">
                    <span>Total:</span>
                    <strong>${total.toFixed(2)}€</strong>
                </div>
                <a href="pagament.html?from=carret" class="btn-checkout">
                    Finalitzar aportació
                </a>
            `;
        },

        /**
         * Renderitza la pàgina completa del carret
         */
        renderCarretPage(items) {
            const total = items.reduce((sum, i) => sum + parseFloat(i.import), 0);

            if (items.length === 0) {
                return `
                    <div class="carret-page-empty">
                        <div class="empty-icon">🛒</div>
                        <h2>El teu carret és buit</h2>
                        <p>Afegeix obres per fer una aportació col·lectiva</p>
                        <a href="mecenatge.html" class="btn-submit">Veure projectes</a>
                    </div>
                `;
            }

            return `
                <div class="carret-page-content">
                    <div class="carret-page-items">
                        ${items.map(item => `
                            <div class="carret-page-item" data-item-id="${item.id}">
                                <div class="item-obra">
                                    <span class="item-titol">${item.obra_titol}</span>
                                    ${item.obra_autor ? `<span class="item-autor">${item.obra_autor}</span>` : ''}
                                </div>
                                <div class="item-import">
                                    <label>Aportació:</label>
                                    <div class="import-input-group">
                                        <input type="number"
                                               class="input-import"
                                               value="${item.import}"
                                               min="1"
                                               step="1"
                                               data-item-id="${item.id}">
                                        <span class="import-currency">€</span>
                                    </div>
                                </div>
                                <button class="btn-remove-page-item" data-item-id="${item.id}">
                                    <span>Eliminar</span>
                                </button>
                            </div>
                        `).join('')}
                    </div>

                    <div class="carret-page-summary">
                        <div class="summary-row">
                            <span>Obres:</span>
                            <span>${items.length}</span>
                        </div>
                        <div class="summary-row summary-total">
                            <span>Total aportació:</span>
                            <strong id="carret-total">${total.toFixed(2)}€</strong>
                        </div>
                        <button class="btn-submit btn-checkout-page" id="btn-checkout">
                            Confirmar i pagar
                        </button>
                        <button class="btn-secondary btn-clear-carret" id="btn-clear-carret">
                            Buidar carret
                        </button>
                    </div>
                </div>
            `;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // EVENT HANDLERS
    // ─────────────────────────────────────────────────────────────────

    function bindGlobalEvents() {
        // Toggle favorit
        document.addEventListener('click', async (e) => {
            const favBtn = e.target.closest('.btn-favorit');
            if (favBtn) {
                e.preventDefault();
                const obra = {
                    id: favBtn.dataset.obraId,
                    titol: favBtn.dataset.obraTitol,
                    autor: favBtn.dataset.obraAutor
                };

                const result = await FavoritsManager.toggle(obra);

                // Actualitzar UI del botó
                if (!result.error) {
                    favBtn.classList.toggle('active', result.added);
                    const icon = favBtn.querySelector('.favorit-icon');
                    if (icon) {
                        icon.textContent = result.added ? '❤️' : '🤍';
                    }
                }
            }

            // Eliminar favorit de la llista
            const removeBtn = e.target.closest('.btn-remove-favorit');
            if (removeBtn) {
                e.preventDefault();
                const obraId = removeBtn.dataset.obraId;
                await FavoritsManager.remove(obraId);

                // Actualitzar UI
                const item = removeBtn.closest('.favorit-item');
                if (item) {
                    item.style.animation = 'fadeOut 0.3s ease forwards';
                    setTimeout(() => item.remove(), 300);
                }
            }

            // Toggle carret dropdown
            const carretBtn = e.target.closest('#btn-toggle-carret');
            if (carretBtn) {
                e.preventDefault();
                const dropdown = document.getElementById('carret-dropdown');
                if (dropdown) {
                    const isVisible = dropdown.style.display !== 'none';
                    dropdown.style.display = isVisible ? 'none' : 'block';
                    if (!isVisible) {
                        await updateCarretDropdown();
                    }
                }
            }

            // Tancar carret dropdown
            const closeBtn = e.target.closest('#btn-close-carret');
            if (closeBtn) {
                const dropdown = document.getElementById('carret-dropdown');
                if (dropdown) dropdown.style.display = 'none';
            }

            // Eliminar item del carret
            const removeItemBtn = e.target.closest('.btn-remove-item, .btn-remove-page-item');
            if (removeItemBtn) {
                e.preventDefault();
                const itemId = removeItemBtn.dataset.itemId;
                await CarretManager.remove(itemId);

                const item = removeItemBtn.closest('.carret-item, .carret-page-item');
                if (item) {
                    item.style.animation = 'fadeOut 0.3s ease forwards';
                    setTimeout(() => {
                        item.remove();
                        updateCarretDropdown();
                        updateCarretPage();
                    }, 300);
                }
            }

            // Buidar carret
            const clearBtn = e.target.closest('#btn-clear-carret');
            if (clearBtn) {
                e.preventDefault();
                if (confirm('Segur que vols buidar el carret?')) {
                    await CarretManager.clear();
                    updateCarretPage();
                }
            }

            // Checkout
            const checkoutBtn = e.target.closest('#btn-checkout');
            if (checkoutBtn) {
                e.preventDefault();
                checkoutBtn.disabled = true;
                checkoutBtn.textContent = 'Processant...';

                const result = await CarretManager.checkout();

                if (result.error) {
                    window.ArionMecenatge?.Toast.show(result.error.message, 'error');
                    checkoutBtn.disabled = false;
                    checkoutBtn.textContent = 'Confirmar i pagar';
                } else {
                    window.ArionMecenatge?.Toast.show('Gràcies pel teu suport!', 'success');
                    setTimeout(() => {
                        window.location.href = 'perfil.html';
                    }, 1500);
                }
            }
        });

        // Actualitzar import al carret
        document.addEventListener('change', async (e) => {
            if (e.target.classList.contains('input-import')) {
                const itemId = e.target.dataset.itemId;
                const newImport = parseFloat(e.target.value) || 1;
                e.target.value = Math.max(1, newImport);

                await CarretManager.updateImport(itemId, e.target.value);
                updateCarretTotal();
            }
        });

        // Tancar dropdown si es clica fora
        document.addEventListener('click', (e) => {
            const miniCarret = document.getElementById('mini-carret');
            const dropdown = document.getElementById('carret-dropdown');
            if (miniCarret && dropdown && !miniCarret.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });
    }

    async function updateCarretDropdown() {
        const itemsContainer = document.getElementById('carret-items');
        const footerContainer = document.getElementById('carret-footer');

        if (!itemsContainer || !footerContainer) return;

        const items = await CarretManager.getAll();
        const total = await CarretManager.getTotal();

        itemsContainer.innerHTML = FavoritsCarretUI.renderCarretItems(items);
        footerContainer.innerHTML = FavoritsCarretUI.renderCarretFooter(total, items.length);
    }

    async function updateCarretPage() {
        const container = document.getElementById('carret-page-container');
        if (!container) return;

        const items = await CarretManager.getAll();
        container.innerHTML = FavoritsCarretUI.renderCarretPage(items);
    }

    function updateCarretTotal() {
        const inputs = document.querySelectorAll('.input-import');
        let total = 0;
        inputs.forEach(input => {
            total += parseFloat(input.value) || 0;
        });

        const totalEl = document.getElementById('carret-total');
        if (totalEl) {
            totalEl.textContent = total.toFixed(2) + '€';
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // INICIALITZACIÓ
    // ─────────────────────────────────────────────────────────────────

    function init() {
        bindGlobalEvents();

        // Actualitzar badge del carret
        CarretManager._updateBadge();

        // Escoltar canvis
        window.addEventListener('carret-changed', () => {
            updateCarretDropdown();
        });
    }

    // Inicialitzar quan el DOM estigui llest
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ─────────────────────────────────────────────────────────────────
    // EXPORTAR API
    // ─────────────────────────────────────────────────────────────────

    window.ArionFavorits = FavoritsManager;
    window.ArionCarret = CarretManager;
    window.ArionFavoritsCarretUI = FavoritsCarretUI;

})();
