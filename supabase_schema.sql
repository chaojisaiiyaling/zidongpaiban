create table if not exists leaves (
  person text not null,
  date text not null,
  primary key (person, date)
);

create table if not exists schedules (
  month_key text primary key,
  records jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists schedules_set_updated_at on schedules;

create trigger schedules_set_updated_at
before update on schedules
for each row
execute function set_updated_at();

alter table leaves enable row level security;
alter table schedules enable row level security;

grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on leaves to anon, authenticated;
grant select, insert, update, delete on schedules to anon, authenticated;

drop policy if exists "Allow public read leaves" on leaves;
drop policy if exists "Allow public insert leaves" on leaves;
drop policy if exists "Allow public update leaves" on leaves;
drop policy if exists "Allow public delete leaves" on leaves;

create policy "Allow public read leaves"
on leaves for select
to anon, authenticated
using (true);

create policy "Allow public insert leaves"
on leaves for insert
to anon, authenticated
with check (true);

create policy "Allow public update leaves"
on leaves for update
to anon, authenticated
using (true)
with check (true);

create policy "Allow public delete leaves"
on leaves for delete
to anon, authenticated
using (true);

drop policy if exists "Allow public read schedules" on schedules;
drop policy if exists "Allow public insert schedules" on schedules;
drop policy if exists "Allow public update schedules" on schedules;
drop policy if exists "Allow public delete schedules" on schedules;

create policy "Allow public read schedules"
on schedules for select
to anon, authenticated
using (true);

create policy "Allow public insert schedules"
on schedules for insert
to anon, authenticated
with check (true);

create policy "Allow public update schedules"
on schedules for update
to anon, authenticated
using (true)
with check (true);

create policy "Allow public delete schedules"
on schedules for delete
to anon, authenticated
using (true);
