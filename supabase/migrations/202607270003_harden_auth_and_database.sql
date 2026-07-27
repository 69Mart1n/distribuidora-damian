-- Security hardening for Distribuidora Damian.
-- This migration is intentionally idempotent where PostgreSQL permits it.

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

alter table public.profiles
  add column if not exists email text,
  add column if not exists active boolean not null default false;

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conname = 'profiles_role_check'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles drop constraint profiles_role_check;
  end if;
  alter table public.profiles
    add constraint profiles_role_check
    check (role in ('admin', 'employee', 'client'));
end
$$;

alter table public.profiles alter column role set default 'client';

create index if not exists profiles_role_active_idx
  on public.profiles (role, active);

create table if not exists private.rate_limit_buckets (
  identifier text not null,
  action text not null,
  window_start timestamptz not null,
  request_count integer not null default 0 check (request_count >= 0),
  primary key (identifier, action, window_start)
);

create table if not exists public.audit_logs (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) on delete set null,
  action text not null,
  entity_type text not null,
  entity_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_logs_created_at_idx
  on public.audit_logs (created_at desc);
create index if not exists audit_logs_user_id_idx
  on public.audit_logs (user_id);

alter table public.audit_logs enable row level security;

create or replace function private.is_active_staff()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.profiles
    where id = (select auth.uid())
      and active
      and role in ('admin', 'employee')
  );
$$;

create or replace function private.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.profiles
    where id = (select auth.uid())
      and active
      and role = 'admin'
  );
$$;

revoke all on function private.is_active_staff() from public, anon;
revoke all on function private.is_admin() from public, anon;
grant execute on function private.is_active_staff() to authenticated;
grant execute on function private.is_admin() to authenticated;

create or replace function private.consume_rate_limit(
  p_action text,
  p_limit integer,
  p_window_seconds integer
)
returns void
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_identifier text;
  v_window_start timestamptz;
  v_count integer;
  v_headers jsonb;
begin
  if p_limit < 1 or p_window_seconds < 1 then
    raise exception 'Invalid rate-limit configuration';
  end if;

  v_headers := coalesce(
    nullif(current_setting('request.headers', true), '')::jsonb,
    '{}'::jsonb
  );
  v_identifier := coalesce(
    (select auth.uid())::text,
    nullif(split_part(coalesce(v_headers ->> 'x-forwarded-for', ''), ',', 1), ''),
    'anonymous'
  );
  v_window_start := to_timestamp(
    floor(extract(epoch from clock_timestamp()) / p_window_seconds) * p_window_seconds
  );

  insert into private.rate_limit_buckets (
    identifier,
    action,
    window_start,
    request_count
  )
  values (v_identifier, p_action, v_window_start, 1)
  on conflict (identifier, action, window_start)
  do update set request_count = private.rate_limit_buckets.request_count + 1
  returning request_count into v_count;

  delete from private.rate_limit_buckets
  where window_start < clock_timestamp() - interval '24 hours';

  if v_count > p_limit then
    raise sqlstate 'PGRST'
      using message = json_build_object(
        'code', 'RATE_LIMITED',
        'message', 'Demasiadas peticiones. Intenta nuevamente en un minuto.'
      )::text,
      detail = json_build_object(
        'status', 429,
        'headers', json_build_object('Retry-After', p_window_seconds::text)
      )::text;
  end if;
end;
$$;

revoke all on function private.consume_rate_limit(text, integer, integer)
  from public, anon, authenticated;

create or replace function public.check_request_limit()
returns void
language plpgsql
volatile
security definer
set search_path = ''
as $$
begin
  perform private.consume_rate_limit('data_api', 300, 60);
end;
$$;

revoke all on function public.check_request_limit() from public;
grant execute on function public.check_request_limit() to anon, authenticated;

alter role authenticator
  set pgrst.db_pre_request = 'public.check_request_limit';
notify pgrst, 'reload config';

create or replace function private.enforce_write_rate_limit()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if (select auth.uid()) is not null then
    perform private.consume_rate_limit('database_write', 60, 60);
  end if;
  return null;
end;
$$;

revoke all on function private.enforce_write_rate_limit()
  from public, anon, authenticated;

