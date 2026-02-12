"""
Interactive Agent for SynthForge.AI.

Handles user interaction for:
1. Reviewing all detected resources after Vision/Filter stages
2. Correcting misidentified resources  
3. Adding missing resources
4. Clarifying uncertain detections

Uses azure.ai.agents.AgentsClient (Foundry agentic pattern).
"""

import json
from typing import Optional, Callable, Awaitable, List, Any
from enum import Enum

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole

from synthforge.config import get_settings
from synthforge.models import (
    DetectedIcon,
    FilterResult,
    ClarificationRequest,
    ClarificationResponse,
    Position,
)
from synthforge.prompts import get_interactive_agent_instructions


class ClarificationType(str, Enum):
    """Type of clarification needed."""
    UNKNOWN_ICON = "unknown_icon"
    AMBIGUOUS_TYPE = "ambiguous_type"
    LOW_CONFIDENCE = "low_confidence"
    MULTIPLE_OPTIONS = "multiple_options"
    USER_REVIEW = "user_review"
    ADD_MISSING = "add_missing"


class UserReviewResult:
    """Result of user review of all detected resources."""
    def __init__(self):
        self.confirmed: List[DetectedIcon] = []
        self.corrected: List[tuple[DetectedIcon, DetectedIcon]] = []  # (original, corrected)
        self.removed: List[DetectedIcon] = []
        self.added: List[DetectedIcon] = []
    
    def get_final_resources(self) -> List[DetectedIcon]:
        """Get the final list of resources after user review."""
        result = list(self.confirmed)
        result.extend([corrected for _, corrected in self.corrected])
        result.extend(self.added)
        return result


