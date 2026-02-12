"""
Code Quality Pipeline - Validation Loop Implementation

Implements: Generate → Validate → Fix Errors → Re-validate → Save

This module provides automated validation and error fixing for generated IaC code.
"""

import asyncio
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a single validation issue found in code."""
    file: str
    line: int
    column: int = 0
    severity: str = "error"  # error, warning, info
    type: str = "unknown"    # syntax, logic, reference, security
    rule: str = ""
    message: str = ""
    current_code: str = ""
    context: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "type": self.type,
            "rule": self.rule,
            "message": self.message,
            "current_code": self.current_code,
            "context": self.context
        }


@dataclass
class ValidationResult:
    """Results from code validation."""
    status: str  # pass, fail, warning
    total_files: int = 0
    files_with_errors: int = 0
    files_with_warnings: int = 0
    error_count: int = 0
    warning_count: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return self.error_count > 0
    
    @property
    def has_warnings(self) -> bool:
        return self.warning_count > 0
    
    def to_dict(self) -> Dict:
        return {
            "overall_status": self.status,
            "validation_summary": {
                "total_files": self.total_files,
                "files_with_errors": self.files_with_errors,
                "files_with_warnings": self.files_with_warnings,
                "error_count": self.error_count,
                "warning_count": self.warning_count
            },
            "issues": [issue.to_dict() for issue in self.issues]
        }


@dataclass
class CodeFix:
    """Represents a suggested fix for a validation issue."""
    issue: ValidationIssue
    suggested_code: str
    explanation: str
    confidence: str  # high, medium, low
    alternatives: List[Dict[str, str]] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "issue": self.issue.to_dict(),
            "fix": {
                "suggested_code": self.suggested_code,
                "explanation": self.explanation,
                "confidence": self.confidence,
                "alternatives": self.alternatives,
                "references": self.references
            }
        }


class TerraformValidator:
    """Validates Terraform code."""
    
    def __init__(self, code_dir: Path):
        self.code_dir = Path(code_dir)
    
    @staticmethod
    def is_terraform_available() -> bool:
        """Check if terraform CLI is available."""
        return shutil.which("terraform") is not None
    
    def validate(self) -> ValidationResult:
        """PHASE 1: Run terraform fmt for syntax-only validation (no init, no validate).
        
        This is called during per-module generation. It only checks formatting and basic
        HCL syntax. Does NOT run terraform validate (which requires terraform init).
        
        For full validation with dependencies, use validate_full() after all modules generated.
        """
        result = ValidationResult(status="pass")
        
        # Check if terraform is installed
        if not self.is_terraform_available():
            logger.warning("Terraform CLI not found in PATH - skipping validation")
            result.status = "warning"
            result.issues.append(
                ValidationIssue(
                    file="<system>",
                    line=0,
                    severity="warning",
                    type="missing_tool",
                    message="Terraform CLI not installed or not in PATH. Install from https://www.terraform.io/downloads"
                )
            )
            return result
        
        try:
            # PHASE 1: Only run terraform fmt -check for formatting/basic syntax
            # DO NOT run terraform validate (requires init with providers)
            fmt_result = subprocess.run(
                ["terraform", "fmt", "-check", "-diff"],
                cwd=self.code_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # fmt returns non-zero if files need formatting (not critical)
            if fmt_result.returncode != 0 and fmt_result.stdout:
                for line in fmt_result.stdout.strip().split('\n'):
                    if line:
                        result.issues.append(
                            ValidationIssue(
                                file=line,
                                line=0,
                                severity="warning",
                                type="formatting",
                                message="File needs formatting (terraform fmt)"
                            )
                        )
                result.status = "warning"
            
            # PHASE 1: Skip terraform validate - it requires terraform init
            # Provider/module errors are expected and will be validated in PHASE 2
            logger.debug("PHASE 1 validation: terraform fmt completed (skipping terraform validate)")
            
        except subprocess.TimeoutExpired:
            logger.error("Terraform fmt timed out")
            result.status = "fail"
            result.issues.append(
                ValidationIssue(
                    file="<unknown>",
                    line=0,
                    severity="error",
                    type="timeout",
                    message="Terraform fmt timed out"
                )
            )
        except Exception as e:
            logger.error(f"Validation error: {e}")
            result.status = "fail"
            result.issues.append(
                ValidationIssue(
                    file="<unknown>",
                    line=0,
                    severity="error",
                    type="exception",
                    message=str(e)
                )
            )
        
        return result
    
    def _parse_init_errors(self, stderr: str, result: ValidationResult) -> ValidationResult:
        """Parse terraform init errors."""
        result.status = "fail"
        result.error_count = 1
        result.issues.append(
            ValidationIssue(
                file="terraform init",
                line=0,
                severity="error",
                type="init",
                message=stderr
            )
        )
        return result
    
    def _parse_validate_output(self, output: Dict, result: ValidationResult) -> ValidationResult:
        """Parse terraform validate JSON output."""
        if not output.get("valid", True):
            result.status = "fail"
            
            # Count files
            files_seen = set()
            
            # Parse diagnostics
            for diag in output.get("diagnostics", []):
                severity = diag.get("severity", "error")
                
                # Extract location info
                location = diag.get("range", {})
                filename = location.get("filename", None)
                
                # If no filename in range, terraform might have it elsewhere
                if not filename:
                    # Try to extract from subject attribute
                    subject = diag.get("address") or diag.get("subject")
                    if subject:
                        logger.debug(f"No filename in range, found subject: {subject}")
                    
                    # Last resort: mark as unknown (will skip fix attempts)
                    filename = "<unknown>"
                    logger.warning(f"Terraform validation error has no filename: {diag.get('summary', 'unknown error')}")
                    logger.debug(f"Diagnostic structure: {json.dumps(diag, indent=2)[:500]}")
                
                files_seen.add(filename)
                
                issue = ValidationIssue(
                    file=filename,
                    line=location.get("start", {}).get("line", 0),
                    column=location.get("start", {}).get("column", 0),
                    severity=severity,
                    type="syntax" if "syntax" in diag.get("detail", "").lower() else "validation",
                    message=diag.get("summary", "") + " - " + diag.get("detail", ""),
                    current_code=diag.get("snippet", {}).get("code", "")
                )
                
                result.issues.append(issue)
                
                if severity == "error":
                    result.error_count += 1
                elif severity == "warning":
                    result.warning_count += 1
            
            result.total_files = len(files_seen)
            result.files_with_errors = len([f for f in files_seen if any(i.file == f and i.severity == "error" for i in result.issues)])
            result.files_with_warnings = len([f for f in files_seen if any(i.file == f and i.severity == "warning" for i in result.issues)])
        
        return result


class BicepValidator:
    """Validates Bicep code."""
    
    def __init__(self, code_dir: Path):
        self.code_dir = Path(code_dir)
    
    @staticmethod
    def is_bicep_available() -> bool:
        """Check if bicep CLI is available."""
        return shutil.which("bicep") is not None
    
    def validate(self) -> ValidationResult:
        """PHASE 1: Run bicep lint for syntax-only validation (no build, no modules).
        
        This is called during per-module generation. It only checks syntax and linting
        rules. Does NOT run bicep build (which requires module resolution).
        
        For full validation with dependencies, use validate_full() after all modules generated.
        """
        result = ValidationResult(status="pass")
        
        # Check if bicep is installed
        if not self.is_bicep_available():
            logger.warning("Bicep CLI not found in PATH - skipping validation")
            result.status = "warning"
            result.issues.append(
                ValidationIssue(
                    file="<system>",
                    line=0,
                    severity="warning",
                    type="missing_tool",
                    message="Bicep CLI not installed or not in PATH. Install from https://aka.ms/bicep-install"
                )
            )
            return result
        
        try:
            # Find all .bicep files
            bicep_files = list(self.code_dir.rglob("*.bicep"))
            result.total_files = len(bicep_files)
            
            if not bicep_files:
                return result
            
            # Lint each file (syntax check without build/module resolution)
            for bicep_file in bicep_files:
                # Use bicep lint for syntax validation without resolving module references
                lint_result = subprocess.run(
                    ["bicep", "lint", str(bicep_file)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Parse output - bicep lint returns warnings/errors to stderr
                if lint_result.stderr:
                    self._parse_bicep_errors(lint_result.stderr, bicep_file, result)
                
                # Non-zero return code indicates errors (not just warnings)
                if lint_result.returncode != 0:
                    # Check if there are actual errors (not just warnings)
                    has_errors = any(i.severity == "error" for i in result.issues if i.file == str(bicep_file))
                    if has_errors:
                        result.status = "fail"
            
            return result
            
        except Exception as e:
            logger.error(f"Bicep validation error: {e}")
            result.status = "fail"
            return result
    
    def _parse_bicep_errors(self, stderr: str, file: Path, result: ValidationResult) -> None:
        """Parse bicep build errors."""
        # Bicep outputs errors in format: file(line,col): Error/Warning: message
        import re
        
        for line in stderr.split('\n'):
            match = re.match(r'(.+)\((\d+),(\d+)\):\s+(Error|Warning):\s+(.+)', line)
            if match:
                _, line_num, col_num, severity, message = match.groups()
                
                issue = ValidationIssue(
                    file=str(file.relative_to(self.code_dir)),
                    line=int(line_num),
                    column=int(col_num),
                    severity=severity.lower(),
                    type="bicep",
                    message=message
                )
                
                result.issues.append(issue)
                
                if severity.lower() == "error":
                    result.error_count += 1
                    result.files_with_errors += 1
                else:
                    result.warning_count += 1
                    result.files_with_warnings += 1


class CodeQualityPipeline:
    """
    Main pipeline for IaC code quality validation and fixing.
    
    Implements: Generate → Validate → Fix Errors → Re-validate → Save
    """
    
    def __init__(self, 
                 iac_type: str,
                 max_fix_iterations: int = 3,
                 quality_agent = None):
        """
        Initialize the pipeline.
        
        Args:
            iac_type: "terraform" or "bicep"
            max_fix_iterations: Maximum number of fix attempts
            quality_agent: Agent that can fix code issues (optional)
        """
        self.iac_type = iac_type.lower()
        self.max_fix_iterations = max_fix_iterations
        self.quality_agent = quality_agent
        
        # Select validator
        if self.iac_type == "terraform":
            self.validator_class = TerraformValidator
        elif self.iac_type == "bicep":
            self.validator_class = BicepValidator
        else:
            raise ValueError(f"Unsupported IaC type: {iac_type}")
    
    async def run(self, generated_code: Dict[str, str], output_dir: Path) -> Tuple[Dict[str, str], ValidationResult]:
        """
        Run the complete validation pipeline.
        
        Args:
            generated_code: Dict of {filename: code_content}
            output_dir: Directory to save validated code
        
        Returns:
            Tuple of (final_code, validation_result)
        """
        logger.info(f"Starting code quality pipeline for {len(generated_code)} files")
        
        # Stage 1: Save initial code to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._save_code(generated_code, temp_path)
            
            # Stage 2: Initial validation
            validator = self.validator_class(temp_path)
            validation_result = validator.validate()
            
            logger.info(f"Initial validation: {validation_result.status} - "
                       f"{validation_result.error_count} errors, "
                       f"{validation_result.warning_count} warnings")
            
            # Log unfixable system errors
            system_errors = [
                issue for issue in validation_result.issues
                if issue.severity == "error" and (not issue.file or issue.file == "<unknown>")
            ]
            if system_errors:
                logger.warning(f"⚠️  Found {len(system_errors)} system/setup errors that cannot be auto-fixed:")
                for err in system_errors:
                    logger.warning(f"   - {err.message[:100]}")
                logger.info("💡 These errors require manual intervention (e.g., terraform init, provider configuration)")
            
            # Stage 3: Fix errors (if quality agent available)
            iteration = 0
            while validation_result.has_errors and iteration < self.max_fix_iterations:
                iteration += 1
                logger.info(f"Attempting fix iteration {iteration}/{self.max_fix_iterations}")
                
                if self.quality_agent is None:
                    logger.warning("No quality agent available for fixes")
                    break
                
                # Get fixes from quality agent (async call)
                fixes = await self._get_fixes(validation_result, generated_code)
                
                if not fixes:
                    logger.warning("No fixes generated")
                    break
                
                # Apply high-confidence fixes
                generated_code = self._apply_fixes(generated_code, fixes)
                
                # Re-save and re-validate
                self._save_code(generated_code, temp_path)
                validation_result = validator.validate()
                
                logger.info(f"After fix iteration {iteration}: {validation_result.status} - "
                           f"{validation_result.error_count} errors, "
                           f"{validation_result.warning_count} warnings")
                
                # If no improvement, break
                if not validation_result.has_errors:
                    break
            
            # Stage 4: Save code regardless of validation status
            # Other modules need to reference this module even if it has errors
            self._save_code(generated_code, output_dir)
            
            if validation_result.status == "pass" or validation_result.status == "warning":
                logger.info(f"✓ Code validated and saved to {output_dir}")
            else:
                logger.error(f"✗ Validation failed after {iteration} iterations (code saved for module references)")
        
        return generated_code, validation_result
    
    def _save_code(self, code: Dict[str, str], directory: Path) -> None:
        """Save code files to directory."""
        directory.mkdir(parents=True, exist_ok=True)
        
        for filename, content in code.items():
            file_path = directory / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
    
    async def _get_fixes(self, validation_result: ValidationResult, code_files: Dict[str, str]) -> List[CodeFix]:
        """Get fixes from quality agent."""
        if self.quality_agent is None:
            logger.warning("No quality agent available for fix generation")
            return []
        
        # Filter out unfixable errors:
        # 1. Errors with no filename (global/system errors)
        # 2. Module dependency errors (other modules not installed yet - expected in PHASE 1)
        # 3. Provider dependency errors (providers not initialized - expected in PHASE 1)
        module_dependency_patterns = [
            "module not installed",
            "module is not yet installed",
            "missing required provider",
            "provider registry.terraform.io",
            "could not find module",
            "failed to install provider",
        ]
        
        fixable_issues = [
            issue for issue in validation_result.issues
            if issue.severity == "error" 
            and issue.file 
            and issue.file != "<unknown>"
            and not any(pattern in issue.message.lower() for pattern in module_dependency_patterns)
        ]
        
        # Log filtered out dependency errors
        dependency_errors = [
            issue for issue in validation_result.issues
            if issue.severity == "error" 
            and any(pattern in issue.message.lower() for pattern in module_dependency_patterns)
        ]
        if dependency_errors:
            logger.info(f"Filtered out {len(dependency_errors)} module/provider dependency errors (expected in PHASE 1):")
            for err in dependency_errors[:3]:  # Show first 3
                logger.debug(f"   - {err.file}:{err.line}: {err.message[:80]}")
        
        if not fixable_issues:
            logger.info(f"No fixable syntax errors found. All {validation_result.error_count} errors are dependency/system errors")
            return []
        
        logger.info(f"Found {len(fixable_issues)} fixable syntax errors out of {validation_result.error_count} total errors")
        
        # Create filtered validation result for agent
        filtered_result = ValidationResult(
            status=validation_result.status,
            total_files=validation_result.total_files,
            files_with_errors=validation_result.files_with_errors,
            error_count=len(fixable_issues),
            warning_count=validation_result.warning_count
        )
        filtered_result.issues = fixable_issues
        
        try:
            # Call the quality agent to generate fixes
            logger.info(f"Requesting fixes from quality agent for {len(fixable_issues)} fixable errors...")
            fixes = await self.quality_agent.generate_fixes(
                validation_result=filtered_result,
                code_files=code_files
            )
            
            high_conf = len([f for f in fixes if f.confidence == "high"])
            logger.info(f"Quality agent generated {len(fixes)} fixes ({high_conf} high-confidence)")
            return fixes
            
        except Exception as e:
            logger.error(f"Error getting fixes from quality agent: {e}", exc_info=True)
            return []
    
    def _apply_fixes(self, code: Dict[str, str], fixes: List[CodeFix]) -> Dict[str, str]:
        """Apply high-confidence fixes to code."""
        updated_code = code.copy()
        
        for fix in fixes:
            if fix.confidence != "high":
                logger.info(f"Skipping low-confidence fix for {fix.issue.file}:{fix.issue.line}")
                continue
            
            filename = fix.issue.file
            
            # Skip fixes for files with unknown location (validation errors without filename)
            if not filename or filename == "<unknown>":
                logger.warning(f"Skipping fix - validation error has no filename. Message: {fix.issue.message}")
                continue
            
            # Try exact match first
            if filename not in updated_code:
                # Try to find filename by basename match (agent might return different path)
                basename = Path(filename).name
                matches = [f for f in updated_code.keys() if Path(f).name == basename]
                
                if len(matches) == 1:
                    filename = matches[0]
                    logger.debug(f"Matched {fix.issue.file} to {filename} by basename")
                elif len(matches) > 1:
                    logger.warning(f"Multiple files match basename '{basename}': {matches}")
                    continue
                else:
                    logger.warning(f"File {fix.issue.file} not found in code. Available files: {list(updated_code.keys())}")
                    continue
            
            # Apply fix (smart string replacement with fallback strategies)
            current_content = updated_code[filename]
            fix_applied = False
            
            # Debug: Log what we're trying to fix
            logger.debug(f"🔍 Attempting to fix {filename}:{fix.issue.line}")
            logger.debug(f"   Issue: {fix.issue.message}")
            logger.debug(f"   Current code (from agent): '{fix.issue.current_code[:100]}'")
            logger.debug(f"   Suggested code: '{fix.suggested_code[:100]}'")
            logger.debug(f"   Confidence: {fix.confidence}")
            
            # Strategy 1: Exact match
            if fix.issue.current_code in current_content:
                updated_code[filename] = current_content.replace(
                    fix.issue.current_code,
                    fix.suggested_code,
                    1  # Replace only first occurrence
                )
                logger.info(f"✓ Applied fix to {filename}:{fix.issue.line} (exact match)")
                fix_applied = True
            
            # Strategy 2: Try stripping whitespace (agent might have different formatting)
            elif fix.issue.current_code.strip() in current_content:
                updated_code[filename] = current_content.replace(
                    fix.issue.current_code.strip(),
                    fix.suggested_code,
                    1
                )
                logger.info(f"✓ Applied fix to {filename}:{fix.issue.line} (whitespace-normalized match)")
                fix_applied = True
            
            # Strategy 3: Extract line from file and check if it contains the code snippet
            elif fix.issue.line > 0:
                lines = current_content.split('\n')
                logger.debug(f"   File has {len(lines)} lines, checking line {fix.issue.line}")
                
                if 0 < fix.issue.line <= len(lines):
                    target_line = lines[fix.issue.line - 1]
                    logger.debug(f"   Actual line {fix.issue.line}: '{target_line.strip()}'")
                    
                    # Check if the current_code is a substring of the line
                    if fix.issue.current_code.strip() in target_line:
                        # Replace the whole line
                        lines[fix.issue.line - 1] = fix.suggested_code
                        updated_code[filename] = '\n'.join(lines)
                        logger.info(f"✓ Applied fix to {filename}:{fix.issue.line} (line-based replacement)")
            # Apply fix using line-based replacement (most reliable)
            current_content = updated_code[filename]
            fix_applied = False
            
            # Debug: Log what we're trying to fix
            logger.debug(f"🔍 Attempting to fix {filename}:{fix.issue.line}")
            logger.debug(f"   Issue: {fix.issue.message}")
            logger.debug(f"   Current code (from agent): '{fix.issue.current_code[:100]}'")
            logger.debug(f"   Suggested code: '{fix.suggested_code[:100]}'")
            logger.debug(f"   Confidence: {fix.confidence}")
            
            # Primary Strategy: Line-based replacement (most reliable when line number available)
            if fix.issue.line > 0:
                lines = current_content.split('\n')
                logger.debug(f"   File has {len(lines)} lines, targeting line {fix.issue.line}")
                
                if 0 < fix.issue.line <= len(lines):
                    original_line = lines[fix.issue.line - 1]
                    logger.debug(f"   Original line {fix.issue.line}: '{original_line.strip()}'")
                    
                    # Replace the line with suggested code (preserve indentation if possible)
                    # Extract leading whitespace from original line
                    leading_space = len(original_line) - len(original_line.lstrip())
                    indent = original_line[:leading_space]
                    
                    # If suggested_code doesn't have indentation, add it
                    if fix.suggested_code and not fix.suggested_code[0].isspace():
                        indented_suggestion = indent + fix.suggested_code.strip()
                    else:
                        indented_suggestion = fix.suggested_code
                    
                    lines[fix.issue.line - 1] = indented_suggestion
                    updated_code[filename] = '\n'.join(lines)
                    logger.info(f"✓ Applied fix to {filename}:{fix.issue.line} (line replacement)")
                    fix_applied = True
                else:
                    logger.warning(f"✗ Line {fix.issue.line} out of range in {filename} (file has {len(lines)} lines)")
                    logger.warning(f"   Agent provided line number {fix.issue.line} but file only has {len(lines)} lines")
            
            # Fallback Strategy 1: Exact string match (if line number not available)
            if not fix_applied and fix.issue.current_code in current_content:
                updated_code[filename] = current_content.replace(
                    fix.issue.current_code,
                    fix.suggested_code,
                    1  # Replace only first occurrence
                )
                logger.info(f"✓ Applied fix to {filename} (exact match fallback)")
                fix_applied = True
            
            # Fallback Strategy 2: Whitespace-normalized match
            if not fix_applied and fix.issue.current_code.strip() in current_content:
                updated_code[filename] = current_content.replace(
                    fix.issue.current_code.strip(),
                    fix.suggested_code,
                    1
                )
                logger.info(f"✓ Applied fix to {filename} (whitespace-normalized fallback)")
                fix_applied = True
            
            if not fix_applied:
                logger.warning(f"✗ Could not apply fix to {filename}:{fix.issue.line}")
                logger.warning(f"   No valid line number and string match failed")
                logger.info(f"   💡 Fix explanation: {fix.explanation}")
                logger.info(f"   🔧 Suggested fix: {fix.suggested_code[:100]}")
        
        return updated_code


def create_validation_report(result: ValidationResult, output_file: Path) -> None:
    """Create a detailed validation report."""
    report = result.to_dict()
    
    # Add grouped issues
    issues_by_file = {}
    for issue in result.issues:
        if issue.file not in issues_by_file:
            issues_by_file[issue.file] = []
        issues_by_file[issue.file].append(issue.to_dict())
    
    report["issues_by_file"] = issues_by_file
    
    # Save report
    output_file.write_text(json.dumps(report, indent=2), encoding='utf-8')
    logger.info(f"Validation report saved to {output_file}")


# Example usage
if __name__ == "__main__":
    # Example: Validate Terraform code
    code = {
        "main.tf": """
resource "azurerm_storage_account" "example" {
  name                = "examplesa"
  resource_group_name = "example-rg"
  # Missing required attribute: location
}
""",
        "variables.tf": """
variable "location" {
  type = string
}
"""
    }
    
    pipeline = CodeQualityPipeline(iac_type="terraform")
    output_dir = Path("./output/validated")
    
    final_code, validation_result = pipeline.run(code, output_dir)
    
    print(f"Status: {validation_result.status}")
    print(f"Errors: {validation_result.error_count}")
    print(f"Warnings: {validation_result.warning_count}")
    
    # Create report
    create_validation_report(validation_result, output_dir / "validation_report.json")
