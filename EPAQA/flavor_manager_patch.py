from novaclient.v1_1.flavors import *
from novaclient.base import Manager
"""novaclient/v1_1/flavors/FlavorManager"""

class CustomeFlavorManager(FlavorManager):
	def _data(self, url, response_key, obj_class=None, body=None):
		if body:
		    _resp, body = self.api.client.post(url, body=body)
		else:
		    _resp, body = self.api.client.get(url)

		if obj_class is None:
		    obj_class = self.resource_class

		data = body[response_key]
		
		if isinstance(data, dict):
		    try:
		        data = data['values']
		    except KeyError:
		        pass
		return data
		
	def vf_list(self, detailed=True, is_public=True):
		"""Get the list of all pci devices"""
		return self._data("/flavors/vf_list","vf_list")

	def total_pci_devices(self, detailed=True, is_public=True):
		"""Get the total pci devices available."""
		return self._data("/flavors/total_pci_devices","total_pci_devices")
	
	def allocated_pci_devices(self, detailed=True, is_public=True):
		"""Get the total pci devices allocated."""
		return self._data("/flavors/allocated_pci_devices","allocated_pci_devices")

	def total_vfs_all_nodes(self, detailed=True, is_public=True):
		"""Get the total pci devices available for all compute nodes."""
		return self._data("/flavors/total_vfs_all_nodes","total_vfs_all_nodes")

	def allocated_vfs_all_nodes(self, detailed=True, is_public=True):
		"""Get the total pci devices allocated for all compute nodes."""
		return self._data("/flavors/allocated_vfs_all_nodes","allocated_vfs_all_nodes")

@classmethod
def custome_flavor_new(cls, *args, **kwargs):
    custome_flavor_manager = object.__new__(CustomeFlavorManager)
    return custome_flavor_manager

FlavorManager.__new__ = custome_flavor_new

