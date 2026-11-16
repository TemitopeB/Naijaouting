-- NaijaOuting visitor accounts (sign in with Google or an email code)
-- Paste all of this into Supabase -> SQL Editor -> New query, then press Run.
-- Run schema.sql first. Safe to run more than once.
--
-- New collections in public.docs:
--   users    one per signed-in visitor: saved events, tourism list, trip, reminder choice
--   outcomes one per visitor: what happened to the events they sent in (approved / not approved)
--   handoff  a short-lived token so a guest's submissions move into their new account
--   remlog   which reminder emails were sent (only the reminder job reads this)

-- 1. Visitors read and write only their own account document
drop policy if exists "people manage their own account" on public.docs;
create policy "people manage their own account" on public.docs
  for all
  using (col in ('users', 'handoff') and id = auth.uid()::text)
  with check (col in ('users', 'handoff') and id = auth.uid()::text);

-- 2. Visitors read (but can't change) what happened to their submissions; admins write these
drop policy if exists "people read their own outcomes" on public.docs;
create policy "people read their own outcomes" on public.docs
  for select using (col = 'outcomes' and id = auth.uid()::text);

-- 3. Move a guest's submissions into the account they just signed in to.
--    Only works with the secret token the guest's own browser saved, only from a guest
--    (anonymous) user, and only within 2 days.
create or replace function public.claim_guest(old_id text, tok text) returns int
language plpgsql security definer set search_path = public as $$
declare
  me text := auth.uid()::text;
  hdata jsonb;
  hat timestamptz;
  c text;
  o jsonb;
  cur jsonb;
  n int := 0;
begin
  if me is null or old_id is null or old_id = me or tok is null or length(tok) < 20 then return 0; end if;
  if exists (select 1 from auth.users where id = auth.uid() and is_anonymous) then return 0; end if;
  if not exists (select 1 from auth.users where id::text = old_id and is_anonymous) then return 0; end if;
  select data, updated_at into hdata, hat from docs where col = 'handoff' and id = old_id;
  if hdata is null or hdata->>'t' is distinct from tok or hat < now() - interval '2 days' then return 0; end if;
  foreach c in array array['submissions', 'corrections', 'messages', 'outcomes'] loop
    select data into o from docs where col = c and id = old_id;
    if o is not null then
      select data into cur from docs where col = c and id = me;
      insert into docs (col, id, data)
        values (c, me, jsonb_build_object('items', coalesce(cur->'items', '[]'::jsonb) || coalesce(o->'items', '[]'::jsonb)))
        on conflict (col, id) do update set data = excluded.data;
      delete from docs where col = c and id = old_id;
      n := n + 1;
    end if;
  end loop;
  delete from docs where col = 'handoff' and id = old_id;
  return n;
end $$;
revoke all on function public.claim_guest(text, text) from public, anon;
grant execute on function public.claim_guest(text, text) to authenticated;

-- 4. "Delete my account": removes the account and everything linked to it (Data Protection Act)
create or replace function public.delete_me() returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then return; end if;
  if public.is_admin() then raise exception 'Admins can''t delete their account from the site. Remove the admin first.'; end if;
  delete from docs where id = auth.uid()::text
    and col in ('users', 'outcomes', 'handoff', 'remlog', 'submissions', 'corrections', 'messages', 'stats');
  delete from auth.users where id = auth.uid();
end $$;
revoke all on function public.delete_me() from public, anon;
grant execute on function public.delete_me() to authenticated;
