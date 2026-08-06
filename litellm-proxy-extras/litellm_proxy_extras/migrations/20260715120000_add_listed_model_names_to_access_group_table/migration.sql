-- AlterTable
ALTER TABLE "LiteLLM_AccessGroupTable"
  ADD COLUMN IF NOT EXISTS "listed_model_names" TEXT[] DEFAULT ARRAY[]::TEXT[];
