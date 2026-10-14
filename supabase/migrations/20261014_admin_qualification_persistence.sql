-- Preserve explicit administrator qualification across scheduled scraper runs.
ALTER TABLE public.offers
    ADD COLUMN IF NOT EXISTS admin_qualified boolean NOT NULL DEFAULT false;
