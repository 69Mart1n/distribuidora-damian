-- One-time, expiring invitations for additional administrators.

create table if not exists private.admin_invitations (
  id uuid primary key default gen_random_uuid(),
  token_hash bytea not null unique,
  created_by uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '72 hours'),
  used_at timestamptz,
  used_by uuid references auth.users(id) on delete set null
);

revoke all on table private.admin_invitations from public, anon, authenticated;

create index if not exists admin_invitations_expires_at_idx
  on private.admin_invitations (expires_at)
  where used_at is null;

create or replace function private.create_admin_invitation()
returns text
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_token text;
begin
  if not private.is_admin() then
    raise insufficient_privilege using message = 'Solo un administrador puede crear invitaciones';
  end if;

  perform private.consume_rate_limit('admin_invitation', 10, 86400);
  v_token := encode(extensions.gen_random_bytes(24), 'hex');

  insert into private.admin_invitations (token_hash, created_by)
  values (extensions.digest(v_token, 'sha256'), (select auth.uid()));

  delete from private.admin_invitations
  where expires_at < now() - interval '7 days';

  return v_token;
end;
$$;

revoke all on function private.create_admin_invitation()
  from public, anon, authenticated;
grant execute on function private.create_admin_invitation() to authenticated;

create or replace function public.create_admin_invitation()
returns text
language sql
volatile
security invoker
set search_path = ''
as $$
  select private.create_admin_invitation();
$$;

revoke all on function public.create_admin_invitation() from public, anon;
grant execute on function public.create_admin_invitation() to authenticated;

create or replace function private.admin_invitation_is_valid(p_token text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from private.admin_invitations
    where token_hash = extensions.digest(p_token, 'sha256')
      and used_at is null
      and expires_at > now()
  );
$$;

revoke all on function private.admin_invitation_is_valid(text)
  from public, anon, authenticated;
grant execute on function private.admin_invitation_is_valid(text)
  to anon, authenticated;

create or replace function public.admin_invitation_is_valid(p_token text)
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
  select private.admin_invitation_is_valid(p_token);
$$;

revoke all on function public.admin_invitation_is_valid(text) from public;
grant execute on function public.admin_invitation_is_valid(text)
  to anon, authenticated;

create or replace function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_first_admin boolean;
  v_invitation_id uuid;
  v_invitation_token text;
  v_is_invited_admin boolean := false;
begin
  perform pg_advisory_xact_lock(hashtext('distribuidora_damian_first_admin'));

  select not exists (
    select 1 from public.profiles where role = 'admin'
  ) into v_first_admin;

  v_invitation_token := nullif(
    trim(coalesce(new.raw_user_meta_data ->> 'admin_invitation_token', '')),
    ''
  );

  if v_invitation_token is not null then
    select id
      into v_invitation_id
    from private.admin_invitations
    where token_hash = extensions.digest(v_invitation_token, 'sha256')
      and used_at is null
      and expires_at > now()
    for update;

    v_is_invited_admin := found;
  end if;

  insert into public.profiles (id, full_name, email, role, active)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1)),
    new.email,
    case when v_first_admin or v_is_invited_admin then 'admin' else 'client' end,
    v_first_admin or v_is_invited_admin
  )
  on conflict (id) do update
  set email = excluded.email,
      updated_at = now();

  if v_is_invited_admin then
    update private.admin_invitations
    set used_at = now(),
        used_by = new.id
    where id = v_invitation_id;
  end if;

  return new;
end;
$$;

notify pgrst, 'reload schema';
