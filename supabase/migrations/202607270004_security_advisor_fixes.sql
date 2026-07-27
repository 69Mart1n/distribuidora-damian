-- Follow-up hardening from the Supabase security and performance advisors.

alter function public.set_updated_at() set search_path = '';

-- Keep exposed RPC wrappers as invokers. The sensitive work stays in the
-- non-exposed private schema and is narrowly granted to the wrapper callers.
grant usage on schema private to anon, authenticated;
grant execute on function private.consume_rate_limit(text, integer, integer)
  to anon, authenticated;

create or replace function public.check_request_limit()
returns void
language plpgsql
volatile
security invoker
set search_path = ''
as $$
begin
  perform private.consume_rate_limit('data_api', 300, 60);
end;
$$;

create or replace function private.bootstrap_admin_available()
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

revoke all on function private.bootstrap_admin_available()
  from public, anon, authenticated;
grant execute on function private.bootstrap_admin_available()
  to anon, authenticated;

create or replace function public.can_bootstrap_admin()
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
  select private.bootstrap_admin_available();
$$;

drop policy if exists "Admins manage promotions" on public.volume_promotions;
create policy "Admins insert promotions"
  on public.volume_promotions for insert to authenticated
  with check ((select private.is_admin()));
create policy "Admins update promotions"
  on public.volume_promotions for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));
create policy "Admins delete promotions"
  on public.volume_promotions for delete to authenticated
  using ((select private.is_admin()));

create index if not exists price_history_changed_by_idx
  on public.price_history (changed_by);
create index if not exists price_history_product_id_idx
  on public.price_history (product_id);
create index if not exists receipt_items_product_id_idx
  on public.receipt_items (product_id);
create index if not exists receipt_items_receipt_id_idx
  on public.receipt_items (receipt_id);
create index if not exists receipt_payments_created_by_idx
  on public.receipt_payments (created_by);
create index if not exists receipt_payments_receipt_id_idx
  on public.receipt_payments (receipt_id);
create index if not exists receipts_created_by_idx
  on public.receipts (created_by);

notify pgrst, 'reload schema';
