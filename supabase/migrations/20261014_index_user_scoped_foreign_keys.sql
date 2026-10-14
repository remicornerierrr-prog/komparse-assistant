-- Support user-scoped RLS queries and OAuth-state cleanup without changing access rules.
create index if not exists matches_user_id_idx
    on public.matches (user_id);

create index if not exists gmail_oauth_states_user_id_idx
    on public.gmail_oauth_states (user_id);
