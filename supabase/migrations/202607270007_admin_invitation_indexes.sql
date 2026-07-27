create index if not exists admin_invitations_created_by_idx
  on private.admin_invitations (created_by);

create index if not exists admin_invitations_used_by_idx
  on private.admin_invitations (used_by);
