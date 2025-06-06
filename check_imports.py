#!/usr/bin/env python3
"""
Dependency Scanner for LLM Code Reviewer
Scans all Python files to find imported packages and checks for missing dependencies.
"""

import os
import re
import ast
import sys
import importlib.util
from pathlib import Path
from collections import defaultdict

# Known standard library modules (partial list - most common ones)
STDLIB_MODULES = {
    'os', 'sys', 'json', 're', 'ast', 'io', 'time', 'datetime', 'typing', 
    'pathlib', 'collections', 'itertools', 'functools', 'traceback',
    'logging', 'argparse', 'subprocess', 'threading', 'multiprocessing',
    'urllib', 'http', 'xml', 'email', 'hashlib', 'base64', 'uuid',
    'warnings', 'importlib', 'pkgutil', 'inspect', 'copy', 'pickle',
    'abc', 'dataclasses', 'fnmatch'  # Added commonly used stdlib modules
}

# Internal project modules that should be excluded
INTERNAL_MODULES = {
    'core', 'services', 'utils', 'libs', 'llms', 'base'
}

class ImportScanner:
    def __init__(self, source_dir="src"):
        self.source_dir = source_dir
        self.imports = defaultdict(set)
        self.missing_deps = set()
        self.available_deps = set()
        
    def scan_file(self, filepath):
        """Scan a single Python file for imports."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the AST to find imports
            tree = ast.parse(content, filename=filepath)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        self.imports[filepath].add(module_name)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        # Skip relative imports (starting with .)
                        if not module_name.startswith('.'):
                            self.imports[filepath].add(module_name)
                            
        except Exception as e:
            print(f"⚠️ Error parsing {filepath}: {e}")
    
    def scan_directory(self):
        """Scan all Python files in the source directory."""
        print(f"🔍 Scanning {self.source_dir} for import statements...")
        
        for root, dirs, files in os.walk(self.source_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    self.scan_file(filepath)
                    
        print(f"📁 Scanned {len(self.imports)} Python files")
    
    def get_all_external_imports(self):
        """Get all unique external imports across all files."""
        all_imports = set()
        for imports in self.imports.values():
            all_imports.update(imports)
            
        # Filter out standard library modules, local imports, and internal modules
        external_imports = set()
        for imp in all_imports:
            if (imp not in STDLIB_MODULES and 
                imp not in INTERNAL_MODULES and
                not imp.startswith('src')):
                external_imports.add(imp)
                
        return external_imports
    
    def check_import_availability(self, import_name):
        """Check if an import is available in the current environment."""
        try:
            spec = importlib.util.find_spec(import_name)
            return spec is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False
    
    def analyze_dependencies(self):
        """Analyze which dependencies are missing."""
        external_imports = self.get_all_external_imports()
        
        print(f"\n📦 Found {len(external_imports)} external imports:")
        
        for imp in sorted(external_imports):
            if self.check_import_availability(imp):
                self.available_deps.add(imp)
                print(f"   ✅ {imp}")
            else:
                self.missing_deps.add(imp)
                print(f"   ❌ {imp} (MISSING)")
                
    def generate_suggestions(self):
        """Generate suggestions for missing dependencies."""
        if not self.missing_deps:
            print("\n🎉 All dependencies are available!")
            return
            
        print(f"\n⚠️ Found {len(self.missing_deps)} missing dependencies:")
        
        # Common package name mappings
        package_mapping = {
            'github': 'PyGithub',
            'yaml': 'PyYAML',
            'jwt': 'PyJWT',
            'PIL': 'Pillow',
            'cv2': 'opencv-python',
            'sklearn': 'scikit-learn',
            'bs4': 'beautifulsoup4',
            'redis': 'redis',
            'psycopg2': 'psycopg2-binary',
        }
        
        print("\n💡 Suggested packages to add to requirements.txt:")
        for dep in sorted(self.missing_deps):
            suggested_name = package_mapping.get(dep, dep)
            print(f"   {suggested_name}")
            
    def check_requirements_file(self):
        """Check what's already in requirements.txt."""
        req_file = "requirements.txt"
        if not os.path.exists(req_file):
            print(f"⚠️ No {req_file} found")
            return set()
            
        existing_packages = set()
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before == or >= etc.)
                    package_name = re.split('[><=!]', line)[0].strip()
                    existing_packages.add(package_name.lower())
                    
        print(f"\n📋 Current requirements.txt has {len(existing_packages)} packages:")
        for pkg in sorted(existing_packages):
            print(f"   • {pkg}")
            
        return existing_packages
    
    def run_analysis(self):
        """Run the complete dependency analysis."""
        print("🔍 LLM Code Reviewer Dependency Scanner")
        print("=" * 60)
        
        self.scan_directory()
        self.analyze_dependencies()
        existing_packages = self.check_requirements_file()
        
        # Check if missing deps are actually in requirements.txt with different names
        print(f"\n🔄 Cross-referencing with requirements.txt...")
        truly_missing = set()
        
        for dep in self.missing_deps:
            # Check various forms of the package name
            variations = [dep, dep.lower(), dep.replace('_', '-')]
            found = False
            
            for var in variations:
                if var in existing_packages:
                    print(f"   ✅ {dep} → found as '{var}' in requirements.txt")
                    found = True
                    break
                    
            if not found:
                truly_missing.add(dep)
                
        if truly_missing:
            print(f"\n❌ Truly missing dependencies ({len(truly_missing)}):")
            for dep in sorted(truly_missing):
                print(f"   • {dep}")
                
            self.generate_suggestions()
        else:
            print("\n🎉 All dependencies are properly covered!")
            
        print(f"\n📊 Summary:")
        print(f"   • External imports found: {len(self.get_all_external_imports())}")
        print(f"   • Available in environment: {len(self.available_deps)}")
        print(f"   • Missing from environment: {len(self.missing_deps)}")
        print(f"   • Packages in requirements.txt: {len(existing_packages)}")
        print(f"   • Truly missing: {len(truly_missing) if 'truly_missing' in locals() else 'N/A'}")

if __name__ == "__main__":
    scanner = ImportScanner()
    scanner.run_analysis() 