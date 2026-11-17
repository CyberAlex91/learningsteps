-- Additive migration: no note contents, identifiers or timestamps are changed.
-- Existing ownerless records stay unassigned and invisible to user-scoped APIs.
BEGIN;
ALTER TABLE public.entries
    ADD COLUMN IF NOT EXISTS owner_tenant_id UUID,
    ADD COLUMN IF NOT EXISTS owner_object_id UUID;
CREATE INDEX IF NOT EXISTS idx_entries_owner_created
    ON public.entries (owner_tenant_id, owner_object_id, created_at, id);
COMMIT;
