#!/usr/bin/env python3
"""
SynthForge.AI - Main Entry Point

Azure Architecture Diagram Analyzer powered by Microsoft Foundry.
Run directly with: python main.py <image>
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def print_msg(message: str, style: str = None, error: bool = False):
    """Print a message with optional Rich styling."""
    if RICH_AVAILABLE and console:
        console.print(message, style=style)
    else:
        output = sys.stderr if error else sys.stdout
        # Strip Rich markup for plain output
        import re
        plain = re.sub(r'\[/?[^\]]+\]', '', message)
        print(plain, file=output)


def print_error(message: str):
    """Print an error message."""
    if RICH_AVAILABLE and console:
        console.print(f"[red]Error:[/red] {message}")
    else:
        print(f"Error: {message}", file=sys.stderr)


def print_success(message: str):
    """Print a success message."""
    if RICH_AVAILABLE and console:
        console.print(f"[green]✓[/green] {message}")
    else:
        print(f"✓ {message}")


def check_azure_authentication() -> bool:
    """
    Check if Azure authentication is valid.
    Uses DefaultAzureCredential to validate access to Azure Cognitive Services.
    
    Returns:
        True if authentication is valid, False otherwise.
    """
    try:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        from azure.core.exceptions import ClientAuthenticationError
        from synthforge.config import get_settings
        
        # Check PROJECT_ENDPOINT first
        config = get_settings()
        if not config.project_endpoint:
            print_error("PROJECT_ENDPOINT is not configured.")
            print_msg("[dim]Please set the PROJECT_ENDPOINT environment variable:[/dim]")
            print_msg("  export PROJECT_ENDPOINT=https://<your-hub>.services.ai.azure.com/api/projects/<project>")
            return False
        
        # Use DefaultAzureCredential (prefers Azure CLI)
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
        
        # Try to get a token for Cognitive Services
        try:
            token_provider = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default"
            )
            token = token_provider()
            if token:
                print_success("Azure authentication valid")
                return True
        except ClientAuthenticationError as e:
            error_msg = str(e)
            
            print_error("Azure authentication failed.")
            print_msg("[dim]Please authenticate using one of the following methods:[/dim]")
            print_msg("  az login                                                    # Azure CLI")
            print_msg("  azd auth login --scope https://cognitiveservices.azure.com/.default  # Azure Developer CLI")
            print_msg("")
            print_msg("[dim]Error details:[/dim]")
            
            if "reauthentication required" in error_msg.lower():
                print_msg("  Token expired - reauthentication required")
            elif "AzureCliCredential" in error_msg and "Failed to invoke" in error_msg:
                print_msg("  Azure CLI not found or not logged in")
            elif "AzureDeveloperCliCredential" in error_msg:
                print_msg("  Azure Developer CLI not logged in")
            else:
                print_msg(f"  {error_msg[:200]}...")
            
            return False
                
    except ImportError as e:
        print_error(f"Required package not installed: {e}")
        print_msg("[dim]Install with: pip install azure-identity[/dim]")
        return False
    except Exception as e:
        print_error(f"Authentication check failed: {e}")
        return False


def setup_logging(level: str = "INFO", quiet: bool = False) -> None:
    """Configure logging with Rich handler.
    
    Args:
        level: Logging level for SynthForge (DEBUG, INFO, WARNING, ERROR)
        quiet: If True, suppress verbose HTTP request logs from libraries
    """
    if RICH_AVAILABLE:
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format="%(message)s",
            handlers=[RichHandler(console=console, rich_tracebacks=True)],
        )
    else:
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    
    if quiet:
        # Suppress verbose HTTP request logs from azure, httpx, httpcore, openai
        for logger_name in [
            "azure",
            "azure.core.pipeline.policies.http_logging_policy",
            "azure.identity",
            "httpx",
            "httpcore",
            "openai",
            "openai._base_client",
        ]:
            logging.getLogger(logger_name).setLevel(logging.WARNING)


def main():
    """Main entry point wrapper."""
    asyncio.run(async_main())


async def async_main():
    """Async main entry point with all CLI logic."""
    parser = argparse.ArgumentParser(
        description="SynthForge.AI - Azure Architecture Diagram Analyzer + IaC Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: Phase 1 extraction + Phase 2 IaC generation (Terraform)
  python main.py architecture.png

  # Extract design only (Phase 1) - skip IaC generation
  python main.py architecture.png --extract

  # Generate Bicep instead of Terraform
  python main.py architecture.png --iac-format bicep

  # Generate both Terraform and Bicep
  python main.py architecture.png --iac-format both

  # Phase 1 + Phase 2 with custom output
  python main.py diagram.png --output ./analysis --iac-format terraform
  
  # Skip interactive review (auto-approve all)
  python main.py architecture.png --no-interactive
  
  # Enable debug logging
  python main.py diagram.png --log-level DEBUG

Phase 2 Workflow (IaC Generation):
  Stage 1: Service Analysis - Extract Azure services from design
  Stage 2: User Validation - Review and approve service list
  Stage 3: Module Mapping - Map to Azure Verified Modules / Terraform
  Stage 4: Module Generation - Generate reusable IaC modules
  Stage 5: Deployment Wrappers - Generate deployment orchestration
  Stage 6: ADO Pipelines - Generate CI/CD pipelines
  
  Output: ./iac/terraform/ or ./iac/bicep/ with production-ready modules

Prerequisites for Deployment:
  See docs/PHASE2_PREREQUISITES.md for required platform inputs

Environment Variables:
  PROJECT_ENDPOINT              Azure AI Foundry project endpoint (required)
  MODEL_DEPLOYMENT_NAME         Model deployment name (default: gpt-4o)
  OUTPUT_DIR                    Default output directory (default: ./output)
        """,
    )
    
    parser.add_argument(
        "image",
        type=Path,
        nargs='?',  # Make image optional
        help="Path to the architecture diagram image (PNG, JPG, etc.). Required for Phase 1, optional if using --skip-phase1",
    )
    
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Skip interactive review (default: interactive mode enabled)",
    )
    
    parser.add_argument(
        "--no-security",
        action="store_true",
        help="Skip security recommendations",
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("./output"),
        help="Output directory for generated files (default: ./output)",
    )
    
    parser.add_argument(
        "--iac",
        action="store_true",
        help="Generate IaC code (runs Phase 1 extraction + Phase 2 IaC generation)",
    )
    
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Run Phase 1 only (design extraction without IaC generation)",
    )
    
    parser.add_argument(
        "--skip-phase1",
        action="store_true",
        help="Skip Phase 1 and run Phase 2 only (requires existing Phase 1 outputs)",
    )
    
    parser.add_argument(
        "--iac-format",
        choices=["terraform", "bicep", "both"],
        default="terraform",
        help="IaC format for Phase 2 generation (default: terraform)",
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "table", "summary"],
        default="summary",
        help="Output format (default: summary)",
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        help="Logging level - enables verbose HTTP logs (DEBUG, INFO, WARNING, ERROR - case insensitive, default: WARNING)",
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose HTTP request logs from Azure/OpenAI libraries",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="SynthForge.AI 0.1.0",
    )
    
    args = parser.parse_args()
    
    # Setup logging - default is quiet (WARNING), verbose when --log-level or --verbose passed
    # Make log level case insensitive
    log_level = args.log_level.upper() if args.log_level else "WARNING"
    
    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    if log_level not in valid_levels:
        parser.error(f"Invalid log level: {args.log_level}. Must be one of {', '.join(valid_levels)} (case insensitive)")
    
    quiet = not (args.log_level is not None or args.verbose)
    setup_logging(log_level, quiet=quiet)
    
    # Display banner
    if RICH_AVAILABLE and console:
        console.print(Panel.fit(
            "[bold blue]SynthForge.AI[/bold blue]\n"
            "[dim]Azure Architecture Diagram Analyzer[/dim]",
            border_style="blue",
        ))
        
        # Display pipeline overview
        console.print("\n[bold cyan]Phase 1:[/bold cyan] Design Extraction & Requirements Gathering")
        console.print("[dim]6-Stage Multi-Agent Pipeline for Azure architecture analysis[/dim]\n")
        console.print("  [dim]0.[/dim] Description         -> Pre-analysis for component context")
        console.print("  [dim]1.[/dim] Vision Agent        -> Detect Azure icons from diagram (GPT-4o Vision)")
        console.print("  [dim]2.[/dim] Filter Agent        -> Classify resources as architectural/non-architectural")
        console.print("  [dim]3.[/dim] Interactive         -> User review and correction of detections")
        console.print("  [dim]4.[/dim] Network Flow        -> Analyze connections, VNets, and data flows")
        console.print("  [dim]5.[/dim] Security Agent      -> Generate RBAC, PE, and MI recommendations")
        console.print("  [dim]6.[/dim] Build Analysis       -> Generate IaC-ready JSON outputs")
        console.print("")
        iac_format_display = args.iac_format.upper() if args.iac_format != "both" else "Terraform + Bicep"
        console.print(f"[bold cyan]Phase 2:[/bold cyan] Infrastructure as Code Generation ([yellow]{iac_format_display}[/yellow])")
        console.print("[dim]6-Stage Multi-Agent Pipeline for IaC module generator[/dim]\n")
        console.print("  [dim]0.[/dim] Load                -> Load Phase 1 analysis outputs")
        console.print("  [dim]1.[/dim] Service Analysis    -> Extract requirements from Phase 1")
        console.print("  [dim]2.[/dim] User Validation     -> Review services & recommendations")
        console.print("  [dim]3.[/dim] Module Mapping      -> Map to AVM/Terraform modules")
        console.print("  [dim]4.[/dim] Module Generation   -> Generate reusable IaC modules")
        console.print("  [dim]5.[/dim] Deployment Wrappers -> Generate deployment orchestration")
        console.print("  [dim]6.[/dim] ADO Pipelines       -> Generate CI/CD pipelines")
        console.print("")
        console.print("")
    else:
        print("\n" + "=" * 50)
        print("  SynthForge.AI")
        print("  Azure Architecture Diagram Analyzer")
        print("=" * 50)
        print("\nPhase 1: Design Extraction & Requirements Gathering")
        print("6-Stage Multi-Agent Pipeline for Azure architecture analysis\n")
        print("  0.  Description     - Pre-analysis for component context (optional)")
        print("  1.  Vision Agent    - Detect Azure icons from diagram (GPT-4o Vision)")
        print("  2.  Filter Agent    - Classify resources as architectural/non-architectural")
        print("  3.  Interactive     - User review and correction of detections")
        print("  4.  Network Flow    - Analyze connections, VNets, and data flows")
        print("  5.  Security Agent  - Generate RBAC, PE, and MI recommendations")
        print("  6.  Build Analysis  - Generate IaC-ready JSON outputs")
        print("")
        iac_format_display = args.iac_format.upper() if args.iac_format != "both" else "Terraform + Bicep"
        print(f"Phase 2: Infrastructure as Code Generation ({iac_format_display})")
        print("6-Stage Multi-Agent Pipeline for IaC module generator\n")
        print("  1.  Service Analysis    -> Extract requirements from Phase 1")
        print("  2.  User Validation     -> Review services & recommendations")
        print("  3.  Module Mapping      -> Map to AVM/Terraform modules")
        print("  4.  Module Generation   -> Generate reusable IaC modules")
        print("  5.  Deployment Wrappers -> Generate deployment orchestration")
        print("  6.  ADO Pipelines       -> Generate CI/CD pipelines\n")
        print("")
        print("")
    
    # Check Azure authentication before running (required)
    print_msg("\n[dim]Checking Azure authentication...[/dim]")
    if not check_azure_authentication():
        print_error("Analysis aborted. Please authenticate and try again.")
        sys.exit(1)
    print_msg("")  # Blank line after auth check
    
    # Determine which phases to run based on CLI arguments
    # Default: Phase 1 only, then Phase 2 if Phase 1 succeeds
    # --extract: Phase 1 only (no Phase 2)
    # --iac: Phase 1 + Phase 2 (IaC generation)
    # --skip-phase1: Phase 2 only (requires existing Phase 1 outputs)
    if args.extract and args.iac:
        print_error("Cannot use both --extract and --iac flags together")
        sys.exit(1)
    
    if args.skip_phase1 and args.extract:
        print_error("Cannot use both --skip-phase1 and --extract flags together")
        sys.exit(1)
    
    if args.skip_phase1:
        # Explicit: Phase 2 only (skip Phase 1)
        run_phase1 = False
        run_phase2 = True
        print_msg("[yellow]Skipping Phase 1 - Running Phase 2 only with existing outputs[/yellow]\n")
    elif args.extract:
        # Explicit: Phase 1 only
        run_phase1 = True
        run_phase2 = False
    elif args.iac:
        # Explicit: Phase 1 + Phase 2
        run_phase1 = True
        run_phase2 = True
    else:
        # Default: Phase 1, then Phase 2 on success
        run_phase1 = True
        run_phase2 = True  # Will run Phase 2 after Phase 1 succeeds
    
    # Phase 1 requires image, Phase 2 requires Phase 1 outputs
    if run_phase1:
        if not args.image:
            print_error("Image file is required for Phase 1")
            print_msg("Usage: python main.py <image> [options]")
            print_msg("Or use --skip-phase1 to run Phase 2 only")
            sys.exit(1)
        
        if not args.image.exists():
            print_error(f"Image file not found: {args.image}")
            sys.exit(1)
        
        # Validate image format
        if args.image.suffix.lower() not in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]:
            print_msg(f"[yellow]Warning:[/yellow] File may not be a supported image format: {args.image.suffix}")
    
    phase1_result = None
    phase2_result = None
    
    # =========================================================================
    # PHASE 1: Design Extraction & Requirements Gathering
    # =========================================================================
    if run_phase1:
        print_msg(f"[dim]Running Phase 1: Design Extraction[/dim]")
        print_msg(f"[dim]Analyzing:[/dim] {args.image}")
        
        # Show which stages will be skipped
        if args.no_interactive:
            print_msg(f"[dim]  • Interactive review: skipped (--no-interactive)[/dim]")
        if args.no_security:
            print_msg(f"[dim]  • Security analysis: skipped (--no-security)[/dim]")
        print_msg("")
        
        phase1_result = await run_phase1_analysis(args)
        
        if not phase1_result.success:
            print_error(phase1_result.error or "Phase 1 failed")
            sys.exit(1)
        
        # Export Phase 1 outputs
        export_phase1_outputs(phase1_result, args.output, args.format)
        
        print_msg(f"\n[bold]{'='*60}[/bold]")
        print_success(f"Phase 1 completed in {phase1_result.duration_seconds:.1f}s")
        print_msg(f"[bold]{'='*60}[/bold]\n")
    
    # =========================================================================
    # PHASE 2: IaC Code Generation
    # =========================================================================
    if run_phase2:
        print_msg(f"\n[bold cyan]{'='*60}[/bold cyan]")
        print_msg(f"[bold cyan]PHASE 2: Infrastructure as Code Generation[/bold cyan]")
        print_msg(f"[bold cyan]{'='*60}[/bold cyan]\n")
        
        # Check Phase 1 outputs exist
        analysis_file = args.output / "architecture_analysis.json"
        if not analysis_file.exists():
            print_error("Phase 1 outputs not found!")
            print_msg("Please run Phase 1 first or use --iac to run both phases")
            sys.exit(1)
        
        from synthforge.workflow_phase2 import Phase2Workflow
        from synthforge.config import get_settings
        from synthforge.workflow import WorkflowProgress
        
        settings = get_settings()
        
        # Phase 2 stage definitions (matching Phase 1 pattern)
        PHASE2_STAGE_INFO = {
            "load": ("Stage 0/6", "Phase 1 Loading", "Loading Phase 1 analysis outputs..."),
            "service_analysis": ("Stage 1/6", "Service Analysis", "Extracting service requirements from Phase 1..."),
            "validation": ("Stage 2/6", "User Validation", "Reviewing services and recommendations..."),
            "module_mapping": ("Stage 3/6", "Module Mapping", "Mapping to Azure Verified Modules..."),
            "module_development": ("Stage 4/6", "Module Generation", "Generating reusable IaC modules..."),
            "deployment_wrappers": ("Stage 5/6", "Deployment Wrappers", "Generating deployment orchestration..."),
            "ado_pipelines": ("Stage 6/6", "ADO Pipelines", "Generating CI/CD pipelines..."),
            "finalize": ("Finalization", "Saving Results", "Saving Phase 2 outputs..."),
            "complete": ("Complete", "Generation Finished", "IaC generation complete!"),
        }
        
        current_stage_p2 = {"name": None}
        
        async def phase2_progress_callback(progress: WorkflowProgress):
            """Display Phase 2 progress updates with stage indicators."""
            stage = progress.stage
            message = progress.message
            
            # Get stage info
            stage_num, stage_name, _ = PHASE2_STAGE_INFO.get(stage, ("", stage.title(), ""))
            
            # Check if we're starting a new stage
            if stage != current_stage_p2["name"]:
                if current_stage_p2["name"] is not None:
                    # Print completion of previous stage
                    prev_num, prev_name, _ = PHASE2_STAGE_INFO.get(current_stage_p2["name"], ("", "", ""))
                    if prev_num and "Complete" not in prev_num and "Finalization" not in prev_num:
                        print_msg(f"  [green]✓[/green] {prev_name} completed")
                
                # Print new stage start
                if stage_num and "Complete" not in stage_num:
                    print_msg(f"\n[bold cyan]▶ {stage_num}: {stage_name}[/bold cyan]")
                
                current_stage_p2["name"] = stage
            
            # Print stage progress details
            if message and "Complete" not in str(stage_num):
                print_msg(f"  [dim]->[/dim] {message}")
        
        workflow = Phase2Workflow(
            output_dir=args.output,
            iac_dir=settings.iac_dir,
            iac_format=args.iac_format,
            pipeline_platform="azure-devops",
        )
        workflow.on_progress(phase2_progress_callback)
        
        try:
            phase2_result = await workflow.run()
            
            print_msg(f"\n[bold]{'='*60}[/bold]")
            if phase2_result.get("status") == "completed":
                print_success(f"✓ Phase 2 complete! Generated {phase2_result.get('module_development', {}).get('total_count', 0)} modules")
                print_msg(f"Output: {phase2_result.get('module_development', {}).get('output_directory', settings.iac_dir)}")
            elif phase2_result.get("status") == "cancelled":
                print_msg("[yellow]Phase 2 cancelled by user[/yellow]")
            else:
                print_error(f"Phase 2 failed: {phase2_result.get('error', 'Unknown error')}")
            print_msg(f"[bold]{'='*60}[/bold]\n")
            
        except Exception as e:
            print_error(f"Phase 2 failed: {e}")
            if args.verbose or log_level == "DEBUG":
                import traceback
                traceback.print_exc()
            sys.exit(1)
        finally:
            workflow.cleanup()


