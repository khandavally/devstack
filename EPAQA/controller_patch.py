from nova.api.openstack.compute.flavors import *
from nova.api.openstack import wsgi
from nova.db.sqlalchemy import api as model_api
from nova.db.sqlalchemy.models import PciDevice, Instance

"""nova/nova/api/openstack/compute/"""

@wsgi.serializers(xml=FlavorsTemplate)
def getdetail(self,req):
        
        isql = "select p.address as address, i.uuid as uuid, i.project_id as project_id , i.workload_type as workload_type, i.policy as policy from pci_devices p left outer join instances i on i.uuid=p.instance_uuid where p.status='allocated'"
        session = model_api.get_session()
        get_list = session.query("address" ,"uuid" , "project_id","workload_type","policy").from_statement(isql).all()
        if get_list:
           return {'getdetail': get_list}
        else:
           return {'getdetail': {}}


def notify_decorator(name, fn):
    return fn

Controller.getdetail = getdetail
