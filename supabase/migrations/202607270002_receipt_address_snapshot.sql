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
    customer_phone_snapshot, customer_address_snapshot, subtotal, discount_type,
    discount_value, discount_amount, total, payment_method, payment_status,
    amount_paid, pending_amount, notes, created_by
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