create or replace function private.write_audit_log()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_id text;
begin
  v_id := case
    when tg_op = 'DELETE' then to_jsonb(old) ->> 'id'
    else to_jsonb(new) ->> 'id'
  end;

  insert into public.audit_logs (
    user_id,
    action,
    entity_type,
    entity_id,
    metadata
  )
  values (
    (select auth.uid()),
    lower(tg_op),
    tg_table_name,
    v_id,
    jsonb_build_object('source', 'web')
  );

  return case when tg_op = 'DELETE' then old else new end;
end;
$$;

revoke all on function private.write_audit_log()
  from public, anon, authenticated;

drop trigger if exists products_write_rate_limit on public.products;
create trigger products_write_rate_limit
  before insert or update or delete on public.products
  for each statement execute function private.enforce_write_rate_limit();
drop trigger if exists customers_write_rate_limit on public.customers;
create trigger customers_write_rate_limit
  before insert or update or delete on public.customers
  for each statement execute function private.enforce_write_rate_limit();
drop trigger if exists receipts_write_rate_limit on public.receipts;
create trigger receipts_write_rate_limit
  before insert or update or delete on public.receipts
  for each statement execute function private.enforce_write_rate_limit();

drop trigger if exists products_audit_log on public.products;
create trigger products_audit_log
  after insert or update or delete on public.products
  for each row execute function private.write_audit_log();
drop trigger if exists customers_audit_log on public.customers;
create trigger customers_audit_log
  after insert or update or delete on public.customers
  for each row execute function private.write_audit_log();
drop trigger if exists receipts_audit_log on public.receipts;
create trigger receipts_audit_log
  after insert or update or delete on public.receipts
  for each row execute function private.write_audit_log();

create or replace function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_first_admin boolean;
begin
  perform pg_advisory_xact_lock(hashtext('distribuidora_damian_first_admin'));

  select not exists (
    select 1 from public.profiles where role = 'admin'
  ) into v_first_admin;

  insert into public.profiles (id, full_name, email, role, active)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1)),
    new.email,
    case when v_first_admin then 'admin' else 'client' end,
    v_first_admin
  )
  on conflict (id) do update
  set email = excluded.email,
      updated_at = now();

  return new;
end;
$$;

revoke all on function private.handle_new_user()
  from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function private.handle_new_user();

drop function if exists public.handle_new_user();

create or replace function public.can_bootstrap_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select not exists (
    select 1 from public.profiles where role = 'admin'
  );
$$;

revoke all on function public.can_bootstrap_admin() from public;
grant execute on function public.can_bootstrap_admin() to anon, authenticated;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'products_name_length_check'
      and conrelid = 'public.products'::regclass
  ) then
    alter table public.products
      add constraint products_name_length_check
      check (char_length(name) between 1 and 200);
  end if;
  if not exists (
    select 1 from pg_constraint
    where conname = 'products_presentation_length_check'
      and conrelid = 'public.products'::regclass
  ) then
    alter table public.products
      add constraint products_presentation_length_check
      check (char_length(presentation) between 1 and 100);
  end if;
  if not exists (
    select 1 from pg_constraint
    where conname = 'customers_name_length_check'
      and conrelid = 'public.customers'::regclass
  ) then
    alter table public.customers
      add constraint customers_name_length_check
      check (char_length(name) between 1 and 200);
  end if;
  if not exists (
    select 1 from pg_constraint
    where conname = 'receipts_notes_length_check'
      and conrelid = 'public.receipts'::regclass
  ) then
    alter table public.receipts
      add constraint receipts_notes_length_check
      check (notes is null or char_length(notes) <= 2000);
  end if;
end
$$;

drop policy if exists "Authenticated users can read profiles" on public.profiles;
drop policy if exists "Users can update their profile" on public.profiles;
drop policy if exists "Authenticated users can manage settings" on public.settings;
drop policy if exists "Authenticated users can manage products" on public.products;
drop policy if exists "Authenticated users can manage customers" on public.customers;
drop policy if exists "Authenticated users can manage receipts" on public.receipts;
drop policy if exists "Authenticated users can manage receipt items" on public.receipt_items;
drop policy if exists "Authenticated users can manage receipt payments" on public.receipt_payments;
drop policy if exists "Authenticated users can manage price history" on public.price_history;
drop policy if exists "Authenticated users can manage promotions" on public.volume_promotions;

create policy "Users read their own profile"
  on public.profiles for select to authenticated
  using ((select auth.uid()) = id or (select private.is_admin()));
create policy "Admins update profiles"
  on public.profiles for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));

create policy "Staff read settings"
  on public.settings for select to authenticated
  using ((select private.is_active_staff()));
