create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  role text not null default 'employee' check (role in ('admin', 'employee')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.settings (
  id smallint primary key default 1 check (id = 1),
  business_name text not null default 'Distribuidora Damián',
  business_phone text,
  business_address text,
  business_email text,
  currency_symbol text not null default '$',
  receipt_prefix text not null default 'BD',
  next_receipt_number integer not null default 501 check (next_receipt_number > 0),
  updated_at timestamptz not null default now()
);

create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  barcode text,
  name text not null,
  presentation text not null default 'Unidad',
  supplier text not null default 'Otros',
  category text not null default 'Otros',
  purchase_price numeric(12, 2),
  wholesale_price numeric(12, 2),
  retail_price numeric(12, 2),
  active boolean not null default true,
  requires_review boolean not null default false,
  source_page smallint,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (supplier, name, presentation)
);

create index if not exists products_search_idx
  on public.products using gin (to_tsvector('spanish', name || ' ' || supplier || ' ' || category));
create index if not exists products_active_idx on public.products(active);

create table if not exists public.customers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  business_name text,
  document text,
  phone text,
  alternative_phone text,
  address text,
  email text,
  customer_type text not null default 'wholesale',
  notes text,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists customers_name_idx on public.customers(name);
create index if not exists customers_phone_idx on public.customers(phone);

create table if not exists public.receipts (
  id uuid primary key default gen_random_uuid(),
  receipt_number integer not null unique,
  receipt_code text not null unique,
  customer_id uuid references public.customers(id),
  customer_name_snapshot text not null,
  customer_phone_snapshot text,
  customer_address_snapshot text,
  issued_at timestamptz not null default now(),
  subtotal numeric(12, 2) not null default 0,
  discount_type text,
  discount_value numeric(12, 2) not null default 0,
  discount_amount numeric(12, 2) not null default 0,
  total numeric(12, 2) not null default 0,
  payment_method text not null default 'cash'
    check (payment_method in ('cash', 'transfer', 'account', 'mixed')),
  payment_status text not null default 'paid'
    check (payment_status in ('paid', 'partial', 'pending')),
  amount_paid numeric(12, 2) not null default 0,
  pending_amount numeric(12, 2) not null default 0,
  notes text,
  status text not null default 'active' check (status in ('active', 'cancelled')),
  cancelled_at timestamptz,
  cancellation_reason text,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists receipts_issued_at_idx on public.receipts(issued_at desc);
create index if not exists receipts_customer_idx on public.receipts(customer_id);
create index if not exists receipts_pending_idx on public.receipts(pending_amount) where pending_amount > 0;

create table if not exists public.receipt_items (
  id uuid primary key default gen_random_uuid(),
  receipt_id uuid not null references public.receipts(id) on delete cascade,
  product_id uuid references public.products(id),
  product_code_snapshot text,
  product_name_snapshot text not null,
  presentation_snapshot text,
  quantity numeric(12, 3) not null check (quantity > 0),
  unit_price numeric(12, 2) not null check (unit_price >= 0),
  discount_percentage numeric(7, 3) not null default 0,
  line_total numeric(12, 2) not null check (line_total >= 0),
  created_at timestamptz not null default now()
);

create table if not exists public.receipt_payments (
  id uuid primary key default gen_random_uuid(),
  receipt_id uuid not null references public.receipts(id) on delete cascade,
  payment_method text not null check (payment_method in ('cash', 'transfer', 'account', 'other')),
  amount numeric(12, 2) not null check (amount > 0),
  paid_at timestamptz not null default now(),
  notes text,
  active boolean not null default true,
  created_by uuid references auth.users(id)
);

create table if not exists public.price_history (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references public.products(id) on delete cascade,
  old_price numeric(12, 2),
  new_price numeric(12, 2),
  reason text,
  changed_by uuid references auth.users(id),
  changed_at timestamptz not null default now()
);

create table if not exists public.volume_promotions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  minimum_kg numeric(10, 2) not null,
  discount_percentage numeric(7, 3) not null,
  active boolean not null default true,
  unique (name, minimum_kg)
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists products_set_updated_at on public.products;
create trigger products_set_updated_at before update on public.products
for each row execute function public.set_updated_at();
drop trigger if exists customers_set_updated_at on public.customers;
create trigger customers_set_updated_at before update on public.customers
for each row execute function public.set_updated_at();
drop trigger if exists receipts_set_updated_at on public.receipts;
create trigger receipts_set_updated_at before update on public.receipts
for each row execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, full_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'full_name', new.email));
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

insert into public.settings (id) values (1) on conflict (id) do nothing;

create or replace function public.create_receipt(p_payload jsonb)
returns jsonb
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_number integer;
  v_prefix text;
  v_receipt_id uuid;
  v_subtotal numeric(12, 2);
  v_discount numeric(12, 2);
  v_total numeric(12, 2);
  v_paid numeric(12, 2);
  v_item jsonb;
