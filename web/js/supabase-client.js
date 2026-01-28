/**
 * ═══════════════════════════════════════════════════════════════════
 * SUPABASE CLIENT - Biblioteca Universal Arion
 * Client Supabase per a autenticació i base de dades
 * ═══════════════════════════════════════════════════════════════════
 */

(function() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────
    // CONFIGURACIÓ
    // IMPORTANT: Substitueix aquests valors pels teus de Supabase
    // ─────────────────────────────────────────────────────────────────

    const SUPABASE_CONFIG = {
        // Substitueix per la teva URL de Supabase (Project Settings > API > URL)
        url: https://rhiulagwcchtaizlckam.supabase.co,

        // Substitueix per la teva anon key (Project Settings > API > anon public)
        anonKey: sb_publishable_IfAT9TMHv9vzoUs1oADVxA_C4h0P4A-,

        // Opcions del client
        options: {
            auth: {
                autoRefreshToken: true,
                persistSession: true,
                storageKey: 'arion_supabase_auth',
                storage: window.localStorage
            }
        }
    };

    // ─────────────────────────────────────────────────────────────────
    // INICIALITZACIÓ DEL CLIENT
    // ─────────────────────────────────────────────────────────────────

    let supabaseClient = null;
    let isConfigured = false;

    /**
     * Verifica si Supabase està configurat
     */
    function checkConfiguration() {
        return SUPABASE_CONFIG.url !== 'https://YOUR_PROJECT_ID.supabase.co' &&
               SUPABASE_CONFIG.anonKey !== 'YOUR_ANON_KEY';
    }

    /**
     * Inicialitza el client Supabase
     */
    async function initSupabase() {
        // Verificar configuració
        if (!checkConfiguration()) {
            console.warn('[Arion] Supabase no configurat. Usant mode localStorage.');
            isConfigured = false;
            return null;
        }

        // Verificar que el SDK està carregat
        if (typeof window.supabase === 'undefined') {
            console.warn('[Arion] SDK de Supabase no carregat.');
            isConfigured = false;
            return null;
        }

        try {
            supabaseClient = window.supabase.createClient(
                SUPABASE_CONFIG.url,
                SUPABASE_CONFIG.anonKey,
                SUPABASE_CONFIG.options
            );
            isConfigured = true;
            console.log('[Arion] Supabase inicialitzat correctament');
            return supabaseClient;
        } catch (error) {
            console.error('[Arion] Error inicialitzant Supabase:', error);
            isConfigured = false;
            return null;
        }
    }

    /**
     * Obté el client Supabase
     */
    function getClient() {
        return supabaseClient;
    }

    /**
     * Comprova si Supabase està disponible
     */
    function isAvailable() {
        return isConfigured && supabaseClient !== null;
    }

    // ─────────────────────────────────────────────────────────────────
    // HELPERS DE BASE DE DADES
    // ─────────────────────────────────────────────────────────────────

    /**
     * Consulta genèrica amb gestió d'errors
     */
    async function query(table, options = {}) {
        if (!isAvailable()) return { data: null, error: { message: 'Supabase no disponible' } };

        try {
            let queryBuilder = supabaseClient.from(table).select(options.select || '*');

            // Filtres
            if (options.eq) {
                for (const [column, value] of Object.entries(options.eq)) {
                    queryBuilder = queryBuilder.eq(column, value);
                }
            }

            // Ordenació
            if (options.order) {
                queryBuilder = queryBuilder.order(options.order.column, {
                    ascending: options.order.ascending ?? true
                });
            }

            // Límit
            if (options.limit) {
                queryBuilder = queryBuilder.limit(options.limit);
            }

            // Rang
            if (options.range) {
                queryBuilder = queryBuilder.range(options.range.from, options.range.to);
            }

            // Single
            if (options.single) {
                queryBuilder = queryBuilder.single();
            }

            return await queryBuilder;
        } catch (error) {
            return { data: null, error };
        }
    }

    /**
     * Inserció amb gestió d'errors
     */
    async function insert(table, data, options = {}) {
        if (!isAvailable()) return { data: null, error: { message: 'Supabase no disponible' } };

        try {
            let queryBuilder = supabaseClient.from(table).insert(data);

            if (options.select) {
                queryBuilder = queryBuilder.select(options.select);
            }

            if (options.single) {
                queryBuilder = queryBuilder.single();
            }

            return await queryBuilder;
        } catch (error) {
            return { data: null, error };
        }
    }

    /**
     * Actualització amb gestió d'errors
     */
    async function update(table, data, match, options = {}) {
        if (!isAvailable()) return { data: null, error: { message: 'Supabase no disponible' } };

        try {
            let queryBuilder = supabaseClient.from(table).update(data);

            // Condicions de match
            for (const [column, value] of Object.entries(match)) {
                queryBuilder = queryBuilder.eq(column, value);
            }

            if (options.select) {
                queryBuilder = queryBuilder.select(options.select);
            }

            if (options.single) {
                queryBuilder = queryBuilder.single();
            }

            return await queryBuilder;
        } catch (error) {
            return { data: null, error };
        }
    }

    /**
     * Eliminació amb gestió d'errors
     */
    async function remove(table, match) {
        if (!isAvailable()) return { data: null, error: { message: 'Supabase no disponible' } };

        try {
            let queryBuilder = supabaseClient.from(table).delete();

            for (const [column, value] of Object.entries(match)) {
                queryBuilder = queryBuilder.eq(column, value);
            }

            return await queryBuilder;
        } catch (error) {
            return { data: null, error };
        }
    }

    /**
     * Crida a funció RPC
     */
    async function rpc(functionName, params = {}) {
        if (!isAvailable()) return { data: null, error: { message: 'Supabase no disponible' } };

        try {
            return await supabaseClient.rpc(functionName, params);
        } catch (error) {
            return { data: null, error };
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // STORAGE
    // ─────────────────────────────────────────────────────────────────

    /**
     * Puja un fitxer a Supabase Storage
     */
    async function uploadFile(bucket, path, file, options = {}) {
        if (!isAvailable()) return { data: null, error: { message: 'Supabase no disponible' } };

        try {
            const { data, error } = await supabaseClient.storage
                .from(bucket)
                .upload(path, file, {
                    cacheControl: options.cacheControl || '3600',
                    upsert: options.upsert || false
                });

            if (error) return { data: null, error };

            // Obtenir URL pública
            const { data: urlData } = supabaseClient.storage
                .from(bucket)
                .getPublicUrl(path);

            return { data: { ...data, publicUrl: urlData.publicUrl }, error: null };
        } catch (error) {
            return { data: null, error };
        }
    }

    /**
     * Elimina un fitxer de Supabase Storage
     */
    async function deleteFile(bucket, paths) {
        if (!isAvailable()) return { data: null, error: { message: 'Supabase no disponible' } };

        try {
            return await supabaseClient.storage
                .from(bucket)
                .remove(Array.isArray(paths) ? paths : [paths]);
        } catch (error) {
            return { data: null, error };
        }
    }

    /**
     * Obté URL pública d'un fitxer
     */
    function getPublicUrl(bucket, path) {
        if (!isAvailable()) return null;

        const { data } = supabaseClient.storage
            .from(bucket)
            .getPublicUrl(path);

        return data.publicUrl;
    }

    // ─────────────────────────────────────────────────────────────────
    // SUBSCRIPCIONS EN TEMPS REAL
    // ─────────────────────────────────────────────────────────────────

    /**
     * Subscriu-se a canvis en una taula
     */
    function subscribe(table, callback, options = {}) {
        if (!isAvailable()) return null;

        const channel = supabaseClient
            .channel(`public:${table}`)
            .on(
                'postgres_changes',
                {
                    event: options.event || '*',
                    schema: 'public',
                    table: table,
                    filter: options.filter
                },
                callback
            )
            .subscribe();

        return channel;
    }

    /**
     * Cancel·la subscripció
     */
    async function unsubscribe(channel) {
        if (channel) {
            await supabaseClient.removeChannel(channel);
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // EXPORTAR API
    // ─────────────────────────────────────────────────────────────────

    // Inicialitzar automàticament quan el DOM estigui llest
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSupabase);
    } else {
        initSupabase();
    }

    // Exportar
    window.ArionSupabase = {
        // Configuració
        init: initSupabase,
        getClient,
        isAvailable,
        config: SUPABASE_CONFIG,

        // Base de dades
        query,
        insert,
        update,
        remove,
        rpc,

        // Storage
        uploadFile,
        deleteFile,
        getPublicUrl,

        // Temps real
        subscribe,
        unsubscribe
    };

})();
