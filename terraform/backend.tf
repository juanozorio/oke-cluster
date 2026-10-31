# ---------------------------------------------------------------------------
# Remote state (Juan)
# ---------------------------------------------------------------------------
# O state fica no bucket S3 "oke-tf-state" (us-east-1), não mais em arquivos
# locais versionados por acidente. Isso dá histórico e um lugar único pro state.
#
# Primeira migração (uma vez só):
#   terraform init -migrate-state      # (ou: tofu init -migrate-state)
# Ele pergunta se quer copiar o terraform.tfstate local para o S3 -> yes.
#
# Recomendado (uma vez, fora do Terraform) para segurança do state:
#   aws s3api put-bucket-versioning --bucket oke-tf-state \
#     --versioning-configuration Status=Enabled
#
# Lock de state: como você monta a escala/cluster sozinho, não há DynamoDB aqui.
# Se um dia quiser trava contra 'apply' simultâneo, use um binário recente
# (Terraform >= 1.10 ou OpenTofu >= 1.8) e adicione a linha:
#     use_lockfile = true
# ---------------------------------------------------------------------------

terraform {
  backend "s3" {
    bucket  = "oke-tf-state"
    key     = "oke-free/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
