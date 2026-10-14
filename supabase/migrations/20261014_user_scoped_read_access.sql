-- P0-1: user-scoped read access for matches and matched offers.
-- Idempotent: replace only the two user-facing SELECT policies.
-- Admin policies are deliberately left untouched.

alter table public.matches enable row level security;
alter table public.offers enable row level security;

drop policy if exists "Users can view own matches" on public.matches;
create policy "Users can view own matches"
  on public.matches
  for select
  to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "Users can view offers from own matches" on public.offers;
create policy "Users can view offers from own matches"
  on public.offers
  for select
  to authenticated
  using (
    exists (
      select 1
      from public.matches as user_match
      where user_match.offer_id = offers.id
        and user_match.user_id = (select auth.uid())
    )
  );

-- No anonymous access; authenticated users can read only through RLS.
revoke all on table public.matches, public.offers from anon, public;
grant select on table public.matches, public.offers to authenticated;

-- Keep the existing admin UPDATE grant/policy on offers intact.
-- No INSERT or DELETE policy is added for users; the existing admin policies
-- are intentionally not modified.
