/**
 * ═══════════════════════════════════════════════════════════════════
 * AUTH MANAGER - Biblioteca Universal Arion
 * Gestió d'autenticació amb Supabase + fallback localStorage
 * ═══════════════════════════════════════════════════════════════════
 */

(function() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────
    // CONSTANTS
    // ─────────────────────────────────────────────────────────────────

    const STORAGE_KEYS = {
        USER: 'arion_user',
        EMAIL: 'arion_user_email',
        PASS: 'arion_user_pass',
        MIGRATION_DONE: 'arion_migration_done'
    };

    // ─────────────────────────────────────────────────────────────────
    // ESTAT INTERN
    // ─────────────────────────────────────────────────────────────────

    let currentUser = null;
    let currentProfile = null;
    let authListeners = [];

    // ─────────────────────────────────────────────────────────────────
    // UTILITATS
    // ─────────────────────────────────────────────────────────────────

    function notifyListeners(event, data) {
        authListeners.forEach(listener => {
            try {
                listener(event, data);
            } catch (e) {
                console.error('[AuthManager] Error en listener:', e);
            }
        });
    }

    // ─────────────────────────────────────────────────────────────────
    // MODE SUPABASE
    // ─────────────────────────────────────────────────────────────────

    const SupabaseAuth = {
        /**
         * Registra un nou usuari
         */
        async register(email, password, metadata = {}) {
            const client = window.ArionSupabase?.getClient();
            if (!client) return { user: null, error: { message: 'Supabase no disponible' } };

            const { data, error } = await client.auth.signUp({
                email,
                password,
                options: {
                    data: {
                        nom: metadata.nom || '',
                        cognom: metadata.cognom || ''
                    }
                }
            });

            if (error) return { user: null, error };

            // Actualitzar perfil amb dades addicionals
            if (data.user && metadata.nom) {
                await window.ArionSupabase.update('profiles', {
                    nom: metadata.nom,
                    cognom: metadata.cognom || '',
                    rebre_newsletter: metadata.newsletter || false
                }, { id: data.user.id });
            }

            return { user: data.user, error: null };
        },

        /**
         * Inicia sessió
         */
        async login(email, password) {
            const client = window.ArionSupabase?.getClient();
            if (!client) return { user: null, error: { message: 'Supabase no disponible' } };

            const { data, error } = await client.auth.signInWithPassword({
                email,
                password
            });

            if (error) return { user: null, error };
            return { user: data.user, error: null };
        },

        /**
         * Inicia sessió amb OAuth (Google, GitHub, etc.)
         */
        async loginWithOAuth(provider) {
            const client = window.ArionSupabase?.getClient();
            if (!client) return { user: null, error: { message: 'Supabase no disponible' } };

            const { data, error } = await client.auth.signInWithOAuth({
                provider,
                options: {
                    redirectTo: window.location.origin + '/perfil.html'
                }
            });

            return { url: data?.url, error };
        },

        /**
         * Tanca sessió
         */
        async logout() {
            const client = window.ArionSupabase?.getClient();
            if (!client) return { error: { message: 'Supabase no disponible' } };

            const { error } = await client.auth.signOut();
            return { error };
        },

        /**
         * Envia email per recuperar contrasenya
         */
        async resetPassword(email) {
            const client = window.ArionSupabase?.getClient();
            if (!client) return { error: { message: 'Supabase no disponible' } };

            const { error } = await client.auth.resetPasswordForEmail(email, {
                redirectTo: window.location.origin + '/reset-password.html'
            });

            return { error };
        },

        /**
         * Actualitza la contrasenya
         */
        async updatePassword(newPassword) {
            const client = window.ArionSupabase?.getClient();
            if (!client) return { error: { message: 'Supabase no disponible' } };

            const { error } = await client.auth.updateUser({
                password: newPassword
            });

            return { error };
        },

        /**
         * Obté l'usuari actual
         */
        async getUser() {
            const client = window.ArionSupabase?.getClient();
            if (!client) return null;

            const { data: { user } } = await client.auth.getUser();
            return user;
        },

        /**
         * Obté la sessió actual
         */
        async getSession() {
            const client = window.ArionSupabase?.getClient();
            if (!client) return null;

            const { data: { session } } = await client.auth.getSession();
            return session;
        },

        /**
         * Obté el perfil de l'usuari
         */
        async getProfile(userId) {
            const { data, error } = await window.ArionSupabase.query('profiles', {
                eq: { id: userId },
                single: true
            });

            if (error) return null;
            return data;
        },

        /**
         * Actualitza el perfil
         */
        async updateProfile(userId, updates) {
            return await window.ArionSupabase.update('profiles', {
                ...updates,
                actualitzat_el: new Date().toISOString()
            }, { id: userId }, { single: true, select: '*' });
        },

        /**
         * Configura listener per canvis d'autenticació
         */
        onAuthStateChange(callback) {
            const client = window.ArionSupabase?.getClient();
            if (!client) return null;

            return client.auth.onAuthStateChange((event, session) => {
                callback(event, session);
            });
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // MODE LOCALSTORAGE (FALLBACK)
    // ─────────────────────────────────────────────────────────────────

    const LocalAuth = {
        /**
         * Registra un nou usuari
         */
        register(email, password, metadata = {}) {
            // Verificar si ja existeix
            const existingEmail = localStorage.getItem(STORAGE_KEYS.EMAIL);
            if (existingEmail === email) {
                return { user: null, error: { message: 'Aquest email ja està registrat' } };
            }

            const user = {
                id: 'usr_' + Date.now(),
                email,
                nom: metadata.nom || email.split('@')[0],
                cognom: metadata.cognom || '',
                creat: new Date().toISOString(),
                mecenatges: [],
                total_aportat: 0,
                punts_totals: 10,
                nivell: 1,
                titol: 'Lector Curiós',
                num_mecenatges: 0,
                num_obres_patrocinades: 0,
                num_propostes: 0,
                num_vots: 0,
                medalles: [],
                avatar_url: null,
                bio: '',
                perfil_public: true,
                rebre_newsletter: metadata.newsletter || false
            };

            localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
            localStorage.setItem(STORAGE_KEYS.EMAIL, email);
            localStorage.setItem(STORAGE_KEYS.PASS, btoa(password));

            return { user, error: null };
        },

        /**
         * Inicia sessió
         */
        login(email, password) {
            const savedEmail = localStorage.getItem(STORAGE_KEYS.EMAIL);
            const savedPass = localStorage.getItem(STORAGE_KEYS.PASS);

            if (savedEmail === email && savedPass === btoa(password)) {
                const userData = localStorage.getItem(STORAGE_KEYS.USER);
                if (userData) {
                    return { user: JSON.parse(userData), error: null };
                }
            }

            // Mode demo: crear usuari temporal
            const user = {
                id: 'usr_demo_' + Date.now(),
                email,
                nom: email.split('@')[0],
                cognom: '',
                creat: new Date().toISOString(),
                mecenatges: [],
                total_aportat: 0,
                punts_totals: 10,
                nivell: 1,
                titol: 'Lector Curiós',
                num_mecenatges: 0,
                num_obres_patrocinades: 0,
                num_propostes: 0,
                num_vots: 0,
                medalles: [],
                avatar_url: null,
                bio: '',
                perfil_public: true
            };

            localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
            return { user, error: null };
        },

        /**
         * Tanca sessió
         */
        logout() {
            localStorage.removeItem(STORAGE_KEYS.USER);
            return { error: null };
        },

        /**
         * Obté l'usuari actual
         */
        getUser() {
            const userData = localStorage.getItem(STORAGE_KEYS.USER);
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
         * Obté el perfil
         */
        getProfile() {
            return this.getUser();
        },

        /**
         * Actualitza el perfil
         */
        updateProfile(updates) {
            const user = this.getUser();
            if (!user) return { data: null, error: { message: 'No autenticat' } };

            const updatedUser = { ...user, ...updates };
            localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(updatedUser));
            return { data: updatedUser, error: null };
        },

        /**
         * Afegeix un mecenatge
         */
        addMecenatge(obraId, obraTitol, importValue) {
            const user = this.getUser();
            if (!user) return null;

            const mecenatge = {
                id: 'mec_' + Date.now(),
                obra_id: obraId,
                obra_titol: obraTitol,
                import: importValue,
                data: new Date().toISOString(),
                tipus: 'micromecenatge',
                estat: 'completat'
            };

            user.mecenatges = user.mecenatges || [];
            user.mecenatges.push(mecenatge);
            user.total_aportat = (user.total_aportat || 0) + importValue;
            user.num_mecenatges = (user.num_mecenatges || 0) + 1;

            // Actualitzar obres úniques
            const obresUniques = new Set(user.mecenatges.map(m => m.obra_id));
            user.num_obres_patrocinades = obresUniques.size;

            // Calcular punts
            const esPrimeraAportacio = user.mecenatges.length === 1;
            let puntsNous = Math.floor(importValue * 10);
            if (esPrimeraAportacio) puntsNous += 25;

            user.punts_totals = (user.punts_totals || 10) + puntsNous;

            // Recalcular nivell
            const nivells = [
                { nivell: 7, punts: 2500, titol: 'Llegenda d\'Arion' },
                { nivell: 6, punts: 1000, titol: 'Benefactor de la Cultura' },
                { nivell: 5, punts: 500, titol: 'Patrocinador Cultural' },
                { nivell: 4, punts: 300, titol: 'Mecenes de les Lletres' },
                { nivell: 3, punts: 150, titol: 'Bibliòfil Dedicat' },
                { nivell: 2, punts: 50, titol: 'Descobridor de Clàssics' },
                { nivell: 1, punts: 0, titol: 'Lector Curiós' }
            ];

            for (const n of nivells) {
                if (user.punts_totals >= n.punts) {
                    user.nivell = n.nivell;
                    user.titol = n.titol;
                    break;
                }
            }

            localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
            return user;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // API PÚBLICA UNIFICADA
    // ─────────────────────────────────────────────────────────────────

    const AuthManager = {
        /**
         * Inicialitza el gestor d'autenticació
         */
        async init() {
            // Esperar que Supabase estigui llest
            await new Promise(resolve => setTimeout(resolve, 100));

            if (window.ArionSupabase?.isAvailable()) {
                // Configurar listener de Supabase
                SupabaseAuth.onAuthStateChange(async (event, session) => {
                    if (event === 'SIGNED_IN' && session?.user) {
                        currentUser = session.user;
                        currentProfile = await SupabaseAuth.getProfile(session.user.id);
                        notifyListeners('SIGNED_IN', { user: currentUser, profile: currentProfile });
                    } else if (event === 'SIGNED_OUT') {
                        currentUser = null;
                        currentProfile = null;
                        notifyListeners('SIGNED_OUT', null);
                    }
                });

                // Verificar sessió existent
                const user = await SupabaseAuth.getUser();
                if (user) {
                    currentUser = user;
                    currentProfile = await SupabaseAuth.getProfile(user.id);

                    // Intentar migració si cal
                    await this.migrateFromLocalStorage();
                }
            } else {
                // Mode localStorage
                currentUser = LocalAuth.getUser();
                currentProfile = currentUser;
            }

            // Actualitzar UI
            this.updateAuthUI();
        },

        /**
         * Registra un nou usuari
         */
        async register(email, password, metadata = {}) {
            if (window.ArionSupabase?.isAvailable()) {
                const result = await SupabaseAuth.register(email, password, metadata);
                if (!result.error && result.user) {
                    currentUser = result.user;
                    currentProfile = await SupabaseAuth.getProfile(result.user.id);
                    notifyListeners('SIGNED_IN', { user: currentUser, profile: currentProfile });
                    this.updateAuthUI();
                }
                return result;
            } else {
                const result = LocalAuth.register(email, password, metadata);
                if (!result.error && result.user) {
                    currentUser = result.user;
                    currentProfile = result.user;
                    notifyListeners('SIGNED_IN', { user: currentUser, profile: currentProfile });
                    this.updateAuthUI();
                }
                return result;
            }
        },

        /**
         * Inicia sessió
         */
        async login(email, password) {
            if (window.ArionSupabase?.isAvailable()) {
                const result = await SupabaseAuth.login(email, password);
                if (!result.error && result.user) {
                    currentUser = result.user;
                    currentProfile = await SupabaseAuth.getProfile(result.user.id);
                    notifyListeners('SIGNED_IN', { user: currentUser, profile: currentProfile });
                    this.updateAuthUI();
                }
                return result;
            } else {
                const result = LocalAuth.login(email, password);
                if (!result.error && result.user) {
                    currentUser = result.user;
                    currentProfile = result.user;
                    notifyListeners('SIGNED_IN', { user: currentUser, profile: currentProfile });
                    this.updateAuthUI();
                }
                return result;
            }
        },

        /**
         * Inicia sessió amb OAuth
         */
        async loginWithOAuth(provider) {
            if (window.ArionSupabase?.isAvailable()) {
                return await SupabaseAuth.loginWithOAuth(provider);
            }
            return { error: { message: 'OAuth no disponible sense Supabase' } };
        },

        /**
         * Tanca sessió
         */
        async logout() {
            if (window.ArionSupabase?.isAvailable()) {
                await SupabaseAuth.logout();
            } else {
                LocalAuth.logout();
            }

            currentUser = null;
            currentProfile = null;
            notifyListeners('SIGNED_OUT', null);
            this.updateAuthUI();
        },

        /**
         * Recupera contrasenya
         */
        async resetPassword(email) {
            if (window.ArionSupabase?.isAvailable()) {
                return await SupabaseAuth.resetPassword(email);
            }
            return { error: { message: 'Recuperació de contrasenya no disponible en mode demo' } };
        },

        /**
         * Actualitza contrasenya
         */
        async updatePassword(newPassword) {
            if (window.ArionSupabase?.isAvailable()) {
                return await SupabaseAuth.updatePassword(newPassword);
            }
            return { error: { message: 'No disponible en mode demo' } };
        },

        /**
         * Comprova si l'usuari està autenticat
         */
        isLoggedIn() {
            return currentUser !== null;
        },

        /**
         * Obté l'usuari actual
         */
        getCurrentUser() {
            return currentUser;
        },

        /**
         * Obté el perfil actual
         */
        getProfile() {
            return currentProfile;
        },

        /**
         * Actualitza el perfil
         */
        async updateProfile(updates) {
            if (window.ArionSupabase?.isAvailable() && currentUser) {
                const result = await SupabaseAuth.updateProfile(currentUser.id, updates);
                if (!result.error) {
                    currentProfile = { ...currentProfile, ...updates };
                }
                return result;
            } else {
                const result = LocalAuth.updateProfile(updates);
                if (!result.error) {
                    currentProfile = result.data;
                }
                return result;
            }
        },

        /**
         * Puja avatar
         */
        async uploadAvatar(file) {
            if (!window.ArionSupabase?.isAvailable() || !currentUser) {
                return { error: { message: 'No disponible' } };
            }

            const fileExt = file.name.split('.').pop();
            const fileName = `${currentUser.id}/avatar.${fileExt}`;

            const result = await window.ArionSupabase.uploadFile('avatars', fileName, file, {
                upsert: true
            });

            if (!result.error && result.data) {
                await this.updateProfile({ avatar_url: result.data.publicUrl });
            }

            return result;
        },

        /**
         * Afegeix mecenatge (localStorage o Supabase)
         */
        async addMecenatge(obraId, obraTitol, importValue, tipus = 'micromecenatge') {
            if (window.ArionSupabase?.isAvailable() && currentUser) {
                const result = await window.ArionSupabase.insert('mecenatges', {
                    usuari_id: currentUser.id,
                    obra_id: obraId,
                    obra_titol: obraTitol,
                    import: importValue,
                    tipus: tipus,
                    estat: 'completat'
                }, { single: true, select: '*' });

                // Refrescar perfil
                if (!result.error) {
                    currentProfile = await SupabaseAuth.getProfile(currentUser.id);

                    // Verificar medalles
                    await window.ArionSupabase.rpc('verificar_medalles', {
                        p_usuari_id: currentUser.id
                    });
                }

                return result;
            } else {
                const user = LocalAuth.addMecenatge(obraId, obraTitol, importValue);
                currentProfile = user;
                return { data: user, error: null };
            }
        },

        /**
         * Registra listener per canvis d'autenticació
         */
        onAuthStateChange(callback) {
            authListeners.push(callback);
            return () => {
                authListeners = authListeners.filter(l => l !== callback);
            };
        },

        /**
         * Migra dades de localStorage a Supabase
         */
        async migrateFromLocalStorage() {
            // Verificar si ja s'ha migrat
            if (localStorage.getItem(STORAGE_KEYS.MIGRATION_DONE)) return;

            const localUser = LocalAuth.getUser();
            if (!localUser || !currentUser) return;

            // Verificar que l'email coincideix
            if (localUser.email !== currentUser.email) return;

            console.log('[AuthManager] Migrant dades de localStorage a Supabase...');

            try {
                // Migrar perfil
                await this.updateProfile({
                    nom: localUser.nom,
                    cognom: localUser.cognom,
                    bio: localUser.bio || '',
                    rebre_newsletter: localUser.rebre_newsletter || false
                });

                // Migrar mecenatges
                if (localUser.mecenatges && localUser.mecenatges.length > 0) {
                    for (const mec of localUser.mecenatges) {
                        await window.ArionSupabase.insert('mecenatges', {
                            usuari_id: currentUser.id,
                            obra_id: mec.obra_id,
                            obra_titol: mec.obra_titol || 'Obra desconeguda',
                            import: mec.import,
                            tipus: mec.tipus || 'micromecenatge',
                            estat: 'completat',
                            data_aportacio: mec.data || new Date().toISOString()
                        });
                    }
                }

                // Marcar migració com a completada
                localStorage.setItem(STORAGE_KEYS.MIGRATION_DONE, 'true');

                // Refrescar perfil
                currentProfile = await SupabaseAuth.getProfile(currentUser.id);

                console.log('[AuthManager] Migració completada');
            } catch (error) {
                console.error('[AuthManager] Error en migració:', error);
            }
        },

        /**
         * Actualitza la UI segons l'estat d'autenticació
         */
        updateAuthUI() {
            const authBtn = document.querySelector('.btn-auth');
            if (authBtn) {
                if (this.isLoggedIn()) {
                    const nom = currentProfile?.nom || currentUser?.email?.split('@')[0] || 'Usuari';
                    authBtn.textContent = nom;
                    authBtn.href = 'perfil.html';
                } else {
                    authBtn.textContent = 'Entrar';
                    authBtn.href = 'login.html';
                }
            }
        },

        /**
         * Comprova si Supabase està disponible
         */
        isSupabaseMode() {
            return window.ArionSupabase?.isAvailable() || false;
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // INICIALITZACIÓ
    // ─────────────────────────────────────────────────────────────────

    // Inicialitzar quan el DOM estigui llest
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => AuthManager.init());
    } else {
        AuthManager.init();
    }

    // Exportar
    window.ArionAuth = AuthManager;

})();
