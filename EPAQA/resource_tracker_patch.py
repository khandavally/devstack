from nova.compute.resource_tracker import ResourceTracker
from nova import utils
from nova import context
from nova import exception
from nova.compute import claims
COMPUTE_RESOURCE_SEMAPHORE = "compute_resources"
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
LOG = logging.getLogger(__name__)


class ResourceTrackerPatch(ResourceTracker):
    """Compute helper class for keeping track of resource usage as instances
    are built and destroyed.
    """

    def __init__(self, host, driver, nodename):
        super(ResourceTrackerPatch, self).__init__(host, driver, nodename)


    @utils.synchronized(COMPUTE_RESOURCE_SEMAPHORE)
    def instance_claim(self, context, instance_ref, limits=None):
        """Indicate that some resources are needed for an upcoming compute
        instance build operation.

        This should be called before the compute node is about to perform
        an instance build operation that will consume additional resources.

        :param context: security context
        :param instance_ref: instance to reserve resources for
        :param limits: Dict of oversubscription limits for memory, disk,
                       and CPUs.
        :returns: A Claim ticket representing the reserved resources.  It can
                  be used to revert the resource usage if an error occurs
                  during the instance build.
        """
        if self.disabled:
            # compute_driver doesn't support resource tracking, just
            # set the 'host' and node fields and continue the build:
            self._set_instance_host_and_node(context, instance_ref)
            return claims.NopClaim()

        # sanity checks:
        if instance_ref['host']:
            LOG.warning(_("Host field should not be set on the instance until "
                          "resources have been claimed."),
                          instance=instance_ref)

        if instance_ref['node']:
            LOG.warning(_("Node field should not be set on the instance "
                          "until resources have been claimed."),
                          instance=instance_ref)
        # get memory overhead required to build this instance:
        overhead = self.driver.estimate_instance_overhead(instance_ref)
        LOG.debug(_("Memory overhead for %(flavor)d MB instance; %(overhead)d "
                    "MB"), {'flavor': instance_ref['memory_mb'],
                            'overhead': overhead['memory_mb']})

        claim = claims.Claim(instance_ref, self, overhead=overhead)
        if self.pci_tracker and limits:
            self.pci_tracker.set_selected_vfs(limits)
        if claim.test(self.compute_node, limits):

            self._set_instance_host_and_node(context, instance_ref)

            # Mark resources in-use and update stats
            self._update_usage_from_instance(self.compute_node, instance_ref)

            elevated = context.elevated()
            # persist changes to the compute node:
            self._update(elevated, self.compute_node)

            return claim

        else:
            raise exception.ComputeResourcesUnavailable()


def notify_decorator(name, fn):
    return fn


@classmethod
def resource_tracker_new(cls, *args, **kwargs):
    resource_tracker = object.__new__(ResourceTrackerPatch)
    return resource_tracker

def ResourceTrackerPatchMain():
    ResourceTracker.__new__ = resource_tracker_new

ResourceTrackerPatchMain()
