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
