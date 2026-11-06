"""Re-derive connector/C/GPU design paths. No electrical or hardware operations."""
from pathlib import Path
import json,hashlib,shlex,collections,re
root=Path(__file__).resolve().parents[2];p=root/'CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF';cad=p/'01_BOARDVIEW/CG161P_R2_boardview.cad';b=cad.read_bytes();text=b.decode('utf-8-sig');nets={};components={};section=None;net=None;component=None
for line_no,line in enumerate(text.splitlines(),1):
 tok=[v.strip('"') for v in shlex.split(line,posix=False)]
 if not tok:continue
 if tok[0].startswith('$'):section=tok[0];continue
 if section=='$SIGNALS':
  if tok[0]=='SIGNAL':net=tok[1];nets[net]={'line':line_no,'nodes':[]}
  elif tok[0]=='NODE':nets[net]['nodes'].append({'component':tok[1],'pin':tok[2],'line':line_no})
 if section=='$COMPONENTS':
  if tok[0]=='COMPONENT':component=tok[1];components[component]={'line':line_no}
  elif component and tok[0] in ['PLACE','LAYER','ROTATION','SHAPE']:components[component][tok[0]]=tok[1:]
assert hashlib.sha256(b).hexdigest()=='7338ccead9423c8ddd61f5c1e4f0147d95b3c6da5af3e9bae0a20fbcfab6264d'
by_pin={};by_component=collections.defaultdict(list)
for net,info in nets.items():
 for node in info['nodes']:
  key=(node['component'],node['pin']);assert key not in by_pin,'duplicate pin across nets'
  by_pin[key]=net;by_component[key[0]].append((key[1],net))
paths=[];sidebands=[]
for con in ['J1','J5','J10']:
 for pin,net in sorted(by_component[con]):
  if not any(x in net for x in ['IFP','HPD','DDC']):continue
  rec={'connector':con,'pin':pin,'net':net,'signal_line':nets[net]['line'],'nodes':nets[net]['nodes']}
  if any(x in net for x in ['AUX','HPD','DDC']):sidebands.append(rec)
  direct=[n for n in nets[net]['nodes'] if n['component']=='G1']
  for n in direct:paths.append({'connector':con,'pin':pin,'net':net,'gpu_pin':n['pin'],'via':None,'scope':'CAD direct net membership'})
  for n in nets[net]['nodes']:
   c=n['component']
   if not c.startswith('C') or len(by_component[c])!=2:continue
   other=[(cp,cn) for cp,cn in by_component[c] if cp!=n['pin']]
   if len(other)!=1:continue
   cp,cn=other[0]
   if not re.fullmatch(r'IFP[A-Z]+_L[0-3]\*?',cn):continue
   for gpu in nets[cn]['nodes']:
    if gpu['component']=='G1':paths.append({'connector':con,'pin':pin,'net':net,'gpu_pin':gpu['pin'],'via':{'component':c,'connector_side_pin':n['pin'],'gpu_side_pin':cp,'gpu_net':cn},'scope':'CAD design across two-terminal capacitor; not DC continuity or populated/working path'})
# HDMI colay footprint uses resistor/capacitor chains. Never traverse ICs or ground.
hdmi_paths=[]
for pin,start_net in by_component['J10']:
 if not start_net.startswith('IFP'):continue
 queue=collections.deque([(start_net,[])])
 seen={start_net}
 while queue:
  net,chain=queue.popleft()
  for node in nets[net]['nodes']:
   if node['component']=='G1' and re.fullmatch(r'IFP[A-Z]+_L[0-3]\*?',net):
    hdmi_paths.append({'connector':'J10','pin':pin,'initial_net':start_net,'gpu_net':net,'gpu_pin':node['pin'],'passive_chain':chain,'scope':'Design connectivity across <=3 two-terminal R/C components; population and electrical function unverified'})
   c=node['component']
   if len(chain)>=3 or not re.fullmatch(r'[RC][0-9]+',c) or len(by_component[c])!=2:continue
   for cp,cn in by_component[c]:
    if cp==node['pin'] or cn in seen or not cn.startswith('IFP'):continue
    seen.add(cn);queue.append((cn,chain+[{'component':c,'from_pin':node['pin'],'to_pin':cp,'from_net':net,'to_net':cn}]))
# One independently known sample anchors parsing to exact source nodes.
assert any(x['connector']=='J1' and x['pin']=='1' and x['gpu_pin']=='BM18' and x['via']['component']=='C47' for x in paths)
images=[]
for rel in ['02_PCB_PHOTOS/ANNOTATED/CMP40HX_PORTS_PHOTO_ANNOTATED.jpg','02_PCB_PHOTOS/PHONE_PREVIEWS/1793813621628.jpg']:
 f=p/rel;images.append({'path':str(f.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'scope':'Supplied photograph; capture/board-to-UUID authentication unknown'})
sideband_components={}
for c in ['Q7','Q509','Q521','C42','C43','R720','R742','D3']:
 sideband_components[c]={'component_metadata':components.get(c),'pins':[],'internal_connections':'UNKNOWN; footprint/name does not define electrical connectivity'}
 for pin,net in by_component.get(c,[]):
  sideband_components[c]['pins'].append({'pin':pin,'net':net,'signal_line':nets[net]['line'],'net_nodes':nets[net]['nodes'] if net!='GND' else [],'net_node_count':len(nets[net]['nodes']),'ground_nodes_omitted':net=='GND'})
r={'sideband_components':sideband_components,'input':{'path':str(cad.relative_to(root)),'sha256':hashlib.sha256(b).hexdigest()},'components':{c:components[c] for c in ['G1','J1','J5','J10']},'connector_gpu_paths':paths,'hdmi_passive_paths':hdmi_paths,'sideband_nets':sidebands,'images_inspected':images,'limits':['Design netlist is not proof of actual CMP copper/population','Two-terminal capacitor paths do not prove live link or DC continuity','No internal connection is invented across Q/U/D multi-pin devices','Package ball names are CAD nodes, not independently authenticated package pinout','No physical restoration or board-unrouted conclusion']}
out=root/'PHASE21_FUNCTIONAL_RESEARCH/evidence/pcb_design_rederived.json';out.write_text(json.dumps(r,indent=2)+'\n')
print('Connector-to-GPU design paths:',dict(collections.Counter(x['connector'] for x in paths)));print('Sideband nets retained:',len(sidebands))

print('HDMI passive design paths:',len(hdmi_paths))
