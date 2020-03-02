import pynetbox
from pprint import pprint
def search_dict_list(a_val, b_val, c_list):
    for line in c_list:
        if line['hostname'] == a_val:
            return line[b_val]
# Define Parent Variables that will be used to auto-generate and assign values
num_spines = 2
num_leafs = 4
p2p_range = '10.0.'
lo0_range = '10.0.250.'
lo1_range = '10.0.255.'
ibgp_range = '10.0.3.'
mgmt_range = '10.4.2.'
ibgp_vlan = '4091'
asn_start = 65000
leaf_int_mlag_peer = 'ae0'

# Generate key/val for Leafs
leaf_list = []
asn = asn_start+1
n = 0
for i in range(num_leafs):
    id = i+1
    device = {}
    device['device_role'] = {'name': 'Leaf'}
    device['interfaces'] = []
    device['bgp_neighbors'] = []
    device['evpn_neighbors'] = []
    device['hostname'] = f'leaf{id}'
    if id%2 == 1:
        device['side'] = 'left'
        device['asn'] = asn
        asn +=1
        device['bgp_neighbors'].append({'neighbor':f'{ibgp_range}{id}', 'remote_as': device['asn'], 'state': 'present'})
        device['interfaces'].append({'interface': 'Lo1', 'address':f'{lo1_range}{id+10}', 'mask':'/32', 'description':'Loopback1 Underlay'})
    else:
        device['side'] = 'right'
        device['asn'] = asn-1
        device['bgp_neighbors'].append({'neighbor':f'{ibgp_range}{id-2}', 'remote_as': device['asn'], 'state': 'present'})
        device['interfaces'].append({'interface': 'Lo1', 'address':f'{lo1_range}{id+9}', 'mask':'/32', 'description':'Loopback1 Underlay'})
    for j in range(num_spines):
        # popov
        #device['interfaces'].append({'interface':f'xe-0/0/{j+11}', 'address':f'{p2p_range}{j+1}.{n+1}', 'mask':'/31', 'description':f'spine{j+1}'})
        device['interfaces'].append({'interface':f'xe-0/0/{j+10}', 'address':f'{p2p_range}{j+1}.{n+1}', 'mask':'/31', 'description':f'spine{j+1}'})
        device['bgp_neighbors'].append({'neighbor':f'{p2p_range}{j+1}.{n}', 'remote_as': asn_start, 'state': 'present'})
        device['evpn_neighbors'].append({'neighbor':f'{lo0_range}{j+1}', 'remote_as': asn_start, 'state': 'present'})
    device['interfaces'].append({'interface': f'Vlan{ibgp_vlan}', 'address':f'{ibgp_range}{i}', 'mask':'/31', 'description':'IBGP Underlay SVI'})
    device['interfaces'].append({'interface': 'Lo0', 'address':f'{lo0_range}{id+10}', 'mask':'/32', 'description':'Loopback0 Underlay'})
    device['interfaces'].append({'interface': 'em0', 'address':f'{mgmt_range}{id+22}', 'mask':'/24', 'description':'OOB Management'})
    leaf_list.append(device)
    n+=2


# Generate key/val for Spines
spine_list = []
asn = asn_start
for i in range(num_spines):
    id = i+1
    device = {}
    device['device_role'] = {'name': 'Spine'}
    device['interfaces'] = []
    device['bgp_neighbors'] = []
    device['evpn_neighbors'] = []
    device['hostname'] = f'spine{id}'
    device['asn'] = asn
    n = 0
    for j in range(num_leafs):
        leaf_asn = search_dict_list(f'leaf{j+1}','asn',leaf_list)
        # popov
        #device['interfaces'].append({'interface':f'xe-0/0/{j+1}', 'address':f'{p2p_range}{id}.{n}', 'mask':'/31', 'description':f'leaf{j+1}'})
        device['interfaces'].append({'interface':f'xe-0/0/{j}', 'address':f'{p2p_range}{id}.{n}', 'mask':'/31', 'description':f'leaf{j}'})
        j = j+1
        device['bgp_neighbors'].append({'neighbor':f'{p2p_range}{id}.{n+1}', 'remote_as': leaf_asn, 'state': 'present'})
        device['evpn_neighbors'].append({'neighbor':f'{lo0_range}{j+11}', 'remote_as': leaf_asn, 'state': 'present'})
        n += 2
    device['interfaces'].append({'interface': 'Lo0', 'address':f'{lo0_range}{id}', 'mask':'/32', 'description':'Loopback0 Underlay'})
    device['interfaces'].append({'interface': 'em0', 'address':f'{mgmt_range}{id+20}', 'mask':'/24', 'description':'OOB Management'})
    spine_list.append(device)

