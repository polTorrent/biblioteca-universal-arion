/**
 * ═══════════════════════════════════════════════════════════════════
 * MECENATGE - Sistema de patrocini de traduccions
 * Biblioteca Universal Arion
 * ═══════════════════════════════════════════════════════════════════
 */

(function() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────
    // CONFIGURACIÓ I CONSTANTS
    // ─────────────────────────────────────────────────────────────────

    const CONFIG = {
        STORAGE_KEYS: {
            USER: 'arion_user',
            CATALEG: 'arion_cataleg',
            MECENATGES: 'arion_mecenatges',
            PROPOSTES: 'arion_propostes'
        },
        DATA_PATHS: {
            CATALEG: 'data/cataleg-traduccions.json',
            MECENATGES: 'data/mecenatges.json',
            PROPOSTES: 'data/propostes.json'
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // GESTIÓ DE DADES (localStorage + JSON)
    // ─────────────────────────────────────────────────────────────────

    const DataManager = {
        /**
         * Carrega dades del servidor o localStorage
         */
        async loadData(key, path) {
            // Primer intentem carregar des de localStorage
            const cached = localStorage.getItem(key);
            if (cached) {
                try {
                    return JSON.parse(cached);
                } catch (e) {
                    console.warn('Error parsing cached data:', e);
                }
            }

            // Si no hi ha cache, carreguem del fitxer JSON
            try {
                const basePath = this.getBasePath();
                const response = await fetch(basePath + path);
                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem(key, JSON.stringify(data));
                    return data;
                }
            } catch (e) {
                console.warn('Error loading data from server:', e);
            }

            return null;
        },

        /**
         * Guarda dades a localStorage
         */
        saveData(key, data) {
            localStorage.setItem(key, JSON.stringify(data));
        },

        /**
         * Obté el base path segons l'entorn
         */
        getBasePath() {
            const path = window.location.pathname;
            if (path.includes('/docs/')) {
                return path.substring(0, path.indexOf('/docs/') + 6);
            }
            return './';
        },

        /**
         * Carrega el catàleg d'obres
         */
        async getCataleg() {
            const data = await this.loadData(
                CONFIG.STORAGE_KEYS.CATALEG,
                CONFIG.DATA_PATHS.CATALEG
            );
            return data?.obres || [];
        },

        /**
         * Carrega els mecenatges
         */
        async getMecenatges() {
            const data = await this.loadData(
                CONFIG.STORAGE_KEYS.MECENATGES,
                CONFIG.DATA_PATHS.MECENATGES
            );
            return data?.mecenatges || [];
        },

        /**
         * Actualitza un mecenatge
         */
        async updateMecenatge(mecenatge) {
            const data = await this.loadData(
                CONFIG.STORAGE_KEYS.MECENATGES,
                CONFIG.DATA_PATHS.MECENATGES
            );

            if (data && data.mecenatges) {
                const index = data.mecenatges.findIndex(m => m.id === mecenatge.id);
                if (index !== -1) {
                    data.mecenatges[index] = mecenatge;
                } else {
                    data.mecenatges.push(mecenatge);
                }
                this.saveData(CONFIG.STORAGE_KEYS.MECENATGES, data);
            }
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // GESTIÓ D'USUARIS (Delegat a ArionAuth si disponible)
    // ─────────────────────────────────────────────────────────────────

    const UserManager = {
        /**
         * Obté l'usuari actual
         */
        getCurrentUser() {
            // Usar ArionAuth si està disponible
            if (window.ArionAuth?.isLoggedIn()) {
                return window.ArionAuth.getProfile();
            }

            // Fallback a localStorage
            const userData = localStorage.getItem(CONFIG.STORAGE_KEYS.USER);
            if (userData) {
                try {
                    return JSON.parse(userData);
                } catch (e) {
                    return null;
                }
            }
            return null;
        },

        /**
         * Verifica si l'usuari està autenticat
         */
        isLoggedIn() {
            if (window.ArionAuth) {
                return window.ArionAuth.isLoggedIn();
            }
            return this.getCurrentUser() !== null;
        },

        /**
         * Registra un nou usuari
         */
        async register(nom, cognom, email, password, newsletter = false) {
            // Usar ArionAuth si està disponible
            if (window.ArionAuth) {
                return await window.ArionAuth.register(email, password, {
                    nom,
                    cognom,
                    newsletter
                });
            }

            // Fallback a localStorage
            const user = {
                id: 'usr_' + Date.now(),
                nom,
                cognom,
                email,
                creat: new Date().toISOString().split('T')[0],
                mecenatges: [],
                total_aportat: 0,
                punts_totals: 10,
                nivell: 1,
                titol: 'Lector Curiós',
                rol: 'usuari'
            };

            localStorage.setItem(CONFIG.STORAGE_KEYS.USER, JSON.stringify(user));
            localStorage.setItem('arion_user_email', email);
            localStorage.setItem('arion_user_pass', btoa(password));

            return { user, error: null };
        },

        /**
         * Inicia sessió
         */
        async login(email, password) {
            // Usar ArionAuth si està disponible
            if (window.ArionAuth) {
                return await window.ArionAuth.login(email, password);
            }

            // Fallback a localStorage
            const savedEmail = localStorage.getItem('arion_user_email');
            const savedPass = localStorage.getItem('arion_user_pass');

            if (savedEmail === email && savedPass === btoa(password)) {
                const userData = localStorage.getItem(CONFIG.STORAGE_KEYS.USER);
                return { user: userData ? JSON.parse(userData) : null, error: null };
            }

            // Demo: permet login amb qualsevol email/password
            const user = {
                id: 'usr_demo_' + Date.now(),
                nom: email.split('@')[0],
                cognom: '',
                email,
                creat: new Date().toISOString().split('T')[0],
                mecenatges: [],
                total_aportat: 0,
                punts_totals: 10,
                nivell: 1,
                titol: 'Lector Curiós',
                rol: 'usuari'
            };

            localStorage.setItem(CONFIG.STORAGE_KEYS.USER, JSON.stringify(user));
            return { user, error: null };
        },

        /**
         * Tanca sessió
         */
        async logout() {
            if (window.ArionAuth) {
                await window.ArionAuth.logout();
            } else {
                localStorage.removeItem(CONFIG.STORAGE_KEYS.USER);
            }
        },

        /**
         * Actualitza l'usuari amb una nova aportació
         */
        async addMecenatge(obraId, obraTitol, importValue) {
            // Usar ArionAuth si està disponible
            if (window.ArionAuth) {
                const result = await window.ArionAuth.addMecenatge(obraId, obraTitol, importValue);

                // Verificar medalles i mostrar animacions
                if (window.ArionGamification && !result.error) {
                    const profile = window.ArionAuth.getProfile();
                    const novesMedalles = window.ArionGamification.Badge.verificarMedalles(profile);

                    for (const medalla of novesMedalles) {
                        const medallaCompleta = window.ArionGamification.MEDALLES[medalla.id];
                        if (medallaCompleta) {
                            setTimeout(() => {
                                window.ArionGamification.Animation.showNovaMedalla(medallaCompleta);
                            }, 500);
                        }
                    }
                }

                return result.data;
            }

            // Fallback a localStorage
            const user = this.getCurrentUser();
            if (user) {
                user.mecenatges = user.mecenatges || [];
                user.mecenatges.push({
                    obra_id: obraId,
                    obra_titol: obraTitol,
                    import: importValue,
                    data: new Date().toISOString().split('T')[0]
                });
                user.total_aportat = (user.total_aportat || 0) + importValue;

                // Calcular punts
                const esPrimeraAportacio = user.mecenatges.length === 1;
                let puntsNous = Math.floor(importValue * 10);
                if (esPrimeraAportacio) puntsNous += 25;
                user.punts_totals = (user.punts_totals || 10) + puntsNous;

                // Actualitzar nivell
                const nivells = [
                    { nivell: 7, punts: 2500 },
                    { nivell: 6, punts: 1000 },
                    { nivell: 5, punts: 500 },
                    { nivell: 4, punts: 300 },
                    { nivell: 3, punts: 150 },
                    { nivell: 2, punts: 50 },
                    { nivell: 1, punts: 0 }
                ];

                for (const n of nivells) {
                    if (user.punts_totals >= n.punts) {
                        user.nivell = n.nivell;
                        break;
                    }
                }

                if (user.total_aportat >= 20) {
                    user.rol = 'mecenes';
                } else if (user.total_aportat >= 5) {
                    user.rol = 'micromecenes';
                }

                localStorage.setItem(CONFIG.STORAGE_KEYS.USER, JSON.stringify(user));

                // Verificar medalles
                if (window.ArionGamification) {
                    const novesMedalles = window.ArionGamification.Badge.verificarMedalles(user);
                    user.medalles = user.medalles || [];
                    for (const medalla of novesMedalles) {
                        user.medalles.push(medalla);
                        const medallaCompleta = window.ArionGamification.MEDALLES[medalla.id];
                        if (medallaCompleta) {
                            setTimeout(() => {
                                window.ArionGamification.Animation.showNovaMedalla(medallaCompleta);
                            }, 500);
                        }
                    }
                    localStorage.setItem(CONFIG.STORAGE_KEYS.USER, JSON.stringify(user));
                }

                return user;
            }
            return null;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // BUSCADOR D'OBRES
    // ─────────────────────────────────────────────────────────────────

    const SearchManager = {
        cataleg: [],

        /**
         * Inicialitza el buscador
         */
        async init() {
            this.cataleg = await DataManager.getCataleg();
            this.bindEvents();
        },

        /**
         * Associa esdeveniments
         */
        bindEvents() {
            const searchInput = document.getElementById('cerca-obra');
            const searchForm = document.querySelector('.buscador-form');

            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    this.search(e.target.value);
                });

                searchInput.addEventListener('focus', () => {
                    if (searchInput.value.length >= 2) {
                        this.search(searchInput.value);
                    }
                });
            }

            if (searchForm) {
                searchForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                });
            }

            // Tancar resultats quan es clica fora
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.buscador-container')) {
                    this.hideResults();
                }
            });
        },

        /**
         * Cerca obres
         */
        search(query) {
            const resultsContainer = document.getElementById('resultats-cerca');
            const noResults = document.querySelector('.no-resultats');

            if (!resultsContainer) return;

            if (query.length < 2) {
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'none';
                if (noResults) noResults.hidden = true;
                return;
            }

            const normalizedQuery = this.normalizeText(query);
            const results = this.cataleg.filter(obra => {
                const searchableText = [
                    obra.titol,
                    obra.titol_original,
                    obra.autor,
                    obra.genere,
                    obra.idioma
                ].join(' ');

                return this.normalizeText(searchableText).includes(normalizedQuery);
            });

            this.showResults(results);
        },

        /**
         * Normalitza text per a cerca
         */
        normalizeText(text) {
            return text
                .toLowerCase()
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '');
        },

        /**
         * Mostra els resultats
         */
        showResults(results) {
            const resultsContainer = document.getElementById('resultats-cerca');
            const noResults = document.querySelector('.no-resultats');

            if (!resultsContainer) return;

            if (results.length === 0) {
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'none';
                if (noResults) noResults.hidden = false;
                return;
            }

            if (noResults) noResults.hidden = true;
            resultsContainer.style.display = 'block';

            resultsContainer.innerHTML = results.map(obra => `
                <div class="resultat-item" data-obra-id="${obra.id}">
                    <div class="resultat-info">
                        <h4>${obra.titol}</h4>
                        <p>${obra.autor} · ${obra.idioma} · ${obra.genere}</p>
                    </div>
                    <div class="resultat-estat">
                        <span class="badge-estat badge-${obra.estat}">${this.getEstatLabel(obra.estat)}</span>
                        <span class="resultat-preu">${obra.cost_traduccio}€</span>
                    </div>
                </div>
            `).join('');

            // Afegir esdeveniments als resultats
            resultsContainer.querySelectorAll('.resultat-item').forEach(item => {
                item.addEventListener('click', () => {
                    const obraId = item.dataset.obraId;
                    this.selectObra(obraId);
                });
            });
        },

        /**
         * Amaga els resultats
         */
        hideResults() {
            const resultsContainer = document.getElementById('resultats-cerca');
            if (resultsContainer) {
                resultsContainer.style.display = 'none';
            }
        },

        /**
         * Selecciona una obra
         */
        selectObra(obraId) {
            const obra = this.cataleg.find(o => o.id === obraId);
            if (obra) {
                if (obra.estat === 'crowdfunding') {
                    // Redirigir a la fitxa de micromecenatge
                    window.location.href = `micromecenatge-${obraId}.html`;
                } else if (obra.estat === 'disponible') {
                    // Obrir modal per iniciar mecenatge
                    MecenatgeManager.showObraModal(obra);
                } else if (obra.estat === 'traduit') {
                    // Redirigir a l'obra traduïda
                    window.location.href = `${obraId}.html`;
                }
            }
        },

        /**
         * Obté l'etiqueta de l'estat
         */
        getEstatLabel(estat) {
            const labels = {
                'disponible': 'Disponible',
                'crowdfunding': 'Micromecenatge',
                'traduit': 'Traduït',
                'en_traduccio': 'En traducció'
            };
            return labels[estat] || estat;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // GESTIÓ DE MECENATGE
    // ─────────────────────────────────────────────────────────────────

    const MecenatgeManager = {
        currentObra: null,
        currentImport: null,

        /**
         * Inicialitza el gestor
         */
        init() {
            this.bindEvents();
            this.loadProjectesActius();
            this.updateAuthUI();
        },

        /**
         * Associa esdeveniments
         */
        bindEvents() {
            // Botons d'aportar
            document.querySelectorAll('.btn-aportar').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const obraId = btn.dataset.obraId;
                    this.startMecenatge(obraId);
                });
            });

            // Nivells de recompensa
            document.querySelectorAll('.nivell-card').forEach(card => {
                card.addEventListener('click', () => {
                    this.selectNivell(card);
                });
            });

            // FAQ accordion
            document.querySelectorAll('.faq-question').forEach(btn => {
                btn.addEventListener('click', () => {
                    const item = btn.closest('.faq-item');
                    item.classList.toggle('open');
                });
            });
        },

        /**
         * Actualitza la UI segons l'estat d'autenticació
         */
        updateAuthUI() {
            const user = UserManager.getCurrentUser();
            const authBtn = document.querySelector('.btn-auth');

            if (authBtn) {
                if (user) {
                    authBtn.textContent = user.nom;
                    authBtn.href = 'perfil.html';
                } else {
                    authBtn.textContent = 'Entrar';
                    authBtn.href = 'login.html';
                }
            }
        },

        /**
         * Carrega els projectes actius de micromecenatge
         */
        async loadProjectesActius() {
            const container = document.getElementById('projectes-actius');
            if (!container) return;

            const cataleg = await DataManager.getCataleg();
            const mecenatges = await DataManager.getMecenatges();

            // Filtrar obres en crowdfunding
            const projectesActius = cataleg.filter(obra => obra.estat === 'crowdfunding');

            if (projectesActius.length === 0) {
                container.innerHTML = '<p class="no-projectes">No hi ha projectes actius en aquest moment.</p>';
                return;
            }

            container.innerHTML = projectesActius.map(obra => {
                const mecenatge = mecenatges.find(m => m.obra_id === obra.id);
                const recaptat = mecenatge?.total || obra.recaptat || 0;
                const objectiu = obra.cost_traduccio;
                const percentatge = Math.min(Math.round((recaptat / objectiu) * 100), 100);
                const numMecenes = mecenatge?.aportacions?.length || obra.mecenes || 0;

                return `
                    <article class="fitxa-micromecenatge">
                        <div class="fitxa-portada">
                            <div class="fitxa-placeholder">${obra.titol[0]}</div>
                        </div>
                        <div class="fitxa-contingut">
                            <h3>${obra.titol}</h3>
                            <p class="fitxa-autor">${obra.autor}</p>
                            <span class="fitxa-idioma">${obra.idioma}</span>

                            <div class="progres-container">
                                <div class="barra-progres">
                                    <div class="progres-fill" style="width: ${percentatge}%"></div>
                                </div>
                                <div class="progres-stats">
                                    <span class="progres-recaptat">${recaptat}€</span>
                                    <span class="progres-objectiu">de ${objectiu}€</span>
                                    <span class="progres-percentatge">${percentatge}%</span>
                                </div>
                            </div>

                            <p class="mecenes-count">👥 ${numMecenes} mecenes</p>
                            <p class="fitxa-descripcio">${obra.descripcio}</p>

                            <div class="fitxa-footer">
                                <a href="micromecenatge-${obra.id}.html" class="btn-veure">Veure</a>
                                <button class="btn-aportar" data-obra-id="${obra.id}">💝 Aportar</button>
                            </div>
                        </div>
                    </article>
                `;
            }).join('');

            // Re-bind events per als nous botons
            container.querySelectorAll('.btn-aportar').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const obraId = btn.dataset.obraId;
                    this.startMecenatge(obraId);
                });
            });
        },

        /**
         * Inicia el procés de mecenatge
         */
        async startMecenatge(obraId) {
            const cataleg = await DataManager.getCataleg();
            const obra = cataleg.find(o => o.id === obraId);

            if (!obra) {
                Toast.show('No s\'ha trobat l\'obra', 'error');
                return;
            }

            this.currentObra = obra;

            // Verificar si l'usuari està autenticat
            if (!UserManager.isLoggedIn()) {
                // Guardar l'obra actual per després del login
                sessionStorage.setItem('mecenatge_pending', JSON.stringify({
                    obraId,
                    returnUrl: window.location.href
                }));
                window.location.href = 'login.html?redirect=mecenatge';
                return;
            }

            // Redirigir a la pàgina de pagament
            sessionStorage.setItem('mecenatge_obra', JSON.stringify(obra));
            window.location.href = 'pagament.html';
        },

        /**
         * Mostra el modal d'obra
         */
        showObraModal(obra) {
            this.currentObra = obra;

            // Crear modal dinàmicament
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal">
                    <div class="modal-header">
                        <h2>${obra.titol}</h2>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p class="obra-autor"><strong>Autor:</strong> ${obra.autor}</p>
                        <p class="obra-idioma"><strong>Idioma original:</strong> ${obra.idioma}</p>
                        <p class="obra-descripcio">${obra.descripcio}</p>

                        <div class="modal-opcions">
                            <h3>Com vols finançar aquesta traducció?</h3>
                            <div class="tipus-buttons" style="margin-top: 1rem;">
                                <button class="btn-tipus btn-tipus-primary" data-tipus="individual">
                                    💎 Mecenatge Individual (${obra.cost_traduccio}€)
                                </button>
                                <button class="btn-tipus btn-tipus-secondary" data-tipus="col·lectiu">
                                    👥 Crear Micromecenatge
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            setTimeout(() => modal.classList.add('active'), 10);

            // Esdeveniments
            modal.querySelector('.modal-close').addEventListener('click', () => {
                this.closeModal(modal);
            });

            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modal);
                }
            });

            modal.querySelector('[data-tipus="individual"]').addEventListener('click', () => {
                this.closeModal(modal);
                this.currentImport = obra.cost_traduccio;
                this.startMecenatge(obra.id);
            });

            modal.querySelector('[data-tipus="col·lectiu"]').addEventListener('click', () => {
                this.closeModal(modal);
                window.location.href = `proposta-traduccio.html?obra=${obra.id}`;
            });
        },

        /**
         * Tanca un modal
         */
        closeModal(modal) {
            modal.classList.remove('active');
            setTimeout(() => modal.remove(), 300);
        },

        /**
         * Selecciona un nivell de recompensa
         */
        selectNivell(card) {
            // Deseleccionar tots
            document.querySelectorAll('.nivell-card').forEach(c => {
                c.classList.remove('selected');
            });

            // Seleccionar el clica
            card.classList.add('selected');

            // Actualitzar l'import
            const importValue = parseInt(card.dataset.import);
            this.currentImport = importValue;

            // Actualitzar el botó de pagament si existeix
            const btnPagar = document.querySelector('.btn-pagar');
            if (btnPagar) {
                btnPagar.textContent = `Confirmar pagament de ${importValue}€`;
            }

            // Actualitzar el resum
            const importDisplay = document.querySelector('.pagament-resum .import');
            if (importDisplay) {
                importDisplay.textContent = importValue + '€';
            }
        },

        /**
         * Processa el pagament (simulat)
         */
        async processPayment() {
            const obra = JSON.parse(sessionStorage.getItem('mecenatge_obra'));
            const importValue = this.currentImport || obra?.cost_traduccio || 5;

            if (!obra) {
                Toast.show('Error: No s\'ha trobat l\'obra', 'error');
                return;
            }

            // Simular processament
            const btn = document.querySelector('.btn-pagar');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Processant...';
            }

            // Esperar una mica per simular el pagament
            await new Promise(resolve => setTimeout(resolve, 1500));

            // Actualitzar l'usuari (amb el nou mètode que suporta Supabase)
            const obraTitol = obra.titol || obra.id;
            await UserManager.addMecenatge(obra.id, obraTitol, importValue);

            // Actualitzar el mecenatge local (per demo/localStorage)
            const mecenatges = await DataManager.getMecenatges();
            let mecenatge = mecenatges.find(m => m.obra_id === obra.id);

            if (mecenatge) {
                const user = UserManager.getCurrentUser();
                mecenatge.aportacions = mecenatge.aportacions || [];
                mecenatge.aportacions.push({
                    usuari_id: user.id,
                    usuari_nom: user.nom + ' ' + (user.cognom ? user.cognom.charAt(0) + '.' : ''),
                    import: importValue,
                    data: new Date().toISOString().split('T')[0]
                });
                mecenatge.total = (mecenatge.total || 0) + importValue;

                await DataManager.updateMecenatge(mecenatge);
            }

            // Mostrar toast de punts si el sistema de gamificació està disponible
            if (window.ArionGamification) {
                const punts = Math.floor(importValue * 10);
                window.ArionGamification.Animation.showPuntsToast(punts, 'per la teva aportació');
            }

            // Mostrar confirmació
            this.showConfirmation(obra, importValue);
        },

        /**
         * Mostra la confirmació del pagament
         */
        showConfirmation(obra, importValue) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay active';
            modal.innerHTML = `
                <div class="modal">
                    <div class="modal-body modal-success">
                        <div class="modal-success-icon">✨</div>
                        <h2>Gràcies pel teu suport!</h2>
                        <p>Has aportat <strong>${importValue}€</strong> a la traducció de <strong>${obra.titol}</strong>.</p>
                        <p>Rebràs un correu de confirmació amb els detalls.</p>
                        <button class="btn-submit" onclick="window.location.href='mecenatge.html'">
                            Tornar al mecenatge
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            sessionStorage.removeItem('mecenatge_obra');
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // FORMULARIS
    // ─────────────────────────────────────────────────────────────────

    const FormManager = {
        /**
         * Inicialitza els formularis
         */
        init() {
            this.initRegistreForm();
            this.initLoginForm();
            this.initPagamentForm();
            this.initPropostaForm();
        },

        /**
         * Formulari de registre
         */
        initRegistreForm() {
            const form = document.getElementById('form-registre');
            if (!form) return;

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const nom = form.querySelector('[name="nom"]').value;
                const cognom = form.querySelector('[name="cognom"]').value;
                const email = form.querySelector('[name="email"]').value;
                const password = form.querySelector('[name="password"]').value;
                const password2 = form.querySelector('[name="password2"]').value;
                const termes = form.querySelector('[name="termes"]').checked;
                const newsletter = form.querySelector('[name="newsletter"]')?.checked || false;

                // Validacions
                if (password !== password2) {
                    Toast.show('Les contrasenyes no coincideixen', 'error');
                    return;
                }

                if (!termes) {
                    Toast.show('Has d\'acceptar els termes i condicions', 'error');
                    return;
                }

                // Desactivar botó
                const submitBtn = form.querySelector('[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Creant compte...';
                }

                // Registrar
                const result = await UserManager.register(nom, cognom, email, password, newsletter);

                if (result.error) {
                    Toast.show('Error: ' + result.error.message, 'error');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Crear compte';
                    }
                    return;
                }

                Toast.show('Compte creat correctament!', 'success');

                // Redirigir
                const redirect = new URLSearchParams(window.location.search).get('redirect');
                setTimeout(() => {
                    if (redirect === 'mecenatge') {
                        window.location.href = 'pagament.html';
                    } else {
                        window.location.href = 'mecenatge.html';
                    }
                }, 1000);
            });
        },

        /**
         * Formulari de login
         */
        initLoginForm() {
            const form = document.getElementById('form-login');
            if (!form) return;

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const email = form.querySelector('[name="email"]').value;
                const password = form.querySelector('[name="password"]').value;

                // Desactivar botó
                const submitBtn = form.querySelector('[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Entrant...';
                }

                const result = await UserManager.login(email, password);

                if (result.error) {
                    Toast.show('Credencials incorrectes: ' + result.error.message, 'error');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Entrar';
                    }
                    return;
                }

                if (result.user) {
                    const nom = result.user.nom || result.user.email?.split('@')[0] || 'Usuari';
                    Toast.show('Benvingut/da, ' + nom + '!', 'success');

                    // Redirigir
                    const redirect = new URLSearchParams(window.location.search).get('redirect');
                    setTimeout(() => {
                        if (redirect === 'mecenatge') {
                            window.location.href = 'pagament.html';
                        } else if (redirect === 'perfil') {
                            window.location.href = 'perfil.html';
                        } else {
                            window.location.href = 'mecenatge.html';
                        }
                    }, 1000);
                } else {
                    Toast.show('Error desconegut', 'error');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Entrar';
                    }
                }
            });
        },

        /**
         * Formulari de pagament
         */
        initPagamentForm() {
            const form = document.getElementById('form-pagament');
            if (!form) return;

            // Carregar dades de l'obra
            const obra = JSON.parse(sessionStorage.getItem('mecenatge_obra'));
            if (obra) {
                const titolEl = form.querySelector('.obra-titol');
                const importEl = form.querySelector('.import');

                if (titolEl) titolEl.textContent = obra.titol + ' - ' + obra.autor;
                if (importEl) importEl.textContent = obra.cost_traduccio + '€';

                MecenatgeManager.currentImport = obra.cost_traduccio;
            }

            // Mètodes de pagament
            form.querySelectorAll('.metode-option').forEach(option => {
                option.addEventListener('click', () => {
                    form.querySelectorAll('.metode-option').forEach(o => {
                        o.classList.remove('selected');
                    });
                    option.classList.add('selected');
                    option.querySelector('input').checked = true;
                });
            });

            form.addEventListener('submit', (e) => {
                e.preventDefault();
                MecenatgeManager.processPayment();
            });
        },

        /**
         * Formulari de proposta de traducció
         */
        initPropostaForm() {
            const form = document.getElementById('form-proposta');
            if (!form) return;

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const proposta = {
                    id: 'prop_' + Date.now(),
                    titol: form.querySelector('[name="titol"]').value,
                    titol_original: form.querySelector('[name="titol_original"]').value,
                    autor: form.querySelector('[name="autor"]').value,
                    idioma: form.querySelector('[name="idioma"]').value,
                    any: parseInt(form.querySelector('[name="any"]').value) || null,
                    genere: form.querySelector('[name="genere"]').value,
                    descripcio: form.querySelector('[name="descripcio"]').value,
                    proposat_per: UserManager.getCurrentUser()?.id || 'anònim',
                    data_proposta: new Date().toISOString().split('T')[0],
                    vots: 0,
                    estat: 'pendent_aprovacio'
                };

                // Guardar proposta
                const data = await DataManager.loadData(
                    CONFIG.STORAGE_KEYS.PROPOSTES,
                    CONFIG.DATA_PATHS.PROPOSTES
                ) || { propostes: [] };

                data.propostes.push(proposta);
                DataManager.saveData(CONFIG.STORAGE_KEYS.PROPOSTES, data);

                Toast.show('Proposta enviada correctament!', 'success');

                setTimeout(() => {
                    window.location.href = 'mecenatge.html';
                }, 1500);
            });
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // TOAST NOTIFICATIONS
    // ─────────────────────────────────────────────────────────────────

    const Toast = {
        container: null,

        /**
         * Inicialitza el contenidor de toasts
         */
        init() {
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.className = 'toast-container';
                document.body.appendChild(this.container);
            }
        },

        /**
         * Mostra un toast
         */
        show(message, type = 'info') {
            this.init();

            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.innerHTML = `
                <span class="toast-icon">${this.getIcon(type)}</span>
                <span class="toast-message">${message}</span>
            `;

            this.container.appendChild(toast);

            // Eliminar després de 4 segons
            setTimeout(() => {
                toast.style.animation = 'slideIn 0.3s ease reverse';
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        },

        /**
         * Obté la icona segons el tipus
         */
        getIcon(type) {
            const icons = {
                success: '✓',
                error: '✕',
                info: 'ℹ'
            };
            return icons[type] || icons.info;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // INICIALITZACIÓ
    // ─────────────────────────────────────────────────────────────────

    document.addEventListener('DOMContentLoaded', () => {
        SearchManager.init();
        MecenatgeManager.init();
        FormManager.init();
    });

    // Exportar per ús extern
    window.ArionMecenatge = {
        DataManager,
        UserManager,
        SearchManager,
        MecenatgeManager,
        Toast
    };

})();
