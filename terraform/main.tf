terraform {
  backend "s3" {
    bucket         = "meu-terraform-state-bucket"    # troque pelo output bucket_name
    key            = "envs/pr-${var.pr_number}/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "meu-terraform-state-bucket-lock" # troque pelo output dynamodb_table
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

resource "vsphere_virtual_machine" "virtualmachine" {
  count             = var.vm_count
  name = format("%s-%02d-%s", var.vm_name_base, count.index + 1, formatdate("YYYYMMDD-HHmmss", timestamp()))
  resource_pool_id  = data.vsphere_compute_cluster.cluster.resource_pool_id
  datastore_id      = data.vsphere_datastore.datastore.id
  force_power_off   = false
  num_cpus          = var.num_cpu
  memory            = var.ram_memory

  guest_id  = data.vsphere_virtual_machine.template.guest_id
  scsi_type = data.vsphere_virtual_machine.template.scsi_type
  network_interface {
    network_id = data.vsphere_network.network.id
  }


  disk {
    label            = format("disk0-%02d", count.index + 1)
    size             = data.vsphere_virtual_machine.template.disks[0].size
    eagerly_scrub    = data.vsphere_virtual_machine.template.disks[0].eagerly_scrub
    thin_provisioned = lookup(data.vsphere_virtual_machine.template.disks[0], "thin_provisioned", true)
  }

  clone {
    template_uuid = data.vsphere_virtual_machine.template.id
    }
  }

  output "vm_ip" {
  description = "IP da VM criada"
  value       = [for vm in vsphere_virtual_machine.virtualmachine : vm.default_ip_address]
}

