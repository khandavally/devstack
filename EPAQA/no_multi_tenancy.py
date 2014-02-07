from sqlalchemy import distinct
from nova.db.sqlalchemy import api as model_api
from nova.db.sqlalchemy.models import PciDevice, Instance, ComputeNode
from nova import exception

class NoMultiTenancy:

    def __init__(self):
        self.db_session = model_api.get_session()

    def execute_no_multitenancy(self, selected_hosts, tenant_id):
        return self._check_multi_tenancy(selected_hosts, tenant_id)
        
    def _check_multi_tenancy(self, selected_hosts, tenant_id):
        node_cck_dict = {}
        for host_name in selected_hosts:
            host_id = self.get_host_id_from_name(host_name)
            if host_id == None:
                continue
            cck_list = self.get_all_ccks_by_node(host_id)
            node_cck_dict[host_name] = []
            for cck_id in cck_list:
                existing_tenants = self.get_existing_tenant_list(host_id, cck_id)
                tenant_id_list = []
                tenant_id_list.append(tenant_id)
                if list(set(existing_tenants) - set(tenant_id_list)) == [] or existing_tenants == []:
                    node_cck_dict[host_name].append(cck_id)
        return node_cck_dict

    def get_host_id_from_name(self, host_name):
        id  = self.db_session.query(ComputeNode.id).filter_by(hypervisor_hostname=host_name).scalar()
        if id != None:
            return int(id)
        else:
            return None

    def get_all_ccks_by_node(self, host_id):
        cck_list = [v[0] for v in self.db_session.query(distinct(PciDevice.bus)).filter_by(compute_node_id=host_id).all()]
        #cck_list = list(self.db_session.query(distinct(PciDevice.bus)).filter_by(compute_node_id=host_id).all())
        return cck_list

    def get_existing_tenant_list(self, host_id, cck_id):
        #existing_instance_uuid_list = [v[0] for v in self.db_session.query(PciDevice.instance_uuid).filter_by(compute_node_id= compute_node_id).filter_by(bus=cck_id).filter_by(status='allocated').all()]
        #existing_project_id_list= [v[0][0] for v in [self.db_session.query(Instance.project_id).filter_by(uuid= v).all() for v in existing_instance_uuid_list]]
        existing_tenants = self.db_session.query("tenant_id").from_statement("select distinct i.project_id as tenant_id from pci_devices p  left outer join instances i on i.uuid=p.instance_uuid where p.status='allocated' and p.bus= :bus and p.compute_node_id= :compute_node_id").params(bus=cck_id, compute_node_id=host_id).all()
        existing_tenants = [v[0] for v in existing_tenants]
        return existing_tenants



def main():
    nmt = No_Multi_Tenancy()
    #import pdb;pdb.set_trace()
    print nmt.execute_no_multitenancy(['switch-serv'],'ca7f43d159494b0cb24ca92707cace0c')

#main()    
"""
existing_instance_uuid_list = [v[0] for v in model_api.get_session().query(models.PciDevice.instance_uuid).filter_by(compute_node_id=1).filter_by(bus='02').filter_by(status='available').all()]
existing_project_id_list= [v[0][0] in for v in [model_api.get_session().query(models.Instance.project_id).filter_by(uuid= v ).all() for v in existing_instance_uuid_list]]
int(model_api.get_session().query(func.count(distinct(models.PciDevice.bus))).scalar())
int(model_api.get_session().query(func.count(models.PciDevice.function)).filter_by(compute_node_id=1).filter_by(status='alloacated').filter_by(project_id)
"""