begin
  if jsonb_array_length(coalesce(p_payload -> 'items', '[]'::jsonb)) = 0 then
    raise exception 'La boleta debe incluir al menos un producto.';
  end if;

  select next_receipt_number, receipt_prefix
  into v_number, v_prefix
  from public.settings
  where id = 1
  for update;

  select coalesce(sum(
    (item ->> 'quantity')::numeric * (item ->> 'unitPrice')::numeric
  ), 0)
  into v_subtotal
  from jsonb_array_elements(p_payload -> 'items') as item;

  v_discount := round(v_subtotal * coalesce((p_payload ->> 'discountPercentage')::numeric, 0) / 100, 2);
  v_total := greatest(v_subtotal - v_discount, 0);
  v_paid := least(greatest(coalesce((p_payload ->> 'amountPaid')::numeric, 0), 0), v_total);

  insert into public.receipts (
    receipt_number, receipt_code, customer_id, customer_name_snapshot,
    customer_phone_snapshot, customer_address_snapshot, subtotal, discount_type, discount_value,
    discount_amount, total, payment_method, payment_status, amount_paid,
    pending_amount, notes, created_by
  )
  values (
    v_number,
    v_prefix || '-' || lpad(v_number::text, 6, '0'),
    nullif(p_payload ->> 'customerId', '')::uuid,
    coalesce(nullif(p_payload ->> 'customerName', ''), 'Cliente ocasional'),
    nullif(p_payload ->> 'customerPhone', ''),
    nullif(p_payload ->> 'customerAddress', ''),
    v_subtotal,
    case when coalesce((p_payload ->> 'discountPercentage')::numeric, 0) > 0 then 'percentage' end,
    coalesce((p_payload ->> 'discountPercentage')::numeric, 0),
    v_discount,
    v_total,
    coalesce(nullif(p_payload ->> 'paymentMethod', ''), 'cash'),
    case when v_paid >= v_total then 'paid' when v_paid > 0 then 'partial' else 'pending' end,
    v_paid,
    v_total - v_paid,
    nullif(p_payload ->> 'notes', ''),
    (select auth.uid())
  )
  returning id into v_receipt_id;

  for v_item in select * from jsonb_array_elements(p_payload -> 'items')
  loop
    insert into public.receipt_items (
      receipt_id, product_id, product_code_snapshot, product_name_snapshot,
      presentation_snapshot, quantity, unit_price, line_total
    )
    values (
      v_receipt_id,
      nullif(v_item ->> 'productId', '')::uuid,
      nullif(v_item ->> 'code', ''),
      v_item ->> 'name',
      nullif(v_item ->> 'presentation', ''),
      (v_item ->> 'quantity')::numeric,
      (v_item ->> 'unitPrice')::numeric,
      round((v_item ->> 'quantity')::numeric * (v_item ->> 'unitPrice')::numeric, 2)
    );
  end loop;

  if v_paid > 0 then
    insert into public.receipt_payments (
      receipt_id, payment_method, amount, created_by
    )
    values (
      v_receipt_id,
      case
        when p_payload ->> 'paymentMethod' = 'mixed' then 'other'
        when p_payload ->> 'paymentMethod' = 'account' then 'other'
        else p_payload ->> 'paymentMethod'
      end,
      v_paid,
      (select auth.uid())
    );
  end if;

  update public.settings set next_receipt_number = v_number + 1 where id = 1;
  return jsonb_build_object(
    'id', v_receipt_id,
    'code', v_prefix || '-' || lpad(v_number::text, 6, '0')
  );
end;
$$;

alter table public.profiles enable row level security;
alter table public.settings enable row level security;
alter table public.products enable row level security;
alter table public.customers enable row level security;
alter table public.receipts enable row level security;
alter table public.receipt_items enable row level security;
alter table public.receipt_payments enable row level security;
alter table public.price_history enable row level security;
alter table public.volume_promotions enable row level security;

create policy "Authenticated users can read profiles"
  on public.profiles for select to authenticated using (true);
create policy "Users can update their profile"
  on public.profiles for update to authenticated
  using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

create policy "Authenticated users can manage settings"
  on public.settings for all to authenticated using (true) with check (true);
create policy "Authenticated users can manage products"
  on public.products for all to authenticated using (true) with check (true);
create policy "Authenticated users can manage customers"
  on public.customers for all to authenticated using (true) with check (true);
create policy "Authenticated users can manage receipts"
  on public.receipts for all to authenticated using (true) with check (true);
create policy "Authenticated users can manage receipt items"
  on public.receipt_items for all to authenticated using (true) with check (true);
create policy "Authenticated users can manage receipt payments"
  on public.receipt_payments for all to authenticated using (true) with check (true);
create policy "Authenticated users can manage price history"
  on public.price_history for all to authenticated using (true) with check (true);
create policy "Authenticated users can manage promotions"
  on public.volume_promotions for all to authenticated using (true) with check (true);

create or replace view public.customer_balances
with (security_invoker = true)
as
select
  c.id,
  c.name,
  count(r.id) filter (where r.status = 'active') as receipts_count,
  coalesce(sum(r.total) filter (where r.status = 'active'), 0) as total_purchased,
  coalesce(sum(r.pending_amount) filter (where r.status = 'active'), 0) as pending_balance
from public.customers c
left join public.receipts r on r.customer_id = c.id
group by c.id, c.name;
