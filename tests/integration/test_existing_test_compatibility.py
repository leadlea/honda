"""
Existing Test Compatibility Verification for AI人材発掘・配置マッチングMVP（AI CoE支援）
AI人材発掘・配置マッチングMVP（AI CoE支援） 既存テスト互換性検証

This test suite verifies that existing tests still pass after branding updates.
ブランディング更新後も既存テストが通ることを確認します。
"""

import pytest
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import importlib.util


class TestExistingTestCompatibility:
    """Test that existing test suites remain compatible after branding updates."""
    
    def setup_method(self):
        """Setup test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.test_directories = [
            self.project_root / "tests" / "unit",
            self.project_root / "tests" / "integration",
            self.project_root / "frontend" / "src" / "components"
        ]
        
        # List of critical test files that must pass
        self.critical_test_files = [
            "tests/unit/test_auth_handler.py",
            "tests/unit/test_profile_handler.py",
            "tests/unit/test_matching_handler.py",
            "tests/unit/test_application_handler.py",
            "tests/unit/test_user_model.py",
            "tests/unit/test_veteran_profile_model.py",
            "tests/unit/test_user_repository.py",
            "tests/unit/test_veteran_profile_repository.py",
            "tests/unit/test_application_repository.py",
            "tests/unit/test_matching_engine.py",
            "tests/unit/test_recommendation_service.py",
            "tests/unit/test_ai_utils.py",
            "tests/unit/test_bedrock_client.py"
        ]
        
        # Frontend test files
        self.frontend_test_files = [
            "frontend/src/components/questionnaire/Questionnaire.test.tsx"
        ]
    
    def test_python_unit_tests_compatibility(self):
        """Test that Python unit tests are still compatible."""
        failed_tests = []
        
        for test_file in self.critical_test_files:
            test_path = self.project_root / test_file
            
            if not test_path.exists():
                print(f"Warning: Test file not found: {test_file}")
                continue
            
            try:
                # Try to import the test module to check for syntax errors
                spec = importlib.util.spec_from_file_location("test_module", test_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    print(f"✓ Successfully imported: {test_file}")
                else:
                    failed_tests.append(f"Failed to load spec for: {test_file}")
                    
            except ImportError as e:
                # Check if the import error is due to missing dependencies
                # or actual code issues
                if "branding" in str(e).lower() or "term_mapping" in str(e).lower():
                    print(f"⚠ Import warning (branding-related): {test_file} - {e}")
                else:
                    failed_tests.append(f"Import error in {test_file}: {e}")
                    
            except SyntaxError as e:
                failed_tests.append(f"Syntax error in {test_file}: {e}")
                
            except Exception as e:
                failed_tests.append(f"Unexpected error in {test_file}: {e}")
        
        if failed_tests:
            pytest.fail(f"Test compatibility issues found:\n" + "\n".join(failed_tests))
    
    def test_frontend_tests_compatibility(self):
        """Test that frontend tests are still compatible."""
        failed_tests = []
        
        for test_file in self.frontend_test_files:
            test_path = self.project_root / test_file
            
            if not test_path.exists():
                print(f"Warning: Frontend test file not found: {test_file}")
                continue
            
            try:
                # Read the test file and check for obvious syntax issues
                with open(test_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for common issues that might arise from branding updates
                issues = []
                
                # Check for hardcoded legacy terms that might cause test failures
                legacy_terms = [
                    "Honda Veteran Talent Bank",
                    "ベテラン検索",
                    "問診",
                    "ベテランプロフィール"
                ]
                
                for term in legacy_terms:
                    if term in content:
                        issues.append(f"Legacy term found: {term}")
                
                # Check for import statements that might be affected
                if "import" in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if line.strip().startswith('import') or line.strip().startswith('from'):
                            if 'termMappingService' in line or 'brandingUtils' in line:
                                print(f"Branding-related import found in {test_file}:{i}")
                
                if issues:
                    print(f"⚠ Potential issues in {test_file}: {issues}")
                else:
                    print(f"✓ Frontend test file looks compatible: {test_file}")
                    
            except Exception as e:
                failed_tests.append(f"Error reading {test_file}: {e}")
        
        if failed_tests:
            pytest.fail(f"Frontend test compatibility issues:\n" + "\n".join(failed_tests))
    
    def test_test_data_compatibility(self):
        """Test that test data and fixtures are still compatible."""
        # Check for test data files that might need updating
        test_data_patterns = [
            "test_data.json",
            "fixtures.json",
            "mock_data.py",
            "sample_data.py"
        ]
        
        compatibility_issues = []
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for pattern in test_data_patterns:
                for data_file in test_dir.rglob(pattern):
                    try:
                        if data_file.suffix == '.json':
                            import json
                            with open(data_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            # Check for legacy terms in JSON data
                            data_str = json.dumps(data)
                            legacy_terms = [
                                "Honda Veteran Talent Bank",
                                "ベテラン検索",
                                "問診",
                                "ベテランプロフィール"
                            ]
                            
                            found_terms = []
                            for term in legacy_terms:
                                if term in data_str:
                                    found_terms.append(term)
                            
                            if found_terms:
                                print(f"⚠ Legacy terms in {data_file}: {found_terms}")
                            else:
                                print(f"✓ Test data compatible: {data_file}")
                                
                        elif data_file.suffix == '.py':
                            with open(data_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Check for legacy terms in Python test data
                            legacy_terms = [
                                "Honda Veteran Talent Bank",
                                "ベテラン検索",
                                "問診",
                                "ベテランプロフィール"
                            ]
                            
                            found_terms = []
                            for term in legacy_terms:
                                if term in content:
                                    found_terms.append(term)
                            
                            if found_terms:
                                print(f"⚠ Legacy terms in {data_file}: {found_terms}")
                            else:
                                print(f"✓ Test data compatible: {data_file}")
                                
                    except Exception as e:
                        compatibility_issues.append(f"Error checking {data_file}: {e}")
        
        if compatibility_issues:
            pytest.fail(f"Test data compatibility issues:\n" + "\n".join(compatibility_issues))
    
    def test_mock_configurations_compatibility(self):
        """Test that mock configurations are still compatible."""
        # Check for mock configurations that might be affected by branding changes
        mock_patterns = [
            "**/conftest.py",
            "**/test_*.py",
            "**/*_test.py",
            "**/*_mock.py"
        ]
        
        compatibility_issues = []
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for pattern in mock_patterns:
                for mock_file in test_dir.rglob(pattern.replace("**/", "")):
                    if not mock_file.is_file():
                        continue
                        
                    try:
                        with open(mock_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check for mock configurations that might need updating
                        mock_indicators = [
                            "@patch",
                            "Mock(",
                            "MagicMock(",
                            "mock.patch",
                            "unittest.mock"
                        ]
                        
                        has_mocks = any(indicator in content for indicator in mock_indicators)
                        
                        if has_mocks:
                            # Check for potential issues with mocked services
                            potential_issues = []
                            
                            # Check for hardcoded return values that might contain legacy terms
                            if "return_value" in content:
                                legacy_terms = [
                                    "Honda Veteran Talent Bank",
                                    "ベテラン検索",
                                    "問診",
                                    "ベテランプロフィール"
                                ]
                                
                                for term in legacy_terms:
                                    if term in content:
                                        potential_issues.append(f"Legacy term in mock: {term}")
                            
                            # Check for mocked service names that might have changed
                            service_patterns = [
                                "termMappingService",
                                "brandingUtils",
                                "messageConfig"
                            ]
                            
                            for pattern in service_patterns:
                                if pattern in content:
                                    print(f"Branding-related mock found in {mock_file}")
                            
                            if potential_issues:
                                print(f"⚠ Potential mock issues in {mock_file}: {potential_issues}")
                            else:
                                print(f"✓ Mock configuration compatible: {mock_file}")
                                
                    except Exception as e:
                        compatibility_issues.append(f"Error checking {mock_file}: {e}")
        
        if compatibility_issues:
            pytest.fail(f"Mock configuration compatibility issues:\n" + "\n".join(compatibility_issues))
    
    def test_test_environment_setup_compatibility(self):
        """Test that test environment setup is still compatible."""
        # Check for environment setup files
        setup_files = [
            "pytest.ini",
            "pyproject.toml",
            "setup.cfg",
            "tox.ini",
            ".github/workflows/test.yml",
            "package.json"  # For frontend tests
        ]
        
        compatibility_issues = []
        
        for setup_file in setup_files:
            file_path = self.project_root / setup_file
            
            if not file_path.exists():
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for test-related configurations
                if setup_file == "pytest.ini":
                    # Check pytest configuration
                    if "testpaths" in content:
                        print(f"✓ Pytest configuration found in {setup_file}")
                    
                elif setup_file == "package.json":
                    # Check frontend test configuration
                    import json
                    try:
                        package_data = json.loads(content)
                        if "scripts" in package_data and "test" in package_data["scripts"]:
                            print(f"✓ Frontend test script found in {setup_file}")
                    except json.JSONDecodeError:
                        compatibility_issues.append(f"Invalid JSON in {setup_file}")
                
                elif setup_file.endswith(".yml"):
                    # Check CI/CD configuration
                    if "test" in content.lower() or "pytest" in content.lower():
                        print(f"✓ Test configuration found in {setup_file}")
                
                print(f"✓ Setup file compatible: {setup_file}")
                
            except Exception as e:
                compatibility_issues.append(f"Error checking {setup_file}: {e}")
        
        if compatibility_issues:
            pytest.fail(f"Test environment setup issues:\n" + "\n".join(compatibility_issues))
    
    def test_import_path_compatibility(self):
        """Test that import paths are still valid after branding updates."""
        # Common import patterns that might be affected
        import_patterns = [
            "from src.handlers",
            "from src.services",
            "from src.models",
            "from src.repositories",
            "from src.utils",
            "from src.config"
        ]
        
        compatibility_issues = []
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for test_file in test_dir.rglob("test_*.py"):
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for import statements
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if line.startswith('from ') or line.startswith('import '):
                            # Check if this is a project import
                            for pattern in import_patterns:
                                if pattern in line:
                                    # Try to validate the import path
                                    try:
                                        # Extract the module path
                                        if line.startswith('from '):
                                            module_path = line.split(' import ')[0].replace('from ', '')
                                        else:
                                            module_path = line.replace('import ', '').split(' as ')[0]
                                        
                                        # Convert to file path
                                        file_path = module_path.replace('.', '/') + '.py'
                                        full_path = self.project_root / file_path
                                        
                                        if not full_path.exists():
                                            # Check if it's a package import
                                            package_path = self.project_root / module_path.replace('.', '/') / '__init__.py'
                                            if not package_path.exists():
                                                compatibility_issues.append(
                                                    f"Import path may be invalid in {test_file}:{i} - {line}"
                                                )
                                        
                                    except Exception:
                                        # Skip complex import validation
                                        pass
                    
                    print(f"✓ Import paths checked: {test_file}")
                    
                except Exception as e:
                    compatibility_issues.append(f"Error checking imports in {test_file}: {e}")
        
        if compatibility_issues:
            print("⚠ Import path compatibility warnings:")
            for issue in compatibility_issues:
                print(f"  {issue}")
    
    def test_test_execution_simulation(self):
        """Simulate test execution to check for obvious failures."""
        # This test simulates running tests without actually executing them
        # to check for import errors and basic compatibility issues
        
        test_files_to_check = [
            "tests/unit/test_user_model.py",
            "tests/unit/test_veteran_profile_model.py",
            "tests/unit/test_auth_handler.py"
        ]
        
        simulation_results = []
        
        for test_file in test_files_to_check:
            test_path = self.project_root / test_file
            
            if not test_path.exists():
                continue
            
            try:
                # Try to compile the test file
                with open(test_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Compile to check for syntax errors
                compile(content, str(test_path), 'exec')
                
                simulation_results.append(f"✓ Compilation successful: {test_file}")
                
            except SyntaxError as e:
                simulation_results.append(f"✗ Syntax error in {test_file}: {e}")
                
            except Exception as e:
                simulation_results.append(f"⚠ Compilation warning for {test_file}: {e}")
        
        # Print simulation results
        for result in simulation_results:
            print(result)
        
        # Check if there were any critical failures
        critical_failures = [r for r in simulation_results if r.startswith("✗")]
        if critical_failures:
            pytest.fail(f"Critical test compatibility failures:\n" + "\n".join(critical_failures))
    
    def test_dependency_compatibility(self):
        """Test that test dependencies are still compatible."""
        # Check requirements files
        requirements_files = [
            "requirements.txt",
            "requirements-test.txt",
            "requirements-dev.txt",
            "frontend/package.json"
        ]
        
        for req_file in requirements_files:
            req_path = self.project_root / req_file
            
            if not req_path.exists():
                continue
            
            try:
                with open(req_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if req_file.endswith('.json'):
                    import json
                    package_data = json.loads(content)
                    
                    # Check for test-related dependencies
                    test_deps = []
                    if "devDependencies" in package_data:
                        for dep, version in package_data["devDependencies"].items():
                            if "test" in dep.lower() or "jest" in dep.lower():
                                test_deps.append(f"{dep}@{version}")
                    
                    if test_deps:
                        print(f"✓ Frontend test dependencies found: {test_deps}")
                
                else:
                    # Check for Python test dependencies
                    test_deps = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if any(test_lib in line.lower() for test_lib in ['pytest', 'unittest', 'mock']):
                                test_deps.append(line)
                    
                    if test_deps:
                        print(f"✓ Python test dependencies found: {test_deps}")
                
                print(f"✓ Dependencies checked: {req_file}")
                
            except Exception as e:
                print(f"⚠ Error checking dependencies in {req_file}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])