-- Store Gmail OAuth credentials only as application-encrypted ciphertext.
-- Edge Functions use the service role; browser roles receive no table privileges.
create table if not exists public.gmail_connections (
    user_id uuid primary key references auth.users(id) on delete cascade,
    gmail_email text not null,
    refresh_token_ciphertext text not null,
    access_token_ciphertext text,
    access_token_expires_at timestamptz,
    granted_scopes text[] not null default '{}',
    connected_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.gmail_oauth_states (
    state_hash text primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);

create index if not exists gmail_oauth_states_created_at_idx
    on public.gmail_oauth_states (created_at);

alter table public.gmail_connections enable row level security;
alter table public.gmail_oauth_states enable row level security;

revoke all on table public.gmail_connections from anon, authenticated;
revoke all on table public.gmail_oauth_states from anon, authenticated;
grant all on table public.gmail_connections to service_role;
grant all on table public.gmail_oauth_states to service_role;

comment on table public.gmail_connections is
    'Gmail OAuth credentials; token values must be application-encrypted before storage.';
comment on table public.gmail_oauth_states is
    'Short-lived, hashed OAuth state values used to bind Google callbacks to a signed-in user.';
