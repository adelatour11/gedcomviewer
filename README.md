# gedcomviewer
**Interactive Family Tree Visualizer**

An interactive, web-based family tree visualization tool that parses GEDCOM files and displays ancestral or descendant relationships with an intuitive, draggable interface. Features automatic layout algorithms, connection finding between individuals, and beautiful gender-coded nodes.

<img width="3839" height="1918" alt="image" src="https://github.com/user-attachments/assets/27459c7d-1f28-4b6e-9b4d-0d54a1136866" />


**Features**

- GEDCOM Import - Load standard GEDCOM genealogy files (.ged)
- Support Tree collapse
- Dual View Modes - Toggle between Ancestors (pedigree) and Descendants views
- Smart Layout - Automatic hierarchical positioning with union nodes for couples
- Person Search - Quick search to find and center any individual
- Connection Finder - Find and highlight shortest path between any two individuals
- Interactive Controls - Drag nodes, zoom/pan, reset layout, fit to view
- Generation Depth - Control how many generations to display
- Sidebar Details - Click any person to view detailed information and relationships


**Prerequisites**

    Python 3.7 or higher
    pip (Python package manager)

**Installation**

Clone the repository:

    git clone https://github.com/yourusername/pedigree-tree.git
    cd pedigree-tree

Install dependencies:

    pip install flask flask-cors python-gedcom

Run the application:

    python app.py

Open your browser and navigate to:

    http://localhost:5000
