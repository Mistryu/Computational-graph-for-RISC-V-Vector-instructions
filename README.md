# Computational Graph for RISC-V Vector Instructions

A visualization tool for RISC-V Vector Extension instruction traces, building dependency graphs and providing an interactive UI for analysis.

## Installation

### 1. Clone the Repository

```bash
cd /home/mistryu/Documents/TUM/Thesis/code
git clone <repository-url> trace_visualisation
cd trace_visualisation
```

### 2. Create Python Virtual Environment

```bash
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install the Package

```bash
pip install -e .
```

This will install:
- dash (>=3.4.0)
- dash-cytoscape (>=1.0.2)
- plotly (>=6.5.2)
- networkx (>=3.6.1)

## Usage

### Step 1: Generate Computation Graph

First, generate the computation graph from your vector instruction trace:

```bash
# Make sure you have a vector_trace.json file in the root directory I'm gonna fix it soon
graph-creation
```

This will:
- Read `vector_trace.json` (or the file specified in `graph_creation.py`)
- Build the dependency graph
- Export to `cytoscape_graph.json`

### Step 2: Launch Visualization UI

```bash
trace-ui
```

The web interface will open at `http://127.0.0.1:8050/`

## Switching Graph Layouts

Edit `src/trace_visualisation/UI/app.py` and replace the `layout` configuration with one of the configs I have commented out. 
