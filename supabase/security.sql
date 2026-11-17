-- NaijaOuting security limits (anti-spam, enforced by the database itself)
-- Paste all of this into Supabase -> SQL Editor -> New query, then press Run.
-- Run after schema.sql (and accounts.sql). Safe to run more than once.
--
-- The website already limits what visitors send, but a script can skip the website.
-- These rules apply to every guest and signed-in visitor, whatever they use.
-- Admins and the scheduled jobs (service key) are not limited.

-- 1. Scam reports ("flags") are private: only the person who sent them and admins can read them.
--    The public warning now appears only after an admin confirms it (overrides/scam).
drop policy if exists "anyone reads public collections" on public.docs;
create policy "anyone reads public collections" on public.docs
  for select using (col in ('events', 'overrides'));

drop policy if exists "people read their own documents" on public.docs;
create policy "people read their own documents" on public.docs
  for select using (col in ('submissions', 'corrections', 'messages', 'stats', 'flags') and id = auth.uid()::text);

-- 2. How many guest documents of one kind exist (counts everyone's, not just your own)
create or replace function public.doc_count(c text) returns int
language sql stable security definer set search_path = public as $$
  select count(*)::int from public.docs where col = c
$$;
revoke all on function public.doc_count(text) from public, anon;
grant execute on function public.doc_count(text) to authenticated;

-- 3. Size and count limits for what visitors write
create or replace function public.docs_limits() returns trigger
language plpgsql set search_path = public as $$
declare
  sz int := pg_column_size(new.data);
  items jsonb := new.data->'items';
  n int := 0;
  max_items int;
  max_size int;
begin
  -- admins, scheduled jobs and the database's own functions are not limited
  if current_user in ('postgres', 'service_role', 'supabase_admin') or public.is_admin() then
    return new;
  end if;

  if items is not null and jsonb_typeof(items) <> 'array' then
    raise exception 'Invalid data' using errcode = 'check_violation';
  end if;
  if items is not null then n := jsonb_array_length(items); end if;

  case new.col
    when 'submissions' then max_items := 20; max_size := 80000;
    when 'corrections' then max_items := 30; max_size := 60000;
    when 'messages'    then max_items := 20; max_size := 40000;
    when 'stats'       then max_items := 0;  max_size := 20000;
    when 'users'       then max_items := 0;  max_size := 120000;
    when 'handoff'     then max_items := 0;  max_size := 600;
    when 'flags' then
      max_items := 0; max_size := 4000;
      if jsonb_typeof(coalesce(new.data->'ids', '[]'::jsonb)) <> 'array'
         or jsonb_array_length(coalesce(new.data->'ids', '[]'::jsonb)) > 30
         or exists (select 1 from jsonb_array_elements(coalesce(new.data->'ids', '[]'::jsonb)) x
                    where jsonb_typeof(x) <> 'string' or (x #>> '{}') !~ '^[A-Za-z0-9_:.-]{1,80}$') then
        raise exception 'Invalid report' using errcode = 'check_violation';
      end if;
    else
      max_items := 0; max_size := 20000;
  end case;

  if sz > max_size or (max_items > 0 and n > max_items) then
    raise exception 'Too much at once. Please wait for us to review what you sent.' using errcode = 'check_violation';
  end if;

  -- one send every few seconds per person
  if tg_op = 'UPDATE' and new.col in ('submissions', 'corrections', 'messages')
     and old.updated_at > now() - interval '3 seconds' then
    raise exception 'Please wait a few seconds and try again.' using errcode = 'check_violation';
  end if;

  -- if someone floods the site with new guests, the review queue stops growing at 3,000 senders
  if tg_op = 'INSERT' and new.col in ('submissions', 'corrections', 'messages', 'flags', 'users', 'stats')
     and public.doc_count(new.col) >= 3000 then
    raise exception 'We are getting a lot of messages right now. Please try again later.' using errcode = 'check_violation';
  end if;

  return new;
end $$;

drop trigger if exists docs_limits on public.docs;
create trigger docs_limits before insert or update on public.docs
  for each row execute function public.docs_limits();

-- 4. Flyer uploads: pictures only (already), file names the website makes,
--    at most 15 a day per person and 400 a day for the whole site.
create or replace function public.flyer_ok() returns boolean
language sql stable security definer set search_path = public, storage as $$
  select
    (select count(*) from storage.objects
      where bucket_id = 'flyers' and created_at > now() - interval '1 day'
        and (owner = auth.uid() or owner_id = auth.uid()::text)) < 15
    and
    (select count(*) from storage.objects
      where bucket_id = 'flyers' and created_at > now() - interval '1 day') < 400
$$;
revoke all on function public.flyer_ok() from public, anon;
grant execute on function public.flyer_ok() to authenticated;

drop policy if exists "visitors upload flyers" on storage.objects;
create policy "visitors upload flyers" on storage.objects
  for insert to authenticated with check (
    bucket_id = 'flyers'
    and (public.is_admin() or (name ~ '^s-[0-9a-z]{16,40}$' and public.flyer_ok()))
  );
