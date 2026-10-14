-- Enforce the same photo upload limits in Storage as in the browser.
-- The bucket remains private; signed URLs are still required for reads.
update storage.buckets
set
  file_size_limit = 5242880,
  allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp']
where id = 'profile-photos'
  and (
    file_size_limit is distinct from 5242880
    or allowed_mime_types is distinct from array['image/jpeg', 'image/png', 'image/webp']::text[]
  );
