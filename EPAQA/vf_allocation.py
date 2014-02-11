from nova.db.sqlalchemy import api as model_api
from nova.db.sqlalchemy.models import PciDevice, Instance, ComputeNode
import collections
#, VFAllocation

session = model_api.get_session()
WORK_LOAD = ["cp","cr"]


def execute_vf_allocation(req_vf,los,req_work,bus_list, *args,**kwargs):
    """This method is called from nova.scheduler.filter_scheduler.FilterScheduler"""
    base_dict = collections.OrderedDict()    
    get_bus_slot = session.query(PciDevice).from_statement("select id,bus,slot from pci_devices where status = :status GROUP BY bus, slot").params(status="available").all()
    obj_list = [obj for obj in get_bus_slot if obj.bus in bus_list]
    if not obj_list:
        return []
    
    """ CLEAR VF_ALLOCATION  TABLE DATA """
    session.execute("truncate vf_allocation")

    """ Get list of PCI devices for Unique bus and slot (unassigned is optional) """
    for obj in obj_list:
        BUS = obj.bus
        SLOT = obj.slot
        cp_vf_assigned = []
        for j in range(len(WORK_LOAD)):

            """ Get the List of VF assigned for each Bus, Slot for workload cp and cr """
            GET_ASS_VF = """select bus,slot,function,count(workload) as count_wl from pci_devices where bus = %s and slot = %s and workload = '%s' and status = 'allocated'""" % (BUS, SLOT, str(WORK_LOAD[j]))

	    cp_vf_ass = int(session.query("count_wl").from_statement(GET_ASS_VF).scalar())
            cp_vf_assigned.append(cp_vf_ass)
        
        """ Get the Policy value from the input """
        los_ass_final = int(los)

        """ Create obtained records as a dictionary  """
        base_dict[str(BUS)+":"+str(SLOT)] = [{'cp': cp_vf_assigned[0], 'cr': cp_vf_assigned[1]}]

        """ VF Allocation Algorithm Logic"""
    if (((req_vf % 2 == 0) and (req_work == "cp-cr")) or (req_work == "cp") or (req_work == "cr")):
        result = VF_Allocation_Extended_Logic(req_vf,los,req_work,base_dict)
        return result
    else:
        return []


def VF_Allocation_Extended_Logic(req_vf,los,req_work,base_dict):

    address_list = []
    address_workload_list = []
    tmp_add_store  = ("")
    REQ_VF = req_work 
    RESET_COUNT = 0
    for k in range(req_vf):
      
        if REQ_VF == "cp-cr" and ( req_vf / 2 != RESET_COUNT ):
            req_work = 'cp'
            RESET_COUNT = RESET_COUNT + 1
        elif REQ_VF == "cp-cr" and ( req_vf / 2 <= RESET_COUNT ):
            req_work = 'cr'

        filter_data = {k: v for k, v in base_dict.iteritems() if v[0][req_work] < los} # Filter the Bus slot having vfs less than los value for selected workload
        if req_work == 'cp':
            final_list = sorted(filter_data, key=lambda x: (filter_data[x][0]['cp'], filter_data[x][0]['cr'])) # sort the filtered dict based on cp cr count
        else:
            final_list = sorted(filter_data, key=lambda x: (filter_data[x][0]['cr'], filter_data[x][0]['cp'])) # sort the filtered dict based on cp cr count
        if len(final_list) >= 1:
            selected_bus_slot = final_list.sort() # Get last bus slot for PCI Instnace request
            selected_bus_slot = final_list[-1]
        else:
            selected_bus_slot = "" 
        
        if selected_bus_slot:
            bus_,slot_ = selected_bus_slot.split(":")
            address = [ad[0] for ad in session.query("address").from_statement("select address from pci_devices where bus = %s and slot = %s and status='available' and function <> 0" % (bus_,slot_)).all() if ad[0] not in address_list]
            if address:
                address_list.append(address[0])
                address_workload_list.append((address[0],req_work))
                base_dict[selected_bus_slot][0][req_work] = base_dict[selected_bus_slot][0][req_work] + 1 # Update the vfs count for selected bus,slot with requested workload


        else:
            break;
    if len(address_list) != req_vf:
        return []
    return address_workload_list
