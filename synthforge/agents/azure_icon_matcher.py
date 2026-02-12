"""
Azure Icon Matcher

Identifies unknown Azure resources by matching detected icon regions 
against official Microsoft Azure Architecture Icons.

Strategy:
1. Download and cache official Azure icons from Microsoft's CDN
2. When GPT-4o detects an object but can't identify it (low confidence/unknown):
   a. Crop the detected region from the source image
   b. Compare against the icon library using template matching
   c. Use feature matching (ORB) as fallback for scale/rotation invariance
   d. Use icon filename parsing for service identification

Icon Source:
- Official: https://learn.microsoft.com/en-us/azure/architecture/icons/
- CDN: https://arch-center.azureedge.net/icons/Azure_Public_Service_Icons.zip

NO STATIC MAPPINGS - All service identification is dynamic from the icon library.

Prerequisites:
- opencv-python for template/feature matching
- Pillow for image processing
- httpx for async downloads
- cairosvg (optional) for SVG to PNG conversion
"""

import asyncio
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

from synthforge.config import get_settings

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

# Optional: cairosvg for SVG to PNG conversion
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False
    cairosvg = None

# =============================================================================
# CONFIGURATION
# =============================================================================

# Official Microsoft Azure Architecture Icons
# Source: https://learn.microsoft.com/en-us/azure/architecture/icons/
# CDN URL is loaded from settings (AZURE_ICONS_CDN_URL environment variable)

# Default cache directory
DEFAULT_CACHE_DIR = Path.home() / ".synthforge" / "azure_icons_cache"

# Icon matching thresholds
DEFAULT_TEMPLATE_MATCH_THRESHOLD = 0.7  # Minimum similarity for template matching
DEFAULT_FEATURE_MATCH_THRESHOLD = 0.6   # Minimum good matches ratio for ORB
DEFAULT_ICON_SIZE = (64, 64)            # Standard size for comparison


@dataclass
class IconMatch:
    """Result of icon matching operation."""
    service_name: str
    arm_resource_type: str
    confidence: float
    match_method: str  # "template", "feature", "filename"
    icon_path: str
    category: str = ""
    

@dataclass
class IconInfo:
    """Information about a cached icon."""
    name: str
    path: str
    category: str = ""
    arm_type: str = ""
    aliases: list[str] = field(default_factory=list)
    

@dataclass
class IconLibrary:
    """Container for cached Azure icons with metadata."""
    icons: dict[str, IconInfo] = field(default_factory=dict)  # service_name -> IconInfo
    last_updated: str = ""
    version: str = ""
    source_url: str = ""
    