class InteractiveAgent:
    """
    Interactive Agent for user review and clarification.
    
    Provides an agentic conversation with the user to:
    1. Review ALL detected resources before security recommendations
    2. Allow correction of misidentified resources
    3. Allow addition of missed resources
    4. Clarify uncertain detections
    """
    
    def __init__(
        self, 
        input_handler: Optional[Callable[[str, List[str]], Awaitable[str]]] = None,
        description_context: Optional[Any] = None,
    ):
        """
        Initialize the Interactive Agent.
        
        Args:
            input_handler: Async callback function that takes (question, options)
                and returns the user's selected answer. If None, uses console input.
            description_context: Optional description from description agent for suggesting missing resources
        """
        self.settings = get_settings()
        self.input_handler = input_handler or self._default_input_handler
        self.description_context = description_context
        self._client: Optional[AgentsClient] = None
        self._agent_id: Optional[str] = None
    
    async def _default_input_handler(self, question: str, options: List[str]) -> str:
        """Default console-based input handler with flexible validation."""
        print(f"\n{question}")
        for i, option in enumerate(options, 1):
            print(f"  {i}. {option}")
        
        # Check if this is a multiple-choice question (has specific options)
        # vs free-form input (empty options list)
        is_multiple_choice = len(options) > 0
        
        while True:
            try:
                if is_multiple_choice:
                    choice = input("Enter choice (number or custom text): ").strip()
                else:
                    choice = input("Enter value: ").strip()
                
                # Handle empty input
                if not choice:
                    if options:
                        print(f"⚠️  Please enter a number (1-{len(options)}) or custom text")
                        continue
                    else:
                        return ""  # Allow empty for free-form
                
                # For multiple choice - accept numbers OR free-form text
                if is_multiple_choice:
                    # Try as number first
                    if choice.isdigit():
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(options):
                            return options[choice_num - 1]
                        else:
                            print(f"⚠️  Number must be between 1 and {len(options)}")
                            continue
                    
                    # Try as text match against options
                    choice_lower = choice.lower()
                    for option in options:
                        if choice_lower in option.lower():
                            return option
                    
                    # Accept as free-form custom input (e.g., ARM type)
                    # This allows users to enter "Microsoft.CognitiveServices/accounts" etc.
                    return choice
                else:
                    # Free-form input - return as-is
                    return choice
                    
            except (ValueError, EOFError):
                if options:
                    print(f"⚠️  Please enter a number (1-{len(options)}) or custom text")
                    continue
                return ""
    
    async def __aenter__(self) -> "InteractiveAgent":
        """Initialize the agent."""
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
        
        self._client = AgentsClient(
            endpoint=self.settings.project_endpoint,
            credential=credential,
        )
        
        instructions = get_interactive_agent_instructions()
        
        agent = self._client.create_agent(
            model=self.settings.model_deployment_name,
            name="InteractiveAgent",
            instructions=instructions,
            temperature=self.settings.model_temperature,
            top_p=0.95,
        )
        self._agent_id = agent.id
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup the agent."""
        if self._client and self._agent_id:
            try:
                self._client.delete_agent(self._agent_id)
            except Exception:
                pass
    
    async def review_all_resources(
        self,
        detected_resources: List[DetectedIcon],
    ) -> UserReviewResult:
        """
        Interactive review of ALL detected resources with user.
        
        This provides an agentic conversation where:
        1. User sees all detected resources
        2. Can confirm, correct, or remove any resource
        3. Can add resources that were missed
        
        Args:
            detected_resources: All resources detected by Vision/Filter agents
            
        Returns:
            UserReviewResult with confirmed, corrected, removed, and added resources
        """
        result = UserReviewResult()
        
        if not detected_resources:
            # No resources detected - ask user if they want to add any
            add_response = await self.input_handler(
                "No Azure resources were detected. Would you like to add resources manually?",
                ["Yes, add resources", "No, continue with empty list"]
            )
            
            if "yes" in add_response.lower() or "add" in add_response.lower():
                await self._add_missing_resources(result)
            
            return result
        
        # Display detected resources (simple list)
        resource_lines = []
        for i, r in enumerate(detected_resources, 1):
            instance = r.name or "Unnamed"
            arm_type = r.arm_resource_type or "Unknown ARM type"
            resource_lines.append(
                f"  {i}. {r.type} ({instance}) | confidence: {r.confidence:.0%} | {arm_type}"
            )
        resource_list = "\n".join(resource_lines)
        
        print(f"\n{'='*60}")
        print("DETECTED AZURE RESOURCES - Please Review")
        print(f"{'='*60}")
        print(resource_list)
        print(f"{'='*60}\n")
        
        # Ask for review action
        review_action = await self.input_handler(
            "Would you like to review and modify the detected resources?",
            [
                "Confirm all - proceed with detected resources",
                "Review each - go through each resource",
                "Quick edit - correct specific resources",
                "Add missing - add resources not detected"
            ]
        )
        
        if "confirm" in review_action.lower():
            # User confirms all resources as-is
            result.confirmed = list(detected_resources)
            
        elif "review each" in review_action.lower():
            # Review each resource one by one
            await self._review_each_resource(detected_resources, result)
            
        elif "quick" in review_action.lower():
            # Quick edit mode - ask which to modify
            result.confirmed = list(detected_resources)  # Start with all confirmed
            await self._quick_edit_resources(detected_resources, result)
            
        elif "add" in review_action.lower():
            # Add missing resources
            result.confirmed = list(detected_resources)
            # First show description-detected missing resources
            await self._suggest_missing_from_description(detected_resources, result)
            # Then allow manual additions
            await self._add_missing_resources(result)
        
        else:
            # Default: confirm all
            result.confirmed = list(detected_resources)
        
        # Final summary
        total = len(result.get_final_resources())
        print(f"\n✓ Final resource count: {total} resources")
        if result.corrected:
            print(f"  - {len(result.corrected)} corrected")
        if result.removed:
            print(f"  - {len(result.removed)} removed")
        if result.added:
            print(f"  - {len(result.added)} added")
        
        return result
    
    async def _review_each_resource(
        self, 
        resources: List[DetectedIcon], 
        result: UserReviewResult
    ):
        """Review each detected resource individually."""
        for i, resource in enumerate(resources, 1):
            print(f"\n[{i}/{len(resources)}] {resource.type}")
            if resource.name:
                print(f"    Name: {resource.name}")
            print(f"    Confidence: {resource.confidence:.0%}")
            if resource.arm_resource_type:
                print(f"    ARM Type: {resource.arm_resource_type}")
            if resource.resource_category:
                print(f"    Category: {resource.resource_category}")
            
            action = await self.input_handler(
                "What would you like to do with this resource?",
                [
                    "Confirm - keep as detected",
                    "Correct - change the service type",
                    "Remove - exclude from analysis",
                    "Skip rest - confirm remaining resources"
                ]
            )
            
            if "confirm" in action.lower():
                result.confirmed.append(resource)
                
            elif "correct" in action.lower():
                corrected = await self._correct_resource(resource)
                result.corrected.append((resource, corrected))
                
            elif "remove" in action.lower():
                result.removed.append(resource)
                
            elif "skip" in action.lower():
                # Confirm this and all remaining resources
                result.confirmed.append(resource)
                result.confirmed.extend(resources[i:])
                break
            else:
                # Default: confirm
                result.confirmed.append(resource)
        
        # Ask if user wants to add missing resources
        add_more = await self.input_handler(
            "Would you like to add any resources that were not detected?",
            ["No, continue", "Yes, add resources"]
        )
        
        if "yes" in add_more.lower() or "add" in add_more.lower():
            await self._add_missing_resources(result)
    
    async def _correct_resource(self, resource: DetectedIcon) -> DetectedIcon:
        """Get corrected information for a resource from user."""
        # Use agent to suggest corrections
        suggestions = await self._get_correction_suggestions(resource)
        
        new_type = await self.input_handler(
            f"What is the correct Azure service type for this resource?",
            suggestions + ["Enter custom type..."]
        )
        
        if "custom" in new_type.lower() or "enter" in new_type.lower():
            new_type = await self.input_handler(
                "Enter the correct Azure service name:",
                []
            )
        
        # Get ARM type and category suggestions from agent
        arm_type = await self._suggest_arm_type(new_type)
        category = await self._suggest_category(new_type)
        
        return DetectedIcon(
            type=new_type,
            name=resource.name,
            position=resource.position,
            bounding_box=resource.bounding_box,
            confidence=1.0,  # User-corrected
            arm_resource_type=arm_type,
            resource_category=category,
            needs_clarification=False,
        )
    
    async def _get_correction_suggestions(self, resource: DetectedIcon) -> List[str]:
        """Use agent to suggest possible correct service types."""
        if not self._client or not self._agent_id:
            # No static fallbacks - let user type service name manually
            return []
        
        # Ask agent for suggestions
        thread = self._client.threads.create()
        
        self._client.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""The detected service '{resource.type}' may be incorrect.
Suggest 5 similar Azure services it could be. Just list the service names, one per line."""
        )
        
        run = self._client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self._agent_id,
        )
        
        if run.status == "completed":
            last_msg = self._client.messages.get_last_message_text_by_role(
                thread_id=thread.id,
                role=MessageRole.AGENT,
            )
            if last_msg:
                lines = [l.strip() for l in last_msg.text.value.strip().split('\n') if l.strip()]
                # Clean up numbering and bullets
                suggestions = []
                for line in lines[:5]:
                    line = line.lstrip('0123456789.-) ')
                    if line:
                        suggestions.append(line)
                if suggestions:
                    return suggestions
        
        # No static fallbacks - return empty list
        return []
    
    async def _suggest_arm_type(self, service_name: str) -> Optional[str]:
        """Use agent to suggest ARM resource type for a service."""
        if not self._client or not self._agent_id:
            return None
        
        thread = self._client.threads.create()
        
        self._client.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""What is the ARM resource type for '{service_name}'?
