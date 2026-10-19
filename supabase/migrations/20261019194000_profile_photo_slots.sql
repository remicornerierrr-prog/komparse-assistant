DO $$
DECLARE
  check_name text;
BEGIN
  FOR check_name IN
    SELECT conname
    FROM pg_constraint
    WHERE conrelid = 'public.profile_photos'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) ILIKE '%photo_type%'
  LOOP
    EXECUTE format(
      'ALTER TABLE public.profile_photos DROP CONSTRAINT %I',
      check_name
    );
  END LOOP;
END
$$;

ALTER TABLE public.profile_photos
  ADD CONSTRAINT profile_photos_photo_type_allowed
  CHECK (
    photo_type IN (
      'portrait',
      'left',
      'right',
      'full_body',
      'photo_5',
      'photo_6',
      'photo_7',
      'photo_8',
      'photo_9',
      'photo_10'
    )
  );

CREATE OR REPLACE FUNCTION public.enforce_profile_photo_limit()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  existing_photo_count integer;
BEGIN
  PERFORM 1
  FROM public.profiles
  WHERE id = NEW.user_id
  FOR UPDATE;

  SELECT count(*)
  INTO existing_photo_count
  FROM public.profile_photos
  WHERE user_id = NEW.user_id
    AND photo_type <> NEW.photo_type;

  IF existing_photo_count >= 10 THEN
    RAISE EXCEPTION 'A profile can have at most 10 photos';
  END IF;

  RETURN NEW;
END
$$;

REVOKE ALL ON FUNCTION public.enforce_profile_photo_limit() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.enforce_profile_photo_limit() TO authenticated;

CREATE TRIGGER profile_photos_limit_before_write
  BEFORE INSERT OR UPDATE OF user_id, photo_type
  ON public.profile_photos
  FOR EACH ROW
  EXECUTE FUNCTION public.enforce_profile_photo_limit();
