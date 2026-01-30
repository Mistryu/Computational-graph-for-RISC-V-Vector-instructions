import dash
from dash import html, callback, Input, Output
import dash_cytoscape as cyto
from pathlib import Path
import argparse
import sys
from trace_visualisation.helper import build_elements, format_hex_data, decode_vtype, decode_vcsr
from .style import CYTOSCAPE_STYLESHEET, LAYOUT_STYLES

cyto.load_extra_layouts()


def create_app(graph_file: str, start: int = 0, end: int = None):
    app = dash.Dash(__name__)
    
    if not Path(graph_file).exists():
        print(f"Error: Graph file '{graph_file}' not found", file=sys.stderr)
        print(f"Please run 'graph-creation' first to generate the graph.", file=sys.stderr)
        sys.exit(1)
    
    try:
        elements = build_elements(graph_file, start=start, end=end)
        print(f"Loading graph from: {graph_file}")
        print(f"Loaded {len(elements)} elements")
    except Exception as e:
        print(f"Error loading graph: {e}", file=sys.stderr)
        sys.exit(1)

    # Check graph size and adjust settings
    num_elements = len(elements)
    is_large_graph = num_elements > 1000
    
    if is_large_graph:
        print(f"Warning: Large graph detected ({num_elements} elements)")
        print(f"Performance optimizations enabled")

    # Pretty good:
    # dagre
    # klay so far my favorite

    # Medium:
    # breathfirst

    # Bad:
    # cose-bilkent

    # Just past one of those in the layout field to check how it works
    # KLAY:
    # {
    #     'name': 'klay',
    #     'klay': {
    #         'direction': 'RIGHT',
    #         'spacing': 50,
    #         'nodePlacement': 'LINEAR_SEGMENTS'
    #     }
    # }
    #
    # DAGRE:
    # {
    #     'name': 'dagre',
    #     'rankDir': 'LR',
    #     'nodeSep': 100,
    #     'rankSep': 150
    # }
    #
    # BREADTHFIRST:
    # {
    #     'name': 'breadthfirst',
    #     'directed': True,
    #     'spacingFactor': 1.5,
    #     'avoidOverlap': True
    # }

    app.layout = html.Div([
        html.Div([
            # Left side - Graph
            html.Div([
                cyto.Cytoscape(
                    id='computation-graph',
                    elements=elements,
                    style=LAYOUT_STYLES['cytoscape'],
                    layout={
                        'name': 'klay',
                        'klay': {
                            'direction': 'RIGHT',
                            'spacing': 50,
                            'nodePlacement': 'LINEAR_SEGMENTS'
                        },
                        'animate': False,
                        'fit': True
                    },
                    stylesheet=CYTOSCAPE_STYLESHEET,
                    userPanningEnabled=True,
                    userZoomingEnabled=True,
                    boxSelectionEnabled=False,
                    minZoom=0.1,
                    maxZoom=3.0,
                    wheelSensitivity=1,
                    responsive=True,
                )
            ], style=LAYOUT_STYLES['graph_panel']),
            
            # Right side - Details panel
            html.Div([
                html.Div(id='details-panel', style=LAYOUT_STYLES['details_content'])
            ], style=LAYOUT_STYLES['details_panel'])
        ], style=LAYOUT_STYLES['flex_wrapper'])
    ], style=LAYOUT_STYLES['container'])


    @callback(
        Output('details-panel', 'children'),
        Input('computation-graph', 'selectedNodeData')
    )
    
    def update_details_panel(selected_nodes):
        if not selected_nodes:
            return html.Div([
                html.H3('Select an instruction to view details', style={'color': '#999999'})
            ], style={'padding': '20px'})
        
        node = selected_nodes[0]
        instr = node.get('instruction', {})
        instr_type = instr.get('type')
        label = node.get('label', '')
        disassembled = label.split('\n', 1)[1] if '\n' in label else 'UNKNOWN'
        
        # Build details content
        details = [
            html.H3(disassembled, style={'marginTop': 0, 'fontFamily': 'monospace', 'fontSize': '16px'}),
            html.Hr(),
            
            html.Div([
                html.H4('Instruction Info', style={'marginBottom': '10px'}),
                html.P([html.Strong('Number: '), str(instr.get('number', 'N/A'))]),
                html.P([html.Strong('PC: '), instr.get('pc', 'N/A')]),
                html.P([html.Strong('Instruction: '), instr.get('instruction', 'N/A')]),
            ]),
            
            html.Hr(),
        ]
        
        # Scalar Registers section (for CSR and load/store)
        scalar_section = []
        
        # For CSR instructions (type 2): show rd, rs1, rs2
        if instr_type == 2:
            scalar_section.append(html.H4('Scalar Registers', style={'marginBottom': '10px'}))
            
            if instr.get('rd') is not None:
                scalar_section.append(html.Div([
                    html.P([html.Strong(f"x{instr.get('rd')} (rd destination):")], style={'marginBottom': '5px'}),
                    format_hex_data(instr.get('rd_value', 'N/A'), bytes_per_group=1)
                ], style={'marginBottom': '15px'}))
            
            if instr.get('rs1') is not None:
                scalar_section.append(html.Div([
                    html.P([html.Strong(f"x{instr.get('rs1')} (rs1 source 1):")], style={'marginBottom': '5px'}),
                    format_hex_data(instr.get('rs1_value', 'N/A'), bytes_per_group=1)
                ], style={'marginBottom': '15px'}))
            
            if instr.get('rs2') is not None:
                scalar_section.append(html.Div([
                    html.P([html.Strong(f"x{instr.get('rs2')} (rs2 source 2):")], style={'marginBottom': '5px'}),
                    format_hex_data(instr.get('rs2_value', 'N/A'), bytes_per_group=1)
                ], style={'marginBottom': '15px'}))
        
        # For load/store instructions (type 3): show rs1
        elif instr_type == 3:
            if instr.get('rs1') is not None:
                scalar_section.append(html.H4('Scalar Registers', style={'marginBottom': '10px'}))
                scalar_section.append(html.Div([
                    html.P([html.Strong(f"x{instr.get('rs1')} (rs1 source addr):")], style={'marginBottom': '5px'}),
                    format_hex_data(instr.get('rs1_value', 'N/A'), bytes_per_group=1)
                ], style={'marginBottom': '15px'}))
        
        if scalar_section:
            details.extend(scalar_section)
        
        vec_section = []
        vec_section.append(html.H4('Vector Registers', style={'marginBottom': '10px'}))

        # Add VD if present
        if 'vd' in instr and instr.get('vd') is not None:
            vec_section.append(
                html.Div([
                    html.P([html.Strong(f"v{instr.get('vd')} (vd destination):")], style={'marginBottom': '5px'}),
                        format_hex_data(instr.get('vd_data', 'N/A'))
                            ], style={'marginBottom': '15px'}))
        
        # Add VS1 if present
        if 'vs1' in instr and instr.get('vs1') is not None:
            vec_section.append(html.Div([
                html.P([html.Strong(f"v{instr.get('vs1')} (vs1 source 1):")], style={'marginBottom': '5px'}),
                        format_hex_data(instr.get('vs1_data', 'N/A'))
                            ], style={'marginBottom': '15px'}))
        
        # Add VS2 if present
        if 'vs2' in instr and instr.get('vs2') is not None:
            vec_section.append(
                html.Div([
                    html.P([html.Strong(f"v{instr.get('vs2')} (vs2 source 2):")], style={'marginBottom': '5px'}),
                        format_hex_data(instr.get('vs2_data', 'N/A'))
                            ], style={'marginBottom': '15px'}))
        
        if len(vec_section) > 1:
            details.extend(vec_section)
        
        # Add RVV state at time of execution with decoded fields
        rvv_state = instr.get('rvv_state', {})
        if rvv_state and any(rvv_state.values()):
            vtype_decoded = decode_vtype(rvv_state.get('vtype'))
            vcsr_decoded = decode_vcsr(rvv_state.get('vcsr'))
            
            rvv_section = [
                html.Hr(),
                html.H4('RVV State (at execution)', style={'marginBottom': '10px'}),
                
                # VL
                html.P([html.Strong('VL: '), 
                       str(rvv_state.get('vl', 'N/A'))],
                       style={'marginBottom': '8px'}),
                
                # VTYPE
                html.Div([
                    html.P([html.Strong('VTYPE: '), str(rvv_state.get('vtype', 'N/A'))]),
                    html.Ul([
                        html.Li(f"vill: {vtype_decoded.get('vill', 'N/A')}"),
                        html.Li(f"vma: {vtype_decoded.get('vma', 'N/A')}"),
                        html.Li(f"vta: {vtype_decoded.get('vta', 'N/A')}"),
                        html.Li(f"vsew: {vtype_decoded.get('vsew', 'N/A')}"),
                        html.Li(f"vlmul: {vtype_decoded.get('vlmul', 'N/A')}")
                    ], style={'marginLeft': '0px', 'fontSize': '16px', 'color': "#030303"})
                ], style={'marginBottom': '8px'}) if vtype_decoded else None,
                
                # VSTART
                html.P([html.Strong('VSTART: '), 
                       str(rvv_state.get('vstart', 'N/A'))],
                       style={'marginBottom': '8px'}),
                
                # VCSR
                html.Div([
                    html.P([html.Strong('VCSR: '), str(rvv_state.get('vcsr', 'N/A'))]),
                    html.Ul([
                        html.Li(f"vxsat (fixed-point saturation): {vcsr_decoded.get('vxsat', 'N/A')}"),
                        html.Li(f"vxrm (rounding mode): {vcsr_decoded.get('vxrm', 'N/A')}")
                    ], style={'marginLeft': '0px', 'fontSize': '16px', 'color': "#000000"})
                ], style={'marginBottom': '8px'}) if vcsr_decoded else None,
                
                # VLENB
                html.P([html.Strong('VLENB (Vector register length in bytes): '), 
                       str(rvv_state.get('vlenb', 'N/A'))],
                       style={'marginBottom': '8px'}),
            ]
            
            rvv_section = [item for item in rvv_section if item is not None]
            details.extend([html.Div(rvv_section)])
        
        return html.Div(details, style={'padding': '10px'})
    
    return app


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Interactive visualization UI for RISC-V vector instruction computation graph',
        epilog='''
Examples:
  %(prog)s                              # Load first 3000 elements
  %(prog)s -s 1000 -e 2000              # Load instructions 1000-2000
  %(prog)s -s 3000                      # Load instructions 3000-6000
  %(prog)s my_graph.json -s 0 -e 1000   # Load first 1000 from custom file
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default='cytoscape_graph.json',
        help='Input graph JSON file (default: cytoscape_graph.json)'
    )
    parser.add_argument(
        '-s', '--start',
        type=int,
        default=0,
        help='Starting instruction number (default: 0)'
    )
    parser.add_argument(
        '-e', '--end',
        type=int,
        default=None,
        help='Ending instruction number (default: None, loads up to max_elements)'
    )
    
    args = parser.parse_args()
    
    if args.start < 0:
        print("Error: start must be >= 0", file=sys.stderr)
        sys.exit(1)
    
    if args.end is not None and args.end <= args.start:
        print("Error: end must be greater than start", file=sys.stderr)
        sys.exit(1)
    
    app = create_app(args.input_file, start=args.start, end=args.end)
    app.run(debug=True)


if __name__ == '__main__':
    main()
