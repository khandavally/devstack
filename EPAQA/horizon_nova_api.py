from novaclient.v1_1 import client as nova_client
from horizon.utils.memoized import memoized
from openstack_dashboard.api import nova as new_nova
from openstack_dashboard.api.nova import *

"""horizon/openstack_dashboard/api/nova"""
@memoized

def vf_list(request, is_public=True):
    """Get the list of available instance sizes (flavors)."""
    return novaclient(request).flavors.vf_list(is_public=is_public)

def total_pci_devices(request, is_public=True):
    """Get the total pci devices available."""
    return novaclient(request).flavors.total_pci_devices(is_public=is_public)

def allocated_pci_devices(request, is_public=True):
    """Get the total pci devices allocated."""
    return novaclient(request).flavors.allocated_pci_devices(is_public=is_public)

def total_vfs_all_nodes(request, is_public=True):
    """Get the total pci devices available for all compute nodes."""
    return novaclient(request).flavors.total_vfs_all_nodes(is_public=is_public)

def allocated_vfs_all_nodes(request, is_public=True):
    """Get the total pci devices allocated for all compute nodes."""
    return novaclient(request).flavors.allocated_vfs_all_nodes(is_public=is_public)

new_nova.__dict__['vf_list'] = vf_list
new_nova.__dict__['total_pci_devices'] = total_pci_devices
new_nova.__dict__['allocated_pci_devices'] = allocated_pci_devices
new_nova.__dict__['total_vfs_all_nodes'] = total_vfs_all_nodes
new_nova.__dict__['allocated_vfs_all_nodes'] = allocated_vfs_all_nodes
