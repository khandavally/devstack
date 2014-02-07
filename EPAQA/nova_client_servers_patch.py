from novaclient.v1_1.servers import ServerManager


class CustomManager(ServerManager):

	def _create(self, url, body, response_key, return_raw=False, **kwargs):
		self.run_hooks('modify_body_for_create', body, **kwargs)
		if kwargs.has_key('workload_type') and kwargs['workload_type'] !='' :
			body['server']['workload_type'] = kwargs['workload_type']
		else:
			body['server']['workload_type']=None
		
		_resp, body = self.api.client.post(url, body=body)
		if return_raw:
		    return body[response_key]

		with self.completion_cache('human_id', self.resource_class, mode="a"):
		    with self.completion_cache('uuid', self.resource_class, mode="a"):
			return self.resource_class(self, body[response_key])


@classmethod
def custome_manager_new(cls, *args, **kwargs):
    custome_manager = object.__new__(CustomManager)
    return custome_manager

ServerManager.__new__ = custome_manager_new
	
