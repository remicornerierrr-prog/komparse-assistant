-- Persist human-readable scheduling and age information without inventing
-- a precise date or numeric age band.
alter table public.offers
    add column if not exists location_status text,
    add column if not exists shoot_date_text text,
    add column if not exists shoot_duration_text text,
    add column if not exists age_description text,
    add column if not exists parser_review_reason text,
    add column if not exists application_method text,
    add column if not exists application_url text;

-- These fields existed in the current project schema; the statements are
-- defensive so this migration can also be run on a fresh/partially migrated DB.
alter table public.offers
    add column if not exists detail_text text,
    add column if not exists parser_needs_review boolean not null default false,
    add column if not exists admin_review_required boolean not null default false;
