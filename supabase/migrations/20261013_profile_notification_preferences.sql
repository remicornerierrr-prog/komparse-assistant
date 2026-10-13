-- Persist user choices for national and regional offer notifications.
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS notify_national boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS notify_regional boolean NOT NULL DEFAULT true;
