-- ═══════════════════════════════════════════════════════════════════
-- MIGRACIÓ 001: Favorits (Cors) i Carret de Mecenatge
-- Biblioteca Universal Arion
-- ═══════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────
-- TAULA: FAVORITS (Cors)
-- Obres marcades com a favorites pels usuaris
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.favorits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuari_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    obra_id TEXT NOT NULL,
    obra_titol TEXT,
    obra_autor TEXT,
    afegit_el TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(usuari_id, obra_id)
);

-- Índexs
CREATE INDEX IF NOT EXISTS idx_favorits_usuari ON public.favorits(usuari_id);
CREATE INDEX IF NOT EXISTS idx_favorits_obra ON public.favorits(obra_id);

-- RLS
ALTER TABLE public.favorits ENABLE ROW LEVEL SECURITY;

-- Usuaris poden veure els seus favorits
CREATE POLICY "Usuaris veuen els seus favorits"
ON public.favorits FOR SELECT
USING (auth.uid() = usuari_id);

-- Usuaris poden afegir favorits
CREATE POLICY "Usuaris poden afegir favorits"
ON public.favorits FOR INSERT
WITH CHECK (auth.uid() = usuari_id);

-- Usuaris poden eliminar els seus favorits
CREATE POLICY "Usuaris poden eliminar favorits"
ON public.favorits FOR DELETE
USING (auth.uid() = usuari_id);

-- ───────────────────────────────────────────────────────────────────
-- TAULA: CARRET
-- Items al carret de mecenatge pendents de pagament
-- ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.carret (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuari_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    obra_id TEXT NOT NULL,
    obra_titol TEXT NOT NULL,
    obra_autor TEXT,
    import DECIMAL(10,2) NOT NULL CHECK (import > 0),
    tipus TEXT NOT NULL DEFAULT 'micromecenatge' CHECK (tipus IN ('individual', 'micromecenatge')),
    afegit_el TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(usuari_id, obra_id)
);

-- Índexs
CREATE INDEX IF NOT EXISTS idx_carret_usuari ON public.carret(usuari_id);

-- RLS
ALTER TABLE public.carret ENABLE ROW LEVEL SECURITY;

-- Usuaris poden veure el seu carret
CREATE POLICY "Usuaris veuen el seu carret"
ON public.carret FOR SELECT
USING (auth.uid() = usuari_id);

-- Usuaris poden afegir al carret
CREATE POLICY "Usuaris poden afegir al carret"
ON public.carret FOR INSERT
WITH CHECK (auth.uid() = usuari_id);

-- Usuaris poden actualitzar el seu carret
CREATE POLICY "Usuaris poden actualitzar carret"
ON public.carret FOR UPDATE
USING (auth.uid() = usuari_id);

-- Usuaris poden eliminar del carret
CREATE POLICY "Usuaris poden eliminar del carret"
ON public.carret FOR DELETE
USING (auth.uid() = usuari_id);

-- ───────────────────────────────────────────────────────────────────
-- Afegir camp num_favorits a profiles
-- ───────────────────────────────────────────────────────────────────

ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS num_favorits INTEGER DEFAULT 0;

-- ───────────────────────────────────────────────────────────────────
-- Trigger: Actualitzar comptador de favorits
-- ───────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.actualitzar_num_favorits()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.profiles
        SET num_favorits = num_favorits + 1
        WHERE id = NEW.usuari_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.profiles
        SET num_favorits = GREATEST(0, num_favorits - 1)
        WHERE id = OLD.usuari_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_favorit_change ON public.favorits;
CREATE TRIGGER on_favorit_change
    AFTER INSERT OR DELETE ON public.favorits
    FOR EACH ROW EXECUTE FUNCTION public.actualitzar_num_favorits();
