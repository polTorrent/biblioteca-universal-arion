-- ═══════════════════════════════════════════════════════════════════
-- BIBLIOTECA ARION - ESQUEMA DE BASE DE DADES SUPABASE
-- Sistema de registre, perfils i gamificació
-- ═══════════════════════════════════════════════════════════════════

-- Activar extensió uuid
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ───────────────────────────────────────────────────────────────────
-- TAULA: NIVELLS
-- Defineix els nivells de gamificació
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.nivells (
    nivell INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    titol TEXT NOT NULL,
    punts_requerits INTEGER NOT NULL DEFAULT 0,
    icona TEXT,
    color TEXT
);

-- Inserir nivells per defecte
INSERT INTO public.nivells (nivell, nom, titol, punts_requerits, icona, color) VALUES
    (1, 'Lector', 'Lector Curiós', 0, '📖', '#8B7355'),
    (2, 'Descobridor', 'Descobridor de Clàssics', 50, '🔍', '#6B8E23'),
    (3, 'Bibliòfil', 'Bibliòfil Dedicat', 150, '📚', '#4682B4'),
    (4, 'Mecenes', 'Mecenes de les Lletres', 300, '🎭', '#9370DB'),
    (5, 'Patrocinador', 'Patrocinador Cultural', 500, '🏛️', '#DAA520'),
    (6, 'Benefactor', 'Benefactor de la Cultura', 1000, '👑', '#CD853F'),
    (7, 'Llegenda', 'Llegenda d''Arion', 2500, '⭐', '#FFD700')
ON CONFLICT (nivell) DO NOTHING;

-- ───────────────────────────────────────────────────────────────────
-- TAULA: MEDALLES
-- Medalles disponibles en el sistema
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.medalles (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    descripcio TEXT NOT NULL,
    icona TEXT NOT NULL,
    categoria TEXT NOT NULL CHECK (categoria IN ('mecenatge', 'comunitat', 'secreta')),
    punts INTEGER NOT NULL DEFAULT 0,
    requisits JSONB,
    secret BOOLEAN DEFAULT FALSE
);

-- Inserir medalles per defecte
INSERT INTO public.medalles (id, nom, descripcio, icona, categoria, punts, requisits, secret) VALUES
    -- Mecenatge
    ('primera-gota', 'Primera Gota', 'Has fet la teva primera aportació', '💧', 'mecenatge', 10, '{"min_aportacions": 1}', FALSE),
    ('mecenes-bronze', 'Mecenes de Bronze', 'Has aportat més de 10€', '🥉', 'mecenatge', 25, '{"min_total": 10}', FALSE),
    ('mecenes-plata', 'Mecenes de Plata', 'Has aportat més de 50€', '🥈', 'mecenatge', 50, '{"min_total": 50}', FALSE),
    ('mecenes-or', 'Mecenes d''Or', 'Has aportat més de 100€', '🥇', 'mecenatge', 100, '{"min_total": 100}', FALSE),
    ('mecenes-diamant', 'Mecenes de Diamant', 'Has aportat més de 500€', '💎', 'mecenatge', 250, '{"min_total": 500}', FALSE),
    ('colleccionista', 'Col·leccionista', 'Has patrocinat 5 obres diferents', '🗃️', 'mecenatge', 75, '{"min_obres": 5}', FALSE),
    ('patrocinador-exclusiu', 'Patrocinador Exclusiu', 'Has finançat una traducció sencera', '🌟', 'mecenatge', 200, '{"financament_complet": true}', FALSE),

    -- Comunitat
    ('veu-activa', 'Veu Activa', 'Has votat 10 propostes', '🗳️', 'comunitat', 20, '{"min_vots": 10}', FALSE),
    ('proposador', 'Proposador', 'Has proposat una traducció', '💡', 'comunitat', 30, '{"min_propostes": 1}', FALSE),
    ('ull-atent', 'Ull Atent', 'Has reportat un error de traducció', '👁️', 'comunitat', 15, '{"min_correccions": 1}', FALSE),
    ('influencer', 'Influencer', 'Has compartit 5 obres a xarxes socials', '📢', 'comunitat', 25, '{"min_compartits": 5}', FALSE),

    -- Secretes
    ('fundador', 'Fundador', 'Ets dels primers 100 usuaris registrats', '🏆', 'secreta', 100, '{"max_usuari_id": 100}', TRUE),
    ('maratonista', 'Maratonista', 'Has aportat 7 dies seguits', '🏃', 'secreta', 50, '{"dies_seguits": 7}', TRUE),
    ('amic-grecs', 'Amic dels Grecs', 'Has patrocinat 3 obres gregues', '🏛️', 'secreta', 40, '{"idioma": "grec", "min_obres": 3}', TRUE),
    ('filolog', 'Fil·lòleg', 'Has llegit més de 10 obres completes', '📜', 'secreta', 60, '{"obres_llegides": 10}', TRUE)
