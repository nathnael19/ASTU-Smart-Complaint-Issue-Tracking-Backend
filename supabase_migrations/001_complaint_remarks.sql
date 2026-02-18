-- Complaint thread: messages from students, staff, and admins on a specific complaint.
-- Run this in Supabase SQL Editor if the table does not exist.

CREATE TABLE IF NOT EXISTS complaint_remarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  complaint_id UUID NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
  author_id UUID NOT NULL REFERENCES users(id),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_complaint_remarks_complaint_id ON complaint_remarks(complaint_id);
CREATE INDEX IF NOT EXISTS idx_complaint_remarks_created_at ON complaint_remarks(created_at);

-- RLS (optional): enable if you want row-level security; otherwise backend uses service role.
-- ALTER TABLE complaint_remarks ENABLE ROW LEVEL SECURITY;
