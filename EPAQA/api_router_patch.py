from nova.api.openstack.compute import *

"""nova/nova/api/openstack/compute/"""

def _setup_routes(self, mapper, ext_mgr, init_only):
	if init_only is None or 'versions' in init_only:
	    self.resources['versions'] = versions.create_resource()
	    mapper.connect("versions", "/",
		        controller=self.resources['versions'],
		        action='show',
		        conditions={"method": ['GET']})

	mapper.redirect("", "/")

	if init_only is None or 'consoles' in init_only:
	    self.resources['consoles'] = consoles.create_resource()
	    mapper.resource("console", "consoles",
		        controller=self.resources['consoles'],
		        parent_resource=dict(member_name='server',
		        collection_name='servers'))

	if init_only is None or 'consoles' in init_only or \
		'servers' in init_only or ips in init_only:
	    self.resources['servers'] = servers.create_resource(ext_mgr)
	    mapper.resource("server", "servers",
		            controller=self.resources['servers'],
		            collection={'detail': 'GET'},
		            member={'action': 'POST'})

	if init_only is None or 'ips' in init_only:
	    self.resources['ips'] = ips.create_resource()
	    mapper.resource("ip", "ips", controller=self.resources['ips'],
		            parent_resource=dict(member_name='server',
		                                 collection_name='servers'))

	if init_only is None or 'images' in init_only:
	    self.resources['images'] = images.create_resource()
	    mapper.resource("image", "images",
		            controller=self.resources['images'],
		            collection={'detail': 'GET'})

	if init_only is None or 'limits' in init_only:
	    self.resources['limits'] = limits.create_resource()
	    mapper.resource("limit", "limits",
		            controller=self.resources['limits'])

	if init_only is None or 'flavors' in init_only:
	    self.resources['flavors'] = flavors.create_resource()
	    mapper.resource("flavor", "flavors",
		            controller=self.resources['flavors'],
		            collection={'detail': 'GET','vf_list': 'GET','total_pci_devices': 'GET','allocated_pci_devices': 'GET','total_vfs_all_nodes': 'GET','allocated_vfs_all_nodes': 'GET'}, 
		            member={'action': 'POST'})

	if init_only is None or 'image_metadata' in init_only:
	    self.resources['image_metadata'] = image_metadata.create_resource()
	    image_metadata_controller = self.resources['image_metadata']

	    mapper.resource("image_meta", "metadata",
		            controller=image_metadata_controller,
		            parent_resource=dict(member_name='image',
		            collection_name='images'))

	    mapper.connect("metadata",
		           "/{project_id}/images/{image_id}/metadata",
		           controller=image_metadata_controller,
		           action='update_all',
		           conditions={"method": ['PUT']})

	if init_only is None or 'server_metadata' in init_only:
	    self.resources['server_metadata'] = \
		server_metadata.create_resource()
	    server_metadata_controller = self.resources['server_metadata']

	    mapper.resource("server_meta", "metadata",
		            controller=server_metadata_controller,
		            parent_resource=dict(member_name='server',
		            collection_name='servers'))

	    mapper.connect("metadata",
		           "/{project_id}/servers/{server_id}/metadata",
		           controller=server_metadata_controller,
		           action='update_all',
		           conditions={"method": ['PUT']})

def notify_decorator(name, fn):
    return fn
APIRouter._setup_routes =  _setup_routes

