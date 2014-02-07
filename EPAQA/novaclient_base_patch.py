from novaclient.base import Manager 

"""novaclient/base/Manager"""

class CustomeManager(Manager):
	def _vf_list(self, url, response_key, obj_class=None, body=None):
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


@classmethod
def custome_manager_new(cls, *args, **kwargs):
    custome_flavor_manager = object.__new__(CustomeManager)
    return custome_flavor_manager

Manager.__new__ = custome_manager_new
