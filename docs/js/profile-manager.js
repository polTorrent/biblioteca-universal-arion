/**
 * ═══════════════════════════════════════════════════════════════════
 * PROFILE MANAGER - Biblioteca Universal Arion
 * Gestió de la pàgina de perfil d'usuari
 * ═══════════════════════════════════════════════════════════════════
 */

(function() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────
    // ESTAT
    // ─────────────────────────────────────────────────────────────────

    let currentProfile = null;
    let userBadges = [];
    let userMecenatges = [];
    let userPropostes = [];

    // ─────────────────────────────────────────────────────────────────
    // INICIALITZACIÓ
    // ─────────────────────────────────────────────────────────────────

    async function init() {
        // Verificar autenticació
        if (!window.ArionAuth?.isLoggedIn()) {
            window.location.href = 'login.html?redirect=perfil';
            return;
        }

        // Carregar dades
        await loadProfileData();

        // Renderitzar UI
        renderProfile();

        // Configurar events
        bindEvents();
    }

    // ─────────────────────────────────────────────────────────────────
    // CÀRREGA DE DADES
    // ─────────────────────────────────────────────────────────────────

    async function loadProfileData() {
        currentProfile = window.ArionAuth.getProfile();

        if (window.ArionSupabase?.isAvailable()) {
            const user = window.ArionAuth.getCurrentUser();

            // Carregar medalles
            const { data: badges } = await window.ArionSupabase.query('usuari_medalles', {
                eq: { usuari_id: user.id },
                select: '*, medalles(*)'
            });
            userBadges = badges || [];

            // Carregar mecenatges
            const { data: mecenatges } = await window.ArionSupabase.query('mecenatges', {
                eq: { usuari_id: user.id },
                order: { column: 'data_aportacio', ascending: false }
            });
            userMecenatges = mecenatges || [];

            // Carregar propostes
            const { data: propostes } = await window.ArionSupabase.query('propostes', {
                eq: { proposat_per: user.id },
                order: { column: 'data_proposta', ascending: false }
            });
            userPropostes = propostes || [];

        } else {
            // Mode localStorage
            userBadges = currentProfile?.medalles || [];
            userMecenatges = currentProfile?.mecenatges || [];
            userPropostes = [];
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // RENDERITZAT
    // ─────────────────────────────────────────────────────────────────

    function renderProfile() {
        if (!currentProfile) return;

        // Capçalera
        renderHeader();

        // Estadístiques
        renderStats();

        // Barra de progrés
        renderProgress();

        // Pestanyes
        renderTabs();
    }

    function renderHeader() {
        const container = document.getElementById('profile-header');
        if (!container) return;

        const nivell = window.ArionGamification?.Level.getNivell(currentProfile.punts_totals || 0) || { icona: '📖', color: '#8B7355' };

        container.innerHTML = `
            <div class="profile-avatar-section">
                <div class="profile-avatar" style="border-color: ${nivell.color}">
                    ${currentProfile.avatar_url ?
                        `<img src="${currentProfile.avatar_url}" alt="${currentProfile.nom}">` :
                        `<span class="avatar-placeholder">${(currentProfile.nom || 'U')[0].toUpperCase()}</span>`
                    }
                    <button class="avatar-edit-btn" title="Canviar avatar">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                    <input type="file" id="avatar-input" accept="image/*" hidden>
                </div>
            </div>

            <div class="profile-info">
                <div class="profile-name-row">
                    <h1 class="profile-name">${currentProfile.nom || 'Usuari'} ${currentProfile.cognom || ''}</h1>
                    <button class="btn-edit-profile" title="Editar perfil">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                </div>

                <div class="profile-level">
                    <span class="level-badge" style="background: ${nivell.color}">
                        ${nivell.icona} Nivell ${currentProfile.nivell || 1}
                    </span>
                    <span class="level-title">${currentProfile.titol || 'Lector Curiós'}</span>
                </div>

                <p class="profile-bio">${currentProfile.bio || 'Encara no has afegit una biografia.'}</p>

                <div class="profile-meta">
                    <span class="profile-email">${currentProfile.email || ''}</span>
                    <span class="profile-joined">
                        Membre des de ${formatDate(currentProfile.creat_el || currentProfile.creat)}
                    </span>
                </div>
            </div>
        `;
    }

    function renderStats() {
        const container = document.getElementById('profile-stats');
        if (!container) return;

        const medallesCount = userBadges.length;

        container.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${formatCurrency(currentProfile.total_aportat || 0)}</div>
                <div class="stat-label">Total aportat</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${currentProfile.num_obres_patrocinades || 0}</div>
                <div class="stat-label">Obres patrocinades</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${currentProfile.punts_totals || 0}</div>
                <div class="stat-label">Punts totals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${medallesCount}</div>
                <div class="stat-label">Medalles</div>
            </div>
        `;
    }

    function renderProgress() {
        const container = document.getElementById('profile-progress');
        if (!container || !window.ArionGamification) return;

        container.innerHTML = window.ArionGamification.UI.renderBarraProgres(currentProfile.punts_totals || 0);
    }

    function renderTabs() {
        // Favorits
        renderFavoritsTab();

        // Medalles
        renderMedallesTab();

        // Historial
        renderHistorialTab();

        // Propostes
        renderPropostesTab();

        // Rànking
        renderRankingTab();
    }

    async function renderFavoritsTab() {
        const container = document.getElementById('tab-favorits');
        if (!container) return;

        container.innerHTML = '<div class="loading">Carregant favorits...</div>';

        // Carregar favorits
        let favorits = [];
        if (window.ArionFavorits) {
            favorits = await window.ArionFavorits.getAll();
        }

        if (favorits.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🤍</div>
                    <h3>No tens cap favorit</h3>
                    <p>Explora el catàleg i marca amb un cor les obres que t'interessin.</p>
                    <a href="index.html" class="btn-submit">Veure catàleg</a>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <h3>Els teus favorits <span class="count-badge">${favorits.length}</span></h3>
            ${window.ArionFavoritsCarretUI?.renderFavoritsLlista(favorits) || ''}
        `;
    }

    function renderMedallesTab() {
        const container = document.getElementById('tab-medalles');
        if (!container || !window.ArionGamification) return;

        const medallesIds = userBadges.map(b => b.medalla_id || b.id || b);

        container.innerHTML = `
            <h3>Les teves medalles</h3>
            ${window.ArionGamification.UI.renderMedalles(medallesIds, currentProfile, true)}
        `;
    }

    function renderHistorialTab() {
        const container = document.getElementById('tab-historial');
        if (!container) return;

        if (userMecenatges.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">💝</div>
                    <h3>Encara no has fet cap aportació</h3>
                    <p>Descobreix els projectes actius i converteix-te en mecenes de la cultura catalana.</p>
                    <a href="mecenatge.html" class="btn-submit">Veure projectes</a>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <h3>Historial d'aportacions</h3>
            <div class="historial-list">
                ${userMecenatges.map(mec => `
                    <div class="historial-item">
                        <div class="historial-info">
                            <span class="historial-titol">${mec.obra_titol || 'Obra'}</span>
                            <span class="historial-data">${formatDate(mec.data_aportacio || mec.data)}</span>
                        </div>
                        <div class="historial-import">
                            <span class="historial-amount">${formatCurrency(mec.import)}</span>
                            <span class="historial-tipus badge-${mec.tipus}">${mec.tipus === 'individual' ? 'Individual' : 'Micromecenatge'}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    function renderPropostesTab() {
        const container = document.getElementById('tab-propostes');
        if (!container) return;

        if (userPropostes.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">💡</div>
                    <h3>No has proposat cap traducció</h3>
                    <p>Tens alguna obra que t'agradaria veure traduïda al català?</p>
                    <a href="proposta-traduccio.html" class="btn-submit">Proposar traducció</a>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <h3>Les teves propostes</h3>
            <div class="propostes-list">
                ${userPropostes.map(prop => `
                    <div class="proposta-item">
                        <div class="proposta-info">
                            <span class="proposta-titol">${prop.titol}</span>
                            <span class="proposta-autor">${prop.autor}</span>
                        </div>
                        <div class="proposta-meta">
                            <span class="proposta-vots">${prop.num_vots || 0} vots</span>
                            <span class="proposta-estat badge-${prop.estat}">${getEstatLabel(prop.estat)}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    async function renderRankingTab() {
        const container = document.getElementById('tab-ranking');
        if (!container || !window.ArionGamification) return;

        container.innerHTML = '<div class="loading">Carregant rànking...</div>';

        const ranking = await window.ArionGamification.Ranking.getRanking(20);
        const userId = window.ArionAuth.getCurrentUser()?.id;

        if (ranking.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🏆</div>
                    <h3>Rànking no disponible</h3>
                    <p>El rànking global només està disponible quan Supabase està configurat.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <h3>Rànking global</h3>
            ${window.ArionGamification.UI.renderRanking(ranking, userId)}
        `;
    }

    // ─────────────────────────────────────────────────────────────────
    // EDICIÓ DE PERFIL
    // ─────────────────────────────────────────────────────────────────

    function showEditModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay active';
        modal.id = 'edit-profile-modal';
        modal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h2>Editar perfil</h2>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="form-edit-profile">
                        <div class="form-group">
                            <label for="edit-nom">Nom</label>
                            <input type="text" id="edit-nom" name="nom" value="${currentProfile.nom || ''}" required>
                        </div>

                        <div class="form-group">
                            <label for="edit-cognom">Cognoms</label>
                            <input type="text" id="edit-cognom" name="cognom" value="${currentProfile.cognom || ''}">
                        </div>

                        <div class="form-group">
                            <label for="edit-bio">Biografia</label>
                            <textarea id="edit-bio" name="bio" rows="3" maxlength="200" placeholder="Explica una mica sobre tu...">${currentProfile.bio || ''}</textarea>
                            <small class="char-count"><span id="bio-count">${(currentProfile.bio || '').length}</span>/200</small>
                        </div>

                        <div class="form-group form-checkbox">
                            <input type="checkbox" id="edit-public" name="perfil_public" ${currentProfile.perfil_public !== false ? 'checked' : ''}>
                            <label for="edit-public">Perfil públic (visible al rànking)</label>
                        </div>

                        <div class="form-group form-checkbox">
                            <input type="checkbox" id="edit-newsletter" name="rebre_newsletter" ${currentProfile.rebre_newsletter ? 'checked' : ''}>
                            <label for="edit-newsletter">Rebre novetats per correu</label>
                        </div>

                        <div class="form-actions">
                            <button type="button" class="btn-secondary" onclick="document.getElementById('edit-profile-modal').remove()">
                                Cancel·lar
                            </button>
                            <button type="submit" class="btn-submit">
                                Guardar canvis
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Events
        modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        // Comptador de caràcters
        const bioInput = modal.querySelector('#edit-bio');
        const bioCount = modal.querySelector('#bio-count');
        bioInput.addEventListener('input', () => {
            bioCount.textContent = bioInput.value.length;
        });

        // Submit
        modal.querySelector('#form-edit-profile').addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveProfile(new FormData(e.target));
            modal.remove();
        });
    }

    async function saveProfile(formData) {
        const updates = {
            nom: formData.get('nom'),
            cognom: formData.get('cognom'),
            bio: formData.get('bio'),
            perfil_public: formData.get('perfil_public') === 'on',
            rebre_newsletter: formData.get('rebre_newsletter') === 'on'
        };

        const { error } = await window.ArionAuth.updateProfile(updates);

        if (error) {
            window.ArionMecenatge?.Toast.show('Error guardant el perfil: ' + error.message, 'error');
            return;
        }

        // Refrescar dades
        currentProfile = window.ArionAuth.getProfile();
        renderProfile();

        window.ArionMecenatge?.Toast.show('Perfil actualitzat correctament', 'success');
    }

    async function uploadAvatar(file) {
        if (!file) return;

        // Validar tipus i mida
        if (!file.type.startsWith('image/')) {
            window.ArionMecenatge?.Toast.show('El fitxer ha de ser una imatge', 'error');
            return;
        }

        if (file.size > 2 * 1024 * 1024) {
            window.ArionMecenatge?.Toast.show('La imatge no pot superar els 2MB', 'error');
            return;
        }

        const { error } = await window.ArionAuth.uploadAvatar(file);

        if (error) {
            window.ArionMecenatge?.Toast.show('Error pujant l\'avatar: ' + error.message, 'error');
            return;
        }

        // Refrescar dades
        currentProfile = window.ArionAuth.getProfile();
        renderProfile();

        window.ArionMecenatge?.Toast.show('Avatar actualitzat correctament', 'success');
    }

    // ─────────────────────────────────────────────────────────────────
    // EVENTS
    // ─────────────────────────────────────────────────────────────────

    function bindEvents() {
        // Editar perfil
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-edit-profile')) {
                showEditModal();
            }

            if (e.target.closest('.avatar-edit-btn')) {
                document.getElementById('avatar-input')?.click();
            }
        });

        // Avatar input
        document.getElementById('avatar-input')?.addEventListener('change', (e) => {
            const file = e.target.files?.[0];
            if (file) uploadAvatar(file);
        });

        // Pestanyes
        document.querySelectorAll('.profile-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;

                // Actualitzar botons
                document.querySelectorAll('.profile-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Actualitzar contingut
                document.querySelectorAll('.profile-tab-content').forEach(c => c.classList.remove('active'));
                document.getElementById(`tab-${tabId}`)?.classList.add('active');
            });
        });

        // Logout
        document.getElementById('btn-logout')?.addEventListener('click', async () => {
            await window.ArionAuth.logout();
            window.location.href = 'index.html';
        });
    }

    // ─────────────────────────────────────────────────────────────────
    // UTILITATS
    // ─────────────────────────────────────────────────────────────────

    function formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('ca-ES', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    function formatCurrency(amount) {
        return new Intl.NumberFormat('ca-ES', {
            style: 'currency',
            currency: 'EUR'
        }).format(amount || 0);
    }

    function getEstatLabel(estat) {
        const labels = {
            'pendent': 'Pendent',
            'aprovada': 'Aprovada',
            'rebutjada': 'Rebutjada',
            'en_traduccio': 'En traducció',
            'completada': 'Completada'
        };
        return labels[estat] || estat;
    }

    // ─────────────────────────────────────────────────────────────────
    // INICIALITZACIÓ
    // ─────────────────────────────────────────────────────────────────

    // Inicialitzar quan el DOM estigui llest
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // Esperar una mica perquè els altres scripts carreguin
        setTimeout(init, 100);
    }

    // Exportar
    window.ArionProfile = {
        init,
        refresh: loadProfileData
    };

})();
