ALTER TABLE public.assistant_knowledge_pdfs
  ADD COLUMN IF NOT EXISTS legal_version_label varchar(120) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS legal_effective_date varchar(10) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS legal_election_type varchar(20) NOT NULL DEFAULT 'UNSPECIFIED';