create policy "Admins update settings"
  on public.settings for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));

create policy "Staff read products"
  on public.products for select to authenticated
  using ((select private.is_active_staff()));
create policy "Staff add products"
  on public.products for insert to authenticated
  with check ((select private.is_active_staff()));
create policy "Staff update products"
  on public.products for update to authenticated
  using ((select private.is_active_staff()))
  with check ((select private.is_active_staff()));

create policy "Staff read customers"
  on public.customers for select to authenticated
  using ((select private.is_active_staff()));
create policy "Staff add customers"
  on public.customers for insert to authenticated
  with check ((select private.is_active_staff()));
create policy "Staff update customers"
  on public.customers for update to authenticated
  using ((select private.is_active_staff()))
  with check ((select private.is_active_staff()));

create policy "Staff read receipts"
  on public.receipts for select to authenticated
  using ((select private.is_active_staff()));
create policy "Staff add receipts"
  on public.receipts for insert to authenticated
  with check ((select private.is_active_staff()));
create policy "Admins update receipts"
  on public.receipts for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));

create policy "Staff read receipt items"
  on public.receipt_items for select to authenticated
  using ((select private.is_active_staff()));
create policy "Staff add receipt items"
  on public.receipt_items for insert to authenticated
  with check ((select private.is_active_staff()));

create policy "Staff read receipt payments"
  on public.receipt_payments for select to authenticated
  using ((select private.is_active_staff()));
create policy "Staff add receipt payments"
  on public.receipt_payments for insert to authenticated
  with check ((select private.is_active_staff()));

create policy "Staff read price history"
  on public.price_history for select to authenticated
  using ((select private.is_active_staff()));
create policy "Staff add price history"
  on public.price_history for insert to authenticated
  with check ((select private.is_active_staff()));

create policy "Staff read promotions"
  on public.volume_promotions for select to authenticated
  using ((select private.is_active_staff()));
create policy "Admins manage promotions"
  on public.volume_promotions for all to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));

create policy "Admins read audit logs"
  on public.audit_logs for select to authenticated
  using ((select private.is_admin()));

revoke all on all tables in schema public from anon;
grant usage on schema public to authenticated;
grant select on public.profiles, public.settings, public.products, public.customers,
  public.receipts, public.receipt_items, public.receipt_payments,
  public.price_history, public.volume_promotions, public.audit_logs
  to authenticated;
grant insert, update on public.products, public.customers to authenticated;
grant insert, update on public.receipts to authenticated;
grant insert on public.receipt_items, public.receipt_payments, public.price_history
  to authenticated;
grant update on public.settings, public.profiles to authenticated;
grant insert on public.audit_logs to postgres;

revoke execute on function public.create_receipt(jsonb) from public, anon;
grant execute on function public.create_receipt(jsonb) to authenticated;

create or replace function public.apply_price_changes(p_changes jsonb)
returns integer
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_change jsonb;
  v_count integer := 0;
  v_old_price numeric(12, 2);
  v_new_price numeric(12, 2);
  v_product_id uuid;
begin
  if not (select private.is_admin()) then
    raise insufficient_privilege using message = 'Solo un administrador puede aplicar precios masivos.';
  end if;

  perform private.consume_rate_limit('bulk_price_update', 5, 60);

  if jsonb_array_length(coalesce(p_changes, '[]'::jsonb)) > 500 then
    raise exception 'No se pueden actualizar mas de 500 productos por operación.';
  end if;

  for v_change in select * from jsonb_array_elements(coalesce(p_changes, '[]'::jsonb))
  loop
    v_product_id := (v_change ->> 'id')::uuid;
    v_new_price := (v_change ->> 'wholesalePrice')::numeric;
    if v_new_price < 0 then
      raise exception 'El precio no puede ser negativo.';
    end if;

    select wholesale_price into v_old_price
    from public.products
    where id = v_product_id
    for update;

    update public.products
    set wholesale_price = v_new_price,
        requires_review = false
    where id = v_product_id;

    insert into public.price_history (
      product_id,
      old_price,
      new_price,
      reason,
      changed_by
    )
    values (
      v_product_id,
      v_old_price,
      v_new_price,
      'Actualización masiva desde la web',
      (select auth.uid())
    );
    v_count := v_count + 1;
  end loop;

  return v_count;
end;
$$;

revoke execute on function public.apply_price_changes(jsonb) from public, anon;
grant execute on function public.apply_price_changes(jsonb) to authenticated;
