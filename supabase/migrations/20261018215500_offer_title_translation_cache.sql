CREATE TABLE IF NOT EXISTS public.offer_title_translations (
  offer_id text NOT NULL,
  target_language text NOT NULL CHECK (target_language IN ('fr', 'en')),
  source_title text NOT NULL,
  translated_title text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (offer_id, target_language)
);

ALTER TABLE public.offer_title_translations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.offer_title_translations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE public.offer_title_translations TO service_role;
