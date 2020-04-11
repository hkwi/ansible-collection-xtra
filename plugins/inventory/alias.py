import logging
import yaml
import os.path
from ansible.plugins.loader import inventory_loader
from ansible.plugins.inventory import BaseInventoryPlugin

# plugin: alias
# next: auto
# path: ../common.yml

class InventoryModule(BaseInventoryPlugin):
	NAME = "alias"
	
	def verify_file(self, path):
		return yaml.safe_load(open(path))["plugin"] == self.NAME
	
	def parse(self, inventory, loader, path, cache=True):
		data = loader.load_from_file(path)
		
		plugin = inventory_loader.get(data["next"])
		next_path = data["path"]
		if not next_path.startswith("/"):
			next_path = os.path.abspath(os.path.join(os.path.dirname(path), next_path))
		assert not os.path.samefile(path, next_path)
		try:
			plugin.parse(inventory, loader, next_path, cache=cache)
		except:
			logging.error("alias inner plugin %s parse error" % next_path, exc_info=True)
			raise
		
		try:
			plugin.update_cache_if_changed()
		except AttributeError:
			pass
