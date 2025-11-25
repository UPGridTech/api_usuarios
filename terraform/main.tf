terraform {
  backend "s3" {
    bucket         = "bkt-senai-02"
    key            = "autoscaling/${var.vm_name}/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "bkt-senai-02-lock"
    encrypt        = true
  }

  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = "~> 2.12"
    }
  }
}

provider "vsphere" {
  user                 = var.vsphere_user
  password             = var.vsphere_password
  vsphere_server       = var.vsphere_server
  allow_unverified_ssl = true
  api_timeout          = 300
}

data "vsphere_datacenter" "datacenter" {
  name = var.vsphere_datacenter
}

data "vsphere_datastore" "datastore" {
  name          = var.vsphere_datastore
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_compute_cluster" "cluster" {
  name          = var.vsphere_cluster_name
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_network" "network" {
  name          = var.mgmt_lan
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_virtual_machine" "template" {
  name          = var.template_name
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

resource "vsphere_virtual_machine" "vm" {
  name             = var.vm_name
  resource_pool_id = data.vsphere_compute_cluster.cluster.resource_pool_id
  datastore_id     = data.vsphere_datastore.datastore.id
  num_cpus         = var.num_cpu
  memory           = var.ram_memory
  force_power_off  = false

  guest_id  = data.vsphere_virtual_machine.template.guest_id
  scsi_type = data.vsphere_virtual_machine.template.scsi_type

  network_interface {
    network_id = data.vsphere_network.network.id
  }

  disk {
    label            = "disk0"
    size             = data.vsphere_virtual_machine.template.disks[0].size
    eagerly_scrub    = data.vsphere_virtual_machine.template.disks[0].eagerly_scrub
    thin_provisioned = lookup(data.vsphere_virtual_machine.template.disks[0], "thin_provisioned", true)
  }

  clone {
    template_uuid = data.vsphere_virtual_machine.template.id
  }
}


output "vm_name" {
  description = "Nome da VM criada"
  value       = vsphere_virtual_machine.vm.name
}

output "vm_ip" {
  description = "IP da VM criada"
  value       = vsphere_virtual_machine.vm.default_ip_address
}
