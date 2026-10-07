-- Lightmark folders. Paste into Supabase > SQL Editor and press Run (safe to run more than once).

create table if not exists public.folders (
  id text primary key default gen_random_uuid()::text,
  name text not null,
  created timestamptz not null default now()
);

alter table public.drawings add column if not exists folder text references public.folders(id) on delete set null;

alter table public.folders enable row level security;
drop policy if exists "password holders" on public.folders;
create policy "password holders" on public.folders for all to anon
  using (public.lm_pass_ok()) with check (public.lm_pass_ok());

grant select, insert, update, delete on public.folders to anon;

-- Make the API notice the new column straight away.
notify pgrst, 'reload schema';
