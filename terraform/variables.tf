variable vsphere_user {
  type        = string
  description = "description"
}

variable vsphere_password {
  type        = string
  description = "description"
  sensitive   = true
}


variable "vsphere_server" {
  type        = string
  default     = "vcenter.upgrid.local"
  description = "ip for vsphere"
}

variable "vsphere_datacenter" {
  type        = string
  default     = "senai-dc"
  description = "datacenter vsphere"
}

variable mgmt_lan {
  type        = string
  default     = "VM Network"
  description = "description"
}

variable interface {
  type        = string
  default     = "vmxnet3"
  description = "description"
}

variable "vsphere_datastore" {
  default = "datastore1"
}
#set itens terminal
variable vm_name_base {
  default = "vm"
}

variable vsphere_cluster_name{}

variable template_name {}

variable domain {}

variable disk_size {}

variable "num_cpu" {}

variable "ram_memory" {}
