from openstack_dashboard import settings
from openstack_dashboard.api.nova import Server,novaclient
from openstack_dashboard.api import nova as new_nova


def server_create(request, name, image, flavor, key_name, user_data,
	          security_groups, block_device_mapping=None,
	          block_device_mapping_v2=None, nics=None,
	          availability_zone=None, instance_count=1, admin_pass=None):
    tenant_data = request.user.authorized_tenants
    current_tenant_description = ''
    for tenant in tenant_data:
        if request.user.tenant_name ==tenant.name:
            current_tenant_description = tenant.description
		

    if request.method =='POST' and request.POST.has_key('workload_type'):
	return Server(novaclient(request).servers.create(
		name, image, flavor, userdata=user_data,
		security_groups=security_groups,
		key_name=key_name, block_device_mapping=block_device_mapping,
		block_device_mapping_v2=block_device_mapping_v2,
		nics=nics, availability_zone=availability_zone,
		min_count=instance_count, admin_pass=admin_pass,workload_type=request.POST['workload_type'],
		policy=current_tenant_description), request)


    else:
	return Server(novaclient(request).servers.create(
		name, image, flavor, userdata=user_data,
		security_groups=security_groups,
		key_name=key_name, block_device_mapping=block_device_mapping,
		block_device_mapping_v2=block_device_mapping_v2,
		nics=nics, availability_zone=availability_zone,
		min_count=instance_count, admin_pass=admin_pass), request)


new_nova.server_create = server_create
	