async def run_phase1_analysis(args):
    """Run Phase 1: Design Extraction & Requirements Gathering."""
    from synthforge.workflow import ArchitectureWorkflow, WorkflowProgress
    
    # Stage descriptions for Phase 1: Design Extraction & Requirements Gathering
    # Stages: 0 (Description), 1a-c (Detection), 2-6 (Analysis)
    STAGE_INFO = {
        "description": ("Stage 0/6", "Architecture Description", "Pre-analyzing architecture for context..."),
        "vision": ("Stage 1/6", "Icon Detection", "Extracting Azure service icons from diagram..."),
        "vision_ocr": ("Stage 1a+1b/6", "Vision + OCR", "Running Vision and OCR detection in parallel..."),
        "vision_merge": ("Stage 1c/6", "Detection Merge", "Merging and deduplicating detections..."),
        "filter": ("Stage 2/6", "Resource Classification", "Classifying detected architecture elements..."),
        "interactive": ("Stage 3/6", "Design Review", "User review of extracted architecture..."),
        "network_flows": ("Stage 4/6", "Network Topology", "Extracting connections, VNets, and data flows..."),
        "security": ("Stage 5/6", "Security Requirements", "Extracting RBAC, PE, and security configurations..."),
        "finalize": ("Stage 6/6", "Build Requirements", "Building IaC-ready requirements output..."),
        "complete": ("Complete", "Extraction Finished", "Architecture extraction complete!"),
    }
    
    current_stage = {"name": None}
    
    async def progress_callback(progress: WorkflowProgress):
        """Display progress updates with stage indicators."""
        stage = progress.stage
        message = progress.message
        
        # Get stage info
        stage_num, stage_name, _ = STAGE_INFO.get(stage, ("", stage.title(), ""))
        
        # Check if we're starting a new stage
        if stage != current_stage["name"]:
            if current_stage["name"] is not None:
                # Print completion of previous stage
                prev_num, prev_name, _ = STAGE_INFO.get(current_stage["name"], ("", "", ""))
                if prev_num and "Complete" not in prev_num:
                    print_msg(f"  [green]✓[/green] {prev_name} completed")
            
            # Print new stage start
            if stage_num and "Complete" not in stage_num:
                print_msg(f"\n[bold cyan]▶ {stage_num}: {stage_name}[/bold cyan]")
            
            current_stage["name"] = stage
        
        # Print stage progress details
        if message and "Complete" not in str(stage_num):
            print_msg(f"  [dim]->[/dim] {message}")
    
    workflow = ArchitectureWorkflow(
        interactive=not args.no_interactive,
        include_security=not args.no_security,
    )
    workflow.on_progress(progress_callback)
    
    try:
        result = await workflow.analyze(args.image)
        return result
    except KeyboardInterrupt:
        print_msg("\n[yellow]Analysis cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        # Import custom exceptions for better error messages
        from synthforge.workflow import (
            SynthForgeError, 
            AzureServiceError, 
            TimeoutError as SynthForgeTimeoutError,
            AuthenticationError as SynthForgeAuthError,
        )
        
        # Provide user-friendly error messages based on exception type
        if isinstance(e, SynthForgeTimeoutError):
            print_msg("\n")
            print_error("Azure AI Foundry Request Timed Out")
            print_msg("[dim]The Azure service is taking too long to respond.[/dim]")
            print_msg("")
            print_msg("[bold]What to do:[/bold]")
            print_msg("  1. [cyan]Wait a moment[/cyan] and try again - this is often temporary")
            print_msg("  2. Check [cyan]https://status.azure.com/[/cyan] for service status")
            print_msg("  3. Try a smaller image if the current one is very large")
            if hasattr(e, 'stage') and e.stage:
                print_msg(f"\n[dim]Failed during: {e.stage}[/dim]")
        elif isinstance(e, SynthForgeAuthError):
            print_msg("\n")
            print_error("Azure Authentication Failed")
            print_msg("[dim]Please authenticate with Azure:[/dim]")
            print_msg("  az login")
            print_msg("  [dim]or[/dim]")
            print_msg("  azd auth login --scope https://cognitiveservices.azure.com/.default")
        elif isinstance(e, AzureServiceError):
            print_msg("\n")
            print_error(str(e))
            if hasattr(e, 'stage') and e.stage:
                print_msg(f"[dim]Failed during: {e.stage}[/dim]")
        else:
            print_error(f"Analysis failed: {e}")
        
        if args.verbose or log_level == "DEBUG":
            print_msg("\n[dim]Stack trace:[/dim]")
            import traceback
            traceback.print_exc()
        
        sys.exit(1)


def export_phase1_outputs(result, output_dir, format_type):
    """Export Phase 1 analysis results to JSON files."""
    import json
    from collections import Counter
    
    # Handle result
    if not result.success:
        return
    
    # Export IaC-ready outputs
    if result.analysis:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export full architecture analysis JSON
        analysis_path = output_dir / "architecture_analysis.json"
        result.analysis.save(str(analysis_path))
        print_success(f"Full analysis: {analysis_path}")
        
        # Export resource summary (instances + grouped resource types)
        # IMPORTANT: Phase 2 IaC needs to distinguish:
        #  - Resource Types (unique service_type + arm_type combinations) → 1 IaC module
        #  - Resource Instances (individual detections) → Multiple deployments of same module
        summary_path = output_dir / "resource_summary.json"
        import re
        
        type_groups = {}
        for r in result.analysis.resources:
            # Normalize service_type by removing parenthetical content
            # Example: "Azure App Service (Zone 1)" -> "Azure App Service"
            normalized_service_type = r.service_type
            if '(' in normalized_service_type:
                normalized_service_type = normalized_service_type.split('(')[0].strip()
            
            key = (normalized_service_type, r.resource_type)
            if key not in type_groups:
                type_groups[key] = {
                    "service_type": normalized_service_type,
                    "arm_type": r.resource_type,
                    "instances": [],
                    "confidences": [],
                }
            type_groups[key]["instances"].append({
                "id": r.id,
                "name": r.name,
                "confidence": r.confidence,
                "original_service_type": r.service_type,  # Preserve original for debugging
            })
            type_groups[key]["confidences"].append(r.confidence)

        resource_types = []
        for group in type_groups.values():
            instance_count = len(group["instances"])
            resource_types.append({
                "service_type": group["service_type"],
                "arm_type": group["arm_type"],
                "instance_count": instance_count,
                "instances": group["instances"],
                "max_confidence": max(group["confidences"]) if group["confidences"] else 0.0,
            })

        summary_data = {
            "detection_statistics": {
                "total_detected": result.analysis.total_detected,
                "total_identified": result.analysis.total_identified,
                "total_resource_types": len(resource_types),  # Number of unique modules needed
                "by_method": result.analysis.detection_methods,
            },
            "total_resources": len(result.analysis.resources),
            "total_resource_types": len(resource_types),
            "total_flows": len(result.analysis.network_flows),
            "total_vnets": len(result.analysis.vnets),
            "total_subnets": len(result.analysis.subnets),
            "resource_types": resource_types,
            "resources": [
                {
                    "name": r.name,
                    "type": r.service_type,
                    "arm_type": r.resource_type,
                    "managed_identity": r.security.managed_identity.enabled,
                    "private_endpoint": {
                        "enabled": r.security.private_endpoint.enabled,
                        "dns_zone": r.security.private_endpoint.private_dns_zone,
                    },
                    "rbac_roles": [
                        {
                            "role": a.role_name,
                            "for_service": a.source_service,
                        }
                        for a in r.security.rbac_assignments
                    ],
                }
                for r in result.analysis.resources
            ],
        }
        with open(summary_path, "w") as f:
            json.dump(summary_data, f, indent=2)
        print_success(f"Resource summary: {summary_path}")
        
        # Export RBAC assignments
        rbac_path = output_dir / "rbac_assignments.json"
        rbac_data = {"assignments": []}
        for resource in result.analysis.resources:
            for assignment in resource.security.rbac_assignments:
                rbac_data["assignments"].append({
                    "target_resource": resource.name,
                    "target_type": resource.service_type,
                    "role_name": assignment.role_name,
                    "principal_type": assignment.principal_type,
                    "source_service": assignment.source_service,
                    "justification": assignment.justification,
                })
        with open(rbac_path, "w") as f:
            json.dump(rbac_data, f, indent=2)
        print_success(f"RBAC assignments: {rbac_path}")
        
        # Export private endpoint configuration
        pe_path = output_dir / "private_endpoints.json"
        pe_data = {
            "private_endpoints": [
                {
                    "resource_name": r.name,
                    "resource_type": r.service_type,
                    "enabled": r.security.private_endpoint.enabled,
                    "recommended": r.security.private_endpoint.recommended,
                    "private_dns_zone": r.security.private_endpoint.private_dns_zone,
                    "group_ids": r.security.private_endpoint.group_ids,
                    "guidance": r.security.private_endpoint.guidance,
                }
                for r in result.analysis.resources
                if r.security.private_endpoint.enabled or r.security.private_endpoint.recommended
            ],
            "vnet_integration": [
                {
                    "resource_name": r.name,
                    "resource_type": r.service_type,
                    "recommended": r.security.vnet_integration.recommended,
                    "subnet_delegation": r.security.vnet_integration.subnet_delegation,
                    "requires_dedicated_subnet": r.security.vnet_integration.requires_dedicated_subnet,
                    "recommended_subnet_size": r.security.vnet_integration.recommended_subnet_size,
                    "guidance": r.security.vnet_integration.guidance,
                }
                for r in result.analysis.resources
                if r.security.vnet_integration.recommended
            ],
        }
        with open(pe_path, "w") as f:
            json.dump(pe_data, f, indent=2)
        print_success(f"Private endpoints: {pe_path}")
        
        # Export network flows
        flows_path = output_dir / "network_flows.json"
        flows_data = {
            "flows": [f.to_dict() for f in result.analysis.network_flows],
            "vnets": result.analysis.vnets,
            "subnets": result.analysis.subnets,
        }
        with open(flows_path, "w") as f:
            json.dump(flows_data, f, indent=2)
        print_success(f"Network flows: {flows_path}")
        
        # Display summary based on format
        if format_type == "table":
            if RICH_AVAILABLE and console:
                table = Table(title="Detected Azure Resources")
                table.add_column("Name", style="cyan")
                table.add_column("Type", style="green")
                table.add_column("Private Endpoint", style="yellow")
                table.add_column("Managed Identity", style="magenta")
                
                for r in result.analysis.resources:
                    pe_status = "✓" if r.security.private_endpoint.enabled else "-"
                    mi_status = "✓" if r.security.managed_identity.enabled else "-"
                    table.add_row(r.name, r.service_type, pe_status, mi_status)
                
                console.print(table)
            else:
                print("\nDetected Azure Resources:")
                print("-" * 80)
                for r in result.analysis.resources:
                    pe_status = "PE" if r.security.private_endpoint.enabled else "-"
                    mi_status = "MI" if r.security.managed_identity.enabled else "-"
                    print(f"  {r.name}: {r.service_type} [{pe_status}] [{mi_status}]")
        
        else:  # summary (default)
            # Group resources by type for cleaner display
            from collections import Counter
            type_counts = Counter(r.service_type for r in result.analysis.resources)
            
            print_msg(f"\n[bold]{'='*60}[/bold]")
            print_msg(f"[bold green]ANALYSIS COMPLETE[/bold green]")
            print_msg(f"[bold]{'='*60}[/bold]")
            
            # Detection statistics
            print_msg(f"\n[bold]Detection Summary:[/bold]")
            print_msg(f"  • Total resources detected: [cyan]{len(result.analysis.resources)}[/cyan]")
            print_msg(f"  • Network flows identified: [cyan]{len(result.analysis.network_flows)}[/cyan]")
            print_msg(f"  • VNet boundaries found: [cyan]{len(result.analysis.vnets)}[/cyan]")
            if result.security_recommendations:
                print_msg(f"  • Security recommendations: [cyan]{len(result.security_recommendations)}[/cyan]")
            
            # Resources by type
            print_msg(f"\n[bold]Resources by Type:[/bold]")
            for svc_type, count in type_counts.most_common():
                count_str = f"{count}x" if count > 1 else "  "
                print_msg(f"  {count_str} [cyan]{svc_type}[/cyan]")
            
            # Output files
            print_msg(f"\n[bold]Output Files:[/bold]")
            print_msg(f"  • {output_dir / 'architecture_analysis.json'}")
            print_msg(f"  • {output_dir / 'resource_summary.json'}")
            print_msg(f"  • {output_dir / 'rbac_assignments.json'}")
            print_msg(f"  • {output_dir / 'private_endpoints.json'}")
            print_msg(f"  • {output_dir / 'network_flows.json'}")


if __name__ == "__main__":
    main()
