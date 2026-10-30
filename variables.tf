# ----------> Compartment <----------

variable "compartment_name" {
  type    = string
  default = "k8s"
}

variable "region" {
  type    = string
  default = "us-ashburn-1"
}

# ---------->VM's----------

variable "shape" {
  type    = string
  default = "VM.Standard.A1.Flex"
}

variable "ocpus_per_node" {
  type    = number
  default = 1
}

variable "memory_in_gbs_per_node" {
  type    = number
  default = 6
}

variable "image_id" {
  type = string
  # Imagem do worker node (OKE) -- arm64/aarch64, obrigatória para o shape A1.Flex.
  #
  # ATUALIZADO 2026-10-30 (Juan): subido de
  #   Oracle-Linux-8.10-aarch64-2025.09.16-0-OKE-1.34.1-1330  (set/2025, kubelet .1)
  # para
  #   Oracle-Linux-8.10-aarch64-2026.09.18-0-OKE-1.34.10-1923 (set/2026, kubelet .10)
  # Isso traz ~1 ano de patches de SO (Oracle Linux 8.10) e o kubelet 1.34.10,
  # removendo as vulnerabilidades da imagem antiga. O patch do worker (.10) tem
  # que ser <= versão do control plane (k8s_version abaixo = v1.34.10).
  #
  # Para listar as imagens mais recentes e pegar o OCID novamente:
  #   oci ce node-pool-options get --node-pool-option-id all --profile DEFAULT \
  #     --query 'data.sources[?contains("source-name",`OKE-1.34`) && contains("source-name",`aarch64`)]'
  default = "ocid1.image.oc1.iad.aaaaaaaa27cmpw7pgf3cjstdgktqwudiu6a3wt65lgsebqni427mrej4tkoq"
}

# ----------> Cluster <----------

variable "k8s_version" {
  type = string
  # Control plane. ATUALIZADO 2026-10-30 (Juan): v1.34.1 -> v1.34.10 (patch de
  # segurança dentro da mesma minor 1.34). A imagem do worker (image_id) usa o
  # mesmo patch .10; nunca deixe o worker num patch maior que o control plane.
  default = "v1.34.10"
}

variable "node_size" {
  type    = number
  default = 4
}

variable "cluster_name" {
  type    = string
  default = "k8s-cluster"
}

# ----------> Network <----------

variable "vcn_name" {
  type    = string
  default = "k8s-vcn"
}

variable "vcn_dns_label" {
  type    = string
  default = "k8svcn"
}

# ----------> Load Balancer <----------

variable "node_port_http" {
  type    = number
  default = 30080
}

variable "node_port_https" {
  type    = number
  default = 30443
}

variable "listener_port_http" {
  type    = number
  default = 80
}

variable "listener_port_https" {
  type    = number
  default = 443
}

# ----------> Auth <----------

variable "ssh_public_key" {
  type = string
}

variable "fingerprint" {
  type = string
}

variable "private_key_path" {
  type = string
}

variable "tenancy_ocid" {
  type = string
}

variable "user_ocid" {
  type = string
}

variable "oci_profile" {
  type = string
}
