"""
Test Script for Code Quality Pipeline

Tests validation pipeline with sample Terraform code.
"""

import sys
from pathlib import Path
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from synthforge.code_quality_pipeline import (
    CodeQualityPipeline,
    create_validation_report
)


def test_valid_terraform():
    """Test with valid Terraform code."""
    print("\n" + "="*80)
    print("TEST 1: Valid Terraform Code")
    print("="*80)
    
    code = {
        "main.tf": """
resource "azurerm_storage_account" "this" {
  name                     = "examplesa"
  resource_group_name      = "example-rg"
  location                 = "eastus"
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
""",
        "variables.tf": """
variable "name" {
  type        = string
  description = "Storage account name"
}

variable "location" {
  type        = string
  description = "Azure region"
}
""",
        "outputs.tf": """
output "id" {
  value       = azurerm_storage_account.this.id
  description = "Storage account ID"
}
"""
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        pipeline = CodeQualityPipeline(iac_type="terraform")
        
        final_code, result = pipeline.run(code, output_dir)
        
        print(f"\nStatus: {result.status}")
        print(f"Errors: {result.error_count}")
        print(f"Warnings: {result.warning_count}")
        
        if result.status == "pass":
            print("✅ Test PASSED")
            return True
        else:
            print("❌ Test FAILED")
            for issue in result.issues:
                print(f"   - {issue.file}:{issue.line} - {issue.message}")
            return False


def test_invalid_terraform():
    """Test with invalid Terraform code (missing required attribute)."""
    print("\n" + "="*80)
    print("TEST 2: Invalid Terraform Code (missing location)")
    print("="*80)
    
    code = {
        "main.tf": """
resource "azurerm_storage_account" "this" {
  name                     = "examplesa"
  resource_group_name      = "example-rg"
  # Missing required: location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
"""
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        pipeline = CodeQualityPipeline(iac_type="terraform")
        
        final_code, result = pipeline.run(code, output_dir)
        
        print(f"\nStatus: {result.status}")
        print(f"Errors: {result.error_count}")
        print(f"Warnings: {result.warning_count}")
        
        if result.status == "fail" and result.error_count > 0:
            print("✅ Test PASSED (correctly detected error)")
            for issue in result.issues[:3]:  # Show first 3
                print(f"   - {issue.file}:{issue.line} - {issue.message}")
            return True
        else:
            print("❌ Test FAILED (should have detected error)")
            return False


def test_conditional_logic():
    """Test with problematic conditional logic."""
    print("\n" + "="*80)
    print("TEST 3: Terraform with Boolean Conditional Issue")
    print("="*80)
    
    code = {
        "locals.tf": """
locals {
  # Problematic: non-explicit boolean comparison
  has_identity = var.managed_identities.system_assigned || length(var.managed_identities.user_assigned_resource_ids) > 0
}
""",
        "main.tf": """
resource "azurerm_storage_account" "this" {
  name                     = var.name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  dynamic "identity" {
    for_each = local.has_identity ? [1] : []
    content {
      type = "SystemAssigned"
    }
  }
}
""",
        "variables.tf": """
variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "managed_identities" {
  type = object({
    system_assigned               = bool
    user_assigned_resource_ids    = list(string)
  })
  default = {
    system_assigned            = false
    user_assigned_resource_ids = []
  }
}
"""
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        pipeline = CodeQualityPipeline(iac_type="terraform")
        
        final_code, result = pipeline.run(code, output_dir)
        
        print(f"\nStatus: {result.status}")
        print(f"Errors: {result.error_count}")
        print(f"Warnings: {result.warning_count}")
        
        # This may pass terraform validate but should be flagged by logic checker
        if result.status in ["pass", "warning"]:
            print("✅ Syntax validation passed")
            print("ℹ️  Note: Logic issues (non-explicit booleans) require Code Quality Agent")
            return True
        else:
            print("❌ Unexpected errors:")
            for issue in result.issues:
                print(f"   - {issue.file}:{issue.line} - {issue.message}")
            return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("CODE QUALITY PIPELINE TESTS")
    print("="*80)
    print("\nPrerequisites:")
    print("  - Terraform CLI installed (terraform)")
    print("  - Azure provider configured")
    print("\nRunning tests...")
    
    results = []
    
    # Test 1: Valid code
    try:
        results.append(("Valid Terraform", test_valid_terraform()))
    except Exception as e:
        print(f"❌ Test 1 Error: {e}")
        results.append(("Valid Terraform", False))
    
    # Test 2: Invalid code
    try:
        results.append(("Invalid Terraform", test_invalid_terraform()))
    except Exception as e:
        print(f"❌ Test 2 Error: {e}")
        results.append(("Invalid Terraform", False))
    
    # Test 3: Logic issues
    try:
        results.append(("Boolean Logic", test_conditional_logic()))
    except Exception as e:
        print(f"❌ Test 3 Error: {e}")
        results.append(("Boolean Logic", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