Reply with ONLY the ARM type like 'Microsoft.Web/sites' or 'Microsoft.Storage/storageAccounts'.
No explanation needed."""
        )
        
        run = self._client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self._agent_id,
        )
        
        if run.status == "completed":
            last_msg = self._client.messages.get_last_message_text_by_role(
                thread_id=thread.id,
                role=MessageRole.AGENT,
            )
            if last_msg:
                arm_type = last_msg.text.value.strip()
                if arm_type.startswith("Microsoft."):
                    return arm_type
        
        return None
    
    async def _suggest_category(self, service_name: str) -> Optional[str]:
        """Use agent to suggest Azure service category from MCP/Bing documentation.
        
        Priority:
        1. Microsoft Learn MCP search (official docs)
        2. Bing Grounding (fallback)
        """
        if not self._client or not self._agent_id:
            return None
        
        thread = self._client.threads.create()
        
        self._client.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""What Azure service category does '{service_name}' belong to?

Search Microsoft Learn documentation first using MCP, then Bing if needed.
Reply with ONLY the official Azure category name from documentation.
No explanation needed."""
        )
        
        run = self._client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self._agent_id,
        )
        
        if run.status == "completed":
            last_msg = self._client.messages.get_last_message_text_by_role(
                thread_id=thread.id,
                role=MessageRole.AGENT,
            )
            if last_msg:
                category = last_msg.text.value.strip()
                # Validate it looks like a real category (not a full sentence)
                if category and len(category) < 50 and not category.endswith('.'):
                    return category
        
        return None
    
    async def _quick_edit_resources(
        self,
        resources: List[DetectedIcon],
        result: UserReviewResult
    ):
        """Quick edit mode - user specifies which resources to modify."""
        while True:
            edit_input = await self.input_handler(
                "Enter resource number to edit (or 'done' to finish, 'add' to add new):",
                [f"{i}. {r.type}" for i, r in enumerate(resources, 1)] + ["done", "add"]
            )
            
            if "done" in edit_input.lower():
                break
            elif "add" in edit_input.lower():
                await self._add_missing_resources(result)
            else:
                # Try to parse resource number
                try:
                    if edit_input.isdigit():
                        idx = int(edit_input) - 1
                    else:
                        # Extract number from selection
                        idx = int(edit_input.split('.')[0]) - 1
                    
                    if 0 <= idx < len(resources):
                        resource = resources[idx]
                        
                        # Check if this resource already has a correction (by position matching)
                        # If yes, we'll update that correction instead of adding a new one
                        existing_correction_idx = None
                        base_resource = resource  # The resource we're editing
                        
                        for corr_idx, (original, corrected) in enumerate(result.corrected):
                            if (original.position.x == resource.position.x and 
                                original.position.y == resource.position.y):
                                existing_correction_idx = corr_idx
                                # Use the LATEST corrected version as the base for further edits
                                base_resource = corrected
                                break
                        
                        # If NOT already corrected, remove from confirmed list
                        # (If already corrected, it's not in confirmed anymore)
                        if existing_correction_idx is None:
                            confirmed_idx_to_remove = None
                            for conf_idx, confirmed_resource in enumerate(result.confirmed):
                                if (confirmed_resource.position.x == resource.position.x and 
                                    confirmed_resource.position.y == resource.position.y):
                                    confirmed_idx_to_remove = conf_idx
                                    break
                            
                            if confirmed_idx_to_remove is not None:
                                result.confirmed.pop(confirmed_idx_to_remove)
                        
                        action = await self.input_handler(
                            f"What would you like to edit for '{base_resource.type}'?",
                            [
                                "Service type - change Azure service type",
                                "Resource name - change instance name",
                                "ARM type - change ARM resource type",
                                "Category - change resource category",
                                "Remove - exclude from analysis"
                            ]
                        )
                        
                        # Parse action - handle both number input (1-5) and text matching
                        action_lower = action.lower().strip()
                        
                        # Try to parse as number first
                        action_num = None
                        if action.strip().isdigit():
                            action_num = int(action.strip())
                        
                        # Map number to action
                        if action_num == 1 or "service type" in action_lower or action_lower == "1":
                            corrected = await self._correct_resource(base_resource)
                            # Update existing correction or add new one
                            if existing_correction_idx is not None:
                                result.corrected[existing_correction_idx] = (resource, corrected)
                            else:
                                result.corrected.append((resource, corrected))
                        elif action_num == 2 or "resource name" in action_lower or action_lower == "2":
                            new_name = await self.input_handler(
                                f"Enter new resource name for '{base_resource.type}' (current: {base_resource.name or 'None'}):",
                                []
                            )
                            updated = DetectedIcon(
                                type=base_resource.type,
                                name=new_name.strip() if new_name.strip() else None,
                                position=base_resource.position,
                                bounding_box=base_resource.bounding_box,
                                confidence=base_resource.confidence,
                                arm_resource_type=base_resource.arm_resource_type,
                                resource_category=base_resource.resource_category,
                                connections=base_resource.connections,
                                needs_clarification=False,
                            )
                            # Update existing correction or add new one
                            if existing_correction_idx is not None:
                                result.corrected[existing_correction_idx] = (resource, updated)
                            else:
                                result.corrected.append((resource, updated))
                        elif action_num == 3 or "arm type" in action_lower or action_lower == "3":
                            current_arm = base_resource.arm_resource_type or "Unknown"
                            new_arm_type = await self.input_handler(
                                f"Enter ARM resource type for '{base_resource.type}' (current: {current_arm}):",
                                []
                            )
                            if new_arm_type.strip():
                                updated = DetectedIcon(
                                    type=base_resource.type,
                                    name=base_resource.name,
                                    position=base_resource.position,
                                    bounding_box=base_resource.bounding_box,
                                    confidence=base_resource.confidence,
                                    arm_resource_type=new_arm_type.strip(),
                                    resource_category=base_resource.resource_category,
                                    connections=base_resource.connections,
                                    needs_clarification=False,
                                )
                                # Update existing correction or add new one
                                if existing_correction_idx is not None:
                                    result.corrected[existing_correction_idx] = (resource, updated)
                                else:
                                    result.corrected.append((resource, updated))
                        elif action_num == 4 or "category" in action_lower or action_lower == "4":
                            current_cat = base_resource.resource_category or "Unknown"
                            new_category = await self.input_handler(
                                f"Enter resource category for '{base_resource.type}' (current: {current_cat}):",
                                []
                            )
                            if new_category.strip():
                                updated = DetectedIcon(
                                    type=base_resource.type,
                                    name=base_resource.name,
                                    position=base_resource.position,
                                    bounding_box=base_resource.bounding_box,
                                    confidence=base_resource.confidence,
                                    arm_resource_type=base_resource.arm_resource_type,
                                    resource_category=new_category.strip(),
                                    connections=base_resource.connections,
                                    needs_clarification=False,
                                )
                                # Update existing correction or add new one
                                if existing_correction_idx is not None:
                                    result.corrected[existing_correction_idx] = (resource, updated)
                                else:
                                    result.corrected.append((resource, updated))
                        elif action_num == 5 or "remove" in action_lower or action_lower == "5":
                            # Explicitly remove only if user chose option 5
                            # If already corrected, remove the correction; otherwise remove from original resource
                            if existing_correction_idx is not None:
                                result.corrected.pop(existing_correction_idx)
                            result.removed.append(resource)
                        else:
                            # Invalid input - re-add resource to confirmed and warn user
                            print(f"⚠️  Invalid choice '{action}'. Please enter a number 1-5 or select from menu.")
                            print(f"   Resource '{base_resource.type}' kept unchanged.")
                            # Only re-add if not already corrected
                            if existing_correction_idx is None:
                                result.confirmed.append(resource)
                except (ValueError, IndexError):
                    print("Invalid selection. Try again.")
    
    async def _suggest_missing_from_description(
        self,
        detected_resources: List[DetectedIcon],
        result: UserReviewResult
    ):
        """Suggest missing resources based on description context."""
        if not self.description_context:
            return
        
        # Get all components from description
        all_description_components = self.description_context.get_all_components() if hasattr(self.description_context, 'get_all_components') else []
        
        if not all_description_components:
            return
        
        # Get all detected service types (normalize for comparison)
        detected_types = set()
        for icon in detected_resources:
            # Normalize: lowercase, remove "azure" prefix
            normalized = icon.type.lower().replace("azure ", "").replace("microsoft ", "").strip()
            detected_types.add(normalized)
        
        # Check for missing resources
        missing = []
        for comp in all_description_components:
            # Normalize component name
            normalized_comp = comp.lower().replace("azure ", "").replace("microsoft ", "").strip()
            
            # Check if any detected type contains this component or vice versa
            found = False
            for detected in detected_types:
                # Fuzzy matching: check substring match in either direction
                if normalized_comp in detected or detected in normalized_comp:
                    found = True
                    break
            
            if not found:
                missing.append(comp)
        
        if not missing:
            return
        
        print(f"\n--- Description Detected {len(missing)} Missing Resources ---")
        print("The architecture description identified these components that were not detected by Vision:\n")
        
        for i, resource in enumerate(missing, 1):
            print(f"  {i}. {resource}")
        
        print("\nWould you like to add any of these resources?")
        
        add_from_description = await self.input_handler(
            "Add resources from description?",
            ["No, skip to manual add", "Yes, select from list"]
        )
        
        if "yes" not in add_from_description.lower() and "select" not in add_from_description.lower():
            return
        
        # Allow user to select which ones to add
        print("\nSelect resources to add (enter numbers separated by commas, or 'all' for all):")
        selection_input = await self.input_handler(
            "Enter selections (e.g., 1,3,5 or 'all' or 'none'):",
            ["all", "none"]
        )
        
        if "none" in selection_input.lower():
            return
        
        # Parse selection
        selected_indices = []
        if "all" in selection_input.lower():
            selected_indices = list(range(len(missing)))
        else:
            # Parse comma-separated numbers
            try:
                parts = selection_input.split(",")
                for part in parts:
                    idx = int(part.strip()) - 1  # Convert to 0-based
                    if 0 <= idx < len(missing):
                        selected_indices.append(idx)
            except ValueError:
                print("Invalid selection format. Skipping description suggestions.")
                return
        
        # Add selected resources
        for idx in selected_indices:
            service_name = missing[idx]
            
            # Get ARM type suggestion from agent
            suggested_arm_type = await self._suggest_arm_type(service_name)
            suggested_category = await self._suggest_category(service_name)
            
            # Create resource with suggested values
            new_resource = DetectedIcon(
                type=service_name,
                name=None,  # No name from description
                position=Position(x=0, y=0),  # No position
                confidence=0.8,  # From description, not Vision
                arm_resource_type=suggested_arm_type or "Unknown",
                resource_category=suggested_category,
                needs_clarification=False,
            )
            result.added.append(new_resource)
            print(f"✓ Added from description: {service_name} | ARM: {suggested_arm_type or 'Unknown'}" + (f" | Category: {suggested_category}" if suggested_category else ""))
    
    async def _add_missing_resources(self, result: UserReviewResult):
        """Allow user to add resources that were not detected."""
        print("\n--- Add Missing Resources (Manual) ---")
        
        while True:
            service_name = await self.input_handler(
                "Enter Azure service name to add (or 'done' to finish):",
                ["done"]
            )
            
            if "done" in service_name.lower() or not service_name.strip():
                break
            
            # Get optional resource name
            resource_name = await self.input_handler(
                f"Enter a name for this {service_name} (optional, press Enter to skip):",
                []
            )
            
            # Get ARM type suggestion from agent
            suggested_arm_type = await self._suggest_arm_type(service_name)
            
            # Ask user to confirm or provide ARM type
            if suggested_arm_type and suggested_arm_type != "Unknown":
                arm_type_input = await self.input_handler(
                    f"ARM resource type for '{service_name}' (detected: {suggested_arm_type}):",
                    [f"Use detected: {suggested_arm_type}", "Enter manually"]
                )
                
                if "manual" in arm_type_input.lower():
                    arm_type_input = await self.input_handler(
                        f"Enter ARM type (e.g., Microsoft.CognitiveServices/accounts):",
                        []
                    )
                    arm_type = arm_type_input.strip() if arm_type_input.strip() else suggested_arm_type
                else:
                    arm_type = suggested_arm_type
            else:
                # No suggestion, ask user to provide
                arm_type_input = await self.input_handler(
                    f"ARM resource type for '{service_name}' (e.g., Microsoft.Storage/storageAccounts):",
                    ["Unknown"]
                )
                arm_type = arm_type_input.strip() if arm_type_input.strip() and "unknown" not in arm_type_input.lower() else "Unknown"
            
            # Get category suggestion from agent
            suggested_category = await self._suggest_category(service_name)
            
            # Ask user to confirm or provide category
            if suggested_category:
                category_input = await self.input_handler(
                    f"Resource category for '{service_name}' (detected: {suggested_category}):",
                    [f"Use detected: {suggested_category}", "Enter manually"]
                )
                
                if "manual" in category_input.lower():
                    category_input = await self.input_handler(
                        f"Enter category (e.g., Compute, Networking, AI/ML, Storage):",
                        []
                    )
                    category = category_input.strip() if category_input.strip() else suggested_category
                else:
                    category = suggested_category
            else:
                # No suggestion, ask user to provide
                category_input = await self.input_handler(
                    f"Resource category for '{service_name}' (e.g., Compute, Networking, AI/ML):",
                    ["Other"]
                )
                category = category_input.strip() if category_input.strip() else None
            
            new_resource = DetectedIcon(
                type=service_name,
                name=resource_name if resource_name.strip() else None,
                position=Position(x=0, y=0),  # User-added, no position
                confidence=1.0,  # User-added
                arm_resource_type=arm_type,
                resource_category=category,
                needs_clarification=False,
            )
            result.added.append(new_resource)
            print(f"✓ Added: {service_name}" + (f" ({resource_name})" if resource_name else "") + f" | ARM: {arm_type}" + (f" | Category: {category}" if category else ""))
    
    async def clarify_resources(
        self, 
        filter_result: FilterResult,
    ) -> List[ClarificationResponse]:
        """
        Clarify resources that need user input.
        
        This handles only the resources marked as 'needs_clarification' by the Filter Agent.
        For full resource review, use review_all_resources() instead.
        
        Args:
            filter_result: Result from filter agent
            
        Returns:
            List of ClarificationResponse with user decisions
        """
        if not filter_result.needs_clarification:
            return []
        
        responses = []
        
        for icon in filter_result.needs_clarification:
            # Generate clarification question
            request = await self._generate_question(icon)
            
            # Get user response
            user_answer = await self.input_handler(
                request.question,
                request.options,
            )
            
            # Process the response
            response = await self._process_response(icon, user_answer, request)
            responses.append(response)
        
        return responses
    
    async def _generate_question(self, icon: DetectedIcon) -> ClarificationRequest:
        """Generate a clarification question for an uncertain resource."""
        if not self._client or not self._agent_id:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        
        # Determine clarification type
        if icon.needs_clarification and icon.clarification_options:
            clarification_type = ClarificationType.MULTIPLE_OPTIONS
            options = icon.clarification_options + ["Enter custom type", "Skip for now"]
        elif icon.confidence < 0.5:
            clarification_type = ClarificationType.UNKNOWN_ICON
            options = ["Keep as detected", "Remove from analysis", "Enter custom type", "Skip for now"]
        elif icon.confidence < 0.7:
            clarification_type = ClarificationType.LOW_CONFIDENCE
            options = [
                f"Yes, this is {icon.type}",
                "No, this is a different service",
                "Remove from analysis",
                "Enter custom type",
                "Skip for now",
            ]
        else:
            clarification_type = ClarificationType.AMBIGUOUS_TYPE
            options = ["Keep as detected", "Specify different type", "Remove", "Enter custom type", "Skip for now"]
        
        # Build question based on type
        if clarification_type == ClarificationType.MULTIPLE_OPTIONS:
            question = f"The detected icon '{icon.type}' could be one of several services. Which is correct?"
        elif clarification_type == ClarificationType.UNKNOWN_ICON:
            question = f"Could not identify the icon at position ({icon.position.x:.0f}, {icon.position.y:.0f}). What should we do?"
        elif clarification_type == ClarificationType.LOW_CONFIDENCE:
            question = f"Is '{icon.type}' correctly identified? (confidence: {icon.confidence:.0%})"
        else:
            question = f"Please confirm the service type for '{icon.name or icon.type}':"
        
        return ClarificationRequest(
            resource=icon,
            question=question,
            options=options,
            clarification_type=clarification_type.value,
        )
    
    async def _process_response(
        self, 
        icon: DetectedIcon, 
        user_answer: str,
        request: ClarificationRequest,
    ) -> ClarificationResponse:
        """Process the user's response and determine action."""
        user_lower = user_answer.lower()
        
        # Check if user entered a custom ARM type directly (contains "Microsoft." or "/" pattern)
        is_arm_type = "microsoft." in user_lower or "/" in user_answer
        
        # Determine action
        if "skip" in user_lower:
            # Skip for now - keep original with clarification flag
            action = "KEEP"
            updated_icon = icon
        elif "remove" in user_lower:
            action = "REMOVE"
            updated_icon = None
        elif "enter custom" in user_lower or is_arm_type:
            # User wants to enter custom type OR already entered ARM type
            action = "UPDATE"
            
            if is_arm_type:
                # User already provided ARM type directly
                new_arm_type = user_answer.strip()
                new_type = icon.type  # Keep original service type
            else:
                # Ask for custom ARM type
                new_arm_type = await self.input_handler(
                    f"Enter ARM type for '{icon.type}' (e.g., Microsoft.CognitiveServices/accounts):",
                    []  # Free-form input
                )
                
                if not new_arm_type.strip() or "skip" in new_arm_type.lower():
                    action = "KEEP"
                    updated_icon = icon
                    return ClarificationResponse(
                        original_resource=icon,
                        clarified_type=icon.type,
                        clarified_arm_type=icon.arm_resource_type,
                        clarified_name=icon.name,
                        should_include=True,
                        user_notes=user_answer,
                    )
                
                new_type = icon.type  # Keep original service type
            
            # Ask for category
            category_input = await self.input_handler(
                f"Resource category (e.g., Compute, AI/ML, Storage, Networking):",
                ["Unknown"]
            )
            category = category_input.strip() if category_input.strip() and "unknown" not in category_input.lower() else icon.resource_category
            
            updated_icon = DetectedIcon(
                type=new_type,
                name=icon.name,
                position=icon.position,
                confidence=1.0,
                arm_resource_type=new_arm_type,
                resource_category=category,
                connections=icon.connections,
                needs_clarification=False,
                clarification_options=[],
            )
        elif "keep" in user_lower or "yes" in user_lower:
            action = "KEEP"
            # Check if ARM type is Unknown - ask user to provide it
            if not icon.arm_resource_type or icon.arm_resource_type == "Unknown":
                arm_type_input = await self.input_handler(
                    f"ARM type for '{icon.type}' is unknown. Please provide ARM type (e.g., Microsoft.Web/sites) or 'skip' to remove:",
                    ["skip"]
                )
                if "skip" in arm_type_input.lower() or not arm_type_input.strip():
                    action = "REMOVE"
                    updated_icon = None
                else:
                    # Ask for category as well
                    category_input = await self.input_handler(
                        f"Resource category for '{icon.type}' (e.g., Compute, Networking, AI/ML, Storage):",
                        ["Unknown"]
                    )
                    category = category_input.strip() if category_input.strip() and "unknown" not in category_input.lower() else icon.resource_category
                    
                    updated_icon = DetectedIcon(
                        type=icon.type,
                        name=icon.name,
                        position=icon.position,
                        confidence=icon.confidence,
                        arm_resource_type=arm_type_input.strip(),
                        resource_category=category,
                        connections=icon.connections,
                        needs_clarification=False,
                        clarification_options=[],
                    )
            else:
                updated_icon = icon
        elif "different" in user_lower or "specify" in user_lower:
            action = "UPDATE"
            
            # For Unknown ARM type resources, ask for ARM type directly (not service type)
            if not icon.arm_resource_type or icon.arm_resource_type.lower() == "unknown":
                arm_type_input = await self.input_handler(
                    f"Enter ARM type for '{icon.type}' (e.g., Microsoft.CognitiveServices/accounts) or 'skip' to remove:",
                    ["skip"]
                )
                
                if "skip" in arm_type_input.lower() or not arm_type_input.strip():
                    action = "KEEP"
                    updated_icon = icon
                else:
                    # User provided ARM type - keep original service type
                    new_arm_type = arm_type_input.strip()
                    new_type = icon.type  # Keep original service type
                    
                    # Ask for category
                    category_input = await self.input_handler(
                        f"Resource category for '{icon.type}' (e.g., Compute, AI/ML, Storage, Networking):",
                        ["Unknown"]
                    )
                    category = category_input.strip() if category_input.strip() and "unknown" not in category_input.lower() else icon.resource_category
                    
                    updated_icon = DetectedIcon(
                        type=new_type,
                        name=icon.name,
                        position=icon.position,
                        confidence=1.0,
                        arm_resource_type=new_arm_type,
                        resource_category=category,
                        connections=icon.connections,
                        needs_clarification=False,
                        clarification_options=[],
                    )
            else:
                # ARM type is known - user wants to change the service type itself
                new_type = await self.input_handler(
                    f"What is the correct Azure service type for '{icon.type}'?",
                    []  # Free-form input
                )
                
                # Validate input
                if not new_type.strip() or new_type.lower() in ["skip", "cancel", "remove"]:
                    action = "REMOVE"
                    updated_icon = None
                else:
                    new_type = new_type.strip()
                    
                    # Resolve ARM type using tools
                    new_arm_type = await self._suggest_arm_type(new_type)
                    new_category = await self._suggest_category(new_type)
                
                    # If tools couldn't resolve, ask user
                    if not new_arm_type or new_arm_type == "Unknown":
                        arm_type_input = await self.input_handler(
                            f"Could not resolve ARM type for '{new_type}'. Please provide ARM type (e.g., Microsoft.CognitiveServices/accounts) or 'skip' to remove:",
                            ["skip"]
                        )
                        if "skip" in arm_type_input.lower() or not arm_type_input.strip():
                            action = "REMOVE"
                            updated_icon = None
                        else:
                            new_arm_type = arm_type_input.strip()
                    
                    # Create updated icon if not removed
                    if action != "REMOVE":
                        updated_icon = DetectedIcon(
                            type=new_type,
                            name=icon.name,
                            position=icon.position,
                            confidence=1.0,
                            arm_resource_type=new_arm_type,
                            resource_category=new_category or icon.resource_category,
                            connections=icon.connections,
                            needs_clarification=False,
                            clarification_options=[],
                        )
                    else:
                        updated_icon = None
        else:
            # User selected a specific option
            action = "UPDATE"
            new_service_type = user_answer if user_answer else icon.type
            
            # Resolve ARM type using tools
            new_arm_type = await self._suggest_arm_type(new_service_type)
            new_category = await self._suggest_category(new_service_type)
            
            # If tools couldn't resolve, ask user
            if not new_arm_type or new_arm_type == "Unknown":
                arm_type_input = await self.input_handler(
                    f"Could not resolve ARM type for '{new_service_type}'. Please provide ARM type (e.g., Microsoft.Storage/storageAccounts) or 'skip' to remove:",
                    ["skip"]
                )
                if "skip" in arm_type_input.lower() or not arm_type_input.strip():
                    action = "REMOVE"
                    updated_icon = None
                else:
                    new_arm_type = arm_type_input.strip()
                    
                    # Ask for category if not resolved
                    if not new_category:
                        category_input = await self.input_handler(
                            f"Resource category for '{new_service_type}' (e.g., Compute, Networking, AI/ML, Storage):",
                            ["Unknown"]
                        )
                        new_category = category_input.strip() if category_input.strip() and "unknown" not in category_input.lower() else icon.resource_category
            
            if action != "REMOVE":
                updated_icon = DetectedIcon(
                    type=new_service_type,
                    name=icon.name,
                    position=icon.position,
                    confidence=1.0,
                    arm_resource_type=new_arm_type,
                    resource_category=new_category or icon.resource_category,
                    connections=icon.connections,
                    needs_clarification=False,
                    clarification_options=[],
                )
            else:
                updated_icon = None
        
        return ClarificationResponse(
            original_resource=icon,
            clarified_type=updated_icon.type if updated_icon else None,
            clarified_arm_type=updated_icon.arm_resource_type if updated_icon else None,
            clarified_name=updated_icon.name if updated_icon else None,
            should_include=(action != "REMOVE"),
            user_notes=user_answer,
        )
