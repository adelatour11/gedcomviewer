from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import tempfile
from collections import defaultdict, deque

try:
    from gedcom.element.individual import IndividualElement
    from gedcom.parser import Parser
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-gedcom==1.1.0"])
    from gedcom.element.individual import IndividualElement
    from gedcom.parser import Parser

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

class FamilyTree:
    def __init__(self):
        self.people = {}
        self.families = {}
        
    def load_gedcom(self, filepath):
        """Parse GEDCOM file and build family relationships"""
        parser = Parser()
        parser.parse_file(filepath)
        elements = parser.get_root_child_elements()
        
        print(f"Parsing {len(elements)} elements...")
        
        # FIRST PASS: Collect all individuals with gender
        for element in elements:
            if isinstance(element, IndividualElement):
                person_id = element.get_pointer()
                name_tuple = element.get_name()
                if name_tuple:
                    given = name_tuple[0] or ""
                    surname = name_tuple[1] or ""
                    name = f"{given} {surname}".strip()
                    if not name or name == " ":
                        name = "Unknown"
                else:
                    name = "Unknown"
                
                birth = ""
                death = ""
                try:
                    birth_data = element.get_birth_data()
                    if birth_data and len(birth_data) > 0 and birth_data[0]:
                        birth = str(birth_data[0])
                except:
                    pass
                try:
                    death_data = element.get_death_data()
                    if death_data and len(death_data) > 0 and death_data[0]:
                        death = str(death_data[0])
                except:
                    pass
                
                # GENDER DETECTION - Multiple methods
                gender = "unknown"
                
                # Method 1: Try is_male/is_female methods
                try:
                    if element.is_male():
                        gender = "male"
                        print(f"✓ Male (is_male): {name}")
                    elif element.is_female():
                        gender = "female"
                        print(f"✓ Female (is_female): {name}")
                except:
                    pass
                
                # Method 2: Look for SEX tag directly in children
                if gender == "unknown":
                    for child in element.get_child_elements():
                        if child.get_tag() == 'SEX':
                            sex_value = child.get_value()
                            if sex_value:
                                sex_upper = sex_value.upper().strip()
                                if sex_upper == 'M':
                                    gender = "male"
                                    print(f"✓ Male (SEX tag): {name}")
                                elif sex_upper == 'F':
                                    gender = "female"
                                    print(f"✓ Female (SEX tag): {name}")
                                break
                
                # Method 3: Check for "1 SEX M" or "1 SEX F" in raw text
                if gender == "unknown":
                    try:
                        raw_text = str(element)
                        if 'SEX M' in raw_text or 'SEX M\n' in raw_text:
                            gender = "male"
                            print(f"✓ Male (raw text): {name}")
                        elif 'SEX F' in raw_text or 'SEX F\n' in raw_text:
                            gender = "female"
                            print(f"✓ Female (raw text): {name}")
                    except:
                        pass
                
                self.people[person_id] = {
                    'id': person_id,
                    'name': name,
                    'birth': birth,
                    'death': death,
                    'gender': gender,
                    'parents': [],
                    'children': [],
                    'spouses': []
                }
        
        print(f"\n{'='*50}")
        print(f"Found {len(self.people)} individuals")
        male_count = sum(1 for p in self.people.values() if p['gender'] == 'male')
        female_count = sum(1 for p in self.people.values() if p['gender'] == 'female')
        unknown_count = len(self.people) - male_count - female_count
        print(f"Gender breakdown: Male={male_count}, Female={female_count}, Unknown={unknown_count}")
        print(f"{'='*50}\n")
        
        # SECOND PASS: Process family relationships and infer gender from family roles
        for element in elements:
            if element.get_tag() == 'FAM':
                family_id = element.get_pointer()
                husband_id = None
                wife_id = None
                children_ids = []
                
                for child in element.get_child_elements():
                    tag = child.get_tag()
                    value = child.get_value()
                    if tag == 'HUSB':
                        husband_id = value
                    elif tag == 'WIFE':
                        wife_id = value
                    elif tag == 'CHIL':
                        children_ids.append(value)
                
                # Store family
                self.families[family_id] = {
                    'id': family_id,
                    'husband_id': husband_id,
                    'wife_id': wife_id,
                    'children_ids': children_ids
                }
                
                # Link spouses and INFER GENDER from family roles
                if husband_id and husband_id in self.people:
                    # Force set gender to male for husband
                    if self.people[husband_id]['gender'] == 'unknown':
                        self.people[husband_id]['gender'] = 'male'
                        print(f"✓ Inferred male from family role: {self.people[husband_id]['name']}")
                    
                    if wife_id and wife_id in self.people:
                        # Force set gender to female for wife
                        if self.people[wife_id]['gender'] == 'unknown':
                            self.people[wife_id]['gender'] = 'female'
                            print(f"✓ Inferred female from family role: {self.people[wife_id]['name']}")
                        
                        if wife_id not in self.people[husband_id]['spouses']:
                            self.people[husband_id]['spouses'].append(wife_id)
                        if husband_id not in self.people[wife_id]['spouses']:
                            self.people[wife_id]['spouses'].append(husband_id)
                
                # Link children to parents
                for child_id in children_ids:
                    if child_id in self.people:
                        if husband_id and husband_id in self.people:
                            if husband_id not in self.people[child_id]['parents']:
                                self.people[child_id]['parents'].append(husband_id)
                            if child_id not in self.people[husband_id]['children']:
                                self.people[husband_id]['children'].append(child_id)
                        if wife_id and wife_id in self.people:
                            if wife_id not in self.people[child_id]['parents']:
                                self.people[child_id]['parents'].append(wife_id)
                            if child_id not in self.people[wife_id]['children']:
                                self.people[wife_id]['children'].append(child_id)
        
        # Final gender report after inference
        male_count_final = sum(1 for p in self.people.values() if p['gender'] == 'male')
        female_count_final = sum(1 for p in self.people.values() if p['gender'] == 'female')
        unknown_count_final = len(self.people) - male_count_final - female_count_final
        print(f"\n{'='*50}")
        print(f"FINAL Gender breakdown after inference:")
        print(f"Male={male_count_final}, Female={female_count_final}, Unknown={unknown_count_final}")
        print(f"{'='*50}\n")
        
        print(f"Found {len(self.families)} families")
        return self
    
    def build_graph_for_d3(self, person_id, direction='ancestors', max_depth=30):
        """Build a DAG (graph) where each person appears once with union nodes for couples"""
        
        nodes_set = set()
        parent_child_map = defaultdict(list)
        child_parent_map = defaultdict(list)
        
        def collect_ancestors(pid, depth, visited):
            if depth > max_depth or pid not in self.people:
                return
            if pid in visited:
                return
            
            visited.add(pid)
            nodes_set.add(pid)
            
            for parent_id in self.people[pid]['parents']:
                if parent_id in self.people:
                    nodes_set.add(parent_id)
                    if pid not in parent_child_map[parent_id]:
                        parent_child_map[parent_id].append(pid)
                    if parent_id not in child_parent_map[pid]:
                        child_parent_map[pid].append(parent_id)
                    collect_ancestors(parent_id, depth + 1, visited)
        
        def collect_descendants(pid, depth, visited):
            if depth > max_depth or pid not in self.people:
                return
            if pid in visited:
                return
            
            visited.add(pid)
            nodes_set.add(pid)
            
            for child_id in self.people[pid]['children']:
                if child_id in self.people:
                    nodes_set.add(child_id)
                    if child_id not in parent_child_map[pid]:
                        parent_child_map[pid].append(child_id)
                    if pid not in child_parent_map[child_id]:
                        child_parent_map[child_id].append(pid)
                    collect_descendants(child_id, depth + 1, visited)
        
        visited = set()
        if direction == 'ancestors':
            collect_ancestors(person_id, 0, visited)
        else:
            collect_descendants(person_id, 0, visited)
        
        # Create union nodes for each unique couple
        union_map = {}
        union_counter = 0
        
        for child_id, parent_ids in child_parent_map.items():
            if len(parent_ids) >= 2:
                couple_key = tuple(sorted(parent_ids))
                if couple_key not in union_map:
                    husband = None
                    wife = None
                    for pid in parent_ids:
                        if self.people[pid]['gender'] == 'male':
                            husband = pid
                        elif self.people[pid]['gender'] == 'female':
                            wife = pid
                    
                    union_map[couple_key] = {
                        'id': f"union_{union_counter}",
                        'husband': husband,
                        'wife': wife,
                        'parents': list(couple_key),
                        'children': []
                    }
                    union_counter += 1
                
                if child_id not in union_map[couple_key]['children']:
                    union_map[couple_key]['children'].append(child_id)
            elif len(parent_ids) == 1:
                parent_id = parent_ids[0]
                single_key = f"single_{parent_id}"
                if single_key not in union_map:
                    union_map[single_key] = {
                        'id': f"union_{union_counter}",
                        'single_parent': parent_id,
                        'parents': [parent_id],
                        'children': []
                    }
                    union_counter += 1
                
                if child_id not in union_map[single_key]['children']:
                    union_map[single_key]['children'].append(child_id)
        
        # Build individual nodes with gender
        nodes = []
        for pid in nodes_set:
            person = self.people[pid]
            nodes.append({
                'id': pid,
                'name': person['name'],
                'birth': person['birth'],
                'death': person['death'],
                'gender': person['gender'],
                'type': 'individual'
            })
        
        # Build union nodes
        union_nodes = []
        for union in union_map.values():
            union_nodes.append({
                'id': union['id'],
                'type': 'union',
                'parents': union['parents'],
                'children': union['children']
            })
        
        # Build edges
        edges = []
        for union in union_map.values():
            union_id = union['id']
            for parent_id in union['parents']:
                edges.append({
                    'source': parent_id,
                    'target': union_id,
                    'type': 'parent-union'
                })
            for child_id in union['children']:
                edges.append({
                    'source': union_id,
                    'target': child_id,
                    'type': 'union-child'
                })
        
        return {
            'nodes': nodes + union_nodes,
            'edges': edges,
            'rootId': person_id
        }
    
    def search_people(self, query):
        """Search for people by name"""
        query_lower = query.lower()
        results = []
        for pid, person in self.people.items():
            if query_lower in person['name'].lower():
                results.append({
                    'id': pid,
                    'name': person['name'],
                    'birth': person['birth'],
                    'death': person['death']
                })
        
        return sorted(results, key=lambda x: x['name'])

