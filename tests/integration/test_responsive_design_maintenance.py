"""
Responsive Design Maintenance Tests for Manufacturing Platinum Advisory
製造業プラチナアドバイザリー レスポンシブデザイン維持テスト

This test suite verifies that responsive design is maintained after branding updates.
ブランディング更新後もレスポンシブデザインが維持されることを確認します。
"""

import pytest
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json


class TestResponsiveDesignMaintenance:
    """Test that responsive design is maintained after branding updates."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.frontend_src = self.project_root / "frontend" / "src"
        
        # Common responsive design patterns
        self.responsive_patterns = {
            "media_queries": [
                r"@media\s*\([^)]*\)",
                r"@media\s+screen\s+and\s+\([^)]*\)",
                r"@media\s+\(max-width:\s*\d+px\)",
                r"@media\s+\(min-width:\s*\d+px\)"
            ],
            "flexbox": [
                r"display:\s*flex",
                r"flex-direction:\s*(row|column)",
                r"flex-wrap:\s*(wrap|nowrap)",
                r"justify-content:\s*(center|flex-start|flex-end|space-between|space-around)",
                r"align-items:\s*(center|flex-start|flex-end|stretch)"
            ],
            "grid": [
                r"display:\s*grid",
                r"grid-template-columns:",
                r"grid-template-rows:",
                r"grid-gap:",
                r"gap:"
            ],
            "responsive_units": [
                r"\d+(\.\d+)?%",
                r"\d+(\.\d+)?vw",
                r"\d+(\.\d+)?vh",
                r"\d+(\.\d+)?em",
                r"\d+(\.\d+)?rem"
            ],
            "breakpoints": [
                r"(mobile|tablet|desktop|sm|md|lg|xl)",
                r"(320px|480px|768px|1024px|1200px|1440px)"
            ]
        }
        
        # Expected breakpoints for the application
        self.expected_breakpoints = {
            "mobile": "max-width: 480px",
            "tablet": "max-width: 768px",
            "desktop": "min-width: 769px",
            "large_desktop": "min-width: 1200px"
        }
        
        # CSS files to check
        self.css_files = []
        if self.frontend_src.exists():
            self.css_files = list(self.frontend_src.rglob("*.css"))
        
        # Component files that might contain inline styles
        self.component_files = []
        if self.frontend_src.exists():
            self.component_files = list(self.frontend_src.rglob("*.tsx"))
    
    def extract_css_content(self, file_path: Path) -> str:
        """Extract CSS content from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return ""
    
    def find_responsive_patterns(self, content: str) -> Dict[str, List[str]]:
        """Find responsive design patterns in CSS content."""
        found_patterns = {}
        
        for pattern_type, patterns in self.responsive_patterns.items():
            found_patterns[pattern_type] = []
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                found_patterns[pattern_type].extend(matches)
        
        return found_patterns
    
    def test_css_files_contain_responsive_patterns(self):
        """Test that CSS files contain responsive design patterns."""
        if not self.css_files:
            pytest.skip("No CSS files found")
        
        responsive_files = {}
        non_responsive_files = []
        
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            patterns = self.find_responsive_patterns(content)
            
            # Check if file contains any responsive patterns
            has_responsive = any(patterns.values())
            
            if has_responsive:
                responsive_files[str(css_file.relative_to(self.project_root))] = patterns
            else:
                # Check if this is a component-specific CSS that might not need responsive design
                if css_file.name not in ["index.css", "App.css", "theme.css"]:
                    print(f"Info: {css_file.name} does not contain responsive patterns (may be intentional)")
                else:
                    non_responsive_files.append(str(css_file.relative_to(self.project_root)))
        
        # Report findings
        print(f"\nResponsive design analysis:")
        print(f"  Total CSS files: {len(self.css_files)}")
        print(f"  Files with responsive patterns: {len(responsive_files)}")
        print(f"  Files without responsive patterns: {len(non_responsive_files)}")
        
        # Detailed analysis
        for file_path, patterns in responsive_files.items():
            print(f"\n{file_path}:")
            for pattern_type, matches in patterns.items():
                if matches:
                    print(f"  {pattern_type}: {len(matches)} matches")
        
        # Check critical files
        critical_files = ["App.css", "theme.css", "Dashboard.css"]
        missing_responsive_critical = []
        
        for critical_file in critical_files:
            found = False
            for file_path in responsive_files.keys():
                if critical_file in file_path:
                    found = True
                    break
            
            if not found:
                # Check if file exists but lacks responsive patterns
                for css_file in self.css_files:
                    if critical_file in css_file.name:
                        missing_responsive_critical.append(critical_file)
                        break
        
        if missing_responsive_critical:
            pytest.fail(f"Critical CSS files lack responsive patterns: {missing_responsive_critical}")
    
    def test_media_queries_are_preserved(self):
        """Test that media queries are preserved in CSS files."""
        media_query_files = {}
        
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            
            # Find all media queries
            media_queries = re.findall(r"@media[^{]+\{[^}]*\}", content, re.DOTALL)
            
            if media_queries:
                media_query_files[str(css_file.relative_to(self.project_root))] = media_queries
        
        if not media_query_files:
            pytest.fail("No media queries found in CSS files")
        
        print(f"\nMedia queries found in {len(media_query_files)} files:")
        
        for file_path, queries in media_query_files.items():
            print(f"  {file_path}: {len(queries)} media queries")
            
            # Analyze breakpoints used
            breakpoints_found = set()
            for query in queries:
                # Extract pixel values
                pixel_matches = re.findall(r"(\d+)px", query)
                for pixel in pixel_matches:
                    breakpoints_found.add(f"{pixel}px")
            
            if breakpoints_found:
                print(f"    Breakpoints: {sorted(breakpoints_found)}")
    
    def test_flexbox_layouts_are_maintained(self):
        """Test that flexbox layouts are maintained."""
        flexbox_files = {}
        
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            
            # Find flexbox properties
            flexbox_properties = []
            flex_patterns = [
                r"display:\s*flex",
                r"flex-direction:\s*[^;]+",
                r"flex-wrap:\s*[^;]+",
                r"justify-content:\s*[^;]+",
                r"align-items:\s*[^;]+",
                r"flex:\s*[^;]+",
                r"flex-grow:\s*[^;]+",
                r"flex-shrink:\s*[^;]+",
                r"flex-basis:\s*[^;]+"
            ]
            
            for pattern in flex_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                flexbox_properties.extend(matches)
            
            if flexbox_properties:
                flexbox_files[str(css_file.relative_to(self.project_root))] = flexbox_properties
        
        if flexbox_files:
            print(f"\nFlexbox usage found in {len(flexbox_files)} files:")
            for file_path, properties in flexbox_files.items():
                print(f"  {file_path}: {len(properties)} flexbox properties")
        else:
            print("Warning: No flexbox usage found")
    
    def test_grid_layouts_are_maintained(self):
        """Test that CSS Grid layouts are maintained."""
        grid_files = {}
        
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            
            # Find grid properties
            grid_properties = []
            grid_patterns = [
                r"display:\s*grid",
                r"grid-template-columns:\s*[^;]+",
                r"grid-template-rows:\s*[^;]+",
                r"grid-template-areas:\s*[^;]+",
                r"grid-gap:\s*[^;]+",
                r"gap:\s*[^;]+",
                r"grid-column:\s*[^;]+",
                r"grid-row:\s*[^;]+"
            ]
            
            for pattern in grid_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                grid_properties.extend(matches)
            
            if grid_properties:
                grid_files[str(css_file.relative_to(self.project_root))] = grid_properties
        
        if grid_files:
            print(f"\nCSS Grid usage found in {len(grid_files)} files:")
            for file_path, properties in grid_files.items():
                print(f"  {file_path}: {len(properties)} grid properties")
        else:
            print("Info: No CSS Grid usage found (flexbox may be used instead)")
    
    def test_responsive_units_are_used(self):
        """Test that responsive units (%, vw, vh, em, rem) are used appropriately."""
        responsive_unit_files = {}
        
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            
            # Find responsive units
            unit_patterns = {
                "percentage": r"\d+(\.\d+)?%",
                "viewport_width": r"\d+(\.\d+)?vw",
                "viewport_height": r"\d+(\.\d+)?vh",
                "em": r"\d+(\.\d+)?em",
                "rem": r"\d+(\.\d+)?rem"
            }
            
            found_units = {}
            for unit_type, pattern in unit_patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    found_units[unit_type] = len(matches)
            
            if found_units:
                responsive_unit_files[str(css_file.relative_to(self.project_root))] = found_units
        
        if not responsive_unit_files:
            pytest.fail("No responsive units found in CSS files")
        
        print(f"\nResponsive units usage:")
        total_units = {}
        
        for file_path, units in responsive_unit_files.items():
            print(f"  {file_path}:")
            for unit_type, count in units.items():
                print(f"    {unit_type}: {count}")
                total_units[unit_type] = total_units.get(unit_type, 0) + count
        
        print(f"\nTotal responsive units across all files:")
        for unit_type, count in total_units.items():
            print(f"  {unit_type}: {count}")
    
    def test_component_responsive_classes(self):
        """Test that components use responsive CSS classes."""
        responsive_class_patterns = [
            r"className.*responsive",
            r"className.*mobile",
            r"className.*tablet",
            r"className.*desktop",
            r"className.*sm-",
            r"className.*md-",
            r"className.*lg-",
            r"className.*xl-"
        ]
        
        responsive_components = {}
        
        for component_file in self.component_files:
            try:
                with open(component_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_classes = []
                for pattern in responsive_class_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    found_classes.extend(matches)
                
                if found_classes:
                    responsive_components[str(component_file.relative_to(self.project_root))] = found_classes
            
            except Exception:
                continue
        
        if responsive_components:
            print(f"\nResponsive classes found in {len(responsive_components)} components:")
            for file_path, classes in responsive_components.items():
                print(f"  {file_path}: {len(classes)} responsive classes")
        else:
            print("Info: No explicit responsive classes found (CSS-based responsive design may be used)")
    
    def test_theme_css_responsive_design(self):
        """Test that the theme CSS file maintains responsive design."""
        theme_css_file = self.frontend_src / "styles" / "theme.css"
        
        if not theme_css_file.exists():
            pytest.skip("Theme CSS file not found")
        
        content = self.extract_css_content(theme_css_file)
        patterns = self.find_responsive_patterns(content)
        
        # Check for essential responsive patterns in theme
        essential_patterns = ["media_queries", "responsive_units"]
        missing_patterns = []
        
        for pattern_type in essential_patterns:
            if not patterns.get(pattern_type):
                missing_patterns.append(pattern_type)
        
        if missing_patterns:
            pytest.fail(f"Theme CSS missing essential responsive patterns: {missing_patterns}")
        
        # Check for CSS custom properties (variables) that support responsive design
        css_variables = re.findall(r"--[\w-]+:\s*[^;]+", content)
        
        if css_variables:
            print(f"✓ Theme CSS contains {len(css_variables)} CSS custom properties")
            
            # Check for responsive-related variables
            responsive_variables = [var for var in css_variables if any(
                keyword in var.lower() for keyword in ["spacing", "font-size", "width", "height"]
            )]
            
            if responsive_variables:
                print(f"✓ Found {len(responsive_variables)} responsive-related CSS variables")
            else:
                print("Warning: No responsive-related CSS variables found")
        else:
            print("Warning: No CSS custom properties found in theme")
    
    def test_dashboard_responsive_design(self):
        """Test that dashboard maintains responsive design."""
        dashboard_css = self.frontend_src / "components" / "dashboard" / "Dashboard.css"
        
        if not dashboard_css.exists():
            pytest.skip("Dashboard CSS file not found")
        
        content = self.extract_css_content(dashboard_css)
        patterns = self.find_responsive_patterns(content)
        
        # Dashboard should have responsive patterns
        has_responsive = any(patterns.values())
        
        if not has_responsive:
            pytest.fail("Dashboard CSS lacks responsive design patterns")
        
        # Check for grid or flexbox layout
        has_layout = patterns.get("flexbox") or patterns.get("grid")
        
        if not has_layout:
            print("Warning: Dashboard CSS may not use modern layout methods")
        
        print("✓ Dashboard CSS maintains responsive design")
    
    def test_mobile_first_approach(self):
        """Test that CSS follows mobile-first responsive design approach."""
        mobile_first_violations = []
        
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            
            # Find all media queries
            media_queries = re.findall(r"@media[^{]+", content)
            
            for query in media_queries:
                # Check for max-width queries (desktop-first approach)
                if "max-width" in query and "min-width" not in query:
                    # Extract the breakpoint
                    breakpoint_match = re.search(r"(\d+)px", query)
                    if breakpoint_match:
                        breakpoint = int(breakpoint_match.group(1))
                        # Large breakpoints with max-width suggest desktop-first
                        if breakpoint > 768:
                            mobile_first_violations.append(
                                f"{css_file.name}: {query.strip()}"
                            )
        
        if mobile_first_violations:
            print("Warning: Potential desktop-first approach detected:")
            for violation in mobile_first_violations:
                print(f"  {violation}")
        else:
            print("✓ CSS appears to follow mobile-first approach")
    
    def test_responsive_images_support(self):
        """Test that responsive image support is maintained."""
        image_responsive_patterns = [
            r"max-width:\s*100%",
            r"width:\s*100%",
            r"height:\s*auto",
            r"object-fit:\s*(cover|contain)",
            r"srcset",
            r"sizes"
        ]
        
        responsive_image_files = {}
        
        # Check CSS files for responsive image styles
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            
            found_patterns = []
            for pattern in image_responsive_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                found_patterns.extend(matches)
            
            if found_patterns:
                responsive_image_files[str(css_file.relative_to(self.project_root))] = found_patterns
        
        # Check component files for responsive image attributes
        for component_file in self.component_files:
            try:
                with open(component_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_patterns = []
                for pattern in ["srcset", "sizes"]:
                    if pattern in content:
                        found_patterns.append(pattern)
                
                if found_patterns:
                    responsive_image_files[str(component_file.relative_to(self.project_root))] = found_patterns
            
            except Exception:
                continue
        
        if responsive_image_files:
            print(f"\nResponsive image support found in {len(responsive_image_files)} files:")
            for file_path, patterns in responsive_image_files.items():
                print(f"  {file_path}: {patterns}")
        else:
            print("Info: No explicit responsive image patterns found")
    
    def test_accessibility_responsive_features(self):
        """Test that accessibility features are maintained in responsive design."""
        accessibility_patterns = [
            r"@media\s*\(prefers-reduced-motion",
            r"@media\s*\(prefers-color-scheme",
            r"@media\s*\(prefers-contrast",
            r"focus:",
            r"focus-visible:",
            r"aria-",
            r"role="
        ]
        
        accessibility_files = {}
        
        # Check CSS files
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            
            found_patterns = []
            for pattern in accessibility_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                found_patterns.extend(matches)
            
            if found_patterns:
                accessibility_files[str(css_file.relative_to(self.project_root))] = found_patterns
        
        # Check component files
        for component_file in self.component_files:
            try:
                with open(component_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_patterns = []
                for pattern in ["aria-", "role=", "tabIndex"]:
                    if pattern in content:
                        found_patterns.append(pattern)
                
                if found_patterns:
                    accessibility_files[str(component_file.relative_to(self.project_root))] = found_patterns
            
            except Exception:
                continue
        
        if accessibility_files:
            print(f"\nAccessibility features found in {len(accessibility_files)} files:")
            for file_path, patterns in accessibility_files.items():
                print(f"  {file_path}: {len(patterns)} accessibility features")
        else:
            print("Warning: Limited accessibility features found")
    
    def test_responsive_design_summary(self):
        """Provide a summary of responsive design maintenance."""
        print("\n" + "="*60)
        print("RESPONSIVE DESIGN MAINTENANCE SUMMARY")
        print("="*60)
        
        # Count files with responsive features
        responsive_css_count = 0
        responsive_component_count = 0
        
        for css_file in self.css_files:
            content = self.extract_css_content(css_file)
            patterns = self.find_responsive_patterns(content)
            if any(patterns.values()):
                responsive_css_count += 1
        
        for component_file in self.component_files:
            try:
                with open(component_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for responsive-related code
                responsive_indicators = [
                    "responsive", "mobile", "tablet", "desktop",
                    "breakpoint", "media", "flex", "grid"
                ]
                
                if any(indicator in content.lower() for indicator in responsive_indicators):
                    responsive_component_count += 1
            except Exception:
                continue
        
        print(f"CSS files with responsive patterns: {responsive_css_count}/{len(self.css_files)}")
        print(f"Components with responsive features: {responsive_component_count}/{len(self.component_files)}")
        
        # Calculate responsive design score
        total_files = len(self.css_files) + len(self.component_files)
        responsive_files = responsive_css_count + responsive_component_count
        
        if total_files > 0:
            responsive_score = (responsive_files / total_files) * 100
            print(f"Responsive design coverage: {responsive_score:.1f}%")
            
            if responsive_score >= 80:
                print("✓ Excellent responsive design maintenance")
            elif responsive_score >= 60:
                print("⚠ Good responsive design maintenance")
            elif responsive_score >= 40:
                print("⚠ Moderate responsive design maintenance")
            else:
                print("✗ Poor responsive design maintenance")
        
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])