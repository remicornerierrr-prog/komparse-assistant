ALTER TABLE public.matches
  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true;

CREATE INDEX IF NOT EXISTS matches_active_user_idx
  ON public.matches (user_id, created_at DESC)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS public.profile_match_refresh_state (
  user_id uuid PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
  profile_updated_at timestamptz NOT NULL,
  refreshed_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.profile_match_refresh_state ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.profile_match_refresh_state FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE public.profile_match_refresh_state TO service_role;
