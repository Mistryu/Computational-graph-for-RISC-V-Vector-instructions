import json
import networkx as nx
from typing import Dict, List, Tuple, Set
from pathlib import Path

class ComputationGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.register_producers = {}
        self.rvv_state = {
            'vl': None,
            'vtype': None,
            'vstart': None,
            'vcsr': None,
            'vlenb': None
        }

    def extract_vector_registers(self, instr: Dict) -> Tuple[Set[int], Set[int]]:
        sources = set()
        destinations = set()
        
        if 'vd' in instr and instr['vd'] is not None:
            destinations.add(instr['vd'])
        
        if 'vs1' in instr and instr['vs1'] is not None:
            sources.add(instr['vs1'])
        if 'vs2' in instr and instr['vs2'] is not None:
            sources.add(instr['vs2'])
        
        return sources, destinations
    
    def update_rvv_state(self, instr: Dict) -> None:
        """Update RVV state if instruction is a CSR instruction (type 2)."""
        if instr.get('type') == 2:
            if 'vl' in instr:
                self.rvv_state['vl'] = instr['vl']
            if 'vtype' in instr:
                self.rvv_state['vtype'] = instr['vtype']
            if 'vstart' in instr:
                self.rvv_state['vstart'] = instr['vstart']
            if 'vcsr' in instr:
                self.rvv_state['vcsr'] = instr['vcsr']
            if 'vlenb' in instr:
                self.rvv_state['vlenb'] = instr['vlenb']

    def build_graph(self, trace: List[Dict]) -> nx.DiGraph:
        for instr in trace:
            instr_id = f"instr_{instr['number']}" # Later change to PC and identify loops 
            
            self.update_rvv_state(instr)
            
            instr_with_state = instr.copy()
            instr_with_state['rvv_state'] = self.rvv_state.copy()
            
            self.graph.add_node(instr_id, instruction=instr_with_state)
            
            sources, destinations = self.extract_vector_registers(instr)
            
            # Add edges from producer instructions
            for src_reg in sources:
                if src_reg in self.register_producers:
                    producer_id = self.register_producers[src_reg]
                    self.graph.add_edge(producer_id, instr_id, register=src_reg)
            
            # Update register producers map
            for dest_reg in destinations:
                self.register_producers[dest_reg] = instr_id
        
        return self.graph
    
    
    def get_graph(self) -> nx.DiGraph:
        return self.graph
    
    
    def to_json(self, output_file: str) -> None:
        elements = []
        
        # Add nodes
        for node_id in self.graph.nodes():
            instr = self.graph.nodes[node_id]['instruction']
            elements.append({
                'data': {
                    'id': node_id,
                    'instruction': instr
                }
            })
        
        # Add edges
        for source, target, data in self.graph.edges(data=True):
            elements.append({
                'data': {
                    'id': f"{source}-{target}",
                    'source': source,
                    'target': target,
                    'register': data.get('register')
                }
            })
        
        # Saving to JSON file
        json_data = {'elements': elements}
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
    
def main() -> None:
    #json_file = "vector_trace.json"
    #json_file = "vector_trace_simple.json"
    json_file = "vector_trace_loop.json"
    #json_file = "vector_trace_huge.json"
    output_file = "cytoscape_graph.json"
    
    builder = ComputationGraphBuilder()
    
    with open(json_file, 'r') as f:
        trace = json.load(f)
            
    builder.build_graph(trace)
    builder.to_json(output_file)
    
    print(f"Graph has {builder.get_graph().number_of_nodes()} nodes and {builder.get_graph().number_of_edges()} edges")
    print(f"Exported to {output_file}")

if __name__ == "__main__":
    main()