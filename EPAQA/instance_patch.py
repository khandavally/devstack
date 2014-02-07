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
from nova.objects.instance import Instance, InstanceList,INSTANCE_DEFAULT_FIELDS
from nova.db.sqlalchemy.models import Instance as InstanceModel
from sqlalchemy import Column, Index, Integer, BigInteger, Enum, String, schema
from nova.openstack.common.db.sqlalchemy import session
from nova.openstack.common.gettextutils import _
from sqlalchemy import MetaData
from nova.db.sqlalchemy import utils

LOG = logging.getLogger(__name__)

class InstancePatch(Instance):

    """Extension to nova.objects.instance class with workload type field
       added.
    """

    # Version 1.0: Initial version
    # Version 1.1: workload type added in fields dictionary
    fields = Instance.fields
    fields['workload_type'] = fields_obj.StringField(nullable=True)
    fields['policy'] = fields_obj.IntegerField(nullable=True)
    fields['pci_devices'] =  fields_obj.ObjectField('PciDeviceListPatch', nullable=True)
    

    def __init__(self, *args, **kwargs):
        super(InstancePatch, self).__init__(*args, **kwargs)
        self.obj_reset_changes()

    def obj_reset_changes(self, fields=None):
        super(InstancePatch, self).obj_reset_changes(fields)
        self._reset_metadata_tracking()

    def obj_what_changed(self):
        changes = super(InstancePatch, self).obj_what_changed()
        if 'metadata' in self and self.metadata != self._orig_metadata:
            changes.add('metadata')
        if 'system_metadata' in self and (self.system_metadata !=
                                          self._orig_system_metadata):
            changes.add('system_metadata')
        return changes
	
    @base.remotable
    def create(self, context):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create', reason='already created')
        updates = self.obj_get_changes()
        updates.pop('id', None)
        expected_attrs = [attr for attr in INSTANCE_DEFAULT_FIELDS if attr in updates]
        if 'security_groups' in updates:
            updates['security_groups'] = [x.name for x in updates['security_groups']]
        if 'info_cache' in updates:
            updates['info_cache'] = {'network_info': updates['info_cache'].network_info.json()}
        updates['workload_type']=context.workload_type
        updates['policy']=context.policy
        db_inst = db.instance_create(context, updates)
        Instance._from_db_object(context, self, db_inst, expected_attrs)   



class InstanceListPatch(InstanceList):
    fields = {
        'objects': fields_obj.ListOfObjectsField('InstancePatch'),
    }

    def __init__(self, *args, **kwargs):
        super(InstanceListPatch, self).__init__(*args, **kwargs)


class InstanceMigrationPatch:  
   
    def upgrade_instance_table(self, migrate_engine):
        LOG.audit(_("upgrading instance table"))
        meta = MetaData(bind=migrate_engine)
        instances = utils.get_table(migrate_engine, 'instances')
        workload_type = Column('workload_type', String(100), nullable=True)
	policy = Column('policy', Integer(11), nullable=True)
        instances.create_column(workload_type)
	instances.create_column(policy)

    def downgrade_instance_table(self, migrate_engine):
        LOG.audit(_("downgrading instance table"))
        meta = MetaData(bind=migrate_engine)
        instances = utils.get_table(migrate_engine, 'instances')
        instances.drop_column('workload_type')
	instances.drop_column('policy')
      
def notify_decorator(name, fn):
    return fn

@classmethod
def instance_patch_new(cls, *args, **kwargs):
    new_instance = object.__new__(InstancePatch)
    return new_instance

@classmethod
def instance_list_patch_new(cls, *args, **kwargs):
    new_instance = object.__new__(InstanceListPatch)
    return new_instance

def InstancePatchMain():
    Instance.__new__ = instance_patch_new
    InstanceList.__new__ = instance_list_patch_new
    InstanceModel.workload_type = Column(String(100), nullable=True)
    InstanceModel.policy = Column(Integer(11), nullable=True)
    obj = InstanceMigrationPatch()
    migrate_engine = session.get_engine()
    try:
        obj.upgrade_instance_table(migrate_engine)
    except Exception as e:
        LOG.warn(_("Upgrading instance_table - %s"), e)  

InstancePatchMain()
