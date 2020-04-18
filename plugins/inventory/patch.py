import itertools
import logging
import yaml
from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.inventory.helpers import get_group_vars
from ansible.template import Templar

# plugin: patch
# 
# patch:
# - block: |
#     all:
#       vars:
#         version: master
#   # chunk without name will be a template for global content
# 
# - name: group01
#   block: |
#     vars:
#       version: master
#     hosts:
#       vhost01:
# 
# - name: all
#   vars: |
#     version: master
#     {% for key in properties.keys() %}
#     {{ key }}: {{ properties[key] }}
#     {% endfor %}
#   # block enables templating variable key
# 
# - name: all
#   vars:
#     version: "{{ master }}"
#   # value 

class InventoryModule(BaseInventoryPlugin):
	NAME = "patch"
	
	def verify_file(self, path):
		return yaml.safe_load(open(path))["plugin"].endswith(self.NAME)
	
	def parse(self, inventory, loader, path, cache=True):
		for hunk in yaml.safe_load(open(path)).get("patch", []):
			try:
				process_hunk(hunk, inventory, loader)
			except:
				logging.error("Error in hunk %s" % hunk, exc_info=True)
				raise

def process_hunk(hunk, inventory, loader):
	name = hunk.get("name", None)
	args = generate_template_vars(inventory, name)
	
	templar = Templar(loader=loader, variables=args)
	templar.environment = templar.environment.overlay(trim_blocks=False)
	
	def template_leaf(obj):
		if isinstance(obj, str):
			return templar.template(obj)
		elif isinstance(obj, list):
			return [template_leaf(o) for o in obj]
		elif isinstance(obj, dict):
			return {k:template_leaf(v) for k,v in obj.items()}
		else:
			return obj
	
	if "vars" in hunk:
		assert name, "vars requires name"
		vars = hunk.get("vars", None)
		
		if vars is None:
			data = None
		elif isinstance(vars, str):
			data = yaml.safe_load(template_leaf(vars))
		elif isinstance(vars, dict):
			data = template_leaf(vars)
		else:
			assert False, "unexpected vars %s" % vars
		
		if name in inventory.hosts:
			set_variable(inventory, name, data, args["hostvars"].get(name))
		else:
			set_variable(inventory, name, data, args["groupvars"].get(name))
	
	else:
		if "block" in hunk:
			block = hunk.get("block", None)
			
			if block is None:
				data = None
			elif isinstance(block, str):
				data = yaml.safe_load(template_leaf(block))
			elif isinstance(block, dict):
				data = template_leaf(block)
			else:
				assert False, "unexpected block %s" % c
		elif "src" in hunk:
			src = os.path.abspath(os.path.join(os.path.dirname(path), hunk["src"]))
			data = yaml.safe_load(template_leaf(open(src).read()))
		else:
			assert False, "block or src required"
		
		if name is None:
			assert isinstance(data, dict)
			for g,d in data.items():
				set_group_hunk(inventory, g, d, args)
		elif name in inventory.hosts:
			set_variable(inventory, name, data, args["hostvars"].get(name))
		else:
			if name not in inventory.groups:
				inventory.add_group(name)
			if isinstance(data, dict):
				set_group_hunk(inventory, name, data, args)
	

def generate_template_vars(inventory, name=None):
	groups = inventory.get_groups_dict()
	groups["all"] = inventory.hosts
	
	hostvars = {}
	for k,host in inventory.hosts.items():
		v = get_group_vars(host.groups)
		v.update(host.get_vars())
		hostvars[k] = v
	
	groupvars = {}
	for k,group in inventory.groups.items():
		v = get_group_vars(group.parent_groups)
		v.update(group.get_vars())
		groupvars[k] = v
	
	args = dict(
		groups = groups,
		hostvars = hostvars,
		groupvars = groupvars
	)
	if name in inventory.hosts:
		args.update(hostvars.get(name,{}))
	elif name:
		args.update(groupvars.get(name,{}))
	
	return args

def set_variable(inventory, name, data, old_data):
	if isinstance(data, dict):
		for k,v in data.items():
			if isinstance(old_data, dict) and k in old_data:
				if is_safe_merge(old_data[k], v):
					logging.info("variable cover name=%s key=%s" % (name, k))
				else:
					logging.warn("variable hiding name=%s key=%s" % (name, k))
			inventory.set_variable(name, k, v)

def set_group_hunk(inventory, group, data, args):
	if data is None:
		return
	assert isinstance(data,dict) 
	
	inventory.add_group(group)
	
	hosts = data.get("hosts")
	if isinstance(hosts, dict):
		for name,vars in hosts.items():
			inventory.add_host(name, group)
			if isinstance(vars, dict):
				set_variable(inventory, name, vars, args["hostvars"].get(name))
	
	vars = data.get("vars")
	if isinstance(vars, dict):
		set_variable(inventory, group, vars, args["groupvars"].get(group))
	
	children = data.get("children")
	if isinstance(children, dict):
		for name,vars in children.items():
			if name not in inventory.groups:
				inventory.add_group(name)
			inventory.add_child(group, name)
			set_group_hunk(inventory, name, vars, args)

def is_safe_merge(old_value, new_value):
	if old_value == new_value:
		return True
	
	if old_value is None:
		return True
	
	if isinstance(old_value, dict) and isinstance(new_value, dict):
		for key in set(old_value.keys()).union(set(new_value.keys())):
			if not is_safe_merge(old_value.get(key), new_value.get(key)):
				return False
		return True
	
	elif isinstance(old_value, list) and isinstance(new_value, list):
		for e in old_value:
			if e not in new_value:
				return False
		return True
	
	return False
