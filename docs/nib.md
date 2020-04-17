# hkwi.xtra.nib inventory plugin

This plugin is for host network information, such as CIDR, IPv4 address,
MAC address and host names. You can put the network information in some 
separate multiple inventory files, and the plugin will merge those
into each host hostvars.
This is useful when a host joins multiple networks.

## Concept

We import RDF words to explain the concept.

Class
- Segment
- IPv4Address
- MacAddress
- Interface
- Host

Property
- segment: object type is Segment
- ipaddr : object type is IPv4Address
- lladdr : object type is MacAddress
- iface  : object type is Interface
- host   : object type is Host
- cidr   : subject type is Segment, and object is a string
- type   : rdf:type
- label  : rdf:label
- value  : rdf:value

Classes that `value` property is the identifier
- IPv4Address
- MacAddress

Classes that `label` property is the identifier
- Segment
- Interface
- Host

Network data structure in turtle format will be as following:

```
[] rdf:type Segment ;
   rdf:value "192.168.0.0/24" ;
   cidr "192.168.0.0/24" ;
   ipaddr [ rdf:type IPv4Address ;
            rdf:value "192.168.0.1" ;
            lladdr [ rdf:type MacAddress ;
                     rdf:value "00:00:5e:00:00:01" ;
                     iface [ rdf:type Interface ;
                             rdf:label "eth0" ;
                             host [ rdf:type Host ;
                                    rdf:label "localhost" .
                                  ]
                           ]
                   ]
          ] .
```

We translate this into yaml representation.

```
---
type: Segment
value: 192.168.0.0/24
cidr: 192.168.0.0/24
ipaddr:
- type: IPv4Address
  value: 192.168.0.1
  lladdr:
  - type: MacAddress
    value: "00:00:5e:00:00:01"
    iface:
    - type: Interface
      label: eth0
      host:
      - type: Host
        label: localhost
```

Rule1. If the type was obvious from property, we can drop it.

```
---
label: segment0
cidr: 192.168.0.0/24
ipaddr:
- value: 192.168.0.1
  lladdr:
  - value: "00:00:5e:00:00:01"
    iface:
    - label: eth0
      host:
      - label: localhost
```

Rule2. If subject does not have any attribute except the identifier,
value may be a string of that identifier.
Rule3. If subject was a single node list, subject may be that single
node without wrapping list.
Rule4. Only one list subject may happen in one depth so as the
meaning of tuple is determinant.

```
cidr: 192.168.0.0/24
ipaddr:
- value: 192.168.0.1
  host: localhost
```

Subject or object may have attributes, which key is anything except the
reserved term.

Ansible variables is `nib`, and the content is list of
(segment, ipaddr, lladdr, iface, host) tuple dictionary.

```
nib:
- segment:
    label: segment0
  ipaddr:
    value: 192.168.0.1
  iface:
    label: eth0
- segment:
    label: segment1
  ipaddr:
    value: 192.168.1.1
  iface:
    label: eth1
```


## Inventory file example

```
---
plugin: hkwi.xtra.nib
---
label: segment0
value: 192.168.0.0/24
cidr: 192.168.0.0/24
ipaddr:
- value: 192.168.0.1
  lladdr:
  - value: "00:00:5e:00:00:01"
    iface:
    - label: eth0
      host:
      - label: localhost
- value: 192.168.0.2
  host: external2
---
label: segment1
value: 192.168.1.0/24
cidr: 192.168.1.0/24
ipaddr:
- value: 192.168.1.1
  lladdr:
  - value: "00:00:5e:00:00:02"
    iface:
    - label: eth1
      host:
      - label: localhost
- value: 192.168.1.2
  host: external2
```


## Using variables

Example:

```
{{ nib | map(attribute="ipaddr.value") | first }}
```
