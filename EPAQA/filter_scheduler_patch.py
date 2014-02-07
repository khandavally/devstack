from nova import exception
from nova.scheduler.filter_scheduler import FilterScheduler
from nova.scheduler import driver, scheduler_options
import random
from oslo.config import cfg
from nova.compute import rpcapi as compute_rpcapi
from nova import notifier
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.pci import pci_request
from nova.scheduler import utils as scheduler_utils
from no_multi_tenancy import NoMultiTenancy
from compute_node_selection import ComputeNodeSelection
from nova.scheduler import vf_allocation_migration_patch
from nova.scheduler import vf_allocation
from nova.openstack.common import log as logging
LOG = logging.getLogger(__name__)

PCI_ALIAS_NAME = 'CaveCreek'

class FilterSchedulerPatch(FilterScheduler):

    """Extension of nova.scheduler.filter_scheduler.FilterScheduler class supports 
	execution of no multi tenancy algorithm, 
	compute node selection algorithm and vf allocation algorithm while scheduling"""
    def __init__(self, *args, **kwargs):
	"""Initilaize member variables"""
        super(FilterSchedulerPatch, self).__init__(*args, **kwargs)
        self.options = scheduler_options.SchedulerOptions()
        self.compute_rpcapi = compute_rpcapi.ComputeAPI()
        self.notifier = notifier.get_notifier('scheduler')

    def schedule_run_instance(self, context, request_spec,
                              admin_password, injected_files,
                              requested_networks, is_first_time,
                              filter_properties, legacy_bdm_in_spec):
        
        payload = dict(request_spec=request_spec)
        self.notifier.info(context, 'scheduler.run_instance.start', payload)

        instance_uuids = request_spec.get('instance_uuids')
        LOG.info(_("Attempting to build %(num_instances)d instance(s) "
                    "uuids: %(instance_uuids)s"),
                  {'num_instances': len(instance_uuids),
                   'instance_uuids': instance_uuids})
        LOG.debug(_("Request Spec: %s") % request_spec)
        weighed_hosts = self._schedule(context, request_spec,
                                       filter_properties, instance_uuids)

        """ EPA_QA part start """
        """  No Multitenancy algorithm  """
        if request_spec['instance_properties']['workload_type'] and \
                        filter_properties.has_key('pci_requests') and  weighed_hosts:
            selected_hosts = [ host.obj.nodename for host in  weighed_hosts]

            tenant_id = filter_properties['project_id']

            pci_requests = filter_properties['pci_requests']
            nmt = NoMultiTenancy() 
            node_cck_dict = nmt.execute_no_multitenancy(selected_hosts, tenant_id)
            node_cck_values = node_cck_dict.values()
            node_cck_list = []

            for i in range(len(node_cck_values)):
                for j in range(len(node_cck_values[i])):
                    node_cck_list.append(node_cck_values[i][j])
            cns = ComputeNodeSelection(weighed_hosts, pci_requests)
            if node_cck_list:
                """ Compute node selection """
                weighed_hosts = cns.execute_compute_node_selection(node_cck_dict)
            else:
                raise exception.NoValidHost(reason="Other tenancy found on all cave creeks")

        """ EPA QA part end """

        # NOTE: Pop instance_uuids as individual creates do not need the
        # set of uuids. Do not pop before here as the upper exception
        # handler fo NoValidHost needs the uuid to set error state
        instance_uuids = request_spec.pop('instance_uuids')

        # NOTE(comstud): Make sure we do not pass this through.  It
        # contains an instance of RpcContext that cannot be serialized.
        filter_properties.pop('context', None)

        for num, instance_uuid in enumerate(instance_uuids):
            request_spec['instance_properties']['launch_index'] = num

            try:
                try:
                    weighed_host = weighed_hosts.pop(0)
		    """ VF allocation algorithm """
                    if request_spec['instance_properties']['policy'] and request_spec['instance_properties']['workload_type'] \
                                               and filter_properties.has_key('pci_requests') and weighed_host:
                        weighed_host.obj.limits['selected_vfs'] = {}
                        req_vf = self.get_requested_number_of_vf_from_pci_requests(filter_properties['pci_requests'])
                        los =  request_spec['instance_properties']['policy']
                        req_work_load_type = request_spec['instance_properties']['workload_type']
                        cck_list = node_cck_dict[weighed_host.obj.nodename]
                        address_list =  vf_allocation.execute_vf_allocation(req_vf, los, req_work_load_type, cck_list)
                        if address_list == []:
                            raise exception.NoValidHost(reason="No suitable vf's found for the instance")
                        else:
                            weighed_host.obj.limits['selected_vfs'][PCI_ALIAS_NAME] = address_list
                    LOG.info(_("Choosing host %(weighed_host)s "
                                "for instance %(instance_uuid)s"),
                              {'weighed_host': weighed_host,
                               'instance_uuid': instance_uuid})
                except IndexError:
                    raise exception.NoValidHost(reason="")
                except Exception as ex:
                    print ex
                    raise ex
                
                self._provision_resource(context, weighed_host,
                                         request_spec,
                                         filter_properties,
                                         requested_networks,
                                         injected_files, admin_password,
                                         is_first_time,
                                         instance_uuid=instance_uuid,
                                         legacy_bdm_in_spec=legacy_bdm_in_spec)
            except Exception as ex:
                # NOTE(vish): we don't reraise the exception here to make sure
                #             that all instances in the request get set to
                #             error properly
                driver.handle_schedule_error(context, ex, instance_uuid,
                                             request_spec)
            # scrub retry host list in case we're scheduling multiple
            # instances:
            retry = filter_properties.get('retry', {})
            retry['hosts'] = []

        self.notifier.info(context, 'scheduler.run_instance.end', payload)

    def get_requested_number_of_vf_from_pci_requests(self, pci_requests):
	"""Returns requested number of vf from pci requests"""
        for pci_request in pci_requests:
            if pci_request['alias_name'] == PCI_ALIAS_NAME:
                return pci_request['count']

def notify_decorator(name, fn):
    """ Default decorator for notify which is used from utils.monkey_patch(). DONT REMOVE IT."""
    return fn


@classmethod
def filter_scheduler_new(cls, *args, **kwargs):
    """Function which helps overridden of __new__ method in nova.scheduler.filter_scheduler_patch.FilterSchedulerPatch"""
    filter_scheduler = object.__new__(FilterSchedulerPatch)
    return filter_scheduler
    
def FilterSchedulerPatchMain():
    FilterScheduler.__new__ = filter_scheduler_new

FilterSchedulerPatchMain()
