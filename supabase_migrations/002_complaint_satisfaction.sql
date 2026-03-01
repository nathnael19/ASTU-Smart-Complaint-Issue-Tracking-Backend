-- Add satisfaction feedback message to complaints table
ALTER TABLE complaints 
ADD COLUMN IF NOT EXISTS satisfaction_message TEXT;

-- Ensure satisfaction_rating exists (it should, but just in case)
ALTER TABLE complaints 
ADD COLUMN IF NOT EXISTS satisfaction_rating INTEGER CHECK (satisfaction_rating >= 1 AND satisfaction_rating <= 5);