ON CONFLICT (id) DO NOTHING;

-- ───────────────────────────────────────────────────────────────────
-- TAULA: PROFILES (estèn auth.users)
-- Perfils d'usuari amb gamificació
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nom TEXT,
    cognom TEXT,
    email TEXT UNIQUE,
    avatar_url TEXT,
    bio TEXT,

    -- Gamificació
    punts_totals INTEGER DEFAULT 10, -- Comença amb 10 punts per registrar-se
    nivell INTEGER DEFAULT 1 REFERENCES public.nivells(nivell),
    titol TEXT DEFAULT 'Lector Curiós',

    -- Estadístiques
    total_aportat DECIMAL(10,2) DEFAULT 0,
    num_mecenatges INTEGER DEFAULT 0,
    num_obres_patrocinades INTEGER DEFAULT 0,
    num_propostes INTEGER DEFAULT 0,
    num_vots INTEGER DEFAULT 0,

    -- Configuració
    perfil_public BOOLEAN DEFAULT TRUE,
    rebre_newsletter BOOLEAN DEFAULT FALSE,

    -- Metadades
    creat_el TIMESTAMPTZ DEFAULT NOW(),
    actualitzat_el TIMESTAMPTZ DEFAULT NOW()
);

-- ───────────────────────────────────────────────────────────────────
-- TAULA: MECENATGES
-- Historial d'aportacions dels usuaris
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.mecenatges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuari_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    obra_id TEXT NOT NULL,
    obra_titol TEXT NOT NULL,
    obra_autor TEXT,
    import DECIMAL(10,2) NOT NULL CHECK (import > 0),
    tipus TEXT NOT NULL CHECK (tipus IN ('individual', 'micromecenatge')),
    data_aportacio TIMESTAMPTZ DEFAULT NOW(),
    estat TEXT DEFAULT 'completat' CHECK (estat IN ('pendent', 'completat', 'cancel·lat', 'reemborsat')),
    stripe_payment_id TEXT,
    metadata JSONB
);

-- ───────────────────────────────────────────────────────────────────
-- TAULA: USUARI_MEDALLES
-- Medalles obtingudes per cada usuari
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.usuari_medalles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuari_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    medalla_id TEXT NOT NULL REFERENCES public.medalles(id) ON DELETE CASCADE,
    obtinguda_el TIMESTAMPTZ DEFAULT NOW(),
    notificada BOOLEAN DEFAULT FALSE,
    UNIQUE(usuari_id, medalla_id)
);

-- ───────────────────────────────────────────────────────────────────
-- TAULA: PROPOSTES
-- Propostes de traduccions dels usuaris
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.propostes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposat_per UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    titol TEXT NOT NULL,
    titol_original TEXT,
    autor TEXT NOT NULL,
    idioma TEXT NOT NULL,
    any_publicacio INTEGER,
    genere TEXT,
    descripcio TEXT,
    estat TEXT DEFAULT 'pendent' CHECK (estat IN ('pendent', 'aprovada', 'rebutjada', 'en_traduccio', 'completada')),
    num_vots INTEGER DEFAULT 0,
    data_proposta TIMESTAMPTZ DEFAULT NOW()
);

