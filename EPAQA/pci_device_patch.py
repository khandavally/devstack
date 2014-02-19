# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Intel Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitationsl
#    under the License.
# 

import copy
import functools

from nova.objects import fields as fields_obj
from nova.pci import pci_utils
from nova import db
from nova import exception
from nova.objects import base
from nova.objects import utils as obj_utils
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging

from nova.objects.pci_device import check_device_status, PciDevice, PciDeviceList
from nova.db.sqlalchemy.models import PciDevice as PciDeviceModel
from sqlalchemy import Column, Index, Integer, BigInteger, Enum, String, schema
from nova.openstack.common.db.sqlalchemy import session
from nova.openstack.common.gettextutils import _
from sqlalchemy import MetaData
from nova.db.sqlalchemy import utils
from nova.objects import pci_device
LOG = logging.getLogger(__name__)



class PciDevicePatch(PciDevice):

    """Extension of nova.objects.pci_device.PciDevice class with
       bus, slot, function fields added.
    """

    # Version 1.0: Initial version
    # Version 1.1: bus, slot, function fields are added in fields dictionary

    fields = PciDevice.fields
    #fields['bus']=fields_obj.StringField()
    #fields['slot']= fields_obj.StringField()
    #fields['function'] =  fields_obj.StringField()
    fields['bus']= obj_utils.str_or_none
    fields['slot']= obj_utils.str_or_none
    fields['function'] = obj_utils.str_or_none
    fields['workload'] = obj_utils.str_or_none

    def update_device(self, dev_dict):
        """Sync the content from device dictionary to device object.

        The resource tracker updates the available devices periodically.
        To avoid meaningless syncs with the database, we update the device
        object only if a value changed.
        """
        # Note(jprabh1x): added bus,slot,function into fields dict as 
        # seperate fields.
        no_changes = ('status', 'instance_uuid', 'id', 'extra_info', 'workload')
        map(lambda x: dev_dict.pop(x, None),
            [key for key in no_changes])

        # Note(jprabh1x): populating values for bus,slot,function from address in dev_dict.
        if dev_dict.has_key("address"):
    		address = pci_utils.parse_address(dev_dict["address"])
    		dev_dict.update({'bus':str(address[1]), 'slot':str(address[2]), 'function':str(address[3])})
        for k, v in dev_dict.items():
            if k in self.fields.keys():
                self[k] = v
            else:
                extra_info = self.extra_info
                extra_info.update({k: str(v)})
                self.extra_info = extra_info

    @check_device_status(dev_status=['claimed', 'allocated'])
    def free(self, instance=None):
        if instance and self.instance_uuid != instance['uuid']:
            raise exception.PciDeviceInvalidOwner(
                compute_node_id=self.compute_node_id,
                address=self.address, owner=self.instance_uuid,
                hopeowner=instance['uuid'])
        old_status = self.status
        self.status = 'available'
        self.instance_uuid = None
        self.workload = None
        if old_status == 'allocated' and instance:
            # Notes(yjiang5): remove this check when instance object for
            # compute manager is finished
            existed = next((dev for dev in instance['pci_devices']
                if dev.id == self.id))
            if isinstance(instance, dict):
                instance['pci_devices'].remove(existed)
            else:
                instance.pci_devices.objects.remove(existed)

    def __init__(self):
        super(PciDevicePatch, self).__init__()
        self.obj_reset_changes()
        self.extra_info = {}

class PciDeviceListPatch(PciDeviceList):

    #fields = {'objects':fields_obj.ListOfObjectsField('PciDevicePatch'),}
    #fields['objects'] =   obj_utils.nested_object(PciDeviceListPatch, none_ok=False) 
    
    def __init__(self):
        super(PciDeviceListPatch, self).__init__()
        self.objects = []
        self.obj_reset_changes()

class PciTableMigrationPatch:   
    """Class handles upgrading and downgrading of pci_devices
       table with bus, slot, function fields.
    """
    def upgrade_pci_device_table(self, migrate_engine):
        LOG.audit(_("upgrading pci_devices table"))
        meta = MetaData(bind=migrate_engine)
        pci_devices = utils.get_table(migrate_engine, 'pci_devices')
        bus = Column('bus', String(2), nullable=False)
        slot = Column('slot', String(2), nullable=False)
        function = Column('function', String(2), nullable=False)
        workload = Column('workload', String(2), nullable=True)
        pci_devices.create_column(bus)
        pci_devices.create_column(slot)
        pci_devices.create_column(function)
        pci_devices.create_column(workload)
        
    def downgrade_pci_device_table(self, migrate_engine):
        LOG.audit(_("downgrading pci_devices table"))
        meta = MetaData(bind=migrate_engine)
        pci_devices = utils.get_table(migrate_engine, 'pci_devices')
        pci_devices.drop_column('bus')
        pci_devices.drop_column('slot')
        pci_devices.drop_column('function')
        pci_devices.drop_column('workload')



def notify_decorator(name, fn):
    """Decorator for notify which is used from utils.monkey_patch()."""
    return fn

@classmethod
def pci_device_list_patch_new(cls, *args, **kwargs):
    """Function which helps overridden of __new__ method in nova.objects.pci_device.PciDeviceList"""
    new_instance = object.__new__(PciDeviceListPatch)
    return new_instance

@classmethod
def pci_device_patch_new(cls, *args, **kwargs):
    """Function which helps overridden of __new__ method in nova.objects.pci_device.PciDevice"""
    new_instance = object.__new__(PciDevicePatch)
    return new_instance



def PciDevicePatchMain():
    PciDevice.__new__ = pci_device_patch_new
    PciDeviceList.__new__ = pci_device_list_patch_new

    PciDeviceModel.bus = Column(String(2), nullable=False)
    PciDeviceModel.slot = Column(String(2), nullable=False)
    PciDeviceModel.function = Column(String(2), nullable=False)
    PciDeviceModel.workload = Column(String(2), nullable=True)
    obj = PciTableMigrationPatch()
    migrate_engine = session.get_engine()
        
    try:
        obj.upgrade_pci_device_table(migrate_engine)
    except Exception as e:
        LOG.warn(_("Upgrading pci_device_table - %s"), e)
		
PciDevicePatchMain()

