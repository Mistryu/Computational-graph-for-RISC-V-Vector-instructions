import json
import networkx as nx
from typing import Dict, List
from .rvv_disassembler import disassemble_rvv
from dash import html

# Here I'm essentially recreating the graph from the JSON file. 
# In theory we could combine graph creation and element building to avoid this step,
# but this keeps things modular and easier to manage.
def load_graph_from_json(json_file: str) -> nx.DiGraph:

    with open(json_file, 'r') as f:
        data = json.load(f)
    
    graph = nx.DiGraph()
    for element in data['elements']:
        element_data = element.get('data', {})
        
        if 'source' in element_data:  # Edge
            source = element_data['source']
            target = element_data['target']
            register = element_data.get('register')
            graph.add_edge(source, target, register=register)
            
        else:  # Node
            node_id = element_data['id']
            instr = element_data['instruction']
            graph.add_node(node_id, instruction=instr)
    
    return graph

# Calculate positions for the nodes based on dependencies.
# It's necessary to make the graph look more readable.
# def calculate_positions(graph: nx.DiGraph) -> Dict[str, Tuple[int, int]]:
#     """
#     Calculate horizontal and vertical positions based on dependencies.
#     Instructions with no dependencies start at x=0.
#     Dependent instructions are placed to the right of their dependencies.
#     """
#     positions = {}
#     x_positions = {}
#     y_counters = {}
    
#     sorted_nodes = list(nx.topological_sort(graph))
    
#     # TODO: This probably will need to be improved due to late instructions being but at the start.
#     for node_id in sorted_nodes:
#         predecessors = list(graph.predecessors(node_id))
        
#         if not predecessors:
#             x = 0
#         else:
#             max_pred_x = max(x_positions[pred] for pred in predecessors)
#             x = max_pred_x + 1
        
#         x_positions[node_id] = x
        
#         if x not in y_counters:
#             y_counters[x] = 0
#         y = y_counters[x]
#         y_counters[x] += 1
        
#         positions[node_id] = (x, y)
    
#     return positions


def build_elements(json_file: str) -> List[Dict]:
    """Builds Cytoscape elements with labels and positions."""
    
    graph = load_graph_from_json(json_file)
    
    elements = []
    
    # Add nodes with computed labels
    for node_id, data in graph.nodes(data=True):
        instr = data['instruction']
        instr_number = instr.get('number', 0)
        instruction_hex = instr.get('instruction', '0x0')
        instruction_int = int(instruction_hex, 16) if isinstance(instruction_hex, str) else instruction_hex
        disassembled = disassemble_rvv(instruction_int)
        label = f"     {instr_number}\n{disassembled}"
        
        elements.append({
            'data': {
                'id': node_id,
                'label': label,
                'type': instr.get('type'),
                'instruction': instr
            }
        })
    
    # Add edges
    for source, target, edge_data in graph.edges(data=True):
        elements.append({
            'data': {
                'id': f"{source}-{target}",
                'source': source,
                'target': target,
                'register': edge_data.get('register')
            }
        })
    
    return elements


def format_hex_data(data: str, bytes_per_group: int = 2) -> html.Div:
    """Format hex data with spacing every N bytes."""
    if not data or data == 'N/A':
        return html.Span('N/A', style={'color': '#999999'})
    
    groups = []
    for i in range(0, len(data), bytes_per_group * 2):
        groups.append(data[i:i + bytes_per_group * 2])
    
    formatted = ' '.join(groups)
    
    return html.Code(
        formatted,
        style={
            'display': 'block',
            'fontFamily': 'monospace',
            'fontSize': '11px',
            'backgroundColor': '#f0f0f0',
            'padding': '8px',
            'borderRadius': '4px',
            'wordBreak': 'break-all',
            'whiteSpace': 'pre-wrap',
            'lineHeight': '1.6'
        }
    )


def decode_vtype(vtype) -> dict:
    if vtype is None or vtype == 'N/A':
        return {}
    
    try:
        vtype_int = int(vtype, 16) if isinstance(vtype, str) else int(vtype)
    except (ValueError, TypeError):
        return {}
    
    vill = (vtype_int >> 7) & 0x1
    vma = (vtype_int >> 7) & 0x1
    vta = (vtype_int >> 6) & 0x1
    vsew = (vtype_int >> 3) & 0x7
    vlmul = vtype_int & 0x7
    
    sew_map = {0: "8-bit", 1: "16-bit", 2: "32-bit", 3: "64-bit"}
    lmul_map = {0: "1", 1: "2", 2: "4", 3: "8", 5: "1/2", 6: "1/4", 7: "1/8"}
    
    return {
        'vill': 'illegal' if vill else 'legal',
        'vma': 'agnostic' if vma else 'undisturbed',
        'vta': 'agnostic' if vta else 'undisturbed',
        'vsew': sew_map.get(vsew, f"reserved({vsew})"),
        'vlmul': f"{lmul_map.get(vlmul, f'reserved({vlmul})')}"
    }


def decode_vcsr(vcsr) -> dict:
    if vcsr is None or vcsr == 'N/A':
        return {}
    
    try:
        vcsr_int = int(vcsr, 16) if isinstance(vcsr, str) else int(vcsr)
    except (ValueError, TypeError):
        return {}
    
    vxsat = (vcsr_int >> 0) & 0x1
    vxrm = (vcsr_int >> 1) & 0x3
    
    vxrm_map = {0: "rnu (round-to-nearest-up)", 1: "rne (round-to-nearest-even)", 
                2: "rdn (round-down)", 3: "rod (round-to-odd)"}
    
    return {
        'vxsat': 'saturated' if vxsat else 'no saturation',
        'vxrm': vxrm_map.get(vxrm, f"reserved({vxrm})")
    }
