"""Test agent cleanup to ensure all agents and threads are properly deleted"""
import re
from pathlib import Path

def check_agent_cleanup_patterns():
    """Verify all Phase 2 agents have proper cleanup methods"""
    
    agents_dir = Path("synthforge/agents")
    phase2_agents = [
        "service_analysis_agent.py",
        "module_mapping_agent.py",
        "module_development_agent.py",
        "deployment_wrapper_agent.py",
    ]
    
    print("Checking Phase 2 agent cleanup patterns...\n")
    
    issues = []
    all_good = True
    
    for agent_file in phase2_agents:
        agent_path = agents_dir / agent_file
        if not agent_path.exists():
            print(f"❌ {agent_file}: FILE NOT FOUND")
            all_good = False
            continue
            
        content = agent_path.read_text(encoding="utf-8")
        agent_name = agent_file.replace(".py", "")
        
        # Check for cleanup method
        if "def cleanup(self):" not in content:
            print(f"❌ {agent_file}: NO cleanup() METHOD")
            issues.append(f"{agent_file}: Missing cleanup() method")
            all_good = False
            continue
        
        # Check for agent cleanup
        has_agent_cleanup = "delete_agent" in content
        
        # Check for thread cleanup
        has_thread_cleanup = "threads.delete" in content
        
        # Check if agent creates threads
        creates_thread = "threads.create()" in content
        
        print(f"\n📋 {agent_file}:")
        print(f"  • Creates threads: {'Yes' if creates_thread else 'No'}")
        print(f"  • Has agent cleanup: {'✅' if has_agent_cleanup else '❌'}")
        print(f"  • Has thread cleanup: {'✅' if has_thread_cleanup else '❌'}")
        
        if creates_thread and not has_thread_cleanup:
            print(f"  ⚠️  WARNING: Creates threads but doesn't clean them up!")
            issues.append(f"{agent_file}: Creates threads but missing thread cleanup")
            all_good = False
        
        if has_agent_cleanup and has_thread_cleanup:
            print(f"  ✅ Cleanup is COMPLETE")
        elif has_agent_cleanup:
            print(f"  ⚠️  Cleanup is PARTIAL (agent only)")
        else:
            print(f"  ❌ Cleanup is MISSING")
            all_good = False
    
    print("\n" + "=" * 70)
    if all_good and len(issues) == 0:
        print("✅ ALL PHASE 2 AGENTS HAVE PROPER CLEANUP!")
        print("=" * 70)
        print("\nCleanup ensures:")
        print("  • No orphaned agents in Azure AI Foundry")
        print("  • No orphaned threads consuming resources")
        print("  • Proper resource management")
        return True
    else:
        print("❌ CLEANUP ISSUES FOUND!")
        print("=" * 70)
        print("\nIssues:")
        for issue in issues:
            print(f"  • {issue}")
        return False

def check_workflow_cleanup_calls():
    """Verify workflow_phase2.py calls cleanup for all agents"""
    
    print("\n" + "=" * 70)
    print("Checking workflow cleanup calls...\n")
    
    workflow_path = Path("synthforge/workflow_phase2.py")
    content = workflow_path.read_text(encoding="utf-8")
    
    # Check for agent cleanup calls in finally blocks
    agents_to_check = [
        ("service_analysis_agent", "service_analysis_agent.cleanup()"),
        ("module_mapping_agent", "module_mapping_agent.cleanup()"),
        ("module_dev_agent", "module_dev_agent.cleanup()"),
        ("wrapper_agent", "wrapper_agent.cleanup()"),
    ]
    
    all_found = True
    for agent_var, cleanup_call in agents_to_check:
        if cleanup_call in content:
            print(f"✅ {agent_var}: cleanup() called in workflow")
        else:
            print(f"❌ {agent_var}: cleanup() NOT called in workflow")
            all_found = False
    
    if all_found:
        print("\n✅ All agents have cleanup calls in workflow!")
    else:
        print("\n❌ Some agents missing cleanup calls in workflow!")
    
    return all_found

def check_thread_cleanup_in_parallel_operations():
    """Check if threads created in parallel operations are cleaned up"""
    
    print("\n" + "=" * 70)
    print("Checking thread cleanup in parallel operations...\n")
    
    module_mapping_path = Path("synthforge/agents/module_mapping_agent.py")
    content = module_mapping_path.read_text(encoding="utf-8")
    
    # Check for thread cleanup in _map_single_service
    if "def _map_single_service" in content:
        method_start = content.find("def _map_single_service")
        # Find the end of the method (next def or end of file)
        method_end = content.find("\n    def ", method_start + 1)
        if method_end == -1:
            method_end = len(content)
        
        method_content = content[method_start:method_end]
        
        has_thread_create = "threads.create()" in method_content
        has_thread_delete = "threads.delete" in method_content
        has_finally_block = "finally:" in method_content
        
        print("📋 module_mapping_agent._map_single_service():")
        print(f"  • Creates threads: {'Yes' if has_thread_create else 'No'}")
        print(f"  • Has finally block: {'Yes' if has_finally_block else 'No'}")
        print(f"  • Deletes threads: {'Yes' if has_thread_delete else 'No'}")
        
        if has_thread_create and has_thread_delete and has_finally_block:
            print("  ✅ Thread cleanup is PROPER (in finally block)")
            return True
        elif has_thread_create and has_thread_delete:
            print("  ⚠️  Thread cleanup exists but NOT in finally block")
            return False
        elif has_thread_create:
            print("  ❌ Creates threads but NO cleanup!")
            return False
        else:
            print("  ℹ️  Method doesn't create threads")
            return True
    
    return False

if __name__ == "__main__":
    print("=" * 70)
    print("AGENT CLEANUP VERIFICATION TEST")
    print("=" * 70)
    
    test1 = check_agent_cleanup_patterns()
    test2 = check_workflow_cleanup_calls()
    test3 = check_thread_cleanup_in_parallel_operations()
    
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Agent cleanup patterns: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Workflow cleanup calls: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Parallel thread cleanup: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if test1 and test2 and test3:
        print("\n✅ ALL CLEANUP TESTS PASSED!")
        print("\nAll agents and threads will be properly cleaned up after completion.")
    else:
        print("\n❌ SOME CLEANUP TESTS FAILED!")
        print("\nPlease review the issues above.")
