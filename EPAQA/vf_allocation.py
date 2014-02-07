from nova.db.sqlalchemy import api as model_api
from nova.db.sqlalchemy.models import PciDevice, Instance, ComputeNode, VFAllocation

session = model_api.get_session()
WORK_LOAD = ["cp","cr"]


def execute_vf_allocation(req_vf,los,req_work,bus_list, *args,**kwargs):
    """This method is called from nova.scheduler.filter_scheduler.FilterScheduler"""
        
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

        """ Update the Records in New Temp Table for population """
        update_vf_table = """INSERT INTO vf_allocation (bus,slot,los,cp_vf,cr_vf,total_vf) VALUES (%s,%s,%s,%s,%s,%s)""" % (BUS,SLOT,los_ass_final,cp_vf_assigned[0],cp_vf_assigned[1],(cp_vf_assigned[0]+cp_vf_assigned[1]))
	insert_record =session.execute(update_vf_table)

        """ VF Allocation Algorithm Logic"""
    if (((req_vf % 2 == 0) and (req_work == "cp-cr")) or (req_work == "cp") or (req_work == "cr")):
        result = VF_Allocation_Extended_Logic(req_vf,los,req_work)
        return result
    else:
        return []


def VF_Allocation_Extended_Logic(req_vf,los,req_work):

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

        """ VF Allocation Calculator """
        if req_work == WORK_LOAD[0]:
            vf_logic = "select bus,slot,IF(cp_vf=0,0,cp_vf/los) as utility_factor from vf_allocation where if(los=0,los = 0 or los = %s,los = %s and (cp_vf) < los)  ORDER by utility_factor DESC limit 1" % (int(los),int(los))
            update_record = "UPDATE vf_allocation SET cp_vf = cp_vf+1, total_vf = total_vf + 1 where bus = %s and slot = %s"
        elif req_work == WORK_LOAD[1]:
            vf_logic="select bus,slot,IF(cr_vf=0,0,cr_vf/los) as utility_factor from vf_allocation where if(los=0,los = 0 or los = %s,los = %s and (cr_vf) < los)  ORDER by utility_factor DESC limit 1" % (int(los),int(los))
            update_record = "UPDATE vf_allocation SET cr_vf = cr_vf+1, total_vf = total_vf + 1 where bus = %s and slot = %s"
        selected_bus_slot = session.query("bus", "slot").from_statement(vf_logic).first()

        if selected_bus_slot:
            bus_,slot_ = selected_bus_slot
            update_los = "UPDATE vf_allocation SET los = if(los = 0, %s, los) where bus = %s"
            update_los_new = session.execute(update_los % (los,bus_))
            update_record = session.execute(update_record % (bus_,slot_ ))           
            address = [ad[0] for ad in session.query("address").from_statement("select address from pci_devices where bus = %s and slot = %s and status='available' and function <> 0" % (bus_,slot_)).all() if ad[0] not in address_list]
            if address:
                address_list.append(address[0])
                address_workload_list.append((address[0],req_work))

        else:
            break;
    if len(address_list) != req_vf:
        return []
    return address_workload_list