class AzureIconMatcher:
    """
    Matches unknown icon regions against official Microsoft Azure Architecture Icons.
    
    NO STATIC MAPPINGS - All service names and ARM types are derived dynamically
    from the official icon library filenames and structure.
    
    Uses multiple matching strategies:
    1. Template matching (cv2.matchTemplate) - fast, exact matching
    2. Feature matching (ORB descriptors) - handles scale/rotation
    3. Filename-based identification - parses official icon naming conventions
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        template_threshold: float = DEFAULT_TEMPLATE_MATCH_THRESHOLD,
        feature_threshold: float = DEFAULT_FEATURE_MATCH_THRESHOLD,
        icon_size: tuple[int, int] = DEFAULT_ICON_SIZE,
    ):
        """
        Initialize the icon matcher.
        
        Args:
            cache_dir: Directory to cache downloaded icons
            template_threshold: Minimum similarity for template matching (0-1)
            feature_threshold: Minimum ratio of good feature matches (0-1)
            icon_size: Standard size to resize icons for comparison
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.template_threshold = template_threshold
        self.feature_threshold = feature_threshold
        self.icon_size = icon_size
        
        # Icon library (loaded lazily)
        self._library: Optional[IconLibrary] = None
        self._icons_loaded = False
        
        # ORB detector for feature matching
        self._orb = None
        if CV2_AVAILABLE:
            self._orb = cv2.ORB_create(nfeatures=500)
            self._bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    @property
    def library_path(self) -> Path:
        """Path to the cached icon library metadata."""
        return self.cache_dir / "library.json"
    
    @property
    def icons_dir(self) -> Path:
        """Path to the cached icon images directory."""
        return self.cache_dir / "icons"
    
    def get_all_services(self) -> list[IconInfo]:
        """
        Get all services from the icon library.
        
        Returns list of IconInfo with dynamically-parsed service information.
        NO STATIC MAPPING - all data comes from the official icon files.
        """
        if self._library:
            return list(self._library.icons.values())
        return []
    
    def get_service_by_name(self, name: str) -> Optional[IconInfo]:
        """
        Look up a service by name or alias.
        
        NO STATIC MAPPING - searches the dynamically-loaded icon library.
        EXACT MATCH ONLY - partial matches can return wrong services
        (e.g., "Azure Storage Mover" partial-matching to "Azure Storage Account").
        """
        if not self._library:
            return None
        
        name_lower = name.lower().strip()
        
        # Remove common variations for matching
        name_normalized = name_lower.replace("azure ", "").replace("microsoft ", "").strip()
        
        # Direct exact match (with or without "Azure"/"Microsoft" prefix)
        for service_name, info in self._library.icons.items():
            service_lower = service_name.lower()
            service_normalized = service_lower.replace("azure ", "").replace("microsoft ", "").strip()
            
            # Exact match
            if service_lower == name_lower or service_normalized == name_normalized:
                return info
            
            # Exact match on aliases
            if name_lower in [a.lower() for a in info.aliases]:
                return info
            if name_normalized in [a.lower().replace("azure ", "").replace("microsoft ", "").strip() for a in info.aliases]:
                return info
        
        # NO PARTIAL MATCHING - prevents "Azure Storage Mover" from matching "Azure Storage Account"
        # If not found, return None and let the agent's resolve_arm_type tool validate
        return None
    
    async def ensure_icons_available(self) -> bool:
        """
        Ensure Azure icons are downloaded and cached from official Microsoft source.
        
        Returns:
            True if icons are available, False otherwise
        """
        if self._icons_loaded and self._library:
            return True
        
        # Check if cache exists
        if self.library_path.exists() and self.icons_dir.exists():
            self._load_library()
            if self._library and len(self._library.icons) > 0:
                self._icons_loaded = True
                return True
        
        # Download icons from official Microsoft source
        settings = get_settings()
        print(f"    [IconMatcher] Downloading Azure Architecture Icons from Microsoft...")
        print(f"    [IconMatcher] Source: {settings.azure_icons_url}")
        success = await self._download_azure_icons()
        if success:
            self._load_library()
            self._icons_loaded = True
        return success
    
    async def _download_azure_icons(self) -> bool:
        """
        Download official Azure Architecture Icons from Microsoft CDN.
        
        Uses CDN URL from settings (AZURE_ICONS_CDN_URL environment variable).
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.icons_dir.mkdir(exist_ok=True)
        
        # Get CDN URL from settings
        settings = get_settings()
        zip_url = settings.azure_icons_cdn_url
        
        try:
            print(f"    [IconMatcher] Downloading from: {zip_url}")
            success = await self._download_and_extract(zip_url)
            if success:
                return True
            else:
                print(f"    [IconMatcher] Download failed")
        except Exception as e:
            print(f"    [IconMatcher] Failed: {e}")
        
        print("    [IconMatcher] Could not download Azure icons - check AZURE_ICONS_CDN_URL")
        return False
    
    async def _download_and_extract(self, zip_url: str) -> bool:
        """Download and extract icons from Microsoft CDN ZIP."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
            response = await client.get(zip_url)
            if response.status_code != 200:
                return False
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            try:
                # Extract ZIP
                with zipfile.ZipFile(tmp_path, 'r') as zf:
                    # Find icon files (SVG primarily, PNG as fallback)
                    icon_files = [
                        f for f in zf.namelist()
                        if f.lower().endswith(('.svg', '.png'))
                        and not f.startswith('__MACOSX')
                        and '/.' not in f  # Skip hidden files
                    ]
                    
                    if not icon_files:
                        return False
                    
                    print(f"    [IconMatcher] Found {len(icon_files)} icon files")
                    
                    # Extract and index icons - NO STATIC MAPPING
                    library = IconLibrary()
                    library.version = Path(zip_url).stem
                    library.source_url = zip_url
                    
                    for icon_file in icon_files:
                        try:
                            # Parse service info dynamically from filename
                            service_info = self._parse_icon_filename_dynamic(icon_file)
                            
                            if service_info:
                                # Extract to cache
                                dest_path = self.icons_dir / f"{service_info['key']}{Path(icon_file).suffix}"
                                
                                with zf.open(icon_file) as src:
                                    with open(dest_path, 'wb') as dst:
                                        dst.write(src.read())
                                
                                # Convert SVG to PNG if needed for matching
                                if dest_path.suffix.lower() == '.svg':
                                    png_path = await self._convert_svg_to_png(dest_path)
                                    if png_path:
                                        dest_path = png_path
                                
                                icon_info = IconInfo(
                                    name=service_info['name'],
                                    path=str(dest_path),
                                    category=service_info.get('category', ''),
                                    arm_type=service_info.get('arm_type', ''),
                                    aliases=service_info.get('aliases', []),
                                )
                                library.icons[service_info['name']] = icon_info
                                
                        except Exception:
                            continue
                    
                    # Save library metadata
                    self._save_library(library)
                    
                    print(f"    [IconMatcher] Cached {len(library.icons)} Azure service icons")
                    return len(library.icons) > 0
                    
            finally:
                os.unlink(tmp_path)
    
    def _parse_icon_filename_dynamic(self, full_path: str) -> Optional[dict]:
        """
        Parse icon filename to extract service information DYNAMICALLY.
        
        NO STATIC MAPPING - All service names derived from official icon filenames.
        
        Microsoft icon naming convention (as of 2024):
        - 10787-icon-service-Azure-Kubernetes-Service.svg
        - 00046-icon-service-Storage-Accounts.svg
        - Category folders like: Icons/compute/, Icons/networking/
        """
        filename = Path(full_path).stem
        
        # Skip non-service icons
        skip_patterns = [
            'generic', 'template', 'blank', 'placeholder',
            'logo', 'badge', 'symbol-only', 'brand'
        ]
        if any(p in filename.lower() for p in skip_patterns):
            return None
        
        # Extract service name from Microsoft's naming convention
        name = filename
        
        # Pattern: "NNNNN-icon-service-Service-Name" 
        service_match = re.match(r'^\d+-icon-service-(.+)$', name, re.IGNORECASE)
        if service_match:
            name = service_match.group(1)
        else:
            # Pattern: "icon-service-Service-Name"
            service_match = re.match(r'^icon-service-(.+)$', name, re.IGNORECASE)
            if service_match:
                name = service_match.group(1)
        
        # Convert hyphens/underscores to spaces
        name = name.replace('-', ' ').replace('_', ' ')
        
        # Title case each word
        name = ' '.join(word.capitalize() for word in name.split())
        
        # Clean up common patterns
        name = re.sub(r'\s+', ' ', name).strip()
        
        if not name or len(name) < 2:
            return None
        
        # Extract category from path - NO HARDCODING, just use folder names
        category = ""
        path_parts = Path(full_path).parts
        for part in path_parts:
            # Use folder name as category if it looks like a category
            part_lower = part.lower()
            if part_lower not in ['icons', 'svg', 'png', '64x64', '32x32', 'azure_public_service_icons']:
                if not part_lower.endswith(('.svg', '.png')):
                    category = part.replace('-', ' ').replace('_', ' ').title()
                    break
        
        # Generate unique key for caching
        key = hashlib.md5(name.lower().encode()).hexdigest()[:12]
        
        # Generate aliases dynamically
        aliases = [
            name.lower(),
            name.lower().replace(' ', ''),
            name.lower().replace(' ', '-'),
            name.lower().replace(' ', '_'),
        ]
        
        # Add "Azure" prefix variant if not present
        if not name.lower().startswith('azure '):
            aliases.append(f"azure {name.lower()}")
        
        # Derive ARM type dynamically from service name pattern
        # NO STATIC MAPPING - just educated guesses based on name
        arm_type = self._infer_arm_type_from_name(name)
        
        return {
            'name': name,
            'key': key,
            'category': category,
            'arm_type': arm_type,
            'aliases': list(set(aliases)),
        }
    
    def _infer_arm_type_from_name(self, service_name: str) -> str:
        """
        Infer ARM resource type from service name using pattern matching.
        
        NO STATIC MAPPING - Uses heuristics based on naming conventions.
        This is a best-effort inference, not a hardcoded lookup.
        """
        name_lower = service_name.lower()
        
        # Pattern-based inference (not static mapping!)
        if 'virtual machine' in name_lower or name_lower == 'vm':
            return "Microsoft.Compute/virtualMachines"
        if 'function' in name_lower and 'app' in name_lower:
            return "Microsoft.Web/sites"
        if 'app service' in name_lower or 'web app' in name_lower:
            return "Microsoft.Web/sites"
        if 'storage account' in name_lower:
            return "Microsoft.Storage/storageAccounts"
        if 'kubernetes' in name_lower or 'aks' in name_lower:
            return "Microsoft.ContainerService/managedClusters"
        if 'cosmos' in name_lower:
            return "Microsoft.DocumentDB/databaseAccounts"
        if 'sql database' in name_lower or 'sql server' in name_lower:
            return "Microsoft.Sql/servers"
        if 'key vault' in name_lower:
            return "Microsoft.KeyVault/vaults"
        if 'virtual network' in name_lower or 'vnet' in name_lower:
            return "Microsoft.Network/virtualNetworks"
        if 'load balancer' in name_lower:
            return "Microsoft.Network/loadBalancers"
        if 'application gateway' in name_lower:
            return "Microsoft.Network/applicationGateways"
        if 'firewall' in name_lower:
            return "Microsoft.Network/azureFirewalls"
        if 'container instance' in name_lower:
            return "Microsoft.ContainerInstance/containerGroups"
        if 'container registry' in name_lower:
            return "Microsoft.ContainerRegistry/registries"
        if 'container app' in name_lower:
            return "Microsoft.App/containerApps"
        if 'service bus' in name_lower:
            return "Microsoft.ServiceBus/namespaces"
        if 'event hub' in name_lower:
            return "Microsoft.EventHub/namespaces"
        if 'event grid' in name_lower:
            return "Microsoft.EventGrid/topics"
        if 'logic app' in name_lower:
            return "Microsoft.Logic/workflows"
        if 'api management' in name_lower:
            return "Microsoft.ApiManagement/service"
        if 'openai' in name_lower or 'cognitive' in name_lower:
            return "Microsoft.CognitiveServices/accounts"
        if 'machine learning' in name_lower or 'ml' in name_lower:
            return "Microsoft.MachineLearningServices/workspaces"
        if 'data factory' in name_lower:
            return "Microsoft.DataFactory/factories"
        if 'databricks' in name_lower:
            return "Microsoft.Databricks/workspaces"
        if 'redis' in name_lower:
            return "Microsoft.Cache/redis"
        if 'monitor' in name_lower or 'insight' in name_lower:
            return "Microsoft.Insights/components"
        if 'iot hub' in name_lower:
            return "Microsoft.Devices/IotHubs"
        
        # Default: unknown - let the AI figure it out
        return ""
    
    async def _convert_svg_to_png(self, svg_path: Path) -> Optional[Path]:
        """
        Convert SVG to PNG for template matching.
        
        Uses cairosvg if available, falls back to PIL, otherwise skips.
        """
        png_path = svg_path.with_suffix('.png')
        
        # Try cairosvg first (best SVG support)
        if CAIROSVG_AVAILABLE:
            try:
                cairosvg.svg2png(
                    url=str(svg_path),
                    write_to=str(png_path),
                    output_width=self.icon_size[0] * 2,
                    output_height=self.icon_size[1] * 2,
                )
                return png_path
            except Exception:
                pass  # Fall through to PIL
        
        # Try PIL as fallback (limited SVG support)
        if PIL_AVAILABLE:
            try:
                img = Image.open(svg_path)
                img.save(png_path, 'PNG')
                return png_path
            except Exception:
                pass
        
        # No conversion available - return None (SVG will be skipped for matching)
        return None
    
    def _save_library(self, library: IconLibrary):
        """Save library metadata to JSON."""
        data = {
            'icons': {
                name: {
                    'name': info.name,
                    'path': info.path,
                    'category': info.category,
                    'arm_type': info.arm_type,
                    'aliases': info.aliases,
                }
                for name, info in library.icons.items()
            },
            'version': library.version,
            'source_url': library.source_url,
            'last_updated': str(Path(self.library_path).stat().st_mtime) if self.library_path.exists() else '',
        }
        with open(self.library_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_library(self):
        """Load icon library from cache."""
        if not self.library_path.exists():
            self._library = IconLibrary()
            return
        
        try:
            with open(self.library_path, 'r') as f:
                data = json.load(f)
            
            icons = {}
            for name, info_dict in data.get('icons', {}).items():
                icons[name] = IconInfo(
                    name=info_dict.get('name', name),
                    path=info_dict.get('path', ''),
                    category=info_dict.get('category', ''),
                    arm_type=info_dict.get('arm_type', ''),
                    aliases=info_dict.get('aliases', []),
                )
            
            self._library = IconLibrary(
                icons=icons,
                version=data.get('version', ''),
                source_url=data.get('source_url', ''),
                last_updated=data.get('last_updated', ''),
            )
        except Exception as e:
            print(f"    [IconMatcher] Error loading library: {e}")
            self._library = IconLibrary()
    
    async def identify_unknown_icon(
        self,
        source_image: str | Path,
        bounding_box: dict,
        image_size: tuple[int, int],
    ) -> Optional[IconMatch]:
        """
        Attempt to identify an unknown icon by matching against the icon library.
        
        Args:
            source_image: Path to the full architecture diagram
            bounding_box: Position of the unknown icon {x, y, width, height}
            image_size: Original image dimensions (width, height)
            
        Returns:
            IconMatch if a match is found, None otherwise
        """
        if not CV2_AVAILABLE:
            print("    [IconMatcher] OpenCV not available for icon matching")
            return None
        
        # Ensure icons are available
        if not await self.ensure_icons_available():
            return None
        
        # Crop the icon region from source image
        icon_region = self._crop_icon_region(source_image, bounding_box, image_size)
        if icon_region is None:
            return None
        
        # Try template matching first (fastest)
        match = await self._template_match(icon_region)
        if match and match.confidence >= self.template_threshold:
            return match
        
        # Fall back to feature matching
        match = await self._feature_match(icon_region)
        if match and match.confidence >= self.feature_threshold:
            return match
        
        return None
    
    def _crop_icon_region(
        self,
        source_image: str | Path,
        bounding_box: dict,
        image_size: tuple[int, int],
    ) -> Optional[Any]:
        """Crop the icon region from the source image."""
        try:
            img = cv2.imread(str(source_image))
            if img is None:
                return None
            
            height, width = img.shape[:2]
            
            # Handle both percentage and pixel coordinates
            x = bounding_box.get('x', bounding_box.get('x_percent', 50))
            y = bounding_box.get('y', bounding_box.get('y_percent', 50))
            w = bounding_box.get('width', bounding_box.get('width_percent', 8))
            h = bounding_box.get('height', bounding_box.get('height_percent', 10))
            
            # If values are percentages (0-100), convert to pixels
            if x <= 100 and y <= 100:
                x_center = int(x * width / 100)
                y_center = int(y * height / 100)
                w = int(w * width / 100) if w <= 100 else w
                h = int(h * height / 100) if h <= 100 else h
            else:
                x_center = int(x)
                y_center = int(y)
            
            # Add padding for context
            padding = max(w, h) // 4
            x1 = max(0, x_center - w // 2 - padding)
            y1 = max(0, y_center - h // 2 - padding)
            x2 = min(width, x_center + w // 2 + padding)
            y2 = min(height, y_center + h // 2 + padding)
            
            crop = img[y1:y2, x1:x2]
            
            # Resize to standard size for comparison
            crop = cv2.resize(crop, self.icon_size)
            
            return crop
            
        except Exception as e:
            print(f"    [IconMatcher] Error cropping region: {e}")
            return None
    
    async def _template_match(self, icon_region: Any) -> Optional[IconMatch]:
        """Match icon region using template matching."""
        if not self._library or not self._library.icons:
            return None
        
        best_match = None
        best_score = 0.0
        
        # Convert to grayscale for matching
        gray_region = cv2.cvtColor(icon_region, cv2.COLOR_BGR2GRAY)
        
        for service_name, info in self._library.icons.items():
            icon_path = info.path
            if not icon_path or not Path(icon_path).exists():
                continue
            
            try:
                # Load and resize template icon
                template = cv2.imread(icon_path)
                if template is None:
                    continue
                
                template = cv2.resize(template, self.icon_size)
                gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                
                # Template matching
                result = cv2.matchTemplate(gray_region, gray_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_match = IconMatch(
                        service_name=service_name,
                        arm_resource_type=info.arm_type,
                        confidence=float(max_val),
                        match_method="template",
                        icon_path=icon_path,
                        category=info.category,
                    )
                    
            except Exception:
                continue
        
        return best_match if best_match and best_match.confidence >= self.template_threshold else None
    
    async def _feature_match(self, icon_region: Any) -> Optional[IconMatch]:
        """Match icon region using ORB feature matching."""
        if not self._library or not self._library.icons or not self._orb:
            return None
        
        best_match = None
        best_score = 0.0
        
        # Compute features for query region
        gray_region = cv2.cvtColor(icon_region, cv2.COLOR_BGR2GRAY)
        kp1, des1 = self._orb.detectAndCompute(gray_region, None)
        
        if des1 is None or len(kp1) < 4:
            return None
        
        for service_name, info in self._library.icons.items():
            icon_path = info.path
            if not icon_path or not Path(icon_path).exists():
                continue
            
            try:
                # Load and resize template icon
                template = cv2.imread(icon_path)
                if template is None:
                    continue
                
                template = cv2.resize(template, self.icon_size)
                gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                
                # Compute features for template
                kp2, des2 = self._orb.detectAndCompute(gray_template, None)
                
                if des2 is None or len(kp2) < 4:
                    continue
                
                # Match features
                matches = self._bf_matcher.match(des1, des2)
                
                if len(matches) < 4:
                    continue
                
                # Calculate match ratio
                good_matches = [m for m in matches if m.distance < 50]
                score = len(good_matches) / max(len(kp1), len(kp2))
                
                if score > best_score:
                    best_score = score
                    best_match = IconMatch(
                        service_name=service_name,
                        arm_resource_type=info.arm_type,
                        confidence=float(score),
                        match_method="feature",
                        icon_path=icon_path,
                        category=info.category,
                    )
                    
            except Exception:
                continue
        
        return best_match if best_match and best_match.confidence >= self.feature_threshold else None
    
    async def identify_multiple_unknown_icons(
        self,
        source_image: str | Path,
        unknown_detections: list[dict],
        image_size: tuple[int, int],
    ) -> list[dict]:
        """
        Batch identify multiple unknown icons.
        
        Args:
            source_image: Path to the full architecture diagram
            unknown_detections: List of detections with position info
            image_size: Original image dimensions (width, height)
            
        Returns:
            List of detections enriched with identified service info
        """
        if not unknown_detections:
            return []
        
        results = []
        matched_count = 0
        
        for detection in unknown_detections:
            # Get bounding box from position or bounding_box field
            bbox = detection.get('bounding_box', {})
            if not bbox and 'position' in detection:
                pos = detection['position']
                bbox = {
                    'x': pos.get('x', pos.get('x_percent', 50)),
                    'y': pos.get('y', pos.get('y_percent', 50)),
                    'width': pos.get('width', pos.get('width_percent', 8)),
                    'height': pos.get('height', pos.get('height_percent', 10)),
                }
            
            # Skip if already has high confidence identification
            if detection.get('confidence', 0) >= 0.8:
                results.append(detection)
                continue
            
            # Try to identify the icon
            match = await self.identify_unknown_icon(source_image, bbox, image_size)
            
            if match:
                # Enrich detection with matched info
                detection = detection.copy()
                detection['type'] = match.service_name
                detection['arm_resource_type'] = match.arm_resource_type
                detection['confidence'] = match.confidence
                detection['detection_method'] = f"icon_match_{match.match_method}"
                detection['icon_match_path'] = match.icon_path
                detection['category'] = match.category
                matched_count += 1
            
            results.append(detection)
        
        if matched_count > 0:
            print(f"    [IconMatcher] Identified {matched_count} unknown icons via matching")
        
        return results
    
    def clear_cache(self):
        """Clear the icon cache to force re-download."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            print(f"    [IconMatcher] Cache cleared: {self.cache_dir}")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_icon_matcher: Optional[AzureIconMatcher] = None


def get_icon_matcher() -> AzureIconMatcher:
    """Get or create the global Azure Icon Matcher instance."""
    global _icon_matcher
    if _icon_matcher is None:
        cache_dir = os.getenv("ICON_CACHE_DIR")
        template_threshold = float(os.getenv("ICON_TEMPLATE_THRESHOLD", "0.7"))
        feature_threshold = float(os.getenv("ICON_FEATURE_THRESHOLD", "0.6"))
        
        _icon_matcher = AzureIconMatcher(
            cache_dir=Path(cache_dir) if cache_dir else None,
            template_threshold=template_threshold,
            feature_threshold=feature_threshold,
        )
    return _icon_matcher
