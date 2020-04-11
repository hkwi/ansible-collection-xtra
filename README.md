# Ansible Collection - hkwi.xtra

## inventory plugin example

Prepare ansible.cfg

```
[defaults]
collections_path=collections

[inventory]
enable_plugins=host_list,script,auto,yaml,ini,hkwi.xtra.alias,hkwi.xtra.patch
```

Then you can use extra inventory plugins

`hkwi.xtra.alias` is useful when you're using inventory directory and import common content into that. Following example file `site01/00_base.yml` imports external `common/base.yml` into `site01/` inventory.

```
---
plugin: hkwi.xtra.alias
next: yaml
path: ../common/base.yml
# import the common knowledge
```

`hkwi.xtra.patch` defines populates vars and or groups based on the inventory info. This helps reducing complex template logic by splitting some into inventory logic. `site01/04_patch.yml` will generate `group01` based on host names, which then template acition can use `group01`.

```
---
plugin: hkwi.xtra.patch
patch:
- name: group01
  block: |
    vars:
      group_name: group01
    hosts:
      {% for host in group.all %}{% if host.endswith("01") %}
      {{ host }}:
      {% endif %}{% endfor %}
```

