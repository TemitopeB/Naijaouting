-- NaijaOuting database setup
-- Paste all of this into Supabase -> SQL Editor -> New query, then press Run.
-- Safe to run more than once.

-- 1. One table holds everything the site stores, as "collections" of documents:
--    events (approved events), overrides (fixes and hidden events), flags,
--    and per-person submissions, corrections, messages and stats.
create table if not exists public.docs (
  col        text        not null,
  id         text        not null,
  data       jsonb       not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (col, id),
  constraint docs_size check (pg_column_size(data) < 300000)
);

-- 2. Who can approve, edit and delete. Add yourself after creating your login (see README).
create table if not exists public.admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid())
$$;

create or replace function public.docs_touch() returns trigger
language plpgsql as $$ begin new.updated_at = now(); return new; end $$;
drop trigger if exists docs_touch on public.docs;
create trigger docs_touch before update on public.docs
  for each row execute function public.docs_touch();

-- 3. Access rules (row level security)
alter table public.docs   enable row level security;
alter table public.admins enable row level security;

drop policy if exists "admins see themselves" on public.admins;
create policy "admins see themselves" on public.admins
  for select using (user_id = auth.uid());

drop policy if exists "anyone reads public collections" on public.docs;
create policy "anyone reads public collections" on public.docs
  for select using (col in ('events', 'overrides', 'flags'));

drop policy if exists "people read their own documents" on public.docs;
create policy "people read their own documents" on public.docs
  for select using (col in ('submissions', 'corrections', 'messages', 'stats') and id = auth.uid()::text);

drop policy if exists "people create their own documents" on public.docs;
create policy "people create their own documents" on public.docs
  for insert with check (col in ('submissions', 'corrections', 'messages', 'stats', 'flags') and id = auth.uid()::text);

drop policy if exists "people update their own documents" on public.docs;
create policy "people update their own documents" on public.docs
  for update using (col in ('submissions', 'corrections', 'messages', 'stats', 'flags') and id = auth.uid()::text)
  with check (col in ('submissions', 'corrections', 'messages', 'stats', 'flags') and id = auth.uid()::text);

drop policy if exists "admins do everything" on public.docs;
create policy "admins do everything" on public.docs
  for all using (public.is_admin()) with check (public.is_admin());

-- 4. Live updates: the site refreshes as soon as an event is approved
do $$ begin
  alter publication supabase_realtime add table public.docs;
exception when duplicate_object then null; when undefined_object then null;
end $$;

-- 5. Flyer storage: public pictures, uploads by visitors, deletes by admins only
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('flyers', 'flyers', true, 5242880, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do nothing;

drop policy if exists "visitors upload flyers" on storage.objects;
create policy "visitors upload flyers" on storage.objects
  for insert to authenticated with check (bucket_id = 'flyers');

drop policy if exists "admins delete flyers" on storage.objects;
create policy "admins delete flyers" on storage.objects
  for delete using (bucket_id = 'flyers' and public.is_admin());
