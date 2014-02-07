# -*- coding: utf-8 -*-
from nova import context
from nova.db.sqlalchemy import models
from nova.db.sqlalchemy import api as model_api
from sqlalchemy import func

PCI_ALIAS_NAME = 'CaveCreek'

class ComputeNodeSelection:

    def __init__(self, weighed_hosts, pci_requests):
        self.db_session = model_api.get_session()
        self.weighed_hosts = weighed_hosts
        self.pci_requests = pci_requests
        pass

    def execute_compute_node_selection(self, node_cck_dict):
        host_name_list = self._calculate_weightage(node_cck_dict)
        weighed_hosts = []
        for host_name in host_name_list:
           weighed_hosts.append(self.get_weighed_hosts(host_name))

        return weighed_hosts

    def _calculate_weightage(self, node_cck_dict):
        node_weightage_dict = {}
        
        requested_num_of_vf = self.get_requested_number_of_vf_from_pci_requests(self.pci_requests)
        if not requested_num_of_vf:
            return []
        for host_name in node_cck_dict.keys():
            host_id =  self.get_host_id_from_name(host_name)
            cck_list = node_cck_dict[host_name]
            vf_count = 0
            for cck in cck_list:
                vf_count += self.get_available_vf_per_cck(host_id, cck)
            available_vf_after_allocation = vf_count - requested_num_of_vf
            weightage = available_vf_after_allocation/(len(node_cck_dict[host_name]) * 14)
            node_weightage_dict[host_name] = weightage
        hosts = self._prioritize_hosts_based_on_weightage(node_weightage_dict)
        return hosts

    def get_weighed_hosts(self, host_name):
        for weighed_host in self.weighed_hosts:
            if weighed_host.obj.nodename == host_name:
                return weighed_host

    def get_host_id_from_name(self, host_name):
        id  = self.db_session.query(models.ComputeNode.id).filter_by(hypervisor_hostname=host_name).scalar()
        if id != None:
            return int(id)
        else:
            return None

    def get_requested_number_of_vf_from_pci_requests(self, pci_requests):
        for pci_request in pci_requests:
            if pci_request['alias_name'] == PCI_ALIAS_NAME:
                return pci_request['count']

    def _prioritize_hosts_based_on_weightage(self, node_weightage_dict):
        return [i[0] for i in sorted(node_weightage_dict.items(),\
                                                 key=lambda x: x[1], reverse=True)]

    def get_available_vf_per_cck(self, node, cck):
        vf = int(self.db_session.query(func.count(models.PciDevice.function)).\
                                        filter_by(compute_node_id=node).\
                                        filter_by(bus=cck).\
                                        filter_by(status='available').scalar())
        return vf




def test():
    node_cck_dict = {1:['02']}
    pci_requests = [{'count':2,'specs': [{'vendor_id':'8086','device_id':'1502'}],'alias_name': 'Cavecreek'}]
    cns = ComputeNodeSelection()
    print cns.get_available_vf_per_cck(1, '02')
    print cns.execute_compute_node_selection(node_cck_dict, pci_requests)

#test()       
