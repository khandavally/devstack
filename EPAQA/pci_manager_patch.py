from nova.pci.pci_manager import PciDevTracker


class PciDevTrackerPatch(PciDevTracker):
    """ Extension of nova.pci.pci_manager.PciDevTracker class to help pci_device allocation 
      based on vf allocation algorithm"""
    def __init__(self, node_id=None):
        super(PciDevTrackerPatch, self).__init__(node_id)
        self.selected_vfs = None


    def set_selected_vfs(self, limits):
	"""Function sets member variable selected_vfs from the passed argument limits"""
        self.selected_vfs = limits.get('selected_vfs', {})

    def get_free_devices_for_requests(self, pci_requests):
        """This is an over loaded function which helps in short listing 
		pci_devices as per the requirement for an instance. 
        """
        alloc = []

        for request in pci_requests:
            if self.selected_vfs:
                available = self._get_selected_devices_for_request(
                request,
                [p for p in self.free_devs if p not in alloc])
            else:
                available = self._get_free_devices_for_request(
                request,
                [p for p in self.free_devs if p not in alloc])
            if not available:
                return []
            alloc.extend(available)
        return alloc

    def _get_selected_devices_for_request(self, pci_request, pci_devs):
	"""Function selects required pci_devices from dev pool as the addrss values are given.""" 
        count = pci_request.get('count', 1)
        spec = pci_request.get('spec', [])
        devs = self._filter_devices_for_spec(spec, pci_devs)
        selected_dev_addresses = [vf_tuple[0] for vf_tuple in self.selected_vfs[pci_request.get('alias_name', 'default')]]
        devs = [self.add_workload_type(dev, pci_request) for dev in devs if dev.address in selected_dev_addresses]
        if len(devs) < count:
            return None
        else:
            return devs[:count]

    def add_workload_type(self, dev, pci_request):
        for vf_tuple in self.selected_vfs[pci_request.get('alias_name', 'default')]:
            if vf_tuple[0] == dev.address:
                dev.workload = vf_tuple[1]
        return dev

def notify_decorator(name, fn):
    """Decorator for notify which is used from utils.monkey_patch()."""
    return fn


@classmethod
def pci_dev_tracker_new(cls, *args, **kwargs):
    """Function which helps overridden of __new__ method in nova.pci.pci_manager.PciDevTracker"""
    pci_dev_tracker = object.__new__(PciDevTrackerPatch)
    return pci_dev_tracker

def PciManagerPatchMain():
    PciDevTracker.__new__ = pci_dev_tracker_new

PciManagerPatchMain()
