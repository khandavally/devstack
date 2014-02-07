from nova.api.openstack.compute.servers import * 
from nova.api.openstack import wsgi




class CustomeController(Controller):
	@wsgi.response(202)
	@wsgi.serializers(xml=FullServerTemplate)
	@wsgi.deserializers(xml=CreateDeserializer)
	def create(self, req, body):
		"""Creates a new server for a given user."""
		if not self.is_valid_body(body, 'server'):
		    raise exc.HTTPUnprocessableEntity()

		context = req.environ['nova.context']
		server_dict = body['server']
		if body['server'].has_key('workload_type'):
			context.workload_type = body['server']['workload_type']
		else:
			context.workload_type = None
                context.policy = self.get_tenant_info(req.environ, 'description')
		
		password = self._get_server_admin_password(server_dict)

		if 'name' not in server_dict:
		    msg = _("Server name is not defined")
		    raise exc.HTTPBadRequest(explanation=msg)

		name = server_dict['name']
		self._validate_server_name(name)
		name = name.strip()

		image_uuid = self._image_from_req_data(body)

		personality = server_dict.get('personality')
		config_drive = None
		if self.ext_mgr.is_loaded('os-config-drive'):
		    config_drive = server_dict.get('config_drive')

		injected_files = []
		if personality:
		    injected_files = self._get_injected_files(personality)

		sg_names = []
		if self.ext_mgr.is_loaded('os-security-groups'):
		    security_groups = server_dict.get('security_groups')
		    if security_groups is not None:
		        sg_names = [sg['name'] for sg in security_groups
		                    if sg.get('name')]
		if not sg_names:
		    sg_names.append('default')

		sg_names = list(set(sg_names))

		requested_networks = None
		if (self.ext_mgr.is_loaded('os-networks')
		        or utils.is_neutron()):
		    requested_networks = server_dict.get('networks')

		if requested_networks is not None:
		    if not isinstance(requested_networks, list):
		        expl = _('Bad networks format')
		        raise exc.HTTPBadRequest(explanation=expl)
		    requested_networks = self._get_requested_networks(
		        requested_networks)

		(access_ip_v4, ) = server_dict.get('accessIPv4'),
		if access_ip_v4 is not None:
		    self._validate_access_ipv4(access_ip_v4)

		(access_ip_v6, ) = server_dict.get('accessIPv6'),
		if access_ip_v6 is not None:
		    self._validate_access_ipv6(access_ip_v6)

		try:
		    flavor_id = self._flavor_id_from_req_data(body)
		except ValueError as error:
		    msg = _("Invalid flavorRef provided.")
		    raise exc.HTTPBadRequest(explanation=msg)

		# optional openstack extensions:
		key_name = None
		if self.ext_mgr.is_loaded('os-keypairs'):
		    key_name = server_dict.get('key_name')

		user_data = None
		if self.ext_mgr.is_loaded('os-user-data'):
		    user_data = server_dict.get('user_data')
		self._validate_user_data(user_data)

		availability_zone = None
		if self.ext_mgr.is_loaded('os-availability-zone'):
		    availability_zone = server_dict.get('availability_zone')

		block_device_mapping = None
		block_device_mapping_v2 = None
		legacy_bdm = True
		if self.ext_mgr.is_loaded('os-volumes'):
		    block_device_mapping = server_dict.get('block_device_mapping', [])
		    for bdm in block_device_mapping:
		        try:
		            block_device.validate_device_name(bdm.get("device_name"))
		            block_device.validate_and_default_volume_size(bdm)
		        except exception.InvalidBDMFormat as e:
		            raise exc.HTTPBadRequest(explanation=e.format_message())

		        if 'delete_on_termination' in bdm:
		            bdm['delete_on_termination'] = strutils.bool_from_string(
		                bdm['delete_on_termination'])

		    if self.ext_mgr.is_loaded('os-block-device-mapping-v2-boot'):
		        # Consider the new data format for block device mapping
		        block_device_mapping_v2 = server_dict.get(
		            'block_device_mapping_v2', [])
		        # NOTE (ndipanov):  Disable usage of both legacy and new
		        #                   block device format in the same request
		        if block_device_mapping and block_device_mapping_v2:
		            expl = _('Using different block_device_mapping syntaxes '
		                     'is not allowed in the same request.')
		            raise exc.HTTPBadRequest(explanation=expl)

		        # Assume legacy format
		        legacy_bdm = not bool(block_device_mapping_v2)

		        try:
		            block_device_mapping_v2 = [
		                block_device.BlockDeviceDict.from_api(bdm_dict)
		                for bdm_dict in block_device_mapping_v2]
		        except exception.InvalidBDMFormat as e:
		            raise exc.HTTPBadRequest(explanation=e.format_message())

		block_device_mapping = (block_device_mapping or
		                        block_device_mapping_v2)

		ret_resv_id = False
		# min_count and max_count are optional.  If they exist, they may come
		# in as strings.  Verify that they are valid integers and > 0.
		# Also, we want to default 'min_count' to 1, and default
		# 'max_count' to be 'min_count'.
		min_count = 1
		max_count = 1
		if self.ext_mgr.is_loaded('os-multiple-create'):
		    ret_resv_id = server_dict.get('return_reservation_id', False)
		    min_count = server_dict.get('min_count', 1)
		    max_count = server_dict.get('max_count', min_count)

		try:
		    min_count = utils.validate_integer(
		        min_count, "min_count", min_value=1)
		    max_count = utils.validate_integer(
		        max_count, "max_count", min_value=1)
		except exception.InvalidInput as e:
		    raise exc.HTTPBadRequest(explanation=e.format_message())

		if min_count > max_count:
		    msg = _('min_count must be <= max_count')
		    raise exc.HTTPBadRequest(explanation=msg)

		auto_disk_config = False
		if self.ext_mgr.is_loaded('OS-DCF'):
		    auto_disk_config = server_dict.get('auto_disk_config')

		scheduler_hints = {}
		if self.ext_mgr.is_loaded('OS-SCH-HNT'):
		    scheduler_hints = server_dict.get('scheduler_hints', {})

		try:
		    _get_inst_type = flavors.get_flavor_by_flavor_id
		    inst_type = _get_inst_type(flavor_id, ctxt=context,
		                               read_deleted="no")

		    (instances, resv_id) = self.compute_api.create(context,
		                    inst_type,
		                    image_uuid,
		                    display_name=name,
		                    display_description=name,
		                    key_name=key_name,
		                    metadata=server_dict.get('metadata', {}),
		                    access_ip_v4=access_ip_v4,
		                    access_ip_v6=access_ip_v6,
		                    injected_files=injected_files,
		                    admin_password=password,
		                    min_count=min_count,
		                    max_count=max_count,
		                    requested_networks=requested_networks,
		                    security_group=sg_names,
		                    user_data=user_data,
		                    availability_zone=availability_zone,
		                    config_drive=config_drive,
		                    block_device_mapping=block_device_mapping,
		                    auto_disk_config=auto_disk_config,
		                    scheduler_hints=scheduler_hints,
		                    legacy_bdm=legacy_bdm)
		except exception.QuotaError as error:
		    raise exc.HTTPRequestEntityTooLarge(
		        explanation=error.format_message(),
		        headers={'Retry-After': 0})
		except exception.InvalidMetadataSize as error:
		    raise exc.HTTPRequestEntityTooLarge(
		        explanation=error.format_message())
		except exception.ImageNotFound as error:
		    msg = _("Can not find requested image")
		    raise exc.HTTPBadRequest(explanation=msg)
		except exception.FlavorNotFound as error:
		    msg = _("Invalid flavorRef provided.")
		    raise exc.HTTPBadRequest(explanation=msg)
		except exception.KeypairNotFound as error:
		    msg = _("Invalid key_name provided.")
		    raise exc.HTTPBadRequest(explanation=msg)
		except exception.ConfigDriveInvalidValue:
		    msg = _("Invalid config_drive provided.")
		    raise exc.HTTPBadRequest(explanation=msg)
		except rpc_common.RemoteError as err:
		    msg = "%(err_type)s: %(err_msg)s" % {'err_type': err.exc_type,
		                                         'err_msg': err.value}
		    raise exc.HTTPBadRequest(explanation=msg)
		except UnicodeDecodeError as error:
		    msg = "UnicodeError: %s" % unicode(error)
		    raise exc.HTTPBadRequest(explanation=msg)
		except (exception.ImageNotActive,
		        exception.InstanceTypeDiskTooSmall,
		        exception.InstanceTypeMemoryTooSmall,
		        exception.InstanceTypeNotFound,
		        exception.InvalidMetadata,
		        exception.InvalidRequest,
		        exception.MultiplePortsNotApplicable,
		        exception.PortNotFound,
		        exception.SecurityGroupNotFound,
		        exception.InvalidBDM) as error:
		    raise exc.HTTPBadRequest(explanation=error.format_message())
		except exception.PortInUse as error:
		    raise exc.HTTPConflict(explanation=error.format_message())

		# If the caller wanted a reservation_id, return it
		if ret_resv_id:
		    return wsgi.ResponseObject({'reservation_id': resv_id},
		                               xml=ServerMultipleCreateTemplate)

		req.cache_db_instances(instances)
		server = self._view_builder.create(req, instances[0])

		if CONF.enable_instance_password:
		    server['server']['adminPass'] = password

		robj = wsgi.ResponseObject(server)

		return self._add_location(robj)

        def get_tenant_info(self, environ, key):
                return environ['keystone.token_info']['access']['token']['tenant'][key]

def notify_decorator(name, fn):
    return fn

@classmethod
def custome_controller_new(cls, *args, **kwargs):
    custome_controller = object.__new__(CustomeController)
    return custome_controller

Controller.__new__ =  custome_controller_new
        


