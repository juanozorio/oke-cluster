terraform {
  required_version = ">= 1.3.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.23" # permite 5.x (correções/CVEs), trava subida acidental pra 6.x
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}