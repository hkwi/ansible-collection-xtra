import logging
import yaml
import os.path
from io import open
from ansible.inventory.helpers import get_group_vars
from ansible.plugins.loader import inventory_loader
from ansible.plugins.inventory import BaseInventoryPlugin

# plugin: hkwi.xtra.nib

class InventoryModule(BaseInventoryPlugin):
	NAME = "nib"
	
	def verify_file(self, path):
		for doc in yaml.safe_load_all(open(path, encoding="UTF-8")):
			return doc["plugin"].endswith(self.NAME)
	
	def parse(self, inventory, loader, path, cache=True):
		data = list(yaml.safe_load_all(open(path, encoding="UTF-8")))
		assert len(data) > 0
		
		nibs = {}
		for k,host in inventory.hosts.items():
			v = get_group_vars(host.groups)
			v.update(host.get_vars())
			
			if "nib" in v and isinstance(v["nib"], list):
				nibs[k] = v["nib"]
		
		rows = parse(*data[1:])
		for row in rows:
			if "host" in row:
				host = row["host"]["label"]
				if host in nibs:
					nibs[host].append(row)
				else:
					nibs[host] = [row]
		
		for name, nib in nibs.items():
			inventory.add_host(name)
			inventory.set_variable(name, "nib", nib)

prop_key=dict(
	segment="label",
	ipaddr="value",
	lladdr="value",
	iface="label",
	host="label",
)

def dict_box(data, key):
	if isinstance(data, str):
		return {key:data}
	elif isinstance(data, dict):
		assert key in data, "key=%s, data=%s" % (key, data)
		return data
#		return {k:v for k in data.items() if k not in ("segment","ipaddr","lladdr","iface","host")}
	assert False, "key=%s, data=%s" % (key, data)

def normalize(prop, obj):
	# list of dict
	key = prop_key[prop]
	if obj is None:
		return []
	elif isinstance(obj, (str, dict)):
		return [dict_box(obj, key)]
	elif isinstance(obj, list):
		return [dict_box(o, key) for o in obj]
	
	assert False, "unexpected %s data type" % key

def merge_dict(a, b):
	assert isinstance(a, dict)
	assert isinstance(b, dict)
	
	kc = set(prop_key.keys())
	ka = set(a.keys()) - kc
	kb = set(b.keys()) - kc
	
	ret = {k:v for k,v in a.items() if k in ka-kb}
	ret.update({k:v for k,v in b.items() if k in kb-ka})
	for k in ka.intersection(kb):
		if a[k] == b[k]:
			ret[k] = a[k]
		else:
			ret[k] = merge_dict(a[k], b[k])
	return ret

def merge_leaf(prop, a, b):
	key = prop_key[prop]
	assert a[key] == b[key], "conflicting definition %s.%s %s != %s" % (prop, key, a[key], b[key])
	return merge_dict(a, b)

def flatten(prop, data, base={}):
	for vn in normalize(prop, data):
		cur = {k:v for k,v in base.items() if k != prop}
		if prop in base:
			cur[prop] = merge_leaf(base[prop], vn)
		else:
			cur[prop] = merge_dict(data, {})
		
		vars = []
		for p in prop_key:
			if p in vn:
				vs = normalize(p, vn[p])
				if isinstance(vn[p], list):
					vars.append([(p,v) for v in vs])
				else:
					cur[p] = vs[0]
		
		if len(vars)==0:
			yield cur
		elif len(vars)==1:
			for p,v in vars[0]:
				for c in flatten(p, v, cur):
					yield c
		else:
			assert False, "entity can have zero or one list"

def to_tree(rows, prop):
	key = prop_key[prop]
	lut = {}
	for row in rows:
		name = row.get(prop,{}).get(key)
		if name is None:
			continue
		elif name not in lut:
			lut[name] = [row]
		else:
			lut[name].append(row)
	
	ret = []
	for name, rows in lut.items():
		data = {}
		for pr in rows:
			data = merge_dict(data, pr[prop])
		
		kseq = ("host","iface","lladdr","ipaddr","segment")
		for k in kseq[kseq.index(prop)+1:]:
			v = to_tree(rows, k)
			if v:
				data[k] = v
		
		ret.append(data)
	
	return ret

def parse(*bulk):
	rows = []
	for data in bulk:
		if not isinstance(data, dict):
			continue
		
		t = data.get("type")
		if "cidr" in data:
			assert t in (None, "Segment")
			prop = "segment"
		else:
			prop = {
				"Segment": "segment",
				"IPv4Address": "ipaddr",
				"MacAddress": "lladdr",
				"Interface": "iface",
				"Host": "host"
			}[t]
		rows += [x for x in flatten(prop, data)]
	
	return rows
