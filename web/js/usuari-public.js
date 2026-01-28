/**
 * ═══════════════════════════════════════════════════════════════════
 * USUARI PUBLIC - Biblioteca Universal Arion
 * Gestió de la pàgina de perfil públic d'usuari
 * ═══════════════════════════════════════════════════════════════════
 */

(function() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────
    // ESTAT
    // ─────────────────────────────────────────────────────────────────

    let profile = null;
    let badges = [];
    let mecenatges = [];
    let rankingPosition = null;

    // ─────────────────────────────────────────────────────────────────
    // INICIALITZACIÓ
    // ─────────────────────────────────────────────────────────────────

    async function init() {
        // Obtenir ID de l'usuari de la URL
        const params = new URLSearchParams(window.location.search);
        const userId = params.get('id');

        if (!userId) {
            showError('ID d\'usuari no especificat', 'Cal proporcionar un ID d\'usuari a la URL.');
            return;
        }

        // Carregar perfil
        await loadProfile(userId);
    }

    // ─────────────────────────────────────────────────────────────────
    // CÀRREGA DE DADES
    // ─────────────────────────────────────────────────────────────────

    async function loadProfile(userId) {
        showLoading(true);

        try {
            if (window.ArionSupabase?.isAvailable()) {
                // Mode Supabase
                await loadFromSupabase(userId);
            } else {
                // Mode localStorage (demo)
                await loadFromLocalStorage(userId);
            }
        } catch (error) {
            console.error('Error carregant perfil:', error);
            showError('Error carregant perfil', 'No s\'ha pogut carregar el perfil. Torna-ho a provar més tard.');
        }
    }

    async function loadFromSupabase(userId) {
        // Carregar perfil
        const { data: profileData, error: profileError } = await window.ArionSupabase.query('profiles', {
            eq: { id: userId },
            single: true
        });

        if (profileError || !profileData) {
            showError('Perfil no trobat', 'Aquest usuari no existeix.');
            return;
        }

        // Verificar privacitat
        if (profileData.perfil_public === false) {
            showError('Perfil privat', 'Aquest usuari ha configurat el seu perfil com a privat.');
            return;
        }

        profile = profileData;

        // Carregar medalles
        const { data: badgesData } = await window.ArionSupabase.query('usuari_medalles', {
            eq: { usuari_id: userId },
            select: '*, medalles(*)'
        });
        badges = badgesData || [];

        // Carregar mecenatges (només títols, sense imports detallats per privacitat)
        const { data: mecData } = await window.ArionSupabase.query('mecenatges', {
            eq: { usuari_id: userId },
            select: 'obra_id, obra_titol, obra_autor, data_aportacio',
            order: { column: 'data_aportacio', ascending: false }
        });
        mecenatges = mecData || [];

        // Obtenir posició al rànking
        const { data: rankingData } = await window.ArionSupabase.query('ranking_usuaris', {
            eq: { id: userId },
            single: true
        });
        rankingPosition = rankingData?.posicio || null;

        renderProfile();
    }

    async function loadFromLocalStorage(userId) {
        // En mode localStorage, només podem veure el nostre propi perfil
        const currentUser = window.ArionAuth?.getProfile() || JSON.parse(localStorage.getItem('arion_user') || 'null');

        if (!currentUser || currentUser.id !== userId) {
            showError('Mode demo', 'En mode demo només pots veure el teu propi perfil. <a href="perfil.html">Vés al teu perfil</a>');
            return;
        }

        // Verificar privacitat
        if (currentUser.perfil_public === false) {
            showError('Perfil privat', 'Has configurat el teu perfil com a privat.');
            return;
        }

        profile = currentUser;
        badges = currentUser.medalles || [];
        mecenatges = currentUser.mecenatges || [];
        rankingPosition = null; // No hi ha rànking en mode localStorage

        renderProfile();
    }

    // ─────────────────────────────────────────────────────────────────
    // RENDERITZAT
    // ─────────────────────────────────────────────────────────────────

    function renderProfile() {
        showLoading(false);
        document.getElementById('usuari-content').style.display = 'block';

        renderHeader();
        renderStats();
        renderProgress();
        renderBadges();
        renderObres();
        renderRanking();
        updatePageTitle();
    }

    function renderHeader() {
        const nivell = window.ArionGamification?.Level.getNivell(profile.punts_totals || 0) || {
            nivell: 1,
            icona: '📖',
            color: '#8B7355'
        };

        // Avatar
        const avatarContainer = document.getElementById('usuari-avatar');
        if (profile.avatar_url) {
            avatarContainer.innerHTML = `<img src="${profile.avatar_url}" alt="${profile.nom}">`;
        } else {
            avatarContainer.innerHTML = `<span class="avatar-placeholder">${(profile.nom || 'U')[0].toUpperCase()}</span>`;
        }

        // Level badge
        const levelBadge = document.getElementById('usuari-level-badge');
        levelBadge.innerHTML = `${nivell.icona} Nivell ${profile.nivell || 1}`;
        levelBadge.style.background = nivell.color;

        // Info
        document.getElementById('usuari-nom').textContent = `${profile.nom || 'Usuari'} ${profile.cognom ? profile.cognom[0] + '.' : ''}`;
        document.getElementById('usuari-titol').textContent = profile.titol || 'Lector Curiós';

        const bioEl = document.getElementById('usuari-bio');
        if (profile.bio) {
            bioEl.textContent = profile.bio;
            bioEl.style.display = 'block';
        } else {
            bioEl.style.display = 'none';
        }

        // Membre des de
        const membreText = document.querySelector('.membre-text');
        if (membreText && profile.creat_el) {
            membreText.textContent = `Membre des de ${formatDate(profile.creat_el || profile.creat)}`;
        }
    }

    function renderStats() {
        const container = document.getElementById('usuari-stats');
        const numMedalles = badges.length;

        container.innerHTML = `
            <div class="usuari-stat-card">
                <div class="usuari-stat-icon">🏅</div>
                <div class="usuari-stat-value">${profile.nivell || 1}</div>
                <div class="usuari-stat-label">Nivell</div>
            </div>
            <div class="usuari-stat-card">
                <div class="usuari-stat-icon">⭐</div>
                <div class="usuari-stat-value">${formatNumber(profile.punts_totals || 0)}</div>
                <div class="usuari-stat-label">Punts</div>
            </div>
            <div class="usuari-stat-card">
                <div class="usuari-stat-icon">📚</div>
                <div class="usuari-stat-value">${profile.num_obres_patrocinades || 0}</div>
                <div class="usuari-stat-label">Obres patrocinades</div>
            </div>
            <div class="usuari-stat-card">
                <div class="usuari-stat-icon">🏆</div>
                <div class="usuari-stat-value">${numMedalles}</div>
                <div class="usuari-stat-label">Medalles</div>
            </div>
        `;
    }

    function renderProgress() {
        const container = document.getElementById('usuari-progress');
        if (!window.ArionGamification) {
            container.style.display = 'none';
            return;
        }

        container.innerHTML = window.ArionGamification.UI.renderBarraProgres(profile.punts_totals || 0);
    }

    function renderBadges() {
        const container = document.getElementById('usuari-medalles');

        if (badges.length === 0) {
            container.innerHTML = `
                <div class="no-medalles">
                    <p>Aquest usuari encara no ha obtingut cap medalla.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = badges.map(badge => {
            // Si ve de Supabase, la medalla està dins de medalles
            const medalla = badge.medalles || window.ArionGamification?.MEDALLES[badge.id] || window.ArionGamification?.MEDALLES[badge.medalla_id] || badge;

            return `
                <div class="usuari-medalla" title="${medalla.descripcio || ''}">
                    <div class="usuari-medalla-icona">${medalla.icona || '🏅'}</div>
                    <div class="usuari-medalla-nom">${medalla.nom || 'Medalla'}</div>
                    ${badge.obtinguda_el ? `
                        <div class="usuari-medalla-data">${formatDateShort(badge.obtinguda_el)}</div>
                    ` : ''}
                </div>
            `;
        }).join('');
    }

    function renderObres() {
        const section = document.getElementById('usuari-obres-section');
        const container = document.getElementById('usuari-obres');

        if (mecenatges.length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';

        // Agrupar per obra (eliminar duplicats)
        const obresUniques = {};
        mecenatges.forEach(mec => {
            if (!obresUniques[mec.obra_id]) {
                obresUniques[mec.obra_id] = {
                    id: mec.obra_id,
                    titol: mec.obra_titol || 'Obra',
                    autor: mec.obra_autor || '',
                    data: mec.data_aportacio || mec.data
                };
            }
        });

        const obres = Object.values(obresUniques);

        container.innerHTML = obres.map(obra => `
            <div class="usuari-obra">
                <div class="usuari-obra-icona">📖</div>
                <div class="usuari-obra-info">
                    <div class="usuari-obra-titol">${obra.titol}</div>
                    ${obra.autor ? `<div class="usuari-obra-autor">${obra.autor}</div>` : ''}
                </div>
            </div>
        `).join('');
    }

    function renderRanking() {
        const container = document.getElementById('usuari-ranking');

        if (rankingPosition === null) {
            container.innerHTML = `
                <p class="ranking-label">Rànking no disponible</p>
            `;
            return;
        }

        const medalIcon = rankingPosition === 1 ? '🥇' :
                         rankingPosition === 2 ? '🥈' :
                         rankingPosition === 3 ? '🥉' : '';

        container.innerHTML = `
            <div class="ranking-position">
                ${medalIcon ? `<span class="ranking-medal">${medalIcon}</span>` : ''}
                <span class="ranking-number">#${rankingPosition}</span>
            </div>
            <p class="ranking-label">Posició al rànking global de mecenes</p>
        `;
    }

    function updatePageTitle() {
        document.title = `${profile.nom || 'Usuari'} - Perfil - Biblioteca Arion`;
    }

    // ─────────────────────────────────────────────────────────────────
    // UI HELPERS
    // ─────────────────────────────────────────────────────────────────

    function showLoading(show) {
        document.getElementById('usuari-loading').style.display = show ? 'flex' : 'none';
    }

    function showError(title, message) {
        showLoading(false);
        document.getElementById('usuari-error').style.display = 'flex';
        document.getElementById('error-title').textContent = title;
        document.getElementById('error-message').innerHTML = message;
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('ca-ES', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    function formatDateShort(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('ca-ES', {
            year: 'numeric',
            month: 'short'
        });
    }

    function formatNumber(num) {
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'k';
        }
        return num.toString();
    }

    // ─────────────────────────────────────────────────────────────────
    // INICIALITZACIÓ
    // ─────────────────────────────────────────────────────────────────

    // Inicialitzar quan el DOM estigui llest
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            // Esperar que els altres scripts carreguin
            setTimeout(init, 150);
        });
    } else {
        setTimeout(init, 150);
    }

    // Exportar
    window.ArionUsuariPublic = {
        init,
        loadProfile
    };

})();