# Combine both Leaf and Spine lists into a single list
#all_devices = spine_list
all_devices = leaf_list + spine_list



############################################################################
# NetBox Tasks
############################################################################
# Connect to NetBox
nb = pynetbox.api(
    'http://192.168.33.10',
    token='5bc7e6e1e045cea46785f44d1e815b6c214bdaf3'
)
# Create new Site
new_site = nb.dcim.sites.get(slug='junos-data')
if not new_site:
    new_site = nb.dcim.sites.create(
        name='Junos Lab Datacenter',
        slug='junos-lab-dc',
    )
# Create Device Role 'Leaf'
nb.dcim.device_roles.create(
    name='Leaf',
    slug='leaf',
    color='2196f3'
)
# Create Device Role 'Spine'
nb.dcim.device_roles.create(
    name='Spine',
    slug='spine',
    color='3f51b5'
)
# NetBox Prefixes - Underlay P2P
for j in range(num_spines):
    nb.ipam.prefixes.create(
        prefix=f'{p2p_range}{j+1}.0/24',
        description=f'spine-{j+1} P2P'
    )
    n = 0
    for h in range(num_leafs):
        nb.ipam.prefixes.create(
            prefix=f'{p2p_range}{j+1}.{n}/31',
            description=f'spine-{j+1}-leaf-{h+1} P2P'
        )
        n+=2
# NetBox Prefixes - Loopback0
nb.ipam.prefixes.create(
        prefix=f'{lo0_range}0/24',
        description=f'Underlay Loopbacks'
    )
# NetBox Prefixes - Loopback1
#nb.ipam.prefixes.create(
#        prefix=f'{lo1_range}0/24',
#    )

# NetBox Prefixes - IBGP Underlay
nb.ipam.prefixes.create(
        prefix=f'{ibgp_range}0/24',
        description=f'Underlay IBGP'
    )
# Iterate over each Device
for dev in all_devices:
    # Create Device in NetBox
    new_device = nb.dcim.devices.create(
        name=dev['hostname'],
        site=new_site.id,
        device_type={
            'model': 'vqfx10k'
        },
        platform={
            'name': 'junos'
        },
        device_role=dev['device_role'],
        custom_fields={
            'bgp_asn': dev['asn']
        },
        local_context_data = {}
    )

    # Assign IP Addresses to Interfaces
    for intf in dev['interfaces']:
        # popov
        #print('#1')
        #print(intf['interface'])
        # IE: create Lo1
        if 'xe-0/0/' not in intf['interface'] and 'em' not in intf['interface']:
            nbintf = nb.dcim.interfaces.create(
                name=intf['interface'],
                form_factor=0,
                description=intf['description'],
                device=new_device.id
            )
        else:
            # Get interface id from NetBox
            nbintf = nb.dcim.interfaces.get(device=dev['hostname'], name=intf['interface'])
            # popov
            #print('#2')
            #print(dev['hostname'])
            #print(intf['interface'])
            nbintf.description = intf['description']
            nbintf.save()
        # Add IP to interface to NetBox
        intip = nb.ipam.ip_addresses.create(
            address=f"{intf['address']}{intf['mask']}",
            status=1,
            interface=nbintf.id,
            )

        # Assign Primary IP to device
        if intf['interface'] is 'Management1':
            new_device.primary_ip4 = {'address': intip.address }
            new_device.save()
    # Assign local config context data
    for k,v in dev.items():
        if 'side' in k:
            new_device.local_context_data.update({k:v})
    new_device.save()
