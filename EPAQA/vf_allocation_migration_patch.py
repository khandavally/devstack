from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey, DateTime, Boolean, Text, Float
from oslo.config import cfg
from nova.db.sqlalchemy import models
from nova.openstack.common.db.sqlalchemy import session
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from sqlalchemy import MetaData
from sqlalchemy import Column, Index, Integer, BigInteger, Enum, String, schema,Table

LOG = logging.getLogger(__name__)


CONF = cfg.CONF
BASE = declarative_base()
	
	
class VFAllocation(BASE, models.NovaBase):
    """Class represents the object for the table vf_allocation"""
    __tablename__ = 'vf_allocation'
    id = Column(Integer, primary_key=True)
    bus = Column(String(255))  
    slot = Column(String(255))
    los = Column(String(255))
    cp_vf = Column(String(255))
    #los_cr = Column(String(255))
    cr_vf  = Column(String(255))
    total_vf = Column(String(255)) 
	
	
class VFAllocationMigrationPatch:
    """Class handles upgrading and downgrading of vf_allocation table"""
    def upgrade(self, migrate_engine):
        meta = MetaData()
        meta.bind = migrate_engine
        vf_allocationt_table = Table(
		 'vf_allocation',
		 meta,
		 Column('id', Integer, primary_key=True),
		 Column('bus', String(255)),
		 Column('slot', String(255)),
		 Column('los', String(255)),
		 Column('cp_vf', String(255)),
		 #Column('los_cr', String(255)),
		 Column('cr_vf', String(255)),
		 Column('total_vf', String(255)) 
	    )
        vf_allocationt_table.create(migrate_engine,checkfirst=True)
    
    def downgrade(self, migrate_engine):
        meta = MetaData()
        meta.bind =migrate_engine
	vf_allocationt_table = Table('vf_allocation',meta,autoload=True)
	vf_allocationt_table.drop(migrate_engine,checkfirst=True)


def notify(name, fn):
    """Decorator for notify which is used from utils.monkey_patch()."""
    return fn


def VFAllocationMain():
    obj = VFAllocationMigrationPatch()
    migrate_engine = session.get_engine()
    try:
        obj.upgrade(migrate_engine)
    except Exception as e:
        LOG.warn(_("Upgrading instance_table - %s"), e)
    models.__dict__['VFAllocation'] = VFAllocation

VFAllocationMain()



