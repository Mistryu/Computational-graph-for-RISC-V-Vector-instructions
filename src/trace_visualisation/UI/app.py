import dash
from dash import html, callback, Input, Output
import dash_cytoscape as cyto
from pathlib import Path
from trace_visualisation.helper import build_elements, format_hex_data
from .style import CYTOSCAPE_STYLESHEET, LAYOUT_STYLES

cyto.load_extra_layouts()

app = dash.Dash(__name__)

#TODO fix this to request the file when running the program 
base_dir = Path(__file__).resolve().parents[3]
json_path = base_dir / "cytoscape_graph.json"
elements = build_elements(str(json_path))

print(f"Loading graph from: {json_path}")
print(f"File exists: {json_path.exists()}")
print(f"Loaded {len(elements)} elements")

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
                    }
                },
                stylesheet=CYTOSCAPE_STYLESHEET,
                userPanningEnabled=True,
                userZoomingEnabled=True,
                boxSelectionEnabled=False,
                minZoom=0.1,
                maxZoom=3.0
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
    
    vec_section = [html.H4('Vector Registers', style={'marginBottom': '10px'})]

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
    
    # Only show vector section if there are vector registers
    if len(vec_section) > 1:
        details.extend(vec_section)
    
    # Add RVV state at time of execution
    rvv_state = instr.get('rvv_state', {})
    if rvv_state and any(rvv_state.values()):
        details.extend([
            html.Hr(),
            html.Div([
                html.H4('RVV State (at execution)', style={'marginBottom': '10px'}),
                html.P([html.Strong('VL: '), str(rvv_state.get('vl', 'N/A'))]),
                html.P([html.Strong('VTYPE: '), str(rvv_state.get('vtype', 'N/A'))]),
                html.P([html.Strong('VSTART: '), str(rvv_state.get('vstart', 'N/A'))]),
                html.P([html.Strong('VCSR: '), str(rvv_state.get('vcsr', 'N/A'))]),
                html.P([html.Strong('VLENB: '), str(rvv_state.get('vlenb', 'N/A'))]),
            ])
        ])
    
    return html.Div(details, style={'padding': '10px'})


def main() -> None:
    app.run(debug=True)

if __name__ == '__main__':
    main()
