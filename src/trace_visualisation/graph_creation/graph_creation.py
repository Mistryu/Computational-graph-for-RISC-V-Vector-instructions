import json
import networkx as nx
from typing import Dict, List, Tuple, Set
from pathlib import Path
import sys
import argparse

class ComputationGraphBuilder:
    def __init__(self, aggregate_loops: bool = False):
        self.graph = nx.DiGraph()
        self.register_producers = {}
        self.aggregate_loops = aggregate_loops
        self.pc_map = {}
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
            self.update_rvv_state(instr)
            
            instr_with_state = instr.copy()
            instr_with_state['rvv_state'] = self.rvv_state.copy()
            
            if self.aggregate_loops:
                pc = instr.get('pc', f"unknown_{instr['number']}")
                
                if pc in self.pc_map:
                    node_id = self.pc_map[pc]
                    existing_instr = self.graph.nodes[node_id]['instruction']
                    
                    if 'iterations' not in existing_instr:
                        existing_instr['iterations'] = [existing_instr.copy()]
                        existing_instr['iteration_count'] = 1
                    
                    existing_instr['iterations'].append(instr_with_state)
                    existing_instr['iteration_count'] += 1
                    
                    self.graph.nodes[node_id]['instruction'] = existing_instr
                else:
                    node_id = f"pc_{pc}"
                    self.pc_map[pc] = node_id
                    self.graph.add_node(node_id, instruction=instr_with_state)
            else:
                node_id = f"instr_{instr['number']}"
                self.graph.add_node(node_id, instruction=instr_with_state)
            
            sources, destinations = self.extract_vector_registers(instr)
            
            for src_reg in sources:
                if src_reg in self.register_producers:
                    producer_id = self.register_producers[src_reg]
                    if producer_id != node_id:
                        self.graph.add_edge(producer_id, node_id, register=src_reg)
            
            for dest_reg in destinations:
                self.register_producers[dest_reg] = node_id
        
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
        
        json_data = {'elements': elements}
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
    
def main() -> None:
    parser = argparse.ArgumentParser(
        description='Build a graph from RISC-V vector instruction trace',
        epilog='''
Examples:
  %(prog)s                              # Load first 3000 elements (all types from vector_trace.json)
  %(prog)s -s 1000 -e 2000              # Load instructions 1000-2000
  %(prog)s -t reg ls                    # Only show register and load/store instructions
  %(prog)s -s 0 -e 500 -t reg           # First 500 register instructions
  %(prog)s my_graph.json -s 0 -e 1000   # Load first 1000 from custom file
  %(prog)s trace.json --aggregate-loops # Aggregate loops by PC
  %(prog)s trace.json -a -o loops.json  # Aggregate loops, custom output

Graph modes:
  Standard: Each instruction execution is a separate node
  Aggregate: Instructions with same PC are merged into one node with iteration data
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default='vector_trace.json',
        help='Input JSON trace file (default: vector_trace.json)'
    )
    parser.add_argument(
        '-o', '--output',
        default='cytoscape_graph.json',
        help='Output graph JSON file (default: cytoscape_graph.json)'
    )
    parser.add_argument(
        '-a', '--aggregate-loops',
        action='store_true',
        help='Aggregate loop iterations by PC (default: False)'
    )
    
    args = parser.parse_args()
    
    json_file = args.input_file
    output_file = args.output
    
    if not Path(json_file).exists():
        print(f"Error: Input file '{json_file}' not found", file=sys.stderr)
        sys.exit(1)
    
    builder = ComputationGraphBuilder(aggregate_loops=args.aggregate_loops)
    
    try:
        with open(json_file, 'r') as f:
            trace = json.load(f)
        
        print(f"Loading trace from: {json_file}")
        if args.aggregate_loops:
            print("Mode: Aggregating loops by program counter")
        else:
            print("Mode: Standard (one node per instruction)")
        
        builder.build_graph(trace)
        builder.to_json(output_file)
        
        print(f"Graph has {builder.get_graph().number_of_nodes()} nodes and {builder.get_graph().number_of_edges()} edges")
        print(f"Exported to {output_file}")
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{json_file}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        
if __name__ == "__main__":
    main()