tree = FamilyTree()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/load', methods=['POST'])
def load_gedcom():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.ged'):
        return jsonify({'error': 'File must be .ged format'}), 400
    
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    file.save(temp_path)
    
    try:
        global tree
        tree = FamilyTree()
        tree.load_gedcom(temp_path)
        os.remove(temp_path)
        
        roots = [p for p in tree.people.values() if not p['parents']]
        
        return jsonify({
            'success': True,
            'stats': {
                'people': len(tree.people),
                'families': len(tree.families),
                'roots': len(roots)
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search():
    query = request.args.get('q', '').strip()
    if query == '':
        return jsonify(sorted(tree.people.values(), key=lambda x: x['name']))
    results = tree.search_people(query)
    return jsonify(sorted(results, key=lambda x: x['name']))

@app.route('/api/person/<person_id>')
def get_person(person_id):
    if person_id not in tree.people:
        return jsonify({'error': 'Person not found'}), 404
    
    person = tree.people[person_id]
    return jsonify({
        'id': person['id'],
        'name': person['name'],
        'birth': person['birth'],
        'death': person['death'],
        'gender': person['gender'],
        'parents': [{'id': pid, 'name': tree.people[pid]['name']} for pid in person['parents'] if pid in tree.people],
        'children': [{'id': cid, 'name': tree.people[cid]['name']} for cid in person['children'] if cid in tree.people],
        'spouses': [{'id': sid, 'name': tree.people[sid]['name']} for sid in person['spouses'] if sid in tree.people]
    })

@app.route('/api/graph/<person_id>')
def get_graph(person_id):
    direction = request.args.get('direction', 'ancestors')
    depth = request.args.get('depth', 30, type=int)
    depth = min(depth, 30)
    
    graph_data = tree.build_graph_for_d3(person_id, direction, depth)
    
    return jsonify({
        'success': True,
        'nodes': graph_data['nodes'],
        'edges': graph_data['edges'],
        'rootId': person_id,
        'direction': direction
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌳 Family Tree - Pedigree with Union Nodes")
    print("="*60)
    print("\n🚀 Starting server at: http://localhost:5000")
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
