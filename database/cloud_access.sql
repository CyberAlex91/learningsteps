-- Apply only to the dedicated LearningSteps database as its administrator.
-- Existing note contents and owner assignments are never updated here.
ALTER TABLE public.entries
    ADD COLUMN IF NOT EXISTS owner_tenant_id UUID,
    ADD COLUMN IF NOT EXISTS owner_object_id UUID;

CREATE INDEX IF NOT EXISTS idx_entries_owner_created
    ON public.entries(owner_tenant_id, owner_object_id, created_at, id);

REVOKE ALL ON DATABASE learningsteps FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON TABLE public.entries FROM PUBLIC;

GRANT CONNECT ON DATABASE learningsteps TO learningsteps_app;
GRANT USAGE ON SCHEMA public TO learningsteps_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.entries TO learningsteps_app;
