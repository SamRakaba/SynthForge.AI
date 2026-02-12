"""
User Validation Workflow: Present service list for user approval/modification.

Similar to InteractiveAgent from Phase 1, presents generated service list
to user for review, acceptance, or modifications before code generation.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from synthforge.agents.service_analysis_agent import ServiceRequirement

logger = logging.getLogger(__name__)

# Try to import Rich for better formatting
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


@dataclass
class UserValidationResult:
    """Result from user validation."""
    
    approved: bool
    modified_services: List[ServiceRequirement]
    user_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "approved": self.approved,
            "modified_services": [s.to_dict() for s in self.modified_services],
            "user_notes": self.user_notes,
        }


class UserValidationWorkflow:
    """
    Interactive workflow for user validation of service list.
    
    Presents the extracted services to the user and allows:
    - Approval to proceed
    - Modifications (add/remove/change services)
    - Cancellation
    """
    
    def __init__(self):
        """Initialize user validation workflow."""
        self.logger = logger
    
    async def validate_services(
        self,
        services: List[ServiceRequirement],
        recommendations_summary: Optional[Dict[str, List[str]]] = None,
        needs_clarification: Optional[List[Dict[str, Any]]] = None,
        excluded_services: Optional[List[Dict[str, Any]]] = None,
    ) -> UserValidationResult:
        """
        Present services to user for validation.
        
        Args:
            services: List of extracted application services for IaC
            recommendations_summary: Consolidated recommendations from Phase 1 + research
            needs_clarification: Services with Unknown ARM types needing user input
            excluded_services: Foundational infrastructure excluded from IaC
            
        Returns:
            UserValidationResult with user decision
        """
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 2: User Validation")
        logger.info("=" * 80)
        
        # Handle services needing clarification FIRST (before showing main list)
        clarified_services = []
        if needs_clarification:
            clarified_services = await self._clarify_unknown_services(needs_clarification)
            # Add clarified services to the main list
            services = services + clarified_services
        
        # Display excluded services (informational)
        if excluded_services:
            self._display_excluded_services(excluded_services)
        
        # Display services by priority
        self._display_services(services)
        
        # Display recommendations summary
        if recommendations_summary:
            self._display_recommendations_summary(recommendations_summary)
        
        # Get user input
        logger.info("\n" + "=" * 80)
        logger.info("Review the service list and recommendations above.")
        logger.info("=" * 80)
        
        while True:
            choice = input(
                "\nOptions:\n"
                "  [A]pprove and continue\n"
                "  [M]odify service list\n"
                "  [C]ancel\n"
                "\nYour choice: "
            ).strip().upper()
            
            if choice == "A":
                logger.info("✓ User approved service list")
                return UserValidationResult(
                    approved=True,
                    modified_services=services,
                    user_notes="Approved as-is",
                )
            
            elif choice == "M":
                modified_services = await self._modify_services(services)
                logger.info("✓ User modified service list")
                return UserValidationResult(
                    approved=True,
                    modified_services=modified_services,
                    user_notes="Modified by user",
                )
            
            elif choice == "C":
                logger.warning("✗ User cancelled Phase 2")
                return UserValidationResult(
                    approved=False,
                    modified_services=[],
                    user_notes="Cancelled by user",
                )
            
            else:
                print("Invalid choice. Please enter A, M, or C.")
    
    def _display_services(self, services: List[ServiceRequirement]):
        """Display services in a readable format with rich console."""
        priority_groups = {
            1: [s for s in services if s.priority == 1],
            2: [s for s in services if s.priority == 2],
            3: [s for s in services if s.priority == 3],
        }
        
        if RICH_AVAILABLE and console:
            # Rich console formatting (matches Phase 1 style)
            console.print()
            console.print(Panel.fit(
                "[bold cyan]EXTRACTED AZURE SERVICES[/bold cyan]",
                border_style="cyan",
                box=box.DOUBLE
            ))
            console.print()
            
            for priority, group in priority_groups.items():
                if not group:
                    continue
                
                priority_names = {
                    1: "Foundation Services",
                    2: "Application Services",
                    3: "Integration Services",
                }
                
                # Create table for this priority group
                table = Table(
                    title=f"{priority_names.get(priority, f'Priority {priority}')}",
                    show_header=True,
                    header_style="bold magenta",
                    border_style="blue",
                    box=box.ROUNDED
                )
                
                table.add_column("#", style="dim", width=3)
                table.add_column("Service Type", style="cyan", width=25)
                table.add_column("Resource Name", style="green", width=20)
                table.add_column("Dependencies", style="yellow", width=15)
                table.add_column("Security", style="red", width=15)
                
                for i, service in enumerate(group, 1):
                    deps = ", ".join(service.dependencies[:2]) if service.dependencies else "-"
                    if service.dependencies and len(service.dependencies) > 2:
                        deps += f" +{len(service.dependencies)-2}"
                    
                    security = []
                    if service.security_requirements:
                        if service.security_requirements.get("managed_identity"):
                            security.append("MI")
                        if service.security_requirements.get("disable_public_access"):
                            security.append("Private")
                    security_str = ", ".join(security) if security else "-"
                    
                    table.add_row(
                        str(i),
                        service.service_type,
                        service.resource_name,
                        deps,
                        security_str
                    )
                
                console.print(table)
                console.print()
            
            console.print(Panel.fit(
                f"[bold]Total Services:[/bold] [cyan]{len(services)}[/cyan]",
                border_style="green"
            ))
            
        else:
            # Fallback to plain text (original implementation)
            print("\n" + "=" * 80)
            print("EXTRACTED AZURE SERVICES")
            print("=" * 80)
            
            for priority, group in priority_groups.items():
                if not group:
                    continue
                
                priority_names = {
                    1: "Foundation Services (VNet, Security)",
                    2: "Application Services (Compute, Data)",
                    3: "Integration Services (API Management, Monitoring)",
                }
                
                print(f"\n{priority_names.get(priority, f'Priority {priority}')}")
                print("-" * 80)
                
                for i, service in enumerate(group, 1):
                    print(f"\n{i}. {service.service_type}")
                    print(f"   Name: {service.resource_name}")
                    
                    if service.configurations:
                        print(f"   Config: {self._format_dict(service.configurations)}")
                    
                    if service.dependencies:
                        print(f"   Depends on: {', '.join(service.dependencies)}")
                    
                    if service.network_requirements:
                        print(f"   Network: {self._format_dict(service.network_requirements)}")
                    
                    if service.security_requirements:
                        print(f"   Security: {self._format_dict(service.security_requirements)}")
            
            print("\n" + "=" * 80)
            print(f"Total Services: {len(services)}")
            print("=" * 80)
    
    def _format_dict(self, d: Dict[str, Any]) -> str:
        """Format dictionary for display."""
        items = [f"{k}={v}" for k, v in d.items()]
        return ", ".join(items[:3]) + ("..." if len(items) > 3 else "")
    
    def _display_recommendations_summary(
        self,
        recommendations_summary: Dict[str, List[str]],
    ):
        """Display recommendations summary with rich formatting."""
        if RICH_AVAILABLE and console:
            console.print()
            console.print(Panel.fit(
                "[bold yellow]RECOMMENDATIONS SUMMARY[/bold yellow]",
                border_style="yellow",
                box=box.DOUBLE
            ))
            console.print()
            
            category_colors = {
                "security": "red",
                "networking": "blue",
                "configuration": "green",
                "dependencies": "magenta",
                "cost_optimization": "cyan",
            }
            
            category_titles = {
                "security": "🔒 Security",
                "networking": "🌐 Networking",
                "configuration": "⚙️  Configuration",
                "dependencies": "🔗 Dependencies",
                "cost_optimization": "💰 Cost Optimization",
            }
            
            for category, items in recommendations_summary.items():
                if not items:
                    continue
                
                color = category_colors.get(category, "white")
                title = category_titles.get(category, category.replace("_", " ").title())
                
                console.print(f"[bold {color}]{title}[/bold {color}]")
                for i, item in enumerate(items, 1):
                    console.print(f"  [dim]{i}.[/dim] {item}")
                console.print()
                
        else:
            # Fallback to plain text
            print("\n" + "=" * 80)
            print("RECOMMENDATIONS SUMMARY")
            print("=" * 80)
            
            for category, items in recommendations_summary.items():
                if not items:
                    continue
                
                print(f"\n{category.replace('_', ' ').upper()}")
                print("-" * 80)
                for i, item in enumerate(items, 1):
                    print(f"{i}. {item}")
            
            print("\n" + "=" * 80)
    
    async def _modify_services(
        self,
        services: List[ServiceRequirement],
    ) -> List[ServiceRequirement]:
        """Interactive service modification."""
        print("\n" + "=" * 80)
        print("SERVICE MODIFICATION")
        print("=" * 80)
        print("\nCurrent services:")
        
        for i, service in enumerate(services, 1):
            print(f"{i}. {service.service_type} ({service.resource_name})")
        
        print("\nModification options:")
        print("  - Enter service number to remove it")
        print("  - Enter 'done' to finish")
        print("  - Note: Adding new services requires re-running ServiceAnalysisAgent")
        
        modified_services = services.copy()
        
        while True:
            choice = input("\nEnter service number to remove (or 'done'): ").strip().lower()
            
            if choice == "done":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(modified_services):
                    removed = modified_services.pop(idx)
                    print(f"✓ Removed: {removed.service_type} ({removed.resource_name})")
                    
                    # Re-display remaining services
                    print("\nRemaining services:")
                    for i, service in enumerate(modified_services, 1):
                        print(f"{i}. {service.service_type} ({service.resource_name})")
                else:
                    print("Invalid service number")
            except ValueError:
                print("Invalid input. Enter a service number or 'done'")
        
        logger.info(f"Modified service list: {len(services)} → {len(modified_services)} services")
        return modified_services
    
    async def _clarify_unknown_services(
        self,
        needs_clarification: List[Dict[str, Any]],
    ) -> List[ServiceRequirement]:
        """
        Interactive clarification for services with Unknown ARM types or categories.
        
        Args:
            needs_clarification: List of services needing clarification
            
        Returns:
            List of ServiceRequirement for clarified services (to add to main list)
        """
        clarified_services = []
        
        if not needs_clarification:
            return clarified_services
        
        logger.info("\n" + "=" * 80)
        logger.warning(f"⚠️  {len(needs_clarification)} SERVICES NEED CLARIFICATION")
        logger.info("=" * 80)
        logger.info("\nThe following services have Unknown ARM types/categories and need your input:")
        
        for i, service_data in enumerate(needs_clarification, 1):
            service_type = service_data.get("service_type", "Unknown")
            resource_name = service_data.get("resource_name", "Unknown")
            clarification_needed = service_data.get("clarification_needed", "ARM type or category unknown")
            suggested_arm_types = service_data.get("suggested_arm_types", [])
            suggested_categories = service_data.get("suggested_categories", [])
            classification_options = service_data.get("classification_options", [])
            current_arm_type = service_data.get("arm_type", "Unknown")
            current_category = service_data.get("resource_category", "Unknown")
            
            logger.info(f"\n{i}. {service_type} ({resource_name})")
            logger.info(f"   Issue: {clarification_needed}")
            logger.info(f"   Current ARM Type: {current_arm_type}")
            logger.info(f"   Current Category: {current_category}")
            
            if suggested_arm_types:
                logger.info(f"   Suggested ARM types:")
                for j, arm_type in enumerate(suggested_arm_types, 1):
                    logger.info(f"     {j}) {arm_type}")
            
            if suggested_categories:
                logger.info(f"   Suggested categories:")
                for j, category in enumerate(suggested_categories, 1):
                    logger.info(f"     {j}) {category}")
            
            if suggested_arm_types:
                logger.info(f"   Suggested ARM types:")
                for j, arm_type in enumerate(suggested_arm_types, 1):
                    logger.info(f"     {j}) {arm_type}")
            
            logger.info(f"\n   Classification options:")
            logger.info(f"     [A] Application service - specify ARM type and include in IaC")
            logger.info(f"     [F] Foundational infrastructure - exclude from IaC")
            logger.info(f"     [S] Skip - not an Azure service")
            
            while True:
                choice = input(f"\n   Your choice for '{service_type}': ").strip().upper()
                
                if choice == "A":
                    # Application service - get ARM type and category
                    arm_type = current_arm_type
                    resource_category = current_category
                    
                    # Get ARM type if Unknown
                    if arm_type == "Unknown":
                        if suggested_arm_types and len(suggested_arm_types) == 1:
                            # Auto-select if only one suggestion
                            arm_type = suggested_arm_types[0]
                            logger.info(f"   ✓ Using ARM type: {arm_type}")
                        elif suggested_arm_types:
                            # Multiple suggestions - let user choose or provide custom
                            logger.info(f"   Select ARM type:")
                            for j, arm_type_option in enumerate(suggested_arm_types, 1):
                                logger.info(f"     {j}) {arm_type_option}")
                            logger.info(f"     C) Enter custom ARM type")
                            
                            arm_choice = input(f"   ARM type choice: ").strip().upper()
                            
                            if arm_choice == "C":
                                arm_type = input(f"   Enter ARM type (e.g., Microsoft.Provider/resourceType): ").strip()
                            else:
                                try:
                                    idx = int(arm_choice) - 1
                                    if 0 <= idx < len(suggested_arm_types):
                                        arm_type = suggested_arm_types[idx]
                                    else:
                                        logger.error(f"   Invalid choice. Skipping service.")
                                        break
                                except ValueError:
                                    logger.error(f"   Invalid input. Skipping service.")
                                    break
                        else:
                            # No suggestions - get custom
                            arm_type = input(f"   Enter ARM type (e.g., Microsoft.Provider/resourceType): ").strip()
                    
                    # Get category if Unknown
                    if resource_category == "Unknown":
                        if suggested_categories and len(suggested_categories) == 1:
                            # Auto-select if only one suggestion
                            resource_category = suggested_categories[0]
                            logger.info(f"   ✓ Using category: {resource_category}")
                        elif suggested_categories:
                            # Multiple suggestions - let user choose or provide custom
                            logger.info(f"   Select resource category:")
                            for j, category_option in enumerate(suggested_categories, 1):
                                logger.info(f"     {j}) {category_option}")
                            logger.info(f"     C) Enter custom category")
                            
                            cat_choice = input(f"   Category choice: ").strip().upper()
                            
                            if cat_choice == "C":
                                resource_category = input(f"   Enter category (e.g., Compute, Storage, AI + Machine Learning): ").strip()
                            else:
                                try:
                                    idx = int(cat_choice) - 1
                                    if 0 <= idx < len(suggested_categories):
                                        resource_category = suggested_categories[idx]
                                    else:
                                        logger.error(f"   Invalid choice. Skipping service.")
                                        break
                                except ValueError:
                                    logger.error(f"   Invalid input. Skipping service.")
                                    break
                        else:
                            # No suggestions - get custom
                            resource_category = input(f"   Enter category (e.g., Compute, Storage, AI + Machine Learning): ").strip()
                    
                    if arm_type and arm_type != "Unknown" and resource_category and resource_category != "Unknown":
                        # Create ServiceRequirement for this clarified service
                        clarified = ServiceRequirement(
                            service_type=service_type,
                            resource_name=resource_name,
                            arm_type=arm_type,
                            resource_category=resource_category,
                            configurations={},
                            dependencies=[],
                            network_requirements={},
                            security_requirements={},
                            priority=2,  # Default to application priority
                            phase1_recommendations=[],
                            research_sources=[],
                        )
                        clarified_services.append(clarified)
                        logger.info(f"   ✓ Added '{service_type}' with ARM type '{arm_type}' and category '{resource_category}'")
                    break
                
                elif choice == "F":
                    # Foundational - skip (already in excluded_services)
                    logger.info(f"   ✓ Classified as foundational infrastructure - excluded from IaC")
                    break
                
                elif choice == "S":
                    # Skip entirely
                    logger.info(f"   ✓ Skipped '{service_type}'")
                    break
                
                else:
                    logger.error(f"   Invalid choice. Please enter A, F, or S.")
        
        if clarified_services:
            logger.info(f"\n✓ Clarified {len(clarified_services)} services for IaC generation")
        
        return clarified_services
    
    def _display_excluded_services(self, excluded_services: List[Dict[str, Any]]):
        """Display services excluded from IaC generation."""
        if not excluded_services:
            return
        
        logger.info("\n" + "=" * 80)
        logger.info(f"🚫 EXCLUDED FROM IaC ({len(excluded_services)} services)")
        logger.info("=" * 80)
        logger.info("\nThe following services are foundational infrastructure:")
        logger.info("(Typically managed by platform/network team, not application IaC)\n")
        
        for service_data in excluded_services:
            service_type = service_data.get("service_type", "Unknown")
            resource_name = service_data.get("resource_name", "Unknown")
            exclusion_reason = service_data.get("exclusion_reason", "Foundational infrastructure")
            classification = service_data.get("classification", "foundational_infrastructure")
            
            logger.info(f"  • {service_type} ({resource_name})")
            logger.info(f"    Reason: {exclusion_reason}")
        
        logger.info("")
    
    def _display_recommendations_summary(self, recommendations: Dict[str, List[str]]):
        """Display consolidated recommendations summary."""
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS SUMMARY")
        print("=" * 80)
        print("\nConsolidated recommendations from Phase 1 analysis + additional research:")
        
        category_titles = {
            "security": "🔒 Security Recommendations",
            "networking": "🌐 Networking Recommendations",
            "configuration": "⚙️ Configuration Recommendations",
            "dependencies": "🔗 Dependency & Deployment Order",
            "cost_optimization": "💰 Cost Optimization"
        }
        
        for category, items in recommendations.items():
            if not items:
                continue
            
            title = category_titles.get(category, category.replace("_", " ").title())
            print(f"\n{title}")
            print("-" * 80)
            
            for i, item in enumerate(items, 1):
                print(f"  {i}. {item}")
        
        print("\n" + "=" * 80)