-- ───────────────────────────────────────────────────────────────────
-- TAULA: VOTS_PROPOSTES
-- Vots dels usuaris a propostes
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.vots_propostes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuari_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    proposta_id UUID NOT NULL REFERENCES public.propostes(id) ON DELETE CASCADE,
    data_vot TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(usuari_id, proposta_id)
);

-- ═══════════════════════════════════════════════════════════════════
-- FUNCIONS I TRIGGERS
-- ═══════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────
-- Funció: Crear perfil automàticament quan es registra un usuari
-- ───────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, nom)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'nom', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger per crear perfil
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ───────────────────────────────────────────────────────────────────
-- Funció: Calcular nivell basat en punts
-- ───────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.calcular_nivell(punts INTEGER)
RETURNS TABLE(nivell INTEGER, titol TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT n.nivell, n.titol
    FROM public.nivells n
    WHERE n.punts_requerits <= punts
    ORDER BY n.punts_requerits DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ───────────────────────────────────────────────────────────────────
-- Funció: Actualitzar estadístiques i nivell després d'un mecenatge
-- ───────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.actualitzar_estadistiques_mecenatge()
RETURNS TRIGGER AS $$
DECLARE
    punts_nous INTEGER;
    nou_nivell INTEGER;
    nou_titol TEXT;
    es_primera_aportacio BOOLEAN;
    num_obres_uniques INTEGER;
BEGIN
    -- Només processar mecenatges completats
    IF NEW.estat != 'completat' THEN
        RETURN NEW;
    END IF;

    -- Comprovar si és la primera aportació
    SELECT COUNT(*) = 1 INTO es_primera_aportacio
    FROM public.mecenatges
    WHERE usuari_id = NEW.usuari_id AND estat = 'completat';

    -- Calcular punts: 10 per cada euro + 25 si és primera aportació
    punts_nous := FLOOR(NEW.import * 10);
    IF es_primera_aportacio THEN
        punts_nous := punts_nous + 25;
    END IF;

    -- Comptar obres úniques patrocinades
    SELECT COUNT(DISTINCT obra_id) INTO num_obres_uniques
    FROM public.mecenatges
    WHERE usuari_id = NEW.usuari_id AND estat = 'completat';

    -- Actualitzar perfil
    UPDATE public.profiles
    SET
        punts_totals = punts_totals + punts_nous,
        total_aportat = total_aportat + NEW.import,
        num_mecenatges = num_mecenatges + 1,
        num_obres_patrocinades = num_obres_uniques,
        actualitzat_el = NOW()
    WHERE id = NEW.usuari_id;

    -- Recalcular nivell
    SELECT n.nivell, n.titol INTO nou_nivell, nou_titol
    FROM public.profiles p, public.calcular_nivell(p.punts_totals + punts_nous) n
    WHERE p.id = NEW.usuari_id;

    IF nou_nivell IS NOT NULL THEN
        UPDATE public.profiles
        SET nivell = nou_nivell, titol = nou_titol
        WHERE id = NEW.usuari_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger per actualitzar estadístiques
DROP TRIGGER IF EXISTS on_mecenatge_created ON public.mecenatges;
CREATE TRIGGER on_mecenatge_created
    AFTER INSERT ON public.mecenatges
    FOR EACH ROW EXECUTE FUNCTION public.actualitzar_estadistiques_mecenatge();

-- ───────────────────────────────────────────────────────────────────
-- Funció: Verificar i atorgar medalles
-- ───────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.verificar_medalles(p_usuari_id UUID)
RETURNS TABLE(medalla_id TEXT, medalla_nom TEXT, nova BOOLEAN) AS $$
DECLARE
    perfil RECORD;
    m RECORD;
    requisits JSONB;
    compleix BOOLEAN;
BEGIN
    -- Obtenir dades del perfil
    SELECT * INTO perfil FROM public.profiles WHERE id = p_usuari_id;

    -- Iterar per totes les medalles
    FOR m IN SELECT * FROM public.medalles LOOP
        requisits := m.requisits;
        compleix := FALSE;

        -- Verificar cada tipus de requisit
        IF requisits ? 'min_aportacions' THEN
            compleix := perfil.num_mecenatges >= (requisits->>'min_aportacions')::INTEGER;
        ELSIF requisits ? 'min_total' THEN
            compleix := perfil.total_aportat >= (requisits->>'min_total')::DECIMAL;
        ELSIF requisits ? 'min_obres' THEN
            compleix := perfil.num_obres_patrocinades >= (requisits->>'min_obres')::INTEGER;
        ELSIF requisits ? 'min_vots' THEN
            compleix := perfil.num_vots >= (requisits->>'min_vots')::INTEGER;
        ELSIF requisits ? 'min_propostes' THEN
            compleix := perfil.num_propostes >= (requisits->>'min_propostes')::INTEGER;
        END IF;

        -- Si compleix i no la té, atorgar-la
        IF compleix THEN
            INSERT INTO public.usuari_medalles (usuari_id, medalla_id)
            VALUES (p_usuari_id, m.id)
            ON CONFLICT (usuari_id, medalla_id) DO NOTHING;

            -- Retornar si és nova
            IF FOUND THEN
                -- Afegir punts de la medalla
                UPDATE public.profiles
                SET punts_totals = punts_totals + m.punts
                WHERE id = p_usuari_id;

                RETURN QUERY SELECT m.id, m.nom, TRUE;
            ELSE
                RETURN QUERY SELECT m.id, m.nom, FALSE;
            END IF;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ───────────────────────────────────────────────────────────────────
-- Funció: Actualitzar comptador de vots
-- ───────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.actualitzar_vots_proposta()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Incrementar vots de la proposta
        UPDATE public.propostes
        SET num_vots = num_vots + 1
        WHERE id = NEW.proposta_id;

        -- Incrementar comptador d'usuari i afegir punts
        UPDATE public.profiles
        SET
            num_vots = num_vots + 1,
            punts_totals = punts_totals + 2
        WHERE id = NEW.usuari_id;

    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.propostes
        SET num_vots = num_vots - 1
        WHERE id = OLD.proposta_id;

        UPDATE public.profiles
        SET num_vots = num_vots - 1
        WHERE id = OLD.usuari_id;
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_vot_proposta ON public.vots_propostes;
CREATE TRIGGER on_vot_proposta
    AFTER INSERT OR DELETE ON public.vots_propostes
    FOR EACH ROW EXECUTE FUNCTION public.actualitzar_vots_proposta();

-- ───────────────────────────────────────────────────────────────────
-- Funció: Registrar nova proposta
-- ───────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.registrar_proposta()
RETURNS TRIGGER AS $$
BEGIN
    -- Afegir punts i incrementar comptador
    UPDATE public.profiles
    SET
        num_propostes = num_propostes + 1,
        punts_totals = punts_totals + 15
    WHERE id = NEW.proposat_per;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_proposta_created ON public.propostes;
CREATE TRIGGER on_proposta_created
    AFTER INSERT ON public.propostes
    FOR EACH ROW EXECUTE FUNCTION public.registrar_proposta();

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS)
-- ═══════════════════════════════════════════════════════════════════

