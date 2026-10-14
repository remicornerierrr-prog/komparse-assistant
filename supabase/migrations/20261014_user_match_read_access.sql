-- Allow signed-in users to read only their own matches and matched offers.
-- Existing administrator policies are intentionally preserved.
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.offers ENABLE ROW LEVEL SECURITY;

-- The anonymous role must not access either table, regardless of any old grants.
REVOKE ALL PRIVILEGES ON TABLE public.matches, public.offers FROM anon;

-- Keep the minimum table privilege needed for SELECT policies to apply.
GRANT SELECT ON TABLE public.matches, public.offers TO authenticated;

-- Clients cannot write matches. Offers remain UPDATE-able only through the
-- pre-existing administrator RLS policy; ordinary users cannot insert/delete.
REVOKE INSERT, UPDATE, DELETE ON TABLE public.matches FROM authenticated;
REVOKE INSERT, DELETE ON TABLE public.offers FROM authenticated;

DROP POLICY IF EXISTS "Users can view own matches" ON public.matches;
CREATE POLICY "Users can view own matches"
    ON public.matches
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can view offers from own matches" ON public.offers;
CREATE POLICY "Users can view offers from own matches"
    ON public.offers
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.matches AS user_match
            WHERE user_match.offer_id = offers.id
              AND user_match.user_id = (SELECT auth.uid())
        )
    );
