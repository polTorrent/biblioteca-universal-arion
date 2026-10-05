/**
 * ═══════════════════════════════════════════════════════════════════
 * GAMIFICATION - Biblioteca Universal Arion
 * Sistema de punts, nivells, medalles i rànking
 * ═══════════════════════════════════════════════════════════════════
 */

(function() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────
    // DEFINICIONS DE NIVELLS
    // ─────────────────────────────────────────────────────────────────

    const NIVELLS = [
        { nivell: 1, nom: 'Lector', titol: 'Lector Curiós', punts: 0, icona: '📖', color: '#8B7355' },
        { nivell: 2, nom: 'Descobridor', titol: 'Descobridor de Clàssics', punts: 50, icona: '🔍', color: '#6B8E23' },
        { nivell: 3, nom: 'Bibliòfil', titol: 'Bibliòfil Dedicat', punts: 150, icona: '📚', color: '#4682B4' },
        { nivell: 4, nom: 'Mecenes', titol: 'Mecenes de les Lletres', punts: 300, icona: '🎭', color: '#9370DB' },
        { nivell: 5, nom: 'Patrocinador', titol: 'Patrocinador Cultural', punts: 500, icona: '🏛️', color: '#DAA520' },
        { nivell: 6, nom: 'Benefactor', titol: 'Benefactor de la Cultura', punts: 1000, icona: '👑', color: '#CD853F' },
        { nivell: 7, nom: 'Llegenda', titol: 'Llegenda d\'Arion', punts: 2500, icona: '⭐', color: '#FFD700' }
    ];

    // ─────────────────────────────────────────────────────────────────
    // DEFINICIONS DE MEDALLES
    // ─────────────────────────────────────────────────────────────────

    const MEDALLES = {
        // Medalles de mecenatge
        'primera-gota': {
            id: 'primera-gota',
            nom: 'Primera Gota',
            descripcio: 'Has fet la teva primera aportació',
            icona: '💧',
            categoria: 'mecenatge',
            punts: 10,
            requisits: { min_aportacions: 1 }
        },
        'mecenes-bronze': {
            id: 'mecenes-bronze',
            nom: 'Mecenes de Bronze',
            descripcio: 'Has aportat més de 10€',
            icona: '🥉',
            categoria: 'mecenatge',
            punts: 25,
            requisits: { min_total: 10 }
        },
        'mecenes-plata': {
            id: 'mecenes-plata',
            nom: 'Mecenes de Plata',
            descripcio: 'Has aportat més de 50€',
            icona: '🥈',
            categoria: 'mecenatge',
            punts: 50,
            requisits: { min_total: 50 }
        },
        'mecenes-or': {
            id: 'mecenes-or',
            nom: 'Mecenes d\'Or',
            descripcio: 'Has aportat més de 100€',
            icona: '🥇',
            categoria: 'mecenatge',
            punts: 100,
            requisits: { min_total: 100 }
        },
        'mecenes-diamant': {
            id: 'mecenes-diamant',
            nom: 'Mecenes de Diamant',
            descripcio: 'Has aportat més de 500€',
            icona: '💎',
            categoria: 'mecenatge',
            punts: 250,
            requisits: { min_total: 500 }
        },
        'colleccionista': {
            id: 'colleccionista',
            nom: 'Col·leccionista',
            descripcio: 'Has patrocinat 5 obres diferents',
            icona: '🗃️',
            categoria: 'mecenatge',
            punts: 75,
            requisits: { min_obres: 5 }
        },
        'patrocinador-exclusiu': {
            id: 'patrocinador-exclusiu',
            nom: 'Patrocinador Exclusiu',
            descripcio: 'Has finançat una traducció sencera',
            icona: '🌟',
            categoria: 'mecenatge',
            punts: 200,
            requisits: { financament_complet: true }
        },

        // Medalles de comunitat
        'veu-activa': {
            id: 'veu-activa',
            nom: 'Veu Activa',
            descripcio: 'Has votat 10 propostes',
            icona: '🗳️',
            categoria: 'comunitat',
            punts: 20,
            requisits: { min_vots: 10 }
        },
        'proposador': {
            id: 'proposador',
            nom: 'Proposador',
            descripcio: 'Has proposat una traducció',
            icona: '💡',
            categoria: 'comunitat',
            punts: 30,
            requisits: { min_propostes: 1 }
        },
        'ull-atent': {
            id: 'ull-atent',
            nom: 'Ull Atent',
            descripcio: 'Has reportat un error de traducció',
            icona: '👁️',
            categoria: 'comunitat',
            punts: 15,
            requisits: { min_correccions: 1 }
        },
        'influencer': {
            id: 'influencer',
            nom: 'Influencer',
            descripcio: 'Has compartit 5 obres a xarxes socials',
            icona: '📢',
            categoria: 'comunitat',
            punts: 25,
            requisits: { min_compartits: 5 }
        },

        // Medalles secretes
        'fundador': {
            id: 'fundador',
            nom: 'Fundador',
            descripcio: 'Ets dels primers 100 usuaris registrats',
            icona: '🏆',
            categoria: 'secreta',
            punts: 100,
            requisits: { max_usuari_id: 100 },
            secret: true
        },
        'maratonista': {
            id: 'maratonista',
            nom: 'Maratonista',
            descripcio: 'Has aportat 7 dies seguits',
            icona: '🏃',
            categoria: 'secreta',
            punts: 50,
            requisits: { dies_seguits: 7 },
            secret: true
        },
        'amic-grecs': {
            id: 'amic-grecs',
            nom: 'Amic dels Grecs',
            descripcio: 'Has patrocinat 3 obres gregues',
            icona: '🏛️',
            categoria: 'secreta',
            punts: 40,
            requisits: { idioma: 'grec', min_obres: 3 },
            secret: true
        },
        'filolog': {
            id: 'filolog',
            nom: 'Fil·lòleg',
            descripcio: 'Has llegit més de 10 obres completes',
            icona: '📜',
            categoria: 'secreta',
            punts: 60,
            requisits: { obres_llegides: 10 },
            secret: true
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // PUNTS
    // ─────────────────────────────────────────────────────────────────

    const PUNTS = {
        REGISTRE: 10,
        PRIMERA_APORTACIO: 25,
        PER_EURO: 10,
        PROPOSTA: 15,
        VOT: 2,
        COMPARTIR: 5,
        CORRECCIO: 10
    };

    // ─────────────────────────────────────────────────────────────────
    // GESTIÓ DE NIVELLS
    // ─────────────────────────────────────────────────────────────────

    const LevelManager = {
        /**
         * Obté el nivell per una quantitat de punts
         */
        getNivell(punts) {
            for (let i = NIVELLS.length - 1; i >= 0; i--) {
                if (punts >= NIVELLS[i].punts) {
                    return NIVELLS[i];
                }
            }
            return NIVELLS[0];
        },

        /**
         * Obté el proper nivell
         */
        getProperNivell(punts) {
            const nivellActual = this.getNivell(punts);
            const index = NIVELLS.findIndex(n => n.nivell === nivellActual.nivell);
            return index < NIVELLS.length - 1 ? NIVELLS[index + 1] : null;
        },

        /**
         * Calcula el progrés cap al proper nivell
         */
        getProgres(punts) {
            const nivellActual = this.getNivell(punts);
            const properNivell = this.getProperNivell(punts);

            if (!properNivell) {
                return { percentatge: 100, puntsActuals: punts, puntsFalten: 0 };
            }

            const puntsBase = nivellActual.punts;
            const puntsObjectiu = properNivell.punts;
            const puntsEnNivell = punts - puntsBase;
            const puntsNecessaris = puntsObjectiu - puntsBase;
            const percentatge = Math.min(100, Math.round((puntsEnNivell / puntsNecessaris) * 100));

            return {
                percentatge,
                puntsActuals: puntsEnNivell,
                puntsTotals: puntsNecessaris,
                puntsFalten: puntsObjectiu - punts
            };
        },

        /**
         * Obté tots els nivells
         */
        getAllNivells() {
            return NIVELLS;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // GESTIÓ DE MEDALLES
    // ─────────────────────────────────────────────────────────────────

    const BadgeManager = {
        /**
         * Verifica si un usuari compleix els requisits d'una medalla
         */
        verificarRequisits(medalla, perfil) {
            const req = medalla.requisits;
            if (!req) return false;

            // Requisits bàsics
            if (req.min_aportacions !== undefined) {
                if ((perfil.num_mecenatges || 0) < req.min_aportacions) return false;
            }
            if (req.min_total !== undefined) {
                if ((perfil.total_aportat || 0) < req.min_total) return false;
            }
            if (req.min_obres !== undefined) {
                if ((perfil.num_obres_patrocinades || 0) < req.min_obres) return false;
            }
            if (req.min_vots !== undefined) {
                if ((perfil.num_vots || 0) < req.min_vots) return false;
            }
            if (req.min_propostes !== undefined) {
                if ((perfil.num_propostes || 0) < req.min_propostes) return false;
            }

            return true;
        },

        /**
         * Verifica totes les medalles per un perfil (mode localStorage)
         */
        verificarMedalles(perfil) {
            const medallesObtingudes = perfil.medalles || [];
            const novesMedalles = [];

            for (const [id, medalla] of Object.entries(MEDALLES)) {
                // Saltar si ja la té
                if (medallesObtingudes.some(m => m.id === id)) continue;

                // Verificar requisits
                if (this.verificarRequisits(medalla, perfil)) {
                    novesMedalles.push({
                        id: medalla.id,
                        nom: medalla.nom,
                        icona: medalla.icona,
                        obtinguda_el: new Date().toISOString()
                    });
                }
            }

            return novesMedalles;
        },

        /**
         * Obté informació d'una medalla
         */
        getMedalla(id) {
            return MEDALLES[id] || null;
        },

        /**
         * Obté totes les medalles (visibles)
         */
        getAllMedalles(incloureSecretes = false) {
            return Object.values(MEDALLES).filter(m => incloureSecretes || !m.secret);
        },

        /**
         * Obté medalles per categoria
         */
        getMedallesPerCategoria(categoria) {
            return Object.values(MEDALLES).filter(m => m.categoria === categoria && !m.secret);
        },

        /**
         * Calcula el progrés cap a una medalla
         */
        getProgresMedalla(medalla, perfil) {
            const req = medalla.requisits;
            if (!req) return null;

            if (req.min_aportacions !== undefined) {
                return {
                    actual: perfil.num_mecenatges || 0,
                    objectiu: req.min_aportacions,
                    percentatge: Math.min(100, Math.round(((perfil.num_mecenatges || 0) / req.min_aportacions) * 100))
                };
            }
            if (req.min_total !== undefined) {
                return {
                    actual: perfil.total_aportat || 0,
                    objectiu: req.min_total,
                    percentatge: Math.min(100, Math.round(((perfil.total_aportat || 0) / req.min_total) * 100)),
                    unitat: '€'
                };
            }
            if (req.min_obres !== undefined) {
                return {
                    actual: perfil.num_obres_patrocinades || 0,
                    objectiu: req.min_obres,
                    percentatge: Math.min(100, Math.round(((perfil.num_obres_patrocinades || 0) / req.min_obres) * 100))
                };
            }
            if (req.min_vots !== undefined) {
                return {
                    actual: perfil.num_vots || 0,
                    objectiu: req.min_vots,
                    percentatge: Math.min(100, Math.round(((perfil.num_vots || 0) / req.min_vots) * 100))
                };
            }
            if (req.min_propostes !== undefined) {
                return {
                    actual: perfil.num_propostes || 0,
                    objectiu: req.min_propostes,
                    percentatge: Math.min(100, Math.round(((perfil.num_propostes || 0) / req.min_propostes) * 100))
                };
            }

            return null;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // SISTEMA D'ANIMACIONS
    // ─────────────────────────────────────────────────────────────────

    const AnimationManager = {
        /**
         * Mostra animació de nova medalla
         */
        showNovaMedalla(medalla) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay modal-medalla active';
            modal.innerHTML = `
                <div class="modal medalla-modal">
                    <div class="medalla-celebracio">
                        <div class="medalla-confetti"></div>
                        <div class="medalla-icona-gran">${medalla.icona}</div>
                        <h2>Nova Medalla!</h2>
                        <h3>${medalla.nom}</h3>
                        <p>${medalla.descripcio}</p>
                        <div class="medalla-punts">+${medalla.punts} punts</div>
                        <button class="btn-submit" onclick="this.closest('.modal-overlay').remove()">
                            Genial!
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // Animació de confetti
            this.createConfetti(modal.querySelector('.medalla-confetti'));

            // Tancar amb Escape
            const closeHandler = (e) => {
                if (e.key === 'Escape') {
                    modal.remove();
                    document.removeEventListener('keydown', closeHandler);
                }
            };
            document.addEventListener('keydown', closeHandler);
        },

        /**
         * Mostra animació de pujada de nivell
         */
        showLevelUp(nivell) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay modal-levelup active';
            modal.innerHTML = `
                <div class="modal levelup-modal">
                    <div class="levelup-celebracio">
                        <div class="levelup-rays"></div>
                        <div class="levelup-icona">${nivell.icona}</div>
                        <h2>Nivell ${nivell.nivell}!</h2>
                        <h3>${nivell.titol}</h3>
                        <p>Has assolit un nou nivell de mecenatge</p>
                        <button class="btn-submit" onclick="this.closest('.modal-overlay').remove()">
                            Continuar
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // Tancar amb Escape
            const closeHandler = (e) => {
                if (e.key === 'Escape') {
                    modal.remove();
                    document.removeEventListener('keydown', closeHandler);
                }
            };
            document.addEventListener('keydown', closeHandler);
        },

        /**
         * Crea efecte de confetti
         */
        createConfetti(container) {
            const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#9370DB'];
            const confettiCount = 50;

            for (let i = 0; i < confettiCount; i++) {
                const confetti = document.createElement('div');
                confetti.className = 'confetti-piece';
                confetti.style.cssText = `
                    position: absolute;
                    width: 10px;
                    height: 10px;
                    background: ${colors[Math.floor(Math.random() * colors.length)]};
                    left: ${Math.random() * 100}%;
                    top: -10px;
                    opacity: 1;
                    transform: rotate(${Math.random() * 360}deg);
                    animation: confetti-fall ${1 + Math.random() * 2}s ease-out forwards;
                    animation-delay: ${Math.random() * 0.5}s;
                `;
                container.appendChild(confetti);
            }

            // Afegir estils d'animació si no existeixen
            if (!document.getElementById('confetti-styles')) {
                const style = document.createElement('style');
                style.id = 'confetti-styles';
                style.textContent = `
                    @keyframes confetti-fall {
                        0% {
                            transform: translateY(0) rotate(0deg);
                            opacity: 1;
                        }
                        100% {
                            transform: translateY(300px) rotate(720deg);
                            opacity: 0;
                        }
                    }
                `;
                document.head.appendChild(style);
            }
        },

        /**
         * Mostra toast de punts guanyats
         */
        showPuntsToast(punts, motiu) {
            const toast = document.createElement('div');
            toast.className = 'punts-toast';
            toast.innerHTML = `
                <span class="punts-toast-icon">⭐</span>
                <span class="punts-toast-text">+${punts} punts</span>
                <span class="punts-toast-motiu">${motiu}</span>
            `;
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
                color: #333;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-weight: 600;
                box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);
                z-index: 10000;
                animation: slideIn 0.3s ease-out;
            `;

            document.body.appendChild(toast);

            setTimeout(() => {
                toast.style.animation = 'slideIn 0.3s ease reverse';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // RÀNKING
    // ─────────────────────────────────────────────────────────────────

    const RankingManager = {
        /**
         * Obté el rànking d'usuaris (Supabase)
         */
        async getRanking(limit = 10) {
            if (window.ArionSupabase?.isAvailable()) {
                const { data, error } = await window.ArionSupabase.query('ranking_usuaris', {
                    limit,
                    order: { column: 'posicio', ascending: true }
                });

                if (error) {
                    console.error('Error obtenint rànking:', error);
                    return [];
                }

                return data || [];
            }

            // Mode localStorage: no hi ha rànking global
            return [];
        },

        /**
         * Obté la posició de l'usuari actual
         */
        async getPosicioUsuari(usuariId) {
            if (window.ArionSupabase?.isAvailable()) {
                const { data, error } = await window.ArionSupabase.query('ranking_usuaris', {
                    eq: { id: usuariId },
                    single: true
                });

                if (error || !data) return null;
                return data.posicio;
            }

            return null;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // RENDERITZAT UI
    // ─────────────────────────────────────────────────────────────────

    const GamificationUI = {
        /**
         * Renderitza la barra de progrés de nivell
         */
        renderBarraProgres(punts) {
            const nivell = LevelManager.getNivell(punts);
            const properNivell = LevelManager.getProperNivell(punts);
            const progres = LevelManager.getProgres(punts);

            if (!properNivell) {
                return `
                    <div class="progress-bar-container">
                        <div class="progress-labels">
                            <span class="progress-current">${nivell.icona} Nivell màxim assolit!</span>
                            <span class="progress-points">${punts} punts</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: 100%; background: linear-gradient(90deg, ${nivell.color}, #FFD700)"></div>
                        </div>
                    </div>
                `;
            }

            return `
                <div class="progress-bar-container">
                    <div class="progress-labels">
                        <span class="progress-current">${nivell.icona} ${nivell.nom}</span>
                        <span class="progress-points">${punts} / ${properNivell.punts} punts</span>
                        <span class="progress-next">${properNivell.icona} ${properNivell.nom}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progres.percentatge}%; background: ${nivell.color}"></div>
                    </div>
                    <p class="progress-remaining">Falten ${progres.puntsFalten} punts per al proper nivell</p>
                </div>
            `;
        },

        /**
         * Renderitza la graella de medalles
         */
        renderMedalles(medallesObtingudes, perfil, mostrarProgrés = true) {
            const totes = BadgeManager.getAllMedalles();
            const obtingudes = medallesObtingudes.map(m => m.id || m);

            return `
                <div class="medalles-grid">
                    ${totes.map(medalla => {
                        const teMedialla = obtingudes.includes(medalla.id);
                        const progres = !teMedialla && mostrarProgrés ?
                            BadgeManager.getProgresMedalla(medalla, perfil) : null;

                        return `
                            <div class="medalla-card ${teMedialla ? 'obtinguda' : 'bloquejada'}" title="${medalla.descripcio}">
                                <div class="medalla-icona ${teMedialla ? '' : 'grayscale'}">${medalla.icona}</div>
                                <div class="medalla-nom">${medalla.nom}</div>
                                ${teMedialla ? `
                                    <div class="medalla-punts">+${medalla.punts} pts</div>
                                ` : progres ? `
                                    <div class="medalla-progres">
                                        <div class="mini-progress">
                                            <div class="mini-progress-fill" style="width: ${progres.percentatge}%"></div>
                                        </div>
                                        <span>${progres.actual}/${progres.objectiu}${progres.unitat || ''}</span>
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        },

        /**
         * Renderitza el rànking
         */
        renderRanking(usuaris, usuariActualId) {
            if (!usuaris || usuaris.length === 0) {
                return '<p class="no-ranking">No hi ha dades de rànking disponibles</p>';
            }

            return `
                <div class="ranking-list">
                    ${usuaris.map((usuari, index) => {
                        const esActual = usuari.id === usuariActualId;
                        const medallaPos = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '';
                        const profileUrl = esActual ? 'perfil.html' : `usuari.html?id=${usuari.id}`;

                        return `
                            <a href="${profileUrl}" class="ranking-item ${esActual ? 'actual' : ''}" title="Veure perfil de ${usuari.nom || 'Anònim'}">
                                <span class="ranking-pos">${medallaPos || (index + 1)}</span>
                                <div class="ranking-avatar">
                                    ${usuari.avatar_url ?
                                        `<img src="${usuari.avatar_url}" alt="${usuari.nom}">` :
                                        `<span>${(usuari.nom || '?')[0].toUpperCase()}</span>`
                                    }
                                </div>
                                <div class="ranking-info">
                                    <span class="ranking-nom">${usuari.nom || 'Anònim'}</span>
                                    <span class="ranking-titol">${usuari.titol || 'Lector Curiós'}</span>
                                </div>
                                <div class="ranking-stats">
                                    <span class="ranking-punts">${usuari.punts_totals || 0} pts</span>
                                    <span class="ranking-medalles">${usuari.num_medalles || 0} 🏅</span>
                                </div>
                            </a>
                        `;
                    }).join('')}
                </div>
            `;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // EXPORTAR API
    // ─────────────────────────────────────────────────────────────────

    window.ArionGamification = {
        // Constants
        NIVELLS,
        MEDALLES,
        PUNTS,

        // Managers
        Level: LevelManager,
        Badge: BadgeManager,
        Ranking: RankingManager,
        Animation: AnimationManager,
        UI: GamificationUI
    };

})();