-- Activar RLS a totes les taules
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mecenatges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuari_medalles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.propostes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vots_propostes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nivells ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medalles ENABLE ROW LEVEL SECURITY;

-- ─── Profiles ───

-- Tothom pot veure perfils públics
CREATE POLICY "Profiles públics visibles per tothom"
ON public.profiles FOR SELECT
USING (perfil_public = TRUE OR auth.uid() = id);

-- Usuaris poden actualitzar el seu propi perfil
CREATE POLICY "Usuaris poden actualitzar el seu perfil"
ON public.profiles FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- ─── Mecenatges ───

-- Usuaris poden veure els seus mecenatges
CREATE POLICY "Usuaris poden veure els seus mecenatges"
ON public.mecenatges FOR SELECT
USING (auth.uid() = usuari_id);

-- Usuaris poden crear mecenatges
CREATE POLICY "Usuaris poden crear mecenatges"
ON public.mecenatges FOR INSERT
WITH CHECK (auth.uid() = usuari_id);

-- ─── Medalles ───

-- Tothom pot veure les medalles (no secretes)
CREATE POLICY "Medalles visibles"
ON public.medalles FOR SELECT
USING (secret = FALSE OR EXISTS (
    SELECT 1 FROM public.usuari_medalles
    WHERE medalla_id = medalles.id AND usuari_id = auth.uid()
));

