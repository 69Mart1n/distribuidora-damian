-- PostgREST may execute read-only requests inside read-only transactions.
-- A pre-request hook that writes counters would block legitimate SELECT/RPC
-- calls. Keep the write and sensitive-operation limits, and remove this hook.

alter role authenticator reset pgrst.db_pre_request;
revoke execute on function public.check_request_limit()
  from public, anon, authenticated;
drop function if exists public.check_request_limit();

revoke execute on function private.consume_rate_limit(text, integer, integer)
  from anon, authenticated;

notify pgrst, 'reload config';
notify pgrst, 'reload schema';
