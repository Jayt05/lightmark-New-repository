-- Lightmark database setup. Paste all of this into Supabase > SQL Editor and press Run.
-- Every read and write must carry the password, checked here on the server (not in the web page).

create table if not exists public.folders (
  id text primary key default gen_random_uuid()::text,
  name text not null,
  created timestamptz not null default now()
);

create table if not exists public.drawings (
  id text primary key default gen_random_uuid()::text,
  name text not null,
  w integer not null,
  h integer not null,
  created timestamptz not null default now(),
  ai boolean not null default false,
  thumb text,
  layers jsonb not null default '[]'::jsonb,
  marks jsonb not null default '[]'::jsonb,
  folder text references public.folders(id) on delete set null
);

create table if not exists public.drawing_images (
  id text primary key references public.drawings(id) on delete cascade,
  data text not null
);

-- To change the password later, edit 'potter' below (keep it lower case) and run this statement again.
create or replace function public.lm_pass_ok() returns boolean
language sql stable as $$
  select lower(coalesce(current_setting('request.headers', true)::json ->> 'x-lightmark-pass', '')) = 'potter'
$$;
grant execute on function public.lm_pass_ok() to anon;

alter table public.drawings enable row level security;
alter table public.drawing_images enable row level security;
alter table public.folders enable row level security;

drop policy if exists "password holders" on public.drawings;
create policy "password holders" on public.drawings for all to anon
  using (public.lm_pass_ok()) with check (public.lm_pass_ok());

drop policy if exists "password holders" on public.drawing_images;
create policy "password holders" on public.drawing_images for all to anon
  using (public.lm_pass_ok()) with check (public.lm_pass_ok());

drop policy if exists "password holders" on public.folders;
create policy "password holders" on public.folders for all to anon
  using (public.lm_pass_ok()) with check (public.lm_pass_ok());

grant select, insert, update, delete on public.drawings, public.drawing_images, public.folders to anon;