-- ─── Usuari Medalles ───

-- Usuaris poden veure les seves medalles
CREATE POLICY "Usuaris veuen les seves medalles"
ON public.usuari_medalles FOR SELECT
USING (auth.uid() = usuari_id);

-- Perfils públics mostren les seves medalles
CREATE POLICY "Medalles de perfils públics"
ON public.usuari_medalles FOR SELECT
USING (EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = usuari_medalles.usuari_id AND perfil_public = TRUE
));

-- ─── Nivells ───

-- Tothom pot veure els nivells
CREATE POLICY "Nivells visibles per tothom"
ON public.nivells FOR SELECT
USING (TRUE);

-- ─── Propostes ───

-- Tothom pot veure propostes aprovades o pròpies
CREATE POLICY "Propostes visibles"
ON public.propostes FOR SELECT
USING (estat IN ('aprovada', 'en_traduccio', 'completada') OR proposat_per = auth.uid());

-- Usuaris autenticats poden crear propostes
CREATE POLICY "Usuaris poden crear propostes"
ON public.propostes FOR INSERT
WITH CHECK (auth.uid() = proposat_per);

-- ─── Vots ───

-- Usuaris poden veure els seus vots
CREATE POLICY "Usuaris veuen els seus vots"
ON public.vots_propostes FOR SELECT
USING (auth.uid() = usuari_id);

-- Usuaris poden votar
CREATE POLICY "Usuaris poden votar"
ON public.vots_propostes FOR INSERT
WITH CHECK (auth.uid() = usuari_id);

-- Usuaris poden eliminar els seus vots
CREATE POLICY "Usuaris poden eliminar vots"
ON public.vots_propostes FOR DELETE
USING (auth.uid() = usuari_id);

-- ═══════════════════════════════════════════════════════════════════
-- ÍNDEXS
-- ═══════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_punts ON public.profiles(punts_totals DESC);
CREATE INDEX IF NOT EXISTS idx_mecenatges_usuari ON public.mecenatges(usuari_id);
CREATE INDEX IF NOT EXISTS idx_mecenatges_obra ON public.mecenatges(obra_id);
CREATE INDEX IF NOT EXISTS idx_usuari_medalles_usuari ON public.usuari_medalles(usuari_id);
CREATE INDEX IF NOT EXISTS idx_propostes_estat ON public.propostes(estat);
CREATE INDEX IF NOT EXISTS idx_propostes_vots ON public.propostes(num_vots DESC);

-- ═══════════════════════════════════════════════════════════════════
-- VISTA: Rànking d'usuaris
-- ═══════════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW public.ranking_usuaris AS
SELECT
    p.id,
    p.nom,
    p.avatar_url,
    p.punts_totals,
    p.nivell,
    p.titol,
    p.total_aportat,
    p.num_mecenatges,
    (SELECT COUNT(*) FROM public.usuari_medalles WHERE usuari_id = p.id) as num_medalles,
    ROW_NUMBER() OVER (ORDER BY p.punts_totals DESC) as posicio
FROM public.profiles p
WHERE p.perfil_public = TRUE
ORDER BY p.punts_totals DESC;

-- Permetre accés a la vista
GRANT SELECT ON public.ranking_usuaris TO authenticated, anon;
